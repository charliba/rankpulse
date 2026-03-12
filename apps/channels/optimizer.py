"""Campaign Optimizer — OneClickAds-style auto-optimization engine for RankPulse.

Monitors Meta/Google Ads campaigns and takes real actions:
- Pauses ad sets when CPA > threshold or ROAS < minimum
- Reactivates ad sets when metrics improve
- Scales budgets for winning campaigns
- Logs all actions to OptimizerAction model

Works with both Meta Ads and Google Ads via the existing
MetaAdsManager / GoogleAdsManager from RankPulse.

Usage:
    from apps.channels.optimizer import CampaignOptimizer
    optimizer = CampaignOptimizer(channel)
    report = optimizer.run_optimization_cycle()
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from .models import Channel, ChannelCredential, OptimizerAction, OptimizerConfig

logger = logging.getLogger("optimizer")


def _get_meta_manager(channel: Channel):
    """Build MetaAdsManager from channel credentials."""
    from apps.analytics.meta_ads_client import MetaAdsManager
    cred = channel.credentials
    return MetaAdsManager(
        access_token=cred.access_token,
        account_id=cred.account_id,
        app_id=getattr(settings, "META_APP_ID", ""),
        app_secret=getattr(settings, "META_APP_SECRET", ""),
    )


def _get_google_manager(channel: Channel):
    """Build GoogleAdsManager from channel credentials."""
    from apps.analytics.ads_client import GoogleAdsManager
    cred = channel.credentials
    return GoogleAdsManager(
        customer_id=cred.customer_id,
        developer_token=settings.GOOGLE_ADS_DEVELOPER_TOKEN or cred.developer_token,
        client_id=settings.GOOGLE_ADS_CLIENT_ID or cred.client_id,
        client_secret=settings.GOOGLE_ADS_CLIENT_SECRET or cred.client_secret,
        refresh_token=cred.refresh_token,
        login_customer_id=cred.login_customer_id,
    )


class CampaignOptimizer:
    """OneClickAds-style campaign optimization engine for a channel."""

    def __init__(self, channel: Channel):
        self.channel = channel
        self.config = self._get_or_create_config()
        self.platform = channel.platform  # "meta_ads" or "google_ads"
        self._manager = None

    @property
    def manager(self):
        if self._manager is None:
            if self.platform == "meta_ads":
                self._manager = _get_meta_manager(self.channel)
            else:
                self._manager = _get_google_manager(self.channel)
        return self._manager

    def _get_or_create_config(self) -> OptimizerConfig:
        config, _ = OptimizerConfig.objects.get_or_create(channel=self.channel)
        return config

    # ── ACTION LOGGING ──────────────────────────────────────────

    def _log(self, action_type: str, target_type: str, target_id: str,
             target_name: str, reason: str, details: dict | None = None):
        OptimizerAction.objects.create(
            channel=self.channel,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            reason=reason,
            details=details or {},
            mode=self.config.mode,
        )
        logger.info("[%s] %s %s '%s' — %s",
                     self.channel.name, action_type, target_type, target_name, reason)

    # ── DATA COLLECTION (META ADS) ──────────────────────────────

    def _meta_active_campaigns(self) -> list[dict]:
        result = self.manager.list_campaigns()
        if not result.get("success"):
            logger.error("Failed to list campaigns: %s", result.get("error"))
            return []
        return [c for c in result.get("campaigns", []) if c.get("status") == "ACTIVE"]

    def _meta_campaign_insights(self, campaign_id: str) -> dict | None:
        days = self.config.lookback_days
        result = self.manager.get_campaign_insights(campaign_id=campaign_id, days=days)
        if not result.get("success") or not result.get("insights"):
            return None
        return result["insights"][0]

    def _meta_ad_sets(self, campaign_id: str) -> list[dict]:
        result = self.manager.list_ad_sets(campaign_id=campaign_id)
        if not result.get("success"):
            return []
        return result.get("ad_sets", [])

    def _meta_ad_set_insights(self, ad_set_id: str) -> dict | None:
        days = self.config.lookback_days
        result = self.manager.get_ad_set_insights(ad_set_id=ad_set_id, days=days)
        if not result.get("success") or not result.get("insights"):
            return None
        return result["insights"][0]

    # ── EVALUATION LOGIC ────────────────────────────────────────

    def _extract_cpa(self, insights: dict) -> float | None:
        """Extract CPA from platform insights."""
        cpa_map = insights.get("cost_per_action", {})
        for action_type in [
            "offsite_conversion.fb_pixel_purchase", "purchase", "lead",
            "offsite_conversion.fb_pixel_lead",
            "onsite_conversion.messaging_conversation_started_7d",
            "link_click",
        ]:
            if action_type in cpa_map:
                return cpa_map[action_type]

        spend = insights.get("spend", 0)
        actions = insights.get("actions", {})
        total_actions = sum(actions.values()) if isinstance(actions, dict) else 0
        if spend > 0 and total_actions > 0:
            return spend / total_actions
        return None

    def _extract_roas(self, insights: dict) -> float | None:
        sale_value = float(self.config.sale_value) if self.config.sale_value else None
        if not sale_value:
            return None
        spend = insights.get("spend", 0)
        if spend <= 0:
            return None
        actions = insights.get("actions", {})
        conversions = 0
        for at in ["purchase", "offsite_conversion.fb_pixel_purchase",
                    "lead", "offsite_conversion.fb_pixel_lead"]:
            conversions += actions.get(at, 0) if isinstance(actions, dict) else 0
        if conversions <= 0:
            return None
        return (conversions * sale_value) / spend

    def _should_pause(self, insights: dict) -> tuple[bool, str]:
        spend = insights.get("spend", 0)
        min_spend = float(self.config.min_spend_to_evaluate)
        if spend < min_spend:
            return False, f"spend R${spend:.2f} < min R${min_spend:.2f}"

        optimize_by = self.config.optimize_by

        if optimize_by == "cpa":
            cpa_max = float(self.config.cpa_max) if self.config.cpa_max else None
            if cpa_max is None:
                return False, "no cpa_max set"
            cpa = self._extract_cpa(insights)
            if cpa is None:
                if self.config.pause_behavior == "flexible":
                    if spend < cpa_max * 2:
                        return False, f"flexible: spend R${spend:.2f} < 2x CPA max R${cpa_max * 2:.2f}"
                if spend >= cpa_max:
                    return True, f"CPA undefined, spend R${spend:.2f} >= max R${cpa_max:.2f}"
                return False, f"no conversions, spend R${spend:.2f} < max R${cpa_max:.2f}"
            if cpa > cpa_max:
                return True, f"CPA R${cpa:.2f} > max R${cpa_max:.2f}"
            return False, f"CPA R${cpa:.2f} OK (max R${cpa_max:.2f})"

        elif optimize_by == "roas":
            roas_min = float(self.config.roas_min) if self.config.roas_min else None
            if roas_min is None:
                return False, "no roas_min set"
            roas = self._extract_roas(insights)
            if roas is None:
                sv = float(self.config.sale_value) if self.config.sale_value else 100
                if spend >= sv / roas_min:
                    return True, f"ROAS undefined, spend R${spend:.2f} too high"
                return False, "ROAS undefined, insufficient data"
            if roas < roas_min:
                return True, f"ROAS {roas:.2f}x < min {roas_min:.2f}x"
            return False, f"ROAS {roas:.2f}x OK (min {roas_min:.2f}x)"

        return False, "unknown optimize_by"

    def _should_scale(self, insights: dict) -> tuple[bool, str, float]:
        multiplier = 1.2 if self.config.scale_behavior == "conservative" else 1.5
        optimize_by = self.config.optimize_by

        if optimize_by == "cpa":
            cpa_max = float(self.config.cpa_max) if self.config.cpa_max else None
            if not cpa_max:
                return False, "no cpa_max set", 1.0
            cpa = self._extract_cpa(insights)
            if cpa is None:
                return False, "no CPA data", 1.0
            if cpa < cpa_max * 0.6:
                return True, f"CPA R${cpa:.2f} well below max R${cpa_max:.2f}", multiplier

        elif optimize_by == "roas":
            roas_min = float(self.config.roas_min) if self.config.roas_min else None
            if not roas_min:
                return False, "no roas_min", 1.0
            roas = self._extract_roas(insights)
            if roas is None:
                return False, "no ROAS data", 1.0
            if roas > roas_min * 1.5:
                return True, f"ROAS {roas:.2f}x well above min {roas_min:.2f}x", multiplier

        return False, "not eligible", 1.0

    # ── META ADS ACTIONS ────────────────────────────────────────

    def _pause_ad_set(self, ad_set_id: str, name: str, reason: str) -> bool:
        if self.config.mode != "active":
            self._log("WOULD_PAUSE", "ad_set", ad_set_id, name, reason)
            return False
        result = self.manager.update_ad_set_status(ad_set_id, "PAUSED")
        if result.get("success"):
            self._log("PAUSED", "ad_set", ad_set_id, name, reason)
            return True
        self._log("PAUSE_FAILED", "ad_set", ad_set_id, name,
                  f"{reason} — error: {result.get('error')}")
        return False

    def _reactivate_ad_set(self, ad_set_id: str, name: str, reason: str) -> bool:
        if self.config.mode != "active":
            self._log("WOULD_REACTIVATE", "ad_set", ad_set_id, name, reason)
            return False
        result = self.manager.update_ad_set_status(ad_set_id, "ACTIVE")
        if result.get("success"):
            self._log("REACTIVATED", "ad_set", ad_set_id, name, reason)
            return True
        self._log("REACTIVATE_FAILED", "ad_set", ad_set_id, name,
                  f"{reason} — error: {result.get('error')}")
        return False

    def _pause_campaign(self, campaign_id: str, name: str, reason: str) -> bool:
        if self.config.mode != "active":
            self._log("WOULD_PAUSE", "campaign", campaign_id, name, reason)
            return False
        result = self.manager.update_campaign_status(campaign_id, "PAUSED")
        if result.get("success"):
            self._log("PAUSED", "campaign", campaign_id, name, reason)
            return True
        self._log("PAUSE_FAILED", "campaign", campaign_id, name,
                  f"{reason} — error: {result.get('error')}")
        return False

    def _scale_budget(self, campaign_id: str, name: str,
                      current_budget: float, multiplier: float, reason: str) -> bool:
        new_budget = current_budget * multiplier
        cap = float(self.config.daily_budget_cap) if self.config.daily_budget_cap else None
        if cap and new_budget > cap:
            new_budget = cap
            reason += f" (capped at R${cap:.2f})"

        if self.config.mode != "active":
            self._log("WOULD_SCALE", "campaign", campaign_id, name,
                      f"{reason} — R${current_budget:.2f} → R${new_budget:.2f}")
            return False

        try:
            from facebook_business.adobjects.campaign import Campaign
            self.manager._ensure_init()
            campaign = Campaign(campaign_id)
            campaign.api_update(params={"daily_budget": int(new_budget * 100)})
            self._log("SCALED", "campaign", campaign_id, name,
                      f"{reason} — R${current_budget:.2f} → R${new_budget:.2f}")
            return True
        except Exception as exc:
            self._log("SCALE_FAILED", "campaign", campaign_id, name,
                      f"{reason} — error: {exc}")
            return False

    # ── MONTHLY BUDGET CHECK ────────────────────────────────────

    def _check_monthly_budget(self) -> tuple[bool, float, float]:
        limit = float(self.config.monthly_budget_limit) if self.config.monthly_budget_limit else 0
        if not limit:
            return False, 0, 0
        try:
            overview = self.manager.get_account_info()
            if not overview.get("success"):
                return False, 0, limit
            spent = overview.get("spend_today", 0) * 30  # rough estimate
            return spent >= limit, spent, limit
        except Exception:
            return False, 0, limit

    # ── MAIN OPTIMIZATION CYCLE ─────────────────────────────────

    def run_optimization_cycle(self) -> dict:
        """Execute a full optimization cycle. Returns a report dict."""
        report = {
            "channel": self.channel.name,
            "platform": self.platform,
            "timestamp": timezone.now().isoformat(),
            "mode": self.config.mode,
            "enabled": self.config.enabled,
            "campaigns_evaluated": 0,
            "ad_sets_evaluated": 0,
            "actions_count": 0,
            "summary": "",
        }

        if not self.config.enabled:
            report["summary"] = "Optimizer disabled"
            return report

        if self.platform != "meta_ads":
            report["summary"] = "Google Ads optimizer coming soon (developer token pending)"
            return report

        # Monthly budget check
        over_limit, monthly_spent, monthly_limit = self._check_monthly_budget()
        if over_limit:
            report["summary"] = f"Monthly limit reached: R${monthly_spent:.2f} / R${monthly_limit:.2f}"
            for camp in self._meta_active_campaigns():
                self._pause_campaign(camp["id"], camp["name"],
                                     f"Monthly budget R${monthly_limit:.2f} reached")
            report["actions_count"] = OptimizerAction.objects.filter(
                channel=self.channel,
                executed_at__gte=timezone.now().replace(hour=0, minute=0, second=0),
            ).count()
            return report

        # Evaluate active campaigns
        campaigns = self._meta_active_campaigns()
        report["campaigns_evaluated"] = len(campaigns)
        excluded_campaigns = self.config.excluded_campaigns or []
        excluded_ad_sets = self.config.excluded_ad_sets or []

        for camp in campaigns:
            cid = camp["id"]
            cname = camp["name"]

            if cid in excluded_campaigns:
                self._log("SKIPPED", "campaign", cid, cname, "excluded")
                continue
            if "[manual]" in cname.lower():
                self._log("SKIPPED", "campaign", cid, cname, "[manual] tag")
                continue

            camp_insights = self._meta_campaign_insights(cid)
            ad_sets = self._meta_ad_sets(cid)
            active_sets = [s for s in ad_sets if s.get("status") == "ACTIVE"]
            paused_sets = [s for s in ad_sets if s.get("status") == "PAUSED"]

            # Evaluate active ad sets for pause
            for ad_set in active_sets:
                asid = ad_set["id"]
                asname = ad_set["name"]
                report["ad_sets_evaluated"] += 1

                if asid in excluded_ad_sets or "[manual]" in asname.lower():
                    self._log("SKIPPED", "ad_set", asid, asname, "excluded")
                    continue

                insights = self._meta_ad_set_insights(asid)
                if not insights:
                    self._log("NO_DATA", "ad_set", asid, asname, "no insights")
                    continue

                should_pause, reason = self._should_pause(insights)
                if should_pause:
                    self._pause_ad_set(asid, asname, reason)

            # Budget scaling for the campaign
            if camp_insights:
                should_scale, scale_reason, mult = self._should_scale(camp_insights)
                if should_scale:
                    budget = camp.get("daily_budget") or 0
                    if budget > 0:
                        self._scale_budget(cid, cname, budget, mult, scale_reason)

            # Check paused ad sets for reactivation
            for ad_set in paused_sets:
                asid = ad_set["id"]
                asname = ad_set["name"]
                if "[manual]" in asname.lower():
                    continue
                insights = self._meta_ad_set_insights(asid)
                if insights:
                    still_bad, reason = self._should_pause(insights)
                    if not still_bad:
                        self._reactivate_ad_set(asid, asname, f"Metrics improved: {reason}")

        report["actions_count"] = OptimizerAction.objects.filter(
            channel=self.channel,
            executed_at__gte=timezone.now().replace(hour=0, minute=0, second=0),
        ).count()
        report["summary"] = (
            f"Evaluated {report['campaigns_evaluated']} campaigns, "
            f"{report['ad_sets_evaluated']} ad sets. "
            f"{report['actions_count']} actions today."
        )
        return report

    # ── STATUS CHECK (read-only) ────────────────────────────────

    def get_status(self) -> dict:
        """Quick status — shows what the optimizer WOULD do (monitor mode)."""
        if self.platform != "meta_ads":
            return {"channel": self.channel.name, "error": "Google Ads optimizer coming soon"}

        campaigns = self._meta_active_campaigns()
        evaluations = []

        for camp in campaigns[:10]:
            cid = camp["id"]
            insights = self._meta_campaign_insights(cid)
            if not insights:
                continue

            cpa = self._extract_cpa(insights)
            roas = self._extract_roas(insights)
            should_pause, reason = self._should_pause(insights)
            should_scale, scale_reason, mult = self._should_scale(insights)

            evaluations.append({
                "campaign_id": cid,
                "campaign_name": camp["name"],
                "status": camp["status"],
                "spend": insights.get("spend", 0),
                "impressions": insights.get("impressions", 0),
                "clicks": insights.get("clicks", 0),
                "cpa": cpa,
                "roas": roas,
                "would_pause": should_pause,
                "pause_reason": reason,
                "would_scale": should_scale,
                "scale_reason": scale_reason,
                "daily_budget": camp.get("daily_budget"),
            })

        return {
            "channel": self.channel.name,
            "config": {
                "enabled": self.config.enabled,
                "mode": self.config.mode,
                "optimize_by": self.config.optimize_by,
                "cpa_max": float(self.config.cpa_max) if self.config.cpa_max else None,
                "roas_min": float(self.config.roas_min) if self.config.roas_min else None,
            },
            "campaigns": evaluations,
            "total_campaigns": len(campaigns),
        }
