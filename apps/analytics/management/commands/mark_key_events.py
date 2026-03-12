"""Management command to mark GA4 events as Key Events (conversions)."""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

from apps.analytics.ga4_admin import GA4AdminClient
from apps.core.models import Site

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Mark GA4 events as Key Events (conversions) via GA4 Admin API."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--site-id", type=int, help="Specific site ID")
        parser.add_argument(
            "--events", nargs="+",
            help="Event names to mark (e.g., purchase sign_up generate_lead)",
        )
        parser.add_argument(
            "--beezle", action="store_true",
            help="Mark all standard Beezle events (purchase, sign_up, generate_lead, share)",
        )
        parser.add_argument(
            "--list", action="store_true",
            help="List current key events instead of creating",
        )
        parser.add_argument(
            "--delete", type=str,
            help="Delete a key event by resource name",
        )

    def handle(self, *args, **options) -> None:
        site_id = options.get("site_id")
        events = options.get("events") or []
        beezle_mode = options.get("beezle", False)
        list_mode = options.get("list", False)
        delete_name = options.get("delete")

        key_path = getattr(settings, "GA4_SERVICE_ACCOUNT_KEY_PATH", "")
        if not key_path:
            self.stdout.write(self.style.ERROR("GA4_SERVICE_ACCOUNT_KEY_PATH not configured."))
            return

        # Resolve property ID
        if site_id:
            try:
                site = Site.objects.get(pk=site_id, is_active=True)
            except Site.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Site {site_id} not found."))
                return
            property_id = site.ga4_property_id
        else:
            property_id = getattr(settings, "GA4_PROPERTY_ID", "")

        if not property_id:
            self.stdout.write(self.style.ERROR(
                "GA4 Property ID not found. Set GA4_PROPERTY_ID in .env or use --site-id.",
            ))
            return

        if site and site.google_refresh_token:
            client = GA4AdminClient(
                property_id=property_id,
                refresh_token=site.google_refresh_token,
            )
        else:
            client = GA4AdminClient(
                property_id=property_id,
                service_account_key_path=key_path,
            )

        if list_mode:
            self.stdout.write(f"\n📊 Key Events for property {property_id}:")
            result = client.list_key_events()
            if result["success"]:
                for ev in result["key_events"]:
                    self.stdout.write(f"  🔑 {ev['event_name']} → {ev['name']}")
                if not result["key_events"]:
                    self.stdout.write("  (no key events)")
            else:
                self.stdout.write(self.style.ERROR(f"  ❌ {result['error']}"))

        elif delete_name:
            result = client.delete_key_event(delete_name)
            if result["success"]:
                self.stdout.write(self.style.SUCCESS(f"  ✅ Deleted: {delete_name}"))
            else:
                self.stdout.write(self.style.ERROR(f"  ❌ {result['error']}"))

        elif beezle_mode:
            self.stdout.write(f"\n🐝 Marking Beezle key events for property {property_id}:")
            results = client.mark_beezle_key_events()
            for r in results:
                event = r.get("requested_event", r.get("event_name", "?"))
                if r.get("success"):
                    self.stdout.write(self.style.SUCCESS(f"  ✅ {event}"))
                elif r.get("already_exists"):
                    self.stdout.write(f"  ⏭️  {event} (already exists)")
                else:
                    self.stdout.write(self.style.ERROR(f"  ❌ {event}: {r.get('error', '')}"))

        elif events:
            self.stdout.write(f"\n🔑 Marking events as Key Events for property {property_id}:")
            for event_name in events:
                result = client.create_key_event(event_name)
                if result.get("success"):
                    self.stdout.write(self.style.SUCCESS(f"  ✅ {event_name}"))
                elif result.get("already_exists"):
                    self.stdout.write(f"  ⏭️  {event_name} (already exists)")
                else:
                    self.stdout.write(self.style.ERROR(f"  ❌ {event_name}: {result.get('error', '')}"))

        else:
            self.stdout.write(self.style.WARNING(
                "Specify --events, --beezle, --list, or --delete.",
            ))
            return

        self.stdout.write(self.style.SUCCESS("\nDone!"))
