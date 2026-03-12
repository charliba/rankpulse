"""Meta Ads API Client — Campaign, Ad Set, Ad, and Insights management.

Manages Meta (Facebook/Instagram) Ads campaigns remotely: create/update
campaigns, ad sets, ads, and retrieve performance insights.

Reference: https://developers.facebook.com/docs/marketing-apis

Requirements:
    - facebook-business pip package
    - Meta App with ads_management + ads_read permissions
    - Long-lived access token or system user token
    - Ad Account ID (format: act_XXXXXXXXX)
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def _init_api(access_token: str, app_id: str = "", app_secret: str = ""):
    """Initialize the Facebook Ads API with credentials."""
    from facebook_business.api import FacebookAdsApi

    FacebookAdsApi.init(
        app_id=app_id,
        app_secret=app_secret,
        access_token=access_token,
    )


class MetaAdsManager:
    """Manages Meta Ads campaigns, ad sets, ads, and insights.

    Usage:
        mgr = MetaAdsManager(
            access_token="EAAxxxx...",
            account_id="act_123456789",
        )
        mgr.list_campaigns()
        mgr.create_campaign("Black Friday", objective="OUTCOME_TRAFFIC")
    """

    def __init__(
        self,
        access_token: str,
        account_id: str,
        app_id: str = "",
        app_secret: str = "",
    ) -> None:
        self.access_token = access_token
        self.account_id = account_id if account_id.startswith("act_") else f"act_{account_id}"
        self.app_id = app_id
        self.app_secret = app_secret
        self._initialized = False

    def _ensure_init(self):
        """Lazy-initialize the API."""
        if not self._initialized:
            _init_api(self.access_token, self.app_id, self.app_secret)
            self._initialized = True

    def _get_account(self):
        """Get the AdAccount object."""
        self._ensure_init()
        from facebook_business.adobjects.adaccount import AdAccount
        return AdAccount(self.account_id)

    # ── Account Info ────────────────────────────────────────────

    def get_account_info(self) -> dict[str, Any]:
        """Get basic ad account information."""
        logger.info("Fetching Meta account info for %s", self.account_id)
        try:
            account = self._get_account()
            fields = [
                "name", "account_id", "account_status", "currency",
                "timezone_name", "balance", "amount_spent",
                "business_name", "business_city", "business_country_code",
            ]
            info = account.api_get(fields=fields)
            status_map = {1: "ACTIVE", 2: "DISABLED", 3: "UNSETTLED", 7: "PENDING_RISK_REVIEW", 9: "IN_GRACE_PERIOD", 101: "PENDING_CLOSURE"}
            return {
                "success": True,
                "id": info.get("account_id", ""),
                "name": info.get("name", ""),
                "status": status_map.get(info.get("account_status", 0), "UNKNOWN"),
                "currency": info.get("currency", ""),
                "timezone": info.get("timezone_name", ""),
                "balance": info.get("balance", "0"),
                "amount_spent": info.get("amount_spent", "0"),
                "business_name": info.get("business_name", ""),
            }
        except Exception as exc:
            logger.error("Meta account info error: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── Campaigns ───────────────────────────────────────────────

    def list_campaigns(self, include_deleted: bool = False) -> dict[str, Any]:
        """List all campaigns in the ad account."""
        logger.info("Listing Meta campaigns for %s", self.account_id)
        try:
            account = self._get_account()
            fields = [
                "name", "objective", "status", "daily_budget",
                "lifetime_budget", "start_time", "stop_time",
                "created_time", "updated_time", "buying_type",
            ]
            params = {}
            if not include_deleted:
                params["filtering"] = [{"field": "effective_status", "operator": "IN", "value": ["ACTIVE", "PAUSED", "ARCHIVED"]}]

            campaigns = account.get_campaigns(fields=fields, params=params)
            result = []
            for c in campaigns:
                result.append({
                    "id": c["id"],
                    "name": c.get("name", ""),
                    "objective": c.get("objective", ""),
                    "status": c.get("status", ""),
                    "daily_budget": float(c.get("daily_budget", 0)) / 100 if c.get("daily_budget") else None,
                    "lifetime_budget": float(c.get("lifetime_budget", 0)) / 100 if c.get("lifetime_budget") else None,
                    "buying_type": c.get("buying_type", ""),
                    "start_time": c.get("start_time", ""),
                    "stop_time": c.get("stop_time", ""),
                    "created_time": c.get("created_time", ""),
                })

            logger.info("Found %d Meta campaigns", len(result))
            return {"success": True, "campaigns": result, "count": len(result)}
        except Exception as exc:
            logger.error("List Meta campaigns error: %s", exc)
            return {"success": False, "error": str(exc)}

    def create_campaign(
        self,
        name: str,
        objective: str = "OUTCOME_TRAFFIC",
        daily_budget_brl: float | None = None,
        lifetime_budget_brl: float | None = None,
        status: str = "PAUSED",
        special_ad_categories: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new campaign.

        Args:
            name: Campaign name.
            objective: OUTCOME_TRAFFIC, OUTCOME_LEADS, OUTCOME_SALES,
                       OUTCOME_AWARENESS, OUTCOME_ENGAGEMENT, OUTCOME_APP_PROMOTION.
            daily_budget_brl: Daily budget in BRL (cents internally).
            lifetime_budget_brl: Lifetime budget in BRL.
            status: ACTIVE or PAUSED (start paused for safety).
            special_ad_categories: EMPLOYMENT, HOUSING, CREDIT, ISSUES_ELECTIONS_POLITICS, or empty list.
        """
        logger.info("Creating Meta campaign '%s' objective=%s", name, objective)
        try:
            account = self._get_account()
            params = {
                "name": name,
                "objective": objective,
                "status": status,
                "special_ad_categories": special_ad_categories or [],
            }
            if daily_budget_brl:
                params["daily_budget"] = int(daily_budget_brl * 100)
            if lifetime_budget_brl:
                params["lifetime_budget"] = int(lifetime_budget_brl * 100)

            campaign = account.create_campaign(params=params)
            logger.info("Meta campaign created: %s", campaign["id"])
            return {
                "success": True,
                "campaign_id": campaign["id"],
                "name": name,
                "objective": objective,
                "status": status,
            }
        except Exception as exc:
            logger.error("Create Meta campaign error: %s", exc)
            return {"success": False, "error": str(exc)}

    def update_campaign_status(
        self, campaign_id: str, status: str = "PAUSED",
    ) -> dict[str, Any]:
        """Update campaign status (ACTIVE, PAUSED, ARCHIVED)."""
        logger.info("Updating Meta campaign %s status to %s", campaign_id, status)
        try:
            self._ensure_init()
            from facebook_business.adobjects.campaign import Campaign
            campaign = Campaign(campaign_id)
            campaign.api_update(params={"status": status})
            return {"success": True, "campaign_id": campaign_id, "status": status}
        except Exception as exc:
            logger.error("Update Meta campaign status error: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── Ad Sets ─────────────────────────────────────────────────

    def list_ad_sets(self, campaign_id: str | None = None) -> dict[str, Any]:
        """List ad sets, optionally filtered by campaign."""
        logger.info("Listing Meta ad sets for %s", self.account_id)
        try:
            account = self._get_account()
            fields = [
                "name", "campaign_id", "status", "daily_budget",
                "lifetime_budget", "start_time", "end_time",
                "billing_event", "optimization_goal",
                "targeting", "bid_amount",
            ]
            params = {}
            if campaign_id:
                params["filtering"] = [{"field": "campaign.id", "operator": "EQUAL", "value": campaign_id}]

            ad_sets = account.get_ad_sets(fields=fields, params=params)
            result = []
            for s in ad_sets:
                targeting = s.get("targeting", {})
                result.append({
                    "id": s["id"],
                    "name": s.get("name", ""),
                    "campaign_id": s.get("campaign_id", ""),
                    "status": s.get("status", ""),
                    "daily_budget": float(s.get("daily_budget", 0)) / 100 if s.get("daily_budget") else None,
                    "lifetime_budget": float(s.get("lifetime_budget", 0)) / 100 if s.get("lifetime_budget") else None,
                    "billing_event": s.get("billing_event", ""),
                    "optimization_goal": s.get("optimization_goal", ""),
                    "bid_amount": float(s.get("bid_amount", 0)) / 100 if s.get("bid_amount") else None,
                    "start_time": s.get("start_time", ""),
                    "end_time": s.get("end_time", ""),
                    "targeting": {
                        "age_min": targeting.get("age_min"),
                        "age_max": targeting.get("age_max"),
                        "genders": targeting.get("genders", []),
                        "geo_locations": targeting.get("geo_locations", {}),
                        "interests": [
                            {"id": i.get("id"), "name": i.get("name")}
                            for i in targeting.get("flexible_spec", [{}])[0].get("interests", [])
                        ] if targeting.get("flexible_spec") else [],
                        "behaviors": [
                            {"id": b.get("id"), "name": b.get("name")}
                            for b in targeting.get("flexible_spec", [{}])[0].get("behaviors", [])
                        ] if targeting.get("flexible_spec") else [],
                        "custom_audiences": [
                            {"id": ca.get("id"), "name": ca.get("name")}
                            for ca in targeting.get("custom_audiences", [])
                        ],
                        "excluded_custom_audiences": [
                            {"id": ca.get("id"), "name": ca.get("name")}
                            for ca in targeting.get("excluded_custom_audiences", [])
                        ],
                        "publisher_platforms": targeting.get("publisher_platforms", []),
                        "facebook_positions": targeting.get("facebook_positions", []),
                        "instagram_positions": targeting.get("instagram_positions", []),
                        "device_platforms": targeting.get("device_platforms", []),
                        "locales": targeting.get("locales", []),
                    },
                })

            return {"success": True, "ad_sets": result, "count": len(result)}
        except Exception as exc:
            logger.error("List Meta ad sets error: %s", exc)
            return {"success": False, "error": str(exc)}

    def create_ad_set(
        self,
        campaign_id: str,
        name: str,
        daily_budget_brl: float = 20.0,
        billing_event: str = "IMPRESSIONS",
        optimization_goal: str = "LINK_CLICKS",
        targeting: dict | None = None,
        status: str = "PAUSED",
        start_time: str | None = None,
    ) -> dict[str, Any]:
        """Create an ad set inside a campaign.

        Args:
            campaign_id: Parent campaign ID.
            name: Ad set name.
            daily_budget_brl: Daily budget in BRL.
            billing_event: IMPRESSIONS, LINK_CLICKS, etc.
            optimization_goal: LINK_CLICKS, IMPRESSIONS, REACH, LANDING_PAGE_VIEWS, etc.
            targeting: Targeting spec dict with geo_locations, age_min/max, interests, etc.
            status: ACTIVE or PAUSED.
            start_time: ISO 8601 start time (optional).
        """
        logger.info("Creating Meta ad set '%s' in campaign %s", name, campaign_id)
        try:
            account = self._get_account()
            default_targeting = {
                "geo_locations": {"countries": ["BR"]},
                "age_min": 18,
                "age_max": 65,
            }
            params = {
                "name": name,
                "campaign_id": campaign_id,
                "daily_budget": int(daily_budget_brl * 100),
                "billing_event": billing_event,
                "optimization_goal": optimization_goal,
                "targeting": targeting or default_targeting,
                "status": status,
            }
            if start_time:
                params["start_time"] = start_time

            ad_set = account.create_ad_set(params=params)
            logger.info("Meta ad set created: %s", ad_set["id"])
            return {
                "success": True,
                "ad_set_id": ad_set["id"],
                "name": name,
                "campaign_id": campaign_id,
                "status": status,
            }
        except Exception as exc:
            logger.error("Create Meta ad set error: %s", exc)
            return {"success": False, "error": str(exc)}

    def update_ad_set_status(
        self, ad_set_id: str, status: str = "PAUSED",
    ) -> dict[str, Any]:
        """Update ad set status."""
        logger.info("Updating Meta ad set %s status to %s", ad_set_id, status)
        try:
            self._ensure_init()
            from facebook_business.adobjects.adset import AdSet
            ad_set = AdSet(ad_set_id)
            ad_set.api_update(params={"status": status})
            return {"success": True, "ad_set_id": ad_set_id, "status": status}
        except Exception as exc:
            logger.error("Update Meta ad set status error: %s", exc)
            return {"success": False, "error": str(exc)}

    def update_ad_set(
        self, ad_set_id: str, **fields,
    ) -> dict[str, Any]:
        """Update ad set fields (targeting, budget, optimization_goal, etc.)."""
        logger.info("Updating Meta ad set %s with fields: %s", ad_set_id, list(fields.keys()))
        try:
            self._ensure_init()
            from facebook_business.adobjects.adset import AdSet
            ad_set = AdSet(ad_set_id)
            # Convert budget from BRL to cents if present
            params = {}
            for k, v in fields.items():
                if k in ("daily_budget", "lifetime_budget") and isinstance(v, (int, float)):
                    params[k] = int(v * 100)
                else:
                    params[k] = v
            ad_set.api_update(params=params)
            return {"success": True, "ad_set_id": ad_set_id, "fields_updated": list(fields.keys())}
        except Exception as exc:
            logger.error("Update Meta ad set error: %s", exc)
            return {"success": False, "error": str(exc)}

    def update_campaign(
        self, campaign_id: str, **fields,
    ) -> dict[str, Any]:
        """Update campaign fields (name, daily_budget, status, etc.)."""
        logger.info("Updating Meta campaign %s with fields: %s", campaign_id, list(fields.keys()))
        try:
            self._ensure_init()
            from facebook_business.adobjects.campaign import Campaign
            campaign = Campaign(campaign_id)
            params = {}
            for k, v in fields.items():
                if k in ("daily_budget", "lifetime_budget") and isinstance(v, (int, float)):
                    params[k] = int(v * 100)
                else:
                    params[k] = v
            campaign.api_update(params=params)
            return {"success": True, "campaign_id": campaign_id, "fields_updated": list(fields.keys())}
        except Exception as exc:
            logger.error("Update Meta campaign error: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── Ads ─────────────────────────────────────────────────────

    def list_ads(self, ad_set_id: str | None = None) -> dict[str, Any]:
        """List ads, optionally filtered by ad set."""
        logger.info("Listing Meta ads for %s", self.account_id)
        try:
            account = self._get_account()
            fields = [
                "name", "adset_id", "campaign_id", "status",
                "creative", "created_time", "updated_time",
            ]
            params = {}
            if ad_set_id:
                params["filtering"] = [{"field": "adset.id", "operator": "EQUAL", "value": ad_set_id}]

            ads = account.get_ads(fields=fields, params=params)
            result = []
            for ad in ads:
                result.append({
                    "id": ad["id"],
                    "name": ad.get("name", ""),
                    "adset_id": ad.get("adset_id", ""),
                    "campaign_id": ad.get("campaign_id", ""),
                    "status": ad.get("status", ""),
                    "creative_id": ad.get("creative", {}).get("id", "") if ad.get("creative") else "",
                    "created_time": ad.get("created_time", ""),
                })

            return {"success": True, "ads": result, "count": len(result)}
        except Exception as exc:
            logger.error("List Meta ads error: %s", exc)
            return {"success": False, "error": str(exc)}

    def create_ad(
        self,
        ad_set_id: str,
        name: str,
        creative_id: str | None = None,
        page_id: str | None = None,
        link_url: str | None = None,
        message: str | None = None,
        image_hash: str | None = None,
        status: str = "PAUSED",
    ) -> dict[str, Any]:
        """Create an ad in an ad set.

        If creative_id is provided, uses existing creative.
        Otherwise creates a new link ad creative from page_id, link_url, message, image_hash.
        """
        logger.info("Creating Meta ad '%s' in ad set %s", name, ad_set_id)
        try:
            account = self._get_account()

            if creative_id:
                creative_spec = {"creative_id": creative_id}
            elif page_id and link_url:
                creative_data = {
                    "object_story_spec": {
                        "page_id": page_id,
                        "link_data": {
                            "link": link_url,
                            "message": message or "",
                        },
                    },
                }
                if image_hash:
                    creative_data["object_story_spec"]["link_data"]["image_hash"] = image_hash

                creative = account.create_ad_creative(params=creative_data)
                creative_spec = {"creative_id": creative["id"]}
            else:
                return {"success": False, "error": "Provide creative_id or (page_id + link_url)."}

            params = {
                "name": name,
                "adset_id": ad_set_id,
                "creative": creative_spec,
                "status": status,
            }

            ad = account.create_ad(params=params)
            logger.info("Meta ad created: %s", ad["id"])
            return {
                "success": True,
                "ad_id": ad["id"],
                "name": name,
                "ad_set_id": ad_set_id,
                "status": status,
            }
        except Exception as exc:
            logger.error("Create Meta ad error: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── Creatives ───────────────────────────────────────────────

    def list_creatives(self) -> dict[str, Any]:
        """List ad creatives in the account."""
        logger.info("Listing Meta creatives for %s", self.account_id)
        try:
            account = self._get_account()
            fields = ["name", "title", "body", "object_story_spec", "thumbnail_url", "status"]
            creatives = account.get_ad_creatives(fields=fields)
            result = []
            for cr in creatives:
                result.append({
                    "id": cr["id"],
                    "name": cr.get("name", ""),
                    "title": cr.get("title", ""),
                    "body": cr.get("body", ""),
                    "thumbnail_url": cr.get("thumbnail_url", ""),
                    "status": cr.get("status", ""),
                })
            return {"success": True, "creatives": result, "count": len(result)}
        except Exception as exc:
            logger.error("List Meta creatives error: %s", exc)
            return {"success": False, "error": str(exc)}

    def upload_image(self, image_path: str) -> dict[str, Any]:
        """Upload an image to the ad account for use in creatives."""
        logger.info("Uploading image to Meta account %s", self.account_id)
        try:
            account = self._get_account()
            from facebook_business.adobjects.adimage import AdImage
            image = AdImage(parent_id=self.account_id)
            image[AdImage.Field.filename] = image_path
            image.remote_create()
            return {
                "success": True,
                "image_hash": image[AdImage.Field.hash],
                "url": image.get("url", ""),
            }
        except Exception as exc:
            logger.error("Upload Meta image error: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── Insights / Performance ──────────────────────────────────

    def get_campaign_insights(
        self,
        campaign_id: str | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get campaign performance insights.

        Args:
            campaign_id: Specific campaign ID, or None for all campaigns.
            days: Number of days to look back.
        """
        logger.info("Fetching Meta campaign insights for %s (days=%d)", self.account_id, days)
        try:
            self._ensure_init()
            since = (date.today() - timedelta(days=days)).isoformat()
            until = date.today().isoformat()

            fields = [
                "campaign_id", "campaign_name", "impressions", "clicks",
                "spend", "reach", "cpc", "cpm", "ctr",
                "actions", "cost_per_action_type",
            ]
            params = {
                "time_range": {"since": since, "until": until},
                "level": "campaign",
            }

            if campaign_id:
                from facebook_business.adobjects.campaign import Campaign
                obj = Campaign(campaign_id)
                insights = obj.get_insights(fields=fields, params=params)
            else:
                account = self._get_account()
                insights = account.get_insights(fields=fields, params=params)

            result = []
            for row in insights:
                actions = {}
                for action in (row.get("actions") or []):
                    actions[action["action_type"]] = int(action["value"])

                cost_per_action = {}
                for cpa in (row.get("cost_per_action_type") or []):
                    cost_per_action[cpa["action_type"]] = float(cpa["value"])

                result.append({
                    "campaign_id": row.get("campaign_id", ""),
                    "campaign_name": row.get("campaign_name", ""),
                    "impressions": int(row.get("impressions", 0)),
                    "clicks": int(row.get("clicks", 0)),
                    "spend": float(row.get("spend", 0)),
                    "reach": int(row.get("reach", 0)),
                    "cpc": float(row.get("cpc", 0)) if row.get("cpc") else None,
                    "cpm": float(row.get("cpm", 0)) if row.get("cpm") else None,
                    "ctr": float(row.get("ctr", 0)) if row.get("ctr") else None,
                    "actions": actions,
                    "cost_per_action": cost_per_action,
                })

            return {"success": True, "insights": result, "count": len(result), "period": f"{since} to {until}"}
        except Exception as exc:
            logger.error("Meta insights error: %s", exc)
            return {"success": False, "error": str(exc)}

    def get_ad_set_insights(
        self,
        ad_set_id: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get ad set performance insights."""
        logger.info("Fetching Meta ad set insights for %s", ad_set_id)
        try:
            self._ensure_init()
            from facebook_business.adobjects.adset import AdSet
            since = (date.today() - timedelta(days=days)).isoformat()
            until = date.today().isoformat()

            fields = [
                "adset_id", "adset_name", "impressions", "clicks",
                "spend", "reach", "cpc", "cpm", "ctr",
            ]
            params = {"time_range": {"since": since, "until": until}}

            ad_set = AdSet(ad_set_id)
            insights = ad_set.get_insights(fields=fields, params=params)

            result = []
            for row in insights:
                result.append({
                    "ad_set_id": row.get("adset_id", ""),
                    "ad_set_name": row.get("adset_name", ""),
                    "impressions": int(row.get("impressions", 0)),
                    "clicks": int(row.get("clicks", 0)),
                    "spend": float(row.get("spend", 0)),
                    "reach": int(row.get("reach", 0)),
                    "cpc": float(row.get("cpc", 0)) if row.get("cpc") else None,
                    "cpm": float(row.get("cpm", 0)) if row.get("cpm") else None,
                    "ctr": float(row.get("ctr", 0)) if row.get("ctr") else None,
                })

            return {"success": True, "insights": result, "count": len(result)}
        except Exception as exc:
            logger.error("Meta ad set insights error: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── Token Management ────────────────────────────────────────

    # ── Deep Audit Data ─────────────────────────────────────────

    def get_ads_with_creatives(self, limit: int = 100) -> dict[str, Any]:
        """Get ads with full creative details (headline, body, CTA, image)."""
        logger.info("Fetching ads with creatives for %s", self.account_id)
        try:
            account = self._get_account()
            fields = [
                "name", "adset_id", "campaign_id", "status",
                "creative", "created_time", "effective_status",
            ]
            params = {
                "filtering": [{"field": "effective_status", "operator": "IN",
                               "value": ["ACTIVE", "PAUSED"]}],
                "limit": limit,
            }
            ads = account.get_ads(fields=fields, params=params)

            result = []
            for ad in ads:
                creative_data = {}
                creative_ref = ad.get("creative")
                if creative_ref and creative_ref.get("id"):
                    try:
                        self._ensure_init()
                        from facebook_business.adobjects.adcreative import AdCreative
                        cr = AdCreative(creative_ref["id"])
                        cr_fields = [
                            "name", "title", "body", "call_to_action_type",
                            "object_story_spec", "thumbnail_url",
                            "effective_object_story_id", "image_url",
                            "link_url", "url_tags",
                        ]
                        cr_data = cr.api_get(fields=cr_fields)
                        oss = cr_data.get("object_story_spec", {})
                        link_data = oss.get("link_data", {})
                        video_data = oss.get("video_data", {})
                        creative_data = {
                            "title": cr_data.get("title", "") or link_data.get("name", ""),
                            "body": cr_data.get("body", "") or link_data.get("message", "") or video_data.get("message", ""),
                            "cta": cr_data.get("call_to_action_type", "") or link_data.get("call_to_action", {}).get("type", ""),
                            "link_url": link_data.get("link", "") or cr_data.get("link_url", ""),
                            "image_url": cr_data.get("image_url", "") or cr_data.get("thumbnail_url", ""),
                            "has_video": bool(video_data),
                            "description": link_data.get("description", ""),
                            "caption": link_data.get("caption", ""),
                        }
                    except Exception:
                        creative_data = {"error": "Could not fetch creative details"}

                result.append({
                    "id": ad["id"],
                    "name": ad.get("name", ""),
                    "adset_id": ad.get("adset_id", ""),
                    "campaign_id": ad.get("campaign_id", ""),
                    "status": ad.get("status", ""),
                    "effective_status": ad.get("effective_status", ""),
                    "creative": creative_data,
                })

            return {"success": True, "ads": result, "count": len(result)}
        except Exception as exc:
            logger.error("Get ads with creatives error: %s", exc)
            return {"success": False, "error": str(exc)}

    def get_demographic_breakdown(self, days: int = 30) -> dict[str, Any]:
        """Get performance breakdown by age and gender."""
        logger.info("Fetching demographic breakdown for %s", self.account_id)
        try:
            account = self._get_account()
            since = (date.today() - timedelta(days=days)).isoformat()
            until = date.today().isoformat()

            fields = [
                "campaign_id", "campaign_name",
                "impressions", "clicks", "spend", "reach",
                "cpc", "ctr", "actions",
            ]
            params = {
                "time_range": {"since": since, "until": until},
                "breakdowns": ["age", "gender"],
                "level": "campaign",
                "filtering": [{"field": "impressions", "operator": "GREATER_THAN", "value": "0"}],
            }
            insights = account.get_insights(fields=fields, params=params)

            result = []
            for row in insights:
                actions = {}
                for a in (row.get("actions") or []):
                    actions[a["action_type"]] = int(a["value"])
                result.append({
                    "campaign_id": row.get("campaign_id", ""),
                    "campaign_name": row.get("campaign_name", ""),
                    "age": row.get("age", ""),
                    "gender": row.get("gender", ""),
                    "impressions": int(row.get("impressions", 0)),
                    "clicks": int(row.get("clicks", 0)),
                    "spend": float(row.get("spend", 0)),
                    "reach": int(row.get("reach", 0)),
                    "cpc": float(row.get("cpc", 0)) if row.get("cpc") else None,
                    "ctr": float(row.get("ctr", 0)) if row.get("ctr") else None,
                    "actions": actions,
                })

            return {"success": True, "data": result, "count": len(result)}
        except Exception as exc:
            logger.error("Demographic breakdown error: %s", exc)
            return {"success": False, "error": str(exc)}

    def get_placement_breakdown(self, days: int = 30) -> dict[str, Any]:
        """Get performance breakdown by placement (feed, stories, reels, etc.)."""
        logger.info("Fetching placement breakdown for %s", self.account_id)
        try:
            account = self._get_account()
            since = (date.today() - timedelta(days=days)).isoformat()
            until = date.today().isoformat()

            fields = [
                "campaign_id", "campaign_name",
                "impressions", "clicks", "spend", "reach",
                "cpc", "cpm", "ctr", "actions",
            ]
            params = {
                "time_range": {"since": since, "until": until},
                "breakdowns": ["publisher_platform", "platform_position"],
                "level": "campaign",
                "filtering": [{"field": "impressions", "operator": "GREATER_THAN", "value": "0"}],
            }
            insights = account.get_insights(fields=fields, params=params)

            result = []
            for row in insights:
                actions = {}
                for a in (row.get("actions") or []):
                    actions[a["action_type"]] = int(a["value"])
                result.append({
                    "campaign_id": row.get("campaign_id", ""),
                    "campaign_name": row.get("campaign_name", ""),
                    "publisher_platform": row.get("publisher_platform", ""),
                    "platform_position": row.get("platform_position", ""),
                    "impressions": int(row.get("impressions", 0)),
                    "clicks": int(row.get("clicks", 0)),
                    "spend": float(row.get("spend", 0)),
                    "reach": int(row.get("reach", 0)),
                    "cpc": float(row.get("cpc", 0)) if row.get("cpc") else None,
                    "cpm": float(row.get("cpm", 0)) if row.get("cpm") else None,
                    "ctr": float(row.get("ctr", 0)) if row.get("ctr") else None,
                    "actions": actions,
                })

            return {"success": True, "data": result, "count": len(result)}
        except Exception as exc:
            logger.error("Placement breakdown error: %s", exc)
            return {"success": False, "error": str(exc)}

    def get_ad_level_insights(self, days: int = 30, limit: int = 50) -> dict[str, Any]:
        """Get ad-level performance insights (which individual ads perform best)."""
        logger.info("Fetching ad-level insights for %s", self.account_id)
        try:
            account = self._get_account()
            since = (date.today() - timedelta(days=days)).isoformat()
            until = date.today().isoformat()

            fields = [
                "ad_id", "ad_name", "adset_id", "adset_name",
                "campaign_id", "campaign_name",
                "impressions", "clicks", "spend", "reach",
                "cpc", "cpm", "ctr", "frequency",
                "actions", "cost_per_action_type",
            ]
            params = {
                "time_range": {"since": since, "until": until},
                "level": "ad",
                "filtering": [{"field": "impressions", "operator": "GREATER_THAN", "value": "0"}],
                "sort": ["spend_descending"],
                "limit": limit,
            }
            insights = account.get_insights(fields=fields, params=params)

            result = []
            for row in insights:
                actions = {}
                for a in (row.get("actions") or []):
                    actions[a["action_type"]] = int(a["value"])
                cost_per_action = {}
                for cpa in (row.get("cost_per_action_type") or []):
                    cost_per_action[cpa["action_type"]] = float(cpa["value"])

                result.append({
                    "ad_id": row.get("ad_id", ""),
                    "ad_name": row.get("ad_name", ""),
                    "adset_id": row.get("adset_id", ""),
                    "adset_name": row.get("adset_name", ""),
                    "campaign_id": row.get("campaign_id", ""),
                    "campaign_name": row.get("campaign_name", ""),
                    "impressions": int(row.get("impressions", 0)),
                    "clicks": int(row.get("clicks", 0)),
                    "spend": float(row.get("spend", 0)),
                    "reach": int(row.get("reach", 0)),
                    "frequency": float(row.get("frequency", 0)) if row.get("frequency") else None,
                    "cpc": float(row.get("cpc", 0)) if row.get("cpc") else None,
                    "cpm": float(row.get("cpm", 0)) if row.get("cpm") else None,
                    "ctr": float(row.get("ctr", 0)) if row.get("ctr") else None,
                    "actions": actions,
                    "cost_per_action": cost_per_action,
                })

            return {"success": True, "data": result, "count": len(result)}
        except Exception as exc:
            logger.error("Ad-level insights error: %s", exc)
            return {"success": False, "error": str(exc)}

    def get_account_overview(self, days: int = 30) -> dict[str, Any]:
        """Get high-level account overview: total spend, reach, frequency."""
        logger.info("Fetching account overview for %s", self.account_id)
        try:
            account = self._get_account()
            since = (date.today() - timedelta(days=days)).isoformat()
            until = date.today().isoformat()

            fields = [
                "impressions", "clicks", "spend", "reach",
                "cpc", "cpm", "ctr", "frequency",
                "actions", "cost_per_action_type",
            ]
            params = {"time_range": {"since": since, "until": until}}
            insights = account.get_insights(fields=fields, params=params)

            for row in insights:
                actions = {}
                for a in (row.get("actions") or []):
                    actions[a["action_type"]] = int(a["value"])
                return {
                    "success": True,
                    "impressions": int(row.get("impressions", 0)),
                    "clicks": int(row.get("clicks", 0)),
                    "spend": float(row.get("spend", 0)),
                    "reach": int(row.get("reach", 0)),
                    "frequency": float(row.get("frequency", 0)) if row.get("frequency") else None,
                    "cpc": float(row.get("cpc", 0)) if row.get("cpc") else None,
                    "cpm": float(row.get("cpm", 0)) if row.get("cpm") else None,
                    "ctr": float(row.get("ctr", 0)) if row.get("ctr") else None,
                    "actions": actions,
                    "period": f"{since} to {until}",
                }

            return {"success": True, "impressions": 0, "spend": 0, "note": "No data for period"}
        except Exception as exc:
            logger.error("Account overview error: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── Token Management ────────────────────────────────────────

    @staticmethod
    def exchange_short_lived_token(
        app_id: str,
        app_secret: str,
        short_lived_token: str,
    ) -> dict[str, Any]:
        """Exchange a short-lived token for a long-lived token (60 days).

        This is called after the OAuth flow returns a short-lived token.
        """
        import requests as http_requests

        try:
            resp = http_requests.get(
                "https://graph.facebook.com/v21.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": app_id,
                    "client_secret": app_secret,
                    "fb_exchange_token": short_lived_token,
                },
                timeout=30,
            )
            data = resp.json()

            if "error" in data:
                return {"success": False, "error": data["error"].get("message", str(data["error"]))}

            return {
                "success": True,
                "access_token": data["access_token"],
                "token_type": data.get("token_type", "bearer"),
                "expires_in": data.get("expires_in", 0),
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}
