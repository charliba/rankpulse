"""GA4 Measurement Protocol Client.

Sends server-side events to Google Analytics 4 using the
Measurement Protocol API.

Reference: https://developers.google.com/analytics/devguides/collection/protocol/ga4
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Endpoints
GA4_COLLECT_URL = "https://www.google-analytics.com/mp/collect"
GA4_DEBUG_URL = "https://www.google-analytics.com/debug/mp/collect"


class GA4Client:
    """Client for GA4 Measurement Protocol.

    Usage:
        client = GA4Client(measurement_id="G-XXXXX", api_secret="secret")
        client.send_event("purchase", client_id="user123", params={
            "currency": "BRL", "value": 97.00, "transaction_id": "sub_abc"
        })
    """

    def __init__(self, measurement_id: str, api_secret: str) -> None:
        self.measurement_id = measurement_id
        self.api_secret = api_secret

    def _build_payload(
        self,
        event_name: str,
        client_id: str,
        params: dict[str, Any] | None = None,
        user_id: str | None = None,
        user_properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build the Measurement Protocol payload."""
        payload: dict[str, Any] = {
            "client_id": client_id,
            "events": [
                {
                    "name": event_name,
                    "params": params or {},
                }
            ],
        }
        if user_id:
            payload["user_id"] = user_id
        if user_properties:
            payload["user_properties"] = {
                k: {"value": v} for k, v in user_properties.items()
            }
        return payload

    def send_event(
        self,
        event_name: str,
        client_id: str | None = None,
        params: dict[str, Any] | None = None,
        user_id: str | None = None,
        user_properties: dict[str, Any] | None = None,
        debug: bool = False,
    ) -> dict[str, Any]:
        """Send a single event to GA4.

        Args:
            event_name: GA4 event name (e.g., 'purchase', 'sign_up').
            client_id: GA4 client_id. Auto-generated if not provided.
            params: Event parameters dict.
            user_id: Optional user identifier.
            user_properties: Optional user properties.
            debug: If True, uses debug endpoint for validation.

        Returns:
            Dict with 'status_code' and 'body' keys.
        """
        if not client_id:
            client_id = str(uuid.uuid4())

        payload = self._build_payload(
            event_name, client_id, params, user_id, user_properties,
        )

        url = GA4_DEBUG_URL if debug else GA4_COLLECT_URL
        query_params = {
            "measurement_id": self.measurement_id,
            "api_secret": self.api_secret,
        }

        logger.info(
            "Sending GA4 event: name=%s, client_id=%s, debug=%s",
            event_name, client_id, debug,
        )

        try:
            response = httpx.post(url, params=query_params, json=payload, timeout=10)
            result = {
                "status_code": response.status_code,
                "body": response.text,
                "success": response.status_code in (200, 204),
            }

            if debug and response.text:
                import json
                try:
                    validation = json.loads(response.text)
                    result["validation"] = validation
                    messages = validation.get("validationMessages", [])
                    if messages:
                        for msg in messages:
                            logger.warning("GA4 validation: %s", msg.get("description", msg))
                    else:
                        logger.info("GA4 event validated successfully")
                except json.JSONDecodeError:
                    pass

            return result

        except httpx.HTTPError as exc:
            logger.error("GA4 HTTP error: %s", exc)
            return {"status_code": 0, "body": str(exc), "success": False}

    def send_purchase(
        self,
        client_id: str,
        transaction_id: str,
        value: float,
        currency: str = "BRL",
        items: list[dict] | None = None,
        customer_type: str = "new",
        **extra_params: Any,
    ) -> dict[str, Any]:
        """Convenience method for purchase events."""
        params: dict[str, Any] = {
            "transaction_id": transaction_id,
            "currency": currency,
            "value": value,
            "customer_type": customer_type,
        }
        if items:
            params["items"] = items
        params.update(extra_params)
        return self.send_event("purchase", client_id=client_id, params=params)

    def send_sign_up(
        self,
        client_id: str,
        method: str = "email",
        **extra_params: Any,
    ) -> dict[str, Any]:
        """Convenience method for sign_up events."""
        params = {"method": method, **extra_params}
        return self.send_event("sign_up", client_id=client_id, params=params)

    def send_generate_lead(
        self,
        client_id: str,
        value: float = 50.0,
        currency: str = "BRL",
        lead_source: str = "organic",
        **extra_params: Any,
    ) -> dict[str, Any]:
        """Convenience method for generate_lead events."""
        params = {
            "currency": currency,
            "value": value,
            "lead_source": lead_source,
            **extra_params,
        }
        return self.send_event("generate_lead", client_id=client_id, params=params)

    def validate_event(
        self,
        event_name: str,
        client_id: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Validate an event using the debug endpoint."""
        return self.send_event(
            event_name, client_id=client_id, params=params, debug=True,
        )
