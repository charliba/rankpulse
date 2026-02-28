"""Management command to set up and manage Google Ads campaigns."""
from __future__ import annotations

import json
import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Manage Google Ads campaigns — setup, list, create, performance reports."

    def add_arguments(self, parser: CommandParser) -> None:
        subparsers = parser.add_subparsers(dest="action", help="Action to perform")

        # List campaigns
        subparsers.add_parser("list", help="List all campaigns")

        # Account info
        subparsers.add_parser("account", help="Show account info")

        # Setup Beezle campaign
        subparsers.add_parser("setup-beezle", help="Create full Beezle campaign setup")

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

    def _get_manager(self):
        """Build GoogleAdsManager from settings."""
        from apps.analytics.ads_client import GoogleAdsManager

        customer_id = getattr(settings, "GOOGLE_ADS_CUSTOMER_ID", "")
        if not customer_id:
            self.stdout.write(self.style.ERROR(
                "GOOGLE_ADS_CUSTOMER_ID not configured. Set it in .env",
            ))
            return None

        return GoogleAdsManager(
            customer_id=customer_id,
            developer_token=getattr(settings, "GOOGLE_ADS_DEVELOPER_TOKEN", ""),
            client_id=getattr(settings, "GOOGLE_ADS_CLIENT_ID", ""),
            client_secret=getattr(settings, "GOOGLE_ADS_CLIENT_SECRET", ""),
            refresh_token=getattr(settings, "GOOGLE_ADS_REFRESH_TOKEN", ""),
            login_customer_id=getattr(settings, "GOOGLE_ADS_LOGIN_CUSTOMER_ID", ""),
        )

    def handle(self, *args, **options) -> None:
        action = options.get("action")
        if not action:
            self.stdout.write(self.style.WARNING("Specify an action: list, account, setup-beezle, create, performance, conversions, status"))
            return

        mgr = self._get_manager()
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

        elif action == "setup-beezle":
            self.stdout.write("\n🐝 Setting up Beezle campaign...")
            result = mgr.setup_beezle_campaign()
            self.stdout.write(json.dumps(result, indent=2, default=str))

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

        self.stdout.write(self.style.SUCCESS("\nDone!"))
