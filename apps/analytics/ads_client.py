"""Google Ads API Client — Campaign, Ad Group, Ad, and Budget management.

Manages Google Ads campaigns remotely: create/update campaigns, ad groups,
responsive search ads, keyword targeting, budgets, and conversion tracking.

Reference: https://developers.google.com/google-ads/api/docs/start

Requirements:
    - google-ads pip package
    - OAuth2 credentials (developer token, client ID/secret, refresh token)
    - Google Ads customer ID

Authentication:
    Unlike GA4/GSC (service account), Google Ads API requires OAuth2 with:
    1. Developer token (from MCC → API Center)
    2. OAuth2 client ID + client secret (from Google Cloud Console)
    3. OAuth2 refresh token (obtained via consent flow)
    4. Customer ID (format: 123-456-7890, stored without dashes)
    5. Optional: Login customer ID (MCC account)
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_client(
    developer_token: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    login_customer_id: str = "",
) -> Any:
    """Build a GoogleAdsClient from credentials.

    Args:
        developer_token: Google Ads API developer token.
        client_id: OAuth2 client ID.
        client_secret: OAuth2 client secret.
        refresh_token: OAuth2 refresh token.
        login_customer_id: MCC account ID (optional).

    Returns:
        google.ads.googleads.client.GoogleAdsClient instance.
    """
    from google.ads.googleads.client import GoogleAdsClient

    config = {
        "developer_token": developer_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "use_proto_plus": True,
    }
    if login_customer_id:
        config["login_customer_id"] = login_customer_id.replace("-", "")

    return GoogleAdsClient.load_from_dict(config)


class GoogleAdsManager:
    """Manages Google Ads campaigns, ad groups, ads, keywords, and budgets.

    Usage:
        mgr = GoogleAdsManager(
            customer_id="1798188324",  # numeric, no dashes
            developer_token="...",
            client_id="...",
            client_secret="...",
            refresh_token="...",
        )
        mgr.list_campaigns()
        mgr.create_campaign("Beezle — Programa de Indicação", daily_budget_brl=50.0)
    """

    def __init__(
        self,
        customer_id: str,
        developer_token: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        login_customer_id: str = "",
    ) -> None:
        self.customer_id = customer_id.replace("-", "")
        self.developer_token = developer_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.login_customer_id = login_customer_id
        self._client = None

    @property
    def client(self):
        """Lazy-load the GoogleAdsClient."""
        if self._client is None:
            self._client = _get_client(
                developer_token=self.developer_token,
                client_id=self.client_id,
                client_secret=self.client_secret,
                refresh_token=self.refresh_token,
                login_customer_id=self.login_customer_id,
            )
        return self._client

    def _get_service(self, service_name: str, version: str = "v23"):
        """Get a Google Ads service client."""
        return self.client.get_service(service_name, version=version)

    # ── Account Info ────────────────────────────────────────────

    def get_account_info(self) -> dict[str, Any]:
        """Get basic account information.

        Returns:
            Dict with account name, currency, timezone, etc.
        """
        logger.info("Fetching account info for customer %s", self.customer_id)
        try:
            ga_service = self._get_service("GoogleAdsService")
            query = """
                SELECT
                    customer.id,
                    customer.descriptive_name,
                    customer.currency_code,
                    customer.time_zone,
                    customer.auto_tagging_enabled,
                    customer.manager
                FROM customer
                LIMIT 1
            """
            response = ga_service.search(
                customer_id=self.customer_id, query=query,
            )
            for row in response:
                customer = row.customer
                return {
                    "success": True,
                    "id": str(customer.id),
                    "name": customer.descriptive_name,
                    "currency": customer.currency_code,
                    "timezone": customer.time_zone,
                    "auto_tagging": customer.auto_tagging_enabled,
                    "is_manager": customer.manager,
                }
            return {"success": False, "error": "No customer data returned"}

        except Exception as exc:
            logger.error("Account info error: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── Campaigns ───────────────────────────────────────────────

    def list_campaigns(self, include_removed: bool = False) -> dict[str, Any]:
        """List all campaigns in the account.

        Args:
            include_removed: Include REMOVED campaigns.

        Returns:
            Dict with list of campaigns.
        """
        logger.info("Listing campaigns for customer %s", self.customer_id)
        try:
            ga_service = self._get_service("GoogleAdsService")
            where = "" if include_removed else "WHERE campaign.status != 'REMOVED'"
            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    campaign.status,
                    campaign.advertising_channel_type,
                    campaign.start_date,
                    campaign.end_date,
                    campaign_budget.amount_micros,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value
                FROM campaign
                {where}
                ORDER BY campaign.id
            """
            response = ga_service.search(
                customer_id=self.customer_id, query=query,
            )
            campaigns = []
            for row in response:
                c = row.campaign
                m = row.metrics
                b = row.campaign_budget
                campaigns.append({
                    "id": str(c.id),
                    "name": c.name,
                    "status": c.status.name,
                    "channel_type": c.advertising_channel_type.name,
                    "start_date": c.start_date,
                    "end_date": c.end_date,
                    "daily_budget_brl": b.amount_micros / 1_000_000 if b.amount_micros else 0,
                    "impressions": m.impressions,
                    "clicks": m.clicks,
                    "cost_brl": m.cost_micros / 1_000_000 if m.cost_micros else 0,
                    "conversions": m.conversions,
                    "conversions_value": m.conversions_value,
                })

            logger.info("Found %d campaigns", len(campaigns))
            return {"success": True, "campaigns": campaigns, "count": len(campaigns)}

        except Exception as exc:
            logger.error("List campaigns error: %s", exc)
            return {"success": False, "error": str(exc)}

    def create_campaign_budget(
        self,
        name: str,
        daily_amount_brl: float,
    ) -> str:
        """Create a campaign budget resource.

        Args:
            name: Budget name.
            daily_amount_brl: Daily budget in BRL.

        Returns:
            Resource name of the created budget.
        """
        budget_service = self._get_service("CampaignBudgetService")
        budget_op = self.client.get_type("CampaignBudgetOperation")
        budget = budget_op.create
        budget.name = name
        budget.amount_micros = int(daily_amount_brl * 1_000_000)
        budget.delivery_method = self.client.enums.BudgetDeliveryMethodEnum.STANDARD

        response = budget_service.mutate_campaign_budgets(
            customer_id=self.customer_id,
            operations=[budget_op],
        )
        resource_name = response.results[0].resource_name
        logger.info("Budget created: %s (R$ %.2f/dia)", resource_name, daily_amount_brl)
        return resource_name

    def create_campaign(
        self,
        name: str,
        daily_budget_brl: float = 50.0,
        channel_type: str = "SEARCH",
        bidding_strategy: str = "MAXIMIZE_CONVERSIONS",
        network_settings: dict[str, bool] | None = None,
    ) -> dict[str, Any]:
        """Create a new Search campaign.

        Args:
            name: Campaign name.
            daily_budget_brl: Daily budget in BRL.
            channel_type: "SEARCH", "DISPLAY", etc.
            bidding_strategy: Bidding strategy type.
            network_settings: Network targeting (search, display, partners).

        Returns:
            Dict with created campaign info or error.
        """
        logger.info("Creating campaign: %s (R$ %.2f/dia)", name, daily_budget_brl)
        try:
            # 1. Create budget
            budget_resource = self.create_campaign_budget(
                name=f"Budget — {name}",
                daily_amount_brl=daily_budget_brl,
            )

            # 2. Create campaign
            campaign_service = self._get_service("CampaignService")
            campaign_op = self.client.get_type("CampaignOperation")
            campaign = campaign_op.create

            campaign.name = name
            campaign.campaign_budget = budget_resource
            campaign.status = self.client.enums.CampaignStatusEnum.PAUSED  # Start paused
            campaign.advertising_channel_type = getattr(
                self.client.enums.AdvertisingChannelTypeEnum, channel_type,
            )

            # Bidding strategy
            if bidding_strategy == "MAXIMIZE_CONVERSIONS":
                campaign.maximize_conversions.target_cpa_micros = 0
            elif bidding_strategy == "MAXIMIZE_CLICKS":
                campaign.maximize_clicks.cpc_bid_ceiling_micros = 0
            elif bidding_strategy == "TARGET_CPA":
                campaign.target_cpa.target_cpa_micros = int(30 * 1_000_000)  # R$30 default

            # Network settings
            ns = network_settings or {
                "target_google_search": True,
                "target_search_network": True,
                "target_content_network": False,
            }
            campaign.network_settings.target_google_search = ns.get("target_google_search", True)
            campaign.network_settings.target_search_network = ns.get("target_search_network", True)
            campaign.network_settings.target_content_network = ns.get("target_content_network", False)

            response = campaign_service.mutate_campaigns(
                customer_id=self.customer_id,
                operations=[campaign_op],
            )
            resource_name = response.results[0].resource_name
            logger.info("Campaign created: %s", resource_name)

            return {
                "success": True,
                "resource_name": resource_name,
                "name": name,
                "status": "PAUSED",
                "daily_budget_brl": daily_budget_brl,
                "bidding_strategy": bidding_strategy,
            }

        except Exception as exc:
            logger.error("Create campaign error: %s", exc)
            return {"success": False, "error": str(exc)}

    def update_campaign_status(
        self,
        campaign_id: str,
        status: str = "ENABLED",
    ) -> dict[str, Any]:
        """Update campaign status (ENABLED, PAUSED, REMOVED).

        Args:
            campaign_id: Campaign ID.
            status: New status.

        Returns:
            Dict with result.
        """
        logger.info("Updating campaign %s status to %s", campaign_id, status)
        try:
            campaign_service = self._get_service("CampaignService")
            campaign_op = self.client.get_type("CampaignOperation")
            campaign = campaign_op.update

            campaign.resource_name = (
                self._get_service("CampaignService")
                .campaign_path(self.customer_id, campaign_id)
            )
            campaign.status = getattr(self.client.enums.CampaignStatusEnum, status)

            from google.protobuf import field_mask_pb2
            campaign_op.update_mask = field_mask_pb2.FieldMask(paths=["status"])

            response = campaign_service.mutate_campaigns(
                customer_id=self.customer_id,
                operations=[campaign_op],
            )
            return {
                "success": True,
                "resource_name": response.results[0].resource_name,
                "new_status": status,
            }

        except Exception as exc:
            logger.error("Update campaign status error: %s", exc)
            return {"success": False, "error": str(exc)}

    def update_campaign_budget_amount(
        self,
        campaign_id: str,
        new_daily_budget_brl: float,
    ) -> dict[str, Any]:
        """Update the daily budget for a campaign.

        Args:
            campaign_id: Campaign ID.
            new_daily_budget_brl: New daily budget in BRL.

        Returns:
            Dict with result.
        """
        logger.info(
            "Updating budget for campaign %s to R$ %.2f",
            campaign_id, new_daily_budget_brl,
        )
        try:
            # First, get the budget resource name
            ga_service = self._get_service("GoogleAdsService")
            query = f"""
                SELECT campaign.campaign_budget
                FROM campaign
                WHERE campaign.id = {campaign_id}
            """
            response = ga_service.search(
                customer_id=self.customer_id, query=query,
            )
            budget_resource = None
            for row in response:
                budget_resource = row.campaign.campaign_budget
                break

            if not budget_resource:
                return {"success": False, "error": "Campaign not found"}

            # Update the budget
            budget_service = self._get_service("CampaignBudgetService")
            budget_op = self.client.get_type("CampaignBudgetOperation")
            budget = budget_op.update
            budget.resource_name = budget_resource
            budget.amount_micros = int(new_daily_budget_brl * 1_000_000)

            from google.protobuf import field_mask_pb2
            budget_op.update_mask = field_mask_pb2.FieldMask(paths=["amount_micros"])

            budget_service.mutate_campaign_budgets(
                customer_id=self.customer_id,
                operations=[budget_op],
            )

            return {
                "success": True,
                "campaign_id": campaign_id,
                "new_daily_budget_brl": new_daily_budget_brl,
            }

        except Exception as exc:
            logger.error("Update budget error: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── Ad Groups ───────────────────────────────────────────────

    def list_ad_groups(self, campaign_id: str) -> dict[str, Any]:
        """List ad groups for a campaign.

        Args:
            campaign_id: Campaign ID.

        Returns:
            Dict with list of ad groups.
        """
        logger.info("Listing ad groups for campaign %s", campaign_id)
        try:
            ga_service = self._get_service("GoogleAdsService")
            query = f"""
                SELECT
                    ad_group.id,
                    ad_group.name,
                    ad_group.status,
                    ad_group.type,
                    ad_group.cpc_bid_micros,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions
                FROM ad_group
                WHERE campaign.id = {campaign_id}
                  AND ad_group.status != 'REMOVED'
            """
            response = ga_service.search(
                customer_id=self.customer_id, query=query,
            )
            ad_groups = []
            for row in response:
                ag = row.ad_group
                m = row.metrics
                ad_groups.append({
                    "id": str(ag.id),
                    "name": ag.name,
                    "status": ag.status.name,
                    "type": ag.type_.name,
                    "cpc_bid_brl": ag.cpc_bid_micros / 1_000_000 if ag.cpc_bid_micros else 0,
                    "impressions": m.impressions,
                    "clicks": m.clicks,
                    "cost_brl": m.cost_micros / 1_000_000 if m.cost_micros else 0,
                    "conversions": m.conversions,
                })

            return {"success": True, "ad_groups": ad_groups, "count": len(ad_groups)}

        except Exception as exc:
            logger.error("List ad groups error: %s", exc)
            return {"success": False, "error": str(exc)}

    def create_ad_group(
        self,
        campaign_id: str,
        name: str,
        cpc_bid_brl: float = 2.0,
    ) -> dict[str, Any]:
        """Create an ad group in a campaign.

        Args:
            campaign_id: Campaign ID.
            name: Ad group name.
            cpc_bid_brl: Default CPC bid in BRL.

        Returns:
            Dict with created ad group info.
        """
        logger.info("Creating ad group '%s' in campaign %s", name, campaign_id)
        try:
            ag_service = self._get_service("AdGroupService")
            ag_op = self.client.get_type("AdGroupOperation")
            ag = ag_op.create

            ag.name = name
            ag.campaign = self._get_service("CampaignService").campaign_path(
                self.customer_id, campaign_id,
            )
            ag.status = self.client.enums.AdGroupStatusEnum.ENABLED
            ag.type_ = self.client.enums.AdGroupTypeEnum.SEARCH_STANDARD
            ag.cpc_bid_micros = int(cpc_bid_brl * 1_000_000)

            response = ag_service.mutate_ad_groups(
                customer_id=self.customer_id,
                operations=[ag_op],
            )
            resource_name = response.results[0].resource_name
            logger.info("Ad group created: %s", resource_name)

            return {
                "success": True,
                "resource_name": resource_name,
                "name": name,
                "cpc_bid_brl": cpc_bid_brl,
            }

        except Exception as exc:
            logger.error("Create ad group error: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── Keywords ────────────────────────────────────────────────

    def add_keywords(
        self,
        ad_group_id: str,
        keywords: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Add keywords to an ad group.

        Args:
            ad_group_id: Ad group ID.
            keywords: List of {"text": "...", "match_type": "BROAD|PHRASE|EXACT"}.

        Returns:
            Dict with results.
        """
        logger.info("Adding %d keywords to ad group %s", len(keywords), ad_group_id)
        try:
            criterion_service = self._get_service("AdGroupCriterionService")
            operations = []

            for kw in keywords:
                op = self.client.get_type("AdGroupCriterionOperation")
                criterion = op.create
                criterion.ad_group = self._get_service("AdGroupService").ad_group_path(
                    self.customer_id, ad_group_id,
                )
                criterion.status = self.client.enums.AdGroupCriterionStatusEnum.ENABLED
                criterion.keyword.text = kw["text"]
                criterion.keyword.match_type = getattr(
                    self.client.enums.KeywordMatchTypeEnum,
                    kw.get("match_type", "BROAD"),
                )
                operations.append(op)

            response = criterion_service.mutate_ad_group_criteria(
                customer_id=self.customer_id,
                operations=operations,
            )

            results = [r.resource_name for r in response.results]
            logger.info("Added %d keywords", len(results))
            return {"success": True, "keywords_added": len(results), "resources": results}

        except Exception as exc:
            logger.error("Add keywords error: %s", exc)
            return {"success": False, "error": str(exc)}

    def list_keywords(self, ad_group_id: str) -> dict[str, Any]:
        """List keywords in an ad group.

        Args:
            ad_group_id: Ad group ID.

        Returns:
            Dict with list of keywords.
        """
        try:
            ga_service = self._get_service("GoogleAdsService")
            query = f"""
                SELECT
                    ad_group_criterion.criterion_id,
                    ad_group_criterion.keyword.text,
                    ad_group_criterion.keyword.match_type,
                    ad_group_criterion.status,
                    ad_group_criterion.quality_info.quality_score,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions
                FROM keyword_view
                WHERE ad_group.id = {ad_group_id}
                  AND ad_group_criterion.status != 'REMOVED'
            """
            response = ga_service.search(
                customer_id=self.customer_id, query=query,
            )
            keywords = []
            for row in response:
                kw = row.ad_group_criterion
                m = row.metrics
                keywords.append({
                    "id": str(kw.criterion_id),
                    "text": kw.keyword.text,
                    "match_type": kw.keyword.match_type.name,
                    "status": kw.status.name,
                    "quality_score": kw.quality_info.quality_score if kw.quality_info else None,
                    "impressions": m.impressions,
                    "clicks": m.clicks,
                    "cost_brl": m.cost_micros / 1_000_000 if m.cost_micros else 0,
                    "conversions": m.conversions,
                })

            return {"success": True, "keywords": keywords, "count": len(keywords)}

        except Exception as exc:
            logger.error("List keywords error: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── Ads (Responsive Search Ads) ─────────────────────────────

    def create_responsive_search_ad(
        self,
        ad_group_id: str,
        headlines: list[str],
        descriptions: list[str],
        final_url: str,
        path1: str = "",
        path2: str = "",
    ) -> dict[str, Any]:
        """Create a Responsive Search Ad (RSA).

        Args:
            ad_group_id: Ad group ID.
            headlines: List of 3-15 headline texts (max 30 chars each).
            descriptions: List of 2-4 description texts (max 90 chars each).
            final_url: Landing page URL.
            path1: Display URL path 1 (max 15 chars).
            path2: Display URL path 2 (max 15 chars).

        Returns:
            Dict with created ad info.
        """
        logger.info("Creating RSA in ad group %s", ad_group_id)
        try:
            ad_group_ad_service = self._get_service("AdGroupAdService")
            op = self.client.get_type("AdGroupAdOperation")
            ad_group_ad = op.create

            ad_group_ad.ad_group = self._get_service("AdGroupService").ad_group_path(
                self.customer_id, ad_group_id,
            )
            ad_group_ad.status = self.client.enums.AdGroupAdStatusEnum.ENABLED

            ad = ad_group_ad.ad
            ad.final_urls.append(final_url)

            # Add headlines
            for headline_text in headlines:
                headline = self.client.get_type("AdTextAsset")
                headline.text = headline_text[:30]  # Enforce limit
                ad.responsive_search_ad.headlines.append(headline)

            # Add descriptions
            for desc_text in descriptions:
                description = self.client.get_type("AdTextAsset")
                description.text = desc_text[:90]  # Enforce limit
                ad.responsive_search_ad.descriptions.append(description)

            if path1:
                ad.responsive_search_ad.path1 = path1[:15]
            if path2:
                ad.responsive_search_ad.path2 = path2[:15]

            response = ad_group_ad_service.mutate_ad_group_ads(
                customer_id=self.customer_id,
                operations=[op],
            )
            resource_name = response.results[0].resource_name
            logger.info("RSA created: %s", resource_name)

            return {
                "success": True,
                "resource_name": resource_name,
                "headlines_count": len(headlines),
                "descriptions_count": len(descriptions),
                "final_url": final_url,
            }

        except Exception as exc:
            logger.error("Create RSA error: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── Conversion Tracking ─────────────────────────────────────

    def list_conversion_actions(self) -> dict[str, Any]:
        """List all conversion actions configured in the account.

        Returns:
            Dict with list of conversion actions.
        """
        logger.info("Listing conversion actions for customer %s", self.customer_id)
        try:
            ga_service = self._get_service("GoogleAdsService")
            query = """
                SELECT
                    conversion_action.id,
                    conversion_action.name,
                    conversion_action.status,
                    conversion_action.type,
                    conversion_action.category,
                    conversion_action.tag_snippets,
                    conversion_action.include_in_conversions_metric,
                    metrics.conversions,
                    metrics.conversions_value
                FROM conversion_action
                WHERE conversion_action.status != 'REMOVED'
            """
            response = ga_service.search(
                customer_id=self.customer_id, query=query,
            )
            actions = []
            for row in response:
                ca = row.conversion_action
                m = row.metrics
                actions.append({
                    "id": str(ca.id),
                    "name": ca.name,
                    "status": ca.status.name,
                    "type": ca.type_.name,
                    "category": ca.category.name,
                    "in_conversions_metric": ca.include_in_conversions_metric,
                    "conversions": m.conversions,
                    "conversions_value": m.conversions_value,
                })

            return {"success": True, "actions": actions, "count": len(actions)}

        except Exception as exc:
            logger.error("List conversion actions error: %s", exc)
            return {"success": False, "error": str(exc)}

    def create_conversion_action(
        self,
        name: str,
        category: str = "PURCHASE",
        conversion_type: str = "WEBPAGE",
        value_settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a conversion action.

        Args:
            name: Conversion action name.
            category: Category (PURCHASE, SIGNUP, LEAD, etc.).
            conversion_type: Type (WEBPAGE, CLICK_TO_CALL, etc.).
            value_settings: Optional value settings dict.

        Returns:
            Dict with created conversion action info.
        """
        logger.info("Creating conversion action: %s", name)
        try:
            conversion_service = self._get_service("ConversionActionService")
            op = self.client.get_type("ConversionActionOperation")
            action = op.create

            action.name = name
            action.status = self.client.enums.ConversionActionStatusEnum.ENABLED
            action.type_ = getattr(
                self.client.enums.ConversionActionTypeEnum, conversion_type,
            )
            action.category = getattr(
                self.client.enums.ConversionActionCategoryEnum, category,
            )

            # Value settings
            if value_settings:
                action.value_settings.default_value = value_settings.get("default_value", 0)
                action.value_settings.default_currency_code = value_settings.get("currency", "BRL")
                action.value_settings.always_use_default_value = value_settings.get(
                    "always_use_default", False,
                )

            response = conversion_service.mutate_conversion_actions(
                customer_id=self.customer_id,
                operations=[op],
            )
            resource_name = response.results[0].resource_name
            logger.info("Conversion action created: %s", resource_name)

            return {
                "success": True,
                "resource_name": resource_name,
                "name": name,
                "category": category,
            }

        except Exception as exc:
            logger.error("Create conversion action error: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── Performance Reports ─────────────────────────────────────

    def get_campaign_performance(
        self,
        campaign_id: str | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get campaign performance metrics.

        Args:
            campaign_id: Optional specific campaign ID.
            days: Number of days to look back.

        Returns:
            Dict with performance data.
        """
        logger.info("Fetching campaign performance (last %d days)", days)
        try:
            ga_service = self._get_service("GoogleAdsService")

            where_clause = "WHERE campaign.status != 'REMOVED'"
            if campaign_id:
                where_clause += f" AND campaign.id = {campaign_id}"

            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    campaign.status,
                    segments.date,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.ctr,
                    metrics.average_cpc,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.cost_per_conversion
                FROM campaign
                {where_clause}
                  AND segments.date DURING LAST_{days}_DAYS
                ORDER BY segments.date DESC
            """

            # Use valid date range per Google Ads API
            valid_ranges = {7: "LAST_7_DAYS", 14: "LAST_14_DAYS", 30: "LAST_30_DAYS"}
            date_range = valid_ranges.get(days, "LAST_30_DAYS")
            query = query.replace(f"LAST_{days}_DAYS", date_range)

            response = ga_service.search(
                customer_id=self.customer_id, query=query,
            )

            rows = []
            for row in response:
                c = row.campaign
                m = row.metrics
                s = row.segments
                rows.append({
                    "campaign_id": str(c.id),
                    "campaign_name": c.name,
                    "date": s.date,
                    "impressions": m.impressions,
                    "clicks": m.clicks,
                    "ctr": m.ctr,
                    "avg_cpc_brl": m.average_cpc / 1_000_000 if m.average_cpc else 0,
                    "cost_brl": m.cost_micros / 1_000_000 if m.cost_micros else 0,
                    "conversions": m.conversions,
                    "conversions_value": m.conversions_value,
                    "cost_per_conversion": m.cost_per_conversion / 1_000_000 if m.cost_per_conversion else 0,
                })

            return {"success": True, "data": rows, "count": len(rows)}

        except Exception as exc:
            logger.error("Campaign performance error: %s", exc)
            return {"success": False, "error": str(exc)}

    def get_keyword_performance(
        self,
        campaign_id: str | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get keyword-level performance.

        Args:
            campaign_id: Optional campaign filter.
            days: Number of days.

        Returns:
            Dict with keyword performance data.
        """
        logger.info("Fetching keyword performance (last %d days)", days)
        try:
            ga_service = self._get_service("GoogleAdsService")

            where_clause = "WHERE ad_group_criterion.status != 'REMOVED'"
            if campaign_id:
                where_clause += f" AND campaign.id = {campaign_id}"

            valid_ranges = {7: "LAST_7_DAYS", 14: "LAST_14_DAYS", 30: "LAST_30_DAYS"}
            date_range = valid_ranges.get(days, "LAST_30_DAYS")

            query = f"""
                SELECT
                    campaign.name,
                    ad_group.name,
                    ad_group_criterion.keyword.text,
                    ad_group_criterion.keyword.match_type,
                    ad_group_criterion.quality_info.quality_score,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.ctr,
                    metrics.average_cpc,
                    metrics.cost_micros,
                    metrics.conversions
                FROM keyword_view
                {where_clause}
                  AND segments.date DURING {date_range}
                ORDER BY metrics.clicks DESC
                LIMIT 100
            """
            response = ga_service.search(
                customer_id=self.customer_id, query=query,
            )

            keywords = []
            for row in response:
                kw = row.ad_group_criterion
                m = row.metrics
                keywords.append({
                    "campaign": row.campaign.name,
                    "ad_group": row.ad_group.name,
                    "keyword": kw.keyword.text,
                    "match_type": kw.keyword.match_type.name,
                    "quality_score": kw.quality_info.quality_score if kw.quality_info else None,
                    "impressions": m.impressions,
                    "clicks": m.clicks,
                    "ctr": m.ctr,
                    "avg_cpc_brl": m.average_cpc / 1_000_000 if m.average_cpc else 0,
                    "cost_brl": m.cost_micros / 1_000_000 if m.cost_micros else 0,
                    "conversions": m.conversions,
                })

            return {"success": True, "keywords": keywords, "count": len(keywords)}

        except Exception as exc:
            logger.error("Keyword performance error: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── Beezle Quick Setup ──────────────────────────────────────

    def setup_beezle_campaign(self) -> dict[str, Any]:
        """Create a complete Beezle campaign setup.

        Creates:
        1. Search campaign with maximize_conversions
        2. Three ad groups (indicação, embaixadores, growth)
        3. Keywords for each ad group
        4. Responsive Search Ads

        Returns:
            Dict with all created resources.
        """
        logger.info("Setting up full Beezle campaign")
        results: dict[str, Any] = {"steps": []}

        try:
            # 1. Create campaign
            campaign_result = self.create_campaign(
                name="Beezle — Programa de Indicação",
                daily_budget_brl=50.0,
                bidding_strategy="MAXIMIZE_CONVERSIONS",
            )
            results["steps"].append({"step": "campaign", "result": campaign_result})
            if not campaign_result["success"]:
                return {"success": False, "error": "Campaign creation failed", "details": results}

            # Extract campaign ID from resource name
            campaign_resource = campaign_result["resource_name"]
            campaign_id = campaign_resource.split("/")[-1]

            # 2. Ad Group: Programa de Indicação
            ag1 = self.create_ad_group(campaign_id, "Programa de Indicação", cpc_bid_brl=2.50)
            results["steps"].append({"step": "ad_group_indicacao", "result": ag1})

            if ag1["success"]:
                ag1_id = ag1["resource_name"].split("/")[-1]

                # Keywords
                kw1 = self.add_keywords(ag1_id, [
                    {"text": "programa de indicação", "match_type": "PHRASE"},
                    {"text": "sistema de indicação para empresas", "match_type": "PHRASE"},
                    {"text": "plataforma de indicação", "match_type": "PHRASE"},
                    {"text": "programa de referral", "match_type": "BROAD"},
                    {"text": "indicação de clientes software", "match_type": "BROAD"},
                ])
                results["steps"].append({"step": "keywords_indicacao", "result": kw1})

                # RSA
                rsa1 = self.create_responsive_search_ad(
                    ad_group_id=ag1_id,
                    headlines=[
                        "Programa de Indicação Beezle",
                        "Crie Seu Programa de Indicação",
                        "Indicação que Gera Receita",
                        "Aumente Vendas por Indicação",
                        "Plataforma de Referral #1",
                    ],
                    descriptions=[
                        "Crie programas de indicação em minutos. Dashboard completo, pagamentos automáticos via Stripe.",
                        "Transforme clientes em embaixadores. Acompanhe indicações, recompensas e ROI em tempo real.",
                    ],
                    final_url="https://beezle.io/vendas/programa-de-indicacao/",
                    path1="indicacao",
                    path2="criar",
                )
                results["steps"].append({"step": "rsa_indicacao", "result": rsa1})

            # 3. Ad Group: Marketing de Embaixadores
            ag2 = self.create_ad_group(campaign_id, "Marketing de Embaixadores", cpc_bid_brl=2.00)
            results["steps"].append({"step": "ad_group_embaixadores", "result": ag2})

            if ag2["success"]:
                ag2_id = ag2["resource_name"].split("/")[-1]

                kw2 = self.add_keywords(ag2_id, [
                    {"text": "marketing de embaixadores", "match_type": "PHRASE"},
                    {"text": "embaixadores de marca", "match_type": "PHRASE"},
                    {"text": "ambassador marketing", "match_type": "BROAD"},
                    {"text": "influenciadores para marcas", "match_type": "BROAD"},
                ])
                results["steps"].append({"step": "keywords_embaixadores", "result": kw2})

                rsa2 = self.create_responsive_search_ad(
                    ad_group_id=ag2_id,
                    headlines=[
                        "Embaixadores de Marca | Beezle",
                        "Marketing com Embaixadores",
                        "Escale com Embaixadores",
                        "Plataforma p/ Embaixadores",
                        "Gerencie Embaixadores Fácil",
                    ],
                    descriptions=[
                        "Recrute e gerencie embaixadores de marca com Beezle. Pagamentos automáticos e dashboard completo.",
                        "Seus clientes são seus melhores vendedores. Ative-os como embaixadores em poucos cliques.",
                    ],
                    final_url="https://beezle.io/vendas/embaixadores-de-marca/",
                    path1="embaixadores",
                )
                results["steps"].append({"step": "rsa_embaixadores", "result": rsa2})

            # 4. Ad Group: Growth Hacking
            ag3 = self.create_ad_group(campaign_id, "Growth Hacking", cpc_bid_brl=1.80)
            results["steps"].append({"step": "ad_group_growth", "result": ag3})

            if ag3["success"]:
                ag3_id = ag3["resource_name"].split("/")[-1]

                kw3 = self.add_keywords(ag3_id, [
                    {"text": "growth hacking ferramenta", "match_type": "BROAD"},
                    {"text": "aquisição de clientes orgânica", "match_type": "BROAD"},
                    {"text": "crescimento por indicação", "match_type": "PHRASE"},
                    {"text": "viral marketing software", "match_type": "BROAD"},
                ])
                results["steps"].append({"step": "keywords_growth", "result": kw3})

                rsa3 = self.create_responsive_search_ad(
                    ad_group_id=ag3_id,
                    headlines=[
                        "Growth Hacking com Beezle",
                        "Cresça por Indicação",
                        "Aquisição Orgânica de Clientes",
                        "Motor de Crescimento Viral",
                        "Escale Sem Ads Caros",
                    ],
                    descriptions=[
                        "Growth hacking via indicações. Reduza CAC e aumente LTV com a plataforma Beezle.",
                        "Transforme cada cliente em um canal de aquisição. Setup em 5 minutos, resultados imediatos.",
                    ],
                    final_url="https://beezle.io/vendas/como-funciona/",
                    path1="growth",
                    path2="indicacao",
                )
                results["steps"].append({"step": "rsa_growth", "result": rsa3})

            # 5. Create conversion actions
            conv1 = self.create_conversion_action(
                name="Beezle — Purchase",
                category="PURCHASE",
                value_settings={"default_value": 97.0, "currency": "BRL"},
            )
            results["steps"].append({"step": "conversion_purchase", "result": conv1})

            conv2 = self.create_conversion_action(
                name="Beezle — Sign Up",
                category="SIGNUP",
            )
            results["steps"].append({"step": "conversion_signup", "result": conv2})

            conv3 = self.create_conversion_action(
                name="Beezle — Lead",
                category="LEAD",
            )
            results["steps"].append({"step": "conversion_lead", "result": conv3})

            results["success"] = True
            results["campaign_id"] = campaign_id
            logger.info("Beezle campaign setup complete")
            return results

        except Exception as exc:
            logger.error("Beezle campaign setup error: %s", exc)
            results["success"] = False
            results["error"] = str(exc)
            return results
