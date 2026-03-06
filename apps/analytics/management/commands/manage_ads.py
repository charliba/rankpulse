"""Management command to manage Google Ads campaigns via channel credentials."""
from __future__ import annotations

import json
import logging

from django.core.management.base import BaseCommand, CommandParser

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Manage Google Ads campaigns — list, create, performance reports (channel-scoped)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--channel-id", type=int, required=True,
            help="ID of the Channel to use for credentials",
        )

        subparsers = parser.add_subparsers(dest="action", help="Action to perform")

        # List campaigns
        subparsers.add_parser("list", help="List all campaigns")

        # Account info
        subparsers.add_parser("account", help="Show account info")

        # Create campaign
        create = subparsers.add_parser("create", help="Create a new campaign")
        create.add_argument("--name", type=str, required=True)
        create.add_argument("--budget", type=float, default=50.0, help="Daily budget in BRL")
        create.add_argument("--strategy", type=str, default="MAXIMIZE_CONVERSIONS")

        # Campaign performance
        perf = subparsers.add_parser("performance", help="Show campaign performance")
        perf.add_argument("--campaign-id", type=str, help="Specific campaign")
        perf.add_argument("--days", type=int, default=30)

        # Conversions
        subparsers.add_parser("conversions", help="List conversion actions")

        # Enable/pause
        status = subparsers.add_parser("status", help="Update campaign status")
        status.add_argument("--campaign-id", type=str, required=True)
        status.add_argument("--set", type=str, choices=["ENABLED", "PAUSED"], required=True)

        # Add sitelink
        sl = subparsers.add_parser("add-sitelink", help="Create a sitelink asset and link to campaign")
        sl.add_argument("--campaign-id", type=str, required=True)
        sl.add_argument("--text", type=str, required=True, help="Sitelink text (max 25 chars)")
        sl.add_argument("--url", type=str, required=True, help="Final URL")
        sl.add_argument("--desc1", type=str, default="", help="Description line 1")
        sl.add_argument("--desc2", type=str, default="", help="Description line 2")

        # Add callout
        co = subparsers.add_parser("add-callout", help="Create a callout asset and link to campaign")
        co.add_argument("--campaign-id", type=str, required=True)
        co.add_argument("--text", type=str, required=True, help="Callout text (max 25 chars)")

        # Add negative keywords
        neg = subparsers.add_parser("add-negatives", help="Add negative keywords to campaign")
        neg.add_argument("--campaign-id", type=str, required=True)
        neg.add_argument("--keywords", type=str, nargs="+", required=True, help="Negative keyword texts")
        neg.add_argument("--match-type", type=str, default="PHRASE", choices=["BROAD", "PHRASE", "EXACT"])

        # Geo targeting
        geo = subparsers.add_parser("geo-target", help="Set geo targeting for campaign")
        geo.add_argument("--campaign-id", type=str, required=True)
        geo.add_argument("--location-ids", type=int, nargs="+", required=True, help="Geo target constant IDs")

    def _get_manager(self, channel):
        """Build GoogleAdsManager from channel credentials."""
        from apps.analytics.ads_client import GoogleAdsManager
        from apps.channels.models import ChannelCredential

        try:
            cred = channel.credentials
        except ChannelCredential.DoesNotExist:
            self.stdout.write(self.style.ERROR("Canal sem credenciais configuradas."))
            return None

        if not channel.is_configured:
            self.stdout.write(self.style.ERROR(
                "Canal não está totalmente configurado. "
                "Preencha todas as credenciais no painel.",
            ))
            return None

        return GoogleAdsManager(
            customer_id=cred.customer_id,
            developer_token=cred.developer_token,
            client_id=cred.client_id,
            client_secret=cred.client_secret,
            refresh_token=cred.refresh_token,
            login_customer_id=cred.login_customer_id,
        )

    def handle(self, *args, **options) -> None:
        from apps.channels.models import Channel

        channel_id = options["channel_id"]
        action = options.get("action")

        try:
            channel = Channel.objects.get(pk=channel_id)
        except Channel.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Canal #{channel_id} não encontrado."))
            return

        if channel.platform != "google_ads":
            self.stdout.write(self.style.ERROR(
                f"Canal #{channel_id} é {channel.get_platform_display()}, não Google Ads.",
            ))
            return

        self.stdout.write(f"📡 Canal: {channel.name} (Projeto: {channel.project.name})\n")

        if not action:
            self.stdout.write(self.style.WARNING(
                "Specify an action: list, account, create, performance, "
                "conversions, status, add-sitelink, add-callout, add-negatives, geo-target"
            ))
            return

        mgr = self._get_manager(channel)
        if not mgr:
            return

        if action == "account":
            result = mgr.get_account_info()
            if result["success"]:
                self.stdout.write(f"\n📊 Google Ads Account")
                self.stdout.write(f"  ID: {result['id']}")
                self.stdout.write(f"  Name: {result['name']}")
                self.stdout.write(f"  Currency: {result['currency']}")
                self.stdout.write(f"  Timezone: {result['timezone']}")
                self.stdout.write(f"  Auto-tagging: {result['auto_tagging']}")
            else:
                self.stdout.write(self.style.ERROR(f"❌ {result['error']}"))

        elif action == "list":
            result = mgr.list_campaigns()
            if result["success"]:
                self.stdout.write(f"\n📋 Campaigns ({result['count']}):")
                for c in result["campaigns"]:
                    status_emoji = "🟢" if c["status"] == "ENABLED" else "⏸️"
                    self.stdout.write(
                        f"  {status_emoji} [{c['id']}] {c['name']} "
                        f"| R${c['daily_budget_brl']:.2f}/dia "
                        f"| {c['clicks']} clicks, {c['conversions']:.0f} conv"
                    )
                if not result["campaigns"]:
                    self.stdout.write("  (no campaigns)")
            else:
                self.stdout.write(self.style.ERROR(f"❌ {result['error']}"))

        elif action == "create":
            name = options["name"]
            budget = options["budget"]
            strategy = options["strategy"]
            self.stdout.write(f"\n🆕 Creating campaign: {name} (R${budget}/dia)")
            result = mgr.create_campaign(name, daily_budget_brl=budget, bidding_strategy=strategy)
            if result["success"]:
                self.stdout.write(self.style.SUCCESS(f"  ✅ Created: {result['resource_name']}"))
            else:
                self.stdout.write(self.style.ERROR(f"  ❌ {result['error']}"))

        elif action == "performance":
            campaign_id = options.get("campaign_id")
            days = options["days"]
            self.stdout.write(f"\n📈 Campaign Performance (last {days} days):")
            result = mgr.get_campaign_performance(campaign_id=campaign_id, days=days)
            if result["success"]:
                for row in result["data"][:30]:
                    self.stdout.write(
                        f"  {row['date']} | {row['campaign_name']} "
                        f"| {row['clicks']} clicks, R${row['cost_brl']:.2f}, "
                        f"{row['conversions']:.0f} conv"
                    )
            else:
                self.stdout.write(self.style.ERROR(f"❌ {result['error']}"))

        elif action == "conversions":
            result = mgr.list_conversion_actions()
            if result["success"]:
                self.stdout.write(f"\n🎯 Conversion Actions ({result['count']}):")
                for ca in result["actions"]:
                    self.stdout.write(
                        f"  [{ca['id']}] {ca['name']} ({ca['category']}) "
                        f"— {ca['conversions']:.0f} conversions"
                    )
            else:
                self.stdout.write(self.style.ERROR(f"❌ {result['error']}"))

        elif action == "status":
            campaign_id = options["campaign_id"]
            new_status = options["set"]
            result = mgr.update_campaign_status(campaign_id, new_status)
            if result["success"]:
                self.stdout.write(self.style.SUCCESS(f"✅ Campaign {campaign_id} → {new_status}"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ {result['error']}"))

        elif action == "add-sitelink":
            campaign_id = options["campaign_id"]
            text = options["text"]
            url = options["url"]
            desc1 = options.get("desc1", "")
            desc2 = options.get("desc2", "")
            self.stdout.write(f"\n🔗 Creating sitelink: {text}")
            sl_result = mgr.create_sitelink_asset(text, url, desc1, desc2)
            if sl_result["success"]:
                link_result = mgr.link_assets_to_campaign(
                    campaign_id, [sl_result["resource_name"]], "SITELINK",
                )
                if link_result["success"]:
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Sitelink created and linked"))
                else:
                    self.stdout.write(self.style.ERROR(f"  ❌ Link failed: {link_result['error']}"))
            else:
                self.stdout.write(self.style.ERROR(f"  ❌ {sl_result['error']}"))

        elif action == "add-callout":
            campaign_id = options["campaign_id"]
            text = options["text"]
            self.stdout.write(f"\n📢 Creating callout: {text}")
            co_result = mgr.create_callout_asset(text)
            if co_result["success"]:
                link_result = mgr.link_assets_to_campaign(
                    campaign_id, [co_result["resource_name"]], "CALLOUT",
                )
                if link_result["success"]:
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Callout created and linked"))
                else:
                    self.stdout.write(self.style.ERROR(f"  ❌ Link failed: {link_result['error']}"))
            else:
                self.stdout.write(self.style.ERROR(f"  ❌ {co_result['error']}"))

        elif action == "add-negatives":
            campaign_id = options["campaign_id"]
            kw_texts = options["keywords"]
            match_type = options.get("match_type", "PHRASE")
            kws = [{"text": t, "match_type": match_type} for t in kw_texts]
            self.stdout.write(f"\n🚫 Adding {len(kws)} negative keywords...")
            result = mgr.add_negative_keywords(campaign_id, kws)
            if result["success"]:
                self.stdout.write(self.style.SUCCESS(f"  ✅ Added {result['negatives_added']} negatives"))
            else:
                self.stdout.write(self.style.ERROR(f"  ❌ {result['error']}"))

        elif action == "geo-target":
            campaign_id = options["campaign_id"]
            location_ids = options["location_ids"]
            self.stdout.write(f"\n🌍 Setting geo targets: {location_ids}")
            result = mgr.set_geo_targets(campaign_id, location_ids)
            if result["success"]:
                self.stdout.write(self.style.SUCCESS(f"  ✅ Set {result['targets_set']} geo targets"))
            else:
                self.stdout.write(self.style.ERROR(f"  ❌ {result['error']}"))

        self.stdout.write(self.style.SUCCESS("\nDone!"))
