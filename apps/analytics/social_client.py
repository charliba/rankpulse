"""Social Media Client — Instagram Business + Facebook Page via Meta Graph API.

Uses the same access_token from Meta Ads (ChannelCredential) but with
additional scopes: instagram_basic, pages_read_engagement, instagram_insights.

The IDs (instagram_business_account_id, facebook_page_id) are stored in
ChannelCredential.extra JSON field.
"""
from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class SocialMediaClient:
    """Fetch Instagram Business and Facebook Page data via Graph API."""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self._session = requests.Session()
        self._session.headers["Accept"] = "application/json"

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        params = params or {}
        params["access_token"] = self.access_token
        url = f"{GRAPH_BASE}/{endpoint}"
        try:
            resp = self._session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.warning("Graph API error for %s: %s", endpoint, exc)
            return {}

    # ── Instagram Business ────────────────────────────────────

    def get_instagram_profile(self, ig_account_id: str) -> dict[str, Any]:
        """Fetch Instagram Business profile: bio, followers, media_count."""
        data = self._get(ig_account_id, {
            "fields": "id,username,name,biography,followers_count,follows_count,media_count,profile_picture_url,website",
        })
        if not data.get("id"):
            return {}
        return {
            "id": data.get("id"),
            "username": data.get("username", ""),
            "name": data.get("name", ""),
            "bio": data.get("biography", ""),
            "followers": data.get("followers_count", 0),
            "following": data.get("follows_count", 0),
            "media_count": data.get("media_count", 0),
            "profile_pic_url": data.get("profile_picture_url", ""),
            "website": data.get("website", ""),
        }

    def get_instagram_recent_posts(self, ig_account_id: str, limit: int = 25) -> list[dict]:
        """Fetch recent Instagram posts with engagement metrics."""
        data = self._get(f"{ig_account_id}/media", {
            "fields": "id,caption,media_type,media_url,thumbnail_url,timestamp,like_count,comments_count,permalink",
            "limit": min(limit, 50),
        })
        posts = []
        for item in data.get("data", []):
            likes = item.get("like_count", 0)
            comments = item.get("comments_count", 0)
            posts.append({
                "id": item.get("id"),
                "caption": (item.get("caption") or "")[:500],
                "media_type": item.get("media_type", ""),
                "timestamp": item.get("timestamp", ""),
                "likes": likes,
                "comments": comments,
                "engagement": likes + comments,
                "permalink": item.get("permalink", ""),
            })
        return posts

    # ── Facebook Page ─────────────────────────────────────────

    def get_facebook_page_info(self, page_id: str) -> dict[str, Any]:
        """Fetch Facebook Page info: about, fan_count, category."""
        data = self._get(page_id, {
            "fields": "id,name,about,category,fan_count,website,single_line_address,phone,cover",
        })
        if not data.get("id"):
            return {}
        return {
            "id": data.get("id"),
            "name": data.get("name", ""),
            "about": data.get("about", ""),
            "category": data.get("category", ""),
            "fan_count": data.get("fan_count", 0),
            "website": data.get("website", ""),
            "address": data.get("single_line_address", ""),
            "phone": data.get("phone", ""),
        }

    def get_facebook_recent_posts(self, page_id: str, limit: int = 25) -> list[dict]:
        """Fetch recent Facebook Page posts with reactions/shares."""
        data = self._get(f"{page_id}/posts", {
            "fields": "id,message,created_time,shares,reactions.summary(true),comments.summary(true),permalink_url",
            "limit": min(limit, 50),
        })
        posts = []
        for item in data.get("data", []):
            reactions = item.get("reactions", {}).get("summary", {}).get("total_count", 0)
            comments = item.get("comments", {}).get("summary", {}).get("total_count", 0)
            shares = item.get("shares", {}).get("count", 0)
            posts.append({
                "id": item.get("id"),
                "message": (item.get("message") or "")[:500],
                "timestamp": item.get("created_time", ""),
                "reactions": reactions,
                "comments": comments,
                "shares": shares,
                "engagement": reactions + comments + shares,
                "permalink": item.get("permalink_url", ""),
            })
        return posts
