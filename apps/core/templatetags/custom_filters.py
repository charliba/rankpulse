import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def _safe_json(obj):
    return mark_safe(json.dumps(obj, ensure_ascii=False))


@register.filter
def organic_card_json(data):
    """Serialize organic card data dict to JSON for Alpine.js bridge."""
    if not data or data.get("error"):
        return _safe_json({"_type": "organic"})
    return _safe_json({
        "_type": "organic",
        "sessions": data.get("sessions", 0),
        "sessions_prev": data.get("sessions_prev", 0),
        "gsc_clicks": data.get("gsc_clicks", 0),
        "gsc_impressions": data.get("gsc_impressions", 0),
        "gsc_clicks_prev": data.get("gsc_clicks_prev", 0),
        "gsc_impressions_prev": data.get("gsc_impressions_prev", 0),
        "gsc_ctr": data.get("gsc_ctr", 0),
        "gsc_position": data.get("gsc_position", 0),
        "top_queries": data.get("top_queries", []),
        "top_pages": data.get("top_pages", []),
        "daily": data.get("daily", []),
    })


@register.filter
def ads_card_json(data):
    """Serialize Google Ads card data dict to JSON for Alpine.js bridge."""
    if not data or not data.get("connected"):
        return _safe_json({"_type": "ads"})
    return _safe_json({
        "_type": "ads",
        "spend": data.get("spend", 0),
        "impressions": data.get("impressions", 0),
        "clicks": data.get("clicks", 0),
        "conversions": data.get("conversions", 0),
        "ctr": data.get("ctr", 0),
        "cpc": data.get("cpc", 0),
        "spend_prev": data.get("spend_prev", 0),
        "clicks_prev": data.get("clicks_prev", 0),
        "daily": data.get("daily", []),
        "campaigns_active": data.get("campaigns_active", 0),
        "campaigns_paused": data.get("campaigns_paused", 0),
    })


@register.filter
def meta_card_json(data):
    """Serialize Meta Ads card data dict to JSON for Alpine.js bridge."""
    if not data or not data.get("connected"):
        return _safe_json({"_type": "meta"})
    return _safe_json({
        "_type": "meta",
        "spend": data.get("spend", 0),
        "impressions": data.get("impressions", 0),
        "clicks": data.get("clicks", 0),
        "reach": data.get("reach", 0),
        "ctr": data.get("ctr", 0),
        "cpc": data.get("cpc", 0),
        "cpm": data.get("cpm", 0),
        "spend_prev": data.get("spend_prev", 0),
        "clicks_prev": data.get("clicks_prev", 0),
        "campaigns_active": data.get("campaigns_active", 0),
    })
