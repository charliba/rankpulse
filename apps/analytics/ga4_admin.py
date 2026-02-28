"""GA4 Admin API Client — Manage Key Events (Conversions).

Uses the Google Analytics Admin API to programmatically mark events
as Key Events (conversions), manage data streams, and custom dimensions.

Reference: https://developers.google.com/analytics/devguides/config/admin/v1

Requirements:
    - google-analytics-admin pip package
    - Service account with GA4 Editor/Admin role
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_admin_client(service_account_key_path: str):
    """Build GA4 Admin API client.

    Args:
        service_account_key_path: Path to the service account JSON key file.

    Returns:
        AnalyticsAdminServiceClient instance.
    """
    from google.analytics.admin_v1alpha import AnalyticsAdminServiceClient
    from google.oauth2 import service_account

    credentials = service_account.Credentials.from_service_account_file(
        service_account_key_path,
        scopes=["https://www.googleapis.com/auth/analytics.edit"],
    )
    return AnalyticsAdminServiceClient(credentials=credentials)


class GA4AdminClient:
    """Client for GA4 Admin API — Key Events and property management.

    Usage:
        client = GA4AdminClient(
            property_id="123456789",
            service_account_key_path="credentials/ga4.json",
        )
        client.create_key_event("purchase")
        events = client.list_key_events()
    """

    def __init__(self, property_id: str, service_account_key_path: str) -> None:
        self.property_id = property_id
        self.service_account_key_path = service_account_key_path
        self._client = None

    @property
    def client(self):
        """Lazy-load the Admin API client."""
        if self._client is None:
            self._client = _get_admin_client(self.service_account_key_path)
        return self._client

    @property
    def parent(self) -> str:
        """GA4 property resource name."""
        return f"properties/{self.property_id}"

    # ── Key Events (Conversions) ────────────────────────────────

    def list_key_events(self) -> dict[str, Any]:
        """List all Key Events (conversion events) for the property.

        Returns:
            Dict with list of key events or error.
        """
        logger.info("Listing key events for property %s", self.property_id)
        try:
            from google.analytics.admin_v1alpha import ListKeyEventsRequest

            request = ListKeyEventsRequest(parent=self.parent)
            response = self.client.list_key_events(request=request)

            events = []
            for event in response:
                events.append({
                    "name": event.name,
                    "event_name": event.event_name,
                    "create_time": str(event.create_time) if event.create_time else "",
                    "deletable": event.deletable,
                    "custom": event.custom,
                    "counting_method": str(event.counting_method) if event.counting_method else "",
                })

            logger.info("Found %d key events", len(events))
            return {"success": True, "key_events": events, "count": len(events)}

        except Exception as exc:
            logger.error("List key events error: %s", exc)
            return {"success": False, "error": str(exc)}

    def create_key_event(
        self,
        event_name: str,
        counting_method: str = "ONCE_PER_EVENT",
    ) -> dict[str, Any]:
        """Mark an event as a Key Event (conversion) in GA4.

        Args:
            event_name: The GA4 event name (e.g., "purchase", "sign_up").
            counting_method: "ONCE_PER_EVENT" or "ONCE_PER_SESSION".

        Returns:
            Dict with created key event details or error.
        """
        logger.info(
            "Creating key event '%s' for property %s", event_name, self.property_id,
        )
        try:
            from google.analytics.admin_v1alpha import (
                CreateKeyEventRequest,
                KeyEvent,
            )

            counting = (
                KeyEvent.CountingMethod.ONCE_PER_EVENT
                if counting_method == "ONCE_PER_EVENT"
                else KeyEvent.CountingMethod.ONCE_PER_SESSION
            )

            key_event = KeyEvent(
                event_name=event_name,
                counting_method=counting,
            )

            request = CreateKeyEventRequest(
                parent=self.parent,
                key_event=key_event,
            )
            response = self.client.create_key_event(request=request)

            logger.info("Key event created: %s → %s", event_name, response.name)
            return {
                "success": True,
                "name": response.name,
                "event_name": response.event_name,
                "counting_method": str(response.counting_method),
            }

        except Exception as exc:
            error_msg = str(exc)
            if "ALREADY_EXISTS" in error_msg:
                logger.warning("Key event '%s' already exists", event_name)
                return {
                    "success": False,
                    "error": f"Key event '{event_name}' already exists",
                    "already_exists": True,
                }
            logger.error("Create key event error: %s", exc)
            return {"success": False, "error": error_msg}

    def delete_key_event(self, key_event_name: str) -> dict[str, Any]:
        """Delete (unmark) a Key Event.

        Args:
            key_event_name: Full resource name
                            (e.g., "properties/123/keyEvents/456").

        Returns:
            Dict with success status.
        """
        logger.info("Deleting key event: %s", key_event_name)
        try:
            from google.analytics.admin_v1alpha import DeleteKeyEventRequest

            request = DeleteKeyEventRequest(name=key_event_name)
            self.client.delete_key_event(request=request)

            logger.info("Key event deleted: %s", key_event_name)
            return {"success": True, "deleted": key_event_name}

        except Exception as exc:
            logger.error("Delete key event error: %s", exc)
            return {"success": False, "error": str(exc)}

    def mark_beezle_key_events(self) -> list[dict[str, Any]]:
        """Mark all Beezle conversion events as Key Events.

        Convenience method that marks the standard Beezle events.

        Returns:
            List of results for each event.
        """
        events_to_mark = [
            "purchase",
            "sign_up",
            "generate_lead",
            "share",
        ]
        results = []
        for event_name in events_to_mark:
            result = self.create_key_event(event_name)
            result["requested_event"] = event_name
            results.append(result)
        return results

    # ── Data Streams ────────────────────────────────────────────

    def list_data_streams(self) -> dict[str, Any]:
        """List all data streams for the property.

        Returns:
            Dict with list of data streams.
        """
        logger.info("Listing data streams for property %s", self.property_id)
        try:
            from google.analytics.admin_v1alpha import ListDataStreamsRequest

            request = ListDataStreamsRequest(parent=self.parent)
            response = self.client.list_data_streams(request=request)

            streams = []
            for stream in response:
                streams.append({
                    "name": stream.name,
                    "display_name": stream.display_name,
                    "type": str(stream.type_) if stream.type_ else "",
                    "create_time": str(stream.create_time) if stream.create_time else "",
                    "update_time": str(stream.update_time) if stream.update_time else "",
                })

            logger.info("Found %d data streams", len(streams))
            return {"success": True, "streams": streams, "count": len(streams)}

        except Exception as exc:
            logger.error("List data streams error: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── Custom Dimensions ───────────────────────────────────────

    def list_custom_dimensions(self) -> dict[str, Any]:
        """List all custom dimensions for the property.

        Returns:
            Dict with list of custom dimensions.
        """
        logger.info("Listing custom dimensions for property %s", self.property_id)
        try:
            from google.analytics.admin_v1alpha import ListCustomDimensionsRequest

            request = ListCustomDimensionsRequest(parent=self.parent)
            response = self.client.list_custom_dimensions(request=request)

            dimensions = []
            for dim in response:
                dimensions.append({
                    "name": dim.name,
                    "parameter_name": dim.parameter_name,
                    "display_name": dim.display_name,
                    "description": dim.description,
                    "scope": str(dim.scope) if dim.scope else "",
                })

            return {"success": True, "dimensions": dimensions, "count": len(dimensions)}

        except Exception as exc:
            logger.error("List custom dimensions error: %s", exc)
            return {"success": False, "error": str(exc)}

    def create_custom_dimension(
        self,
        parameter_name: str,
        display_name: str,
        description: str = "",
        scope: str = "EVENT",
    ) -> dict[str, Any]:
        """Create a custom dimension.

        Args:
            parameter_name: Event parameter name (e.g., "customer_type").
            display_name: Human-readable name.
            description: Optional description.
            scope: "EVENT" or "USER".

        Returns:
            Dict with created dimension or error.
        """
        logger.info("Creating custom dimension: %s", parameter_name)
        try:
            from google.analytics.admin_v1alpha import (
                CreateCustomDimensionRequest,
                CustomDimension,
            )

            dim_scope = (
                CustomDimension.DimensionScope.EVENT
                if scope == "EVENT"
                else CustomDimension.DimensionScope.USER
            )

            custom_dim = CustomDimension(
                parameter_name=parameter_name,
                display_name=display_name,
                description=description,
                scope=dim_scope,
            )

            request = CreateCustomDimensionRequest(
                parent=self.parent,
                custom_dimension=custom_dim,
            )
            response = self.client.create_custom_dimension(request=request)

            return {
                "success": True,
                "name": response.name,
                "parameter_name": response.parameter_name,
                "display_name": response.display_name,
            }

        except Exception as exc:
            logger.error("Create custom dimension error: %s", exc)
            return {"success": False, "error": str(exc)}
