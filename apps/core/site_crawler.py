"""Site Crawler — Deep URL discovery using Crawl4AI + sitemap + BFS.

Discovers all pages on a client's site for brand intelligence,
cross-referencing with Google Search Console and GA4 data.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────────────

MAX_PAGES = 100
REQUEST_DELAY = 1.0  # seconds between requests
USER_AGENT = "RankPulse-Crawler/1.0 (Site Intelligence Bot)"
TIMEOUT = 15


def _normalize_url(url: str, base: str) -> str | None:
    """Normalize a URL relative to base, filtering non-page URLs."""
    if not url:
        return None
    # Skip non-http, anchors-only, mailto, tel, javascript
    if url.startswith(("mailto:", "tel:", "javascript:", "#", "data:")):
        return None

    absolute = urljoin(base, url)
    parsed = urlparse(absolute)

    # Only http(s)
    if parsed.scheme not in ("http", "https"):
        return None

    # Strip fragment
    clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if parsed.query:
        clean += f"?{parsed.query}"

    # Remove trailing slash for consistency
    clean = clean.rstrip("/")

    return clean


def _is_same_domain(url: str, base_domain: str) -> bool:
    """Check if URL belongs to the same domain."""
    parsed = urlparse(url)
    host = parsed.netloc.lower().lstrip("www.")
    return host == base_domain.lower().lstrip("www.")


def _skip_extension(url: str) -> bool:
    """Skip non-page file extensions."""
    path = urlparse(url).path.lower()
    skip_exts = (
        ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
        ".pdf", ".zip", ".rar", ".tar", ".gz",
        ".css", ".js", ".map", ".woff", ".woff2", ".ttf", ".eot",
        ".mp3", ".mp4", ".avi", ".mov", ".webm",
        ".xml", ".json", ".txt",
    )
    return any(path.endswith(ext) for ext in skip_exts)


def _fetch_sitemap_urls(base_url: str) -> list[str]:
    """Try to extract URLs from sitemap.xml."""
    urls = []
    sitemap_locations = [
        f"{base_url.rstrip('/')}/sitemap.xml",
        f"{base_url.rstrip('/')}/sitemap_index.xml",
    ]

    for sitemap_url in sitemap_locations:
        try:
            resp = requests.get(
                sitemap_url,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT,
            )
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "lxml-xml")

            # Check for sitemap index
            sitemaps = soup.find_all("sitemap")
            if sitemaps:
                for sm in sitemaps[:5]:  # limit sub-sitemaps
                    loc = sm.find("loc")
                    if loc and loc.text:
                        try:
                            sub_resp = requests.get(
                                loc.text.strip(),
                                headers={"User-Agent": USER_AGENT},
                                timeout=TIMEOUT,
                            )
                            sub_soup = BeautifulSoup(sub_resp.text, "lxml-xml")
                            for url_tag in sub_soup.find_all("url"):
                                loc_tag = url_tag.find("loc")
                                if loc_tag and loc_tag.text:
                                    urls.append(loc_tag.text.strip())
                        except Exception:
                            continue

            # Direct URL entries
            for url_tag in soup.find_all("url"):
                loc = url_tag.find("loc")
                if loc and loc.text:
                    urls.append(loc.text.strip())

            if urls:
                break

        except Exception as e:
            logger.debug("Sitemap fetch failed for %s: %s", sitemap_url, e)

    return urls[:MAX_PAGES * 2]


def _bfs_crawl(base_url: str, known_urls: set[str], max_pages: int) -> list[dict]:
    """BFS crawl from base_url, extracting links and basic page info."""
    base_domain = urlparse(base_url).netloc.lower().lstrip("www.")
    visited: set[str] = set()
    queue = [base_url.rstrip("/")]
    results = []

    # Add known URLs to queue
    for url in known_urls:
        normalized = url.rstrip("/")
        if normalized not in queue:
            queue.append(normalized)

    while queue and len(results) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        if _skip_extension(url):
            continue
        if not _is_same_domain(url, base_domain):
            continue

        visited.add(url)
        time.sleep(REQUEST_DELAY)

        try:
            resp = requests.get(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
                timeout=TIMEOUT,
                allow_redirects=True,
            )

            page_info = {
                "url": url,
                "status": resp.status_code,
                "title": "",
                "word_count": 0,
            }

            if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                soup = BeautifulSoup(resp.text[:100_000], "html.parser")

                # Extract title
                title_tag = soup.find("title")
                if title_tag:
                    page_info["title"] = title_tag.get_text(strip=True)[:200]

                # Word count
                text = soup.get_text(separator=" ", strip=True)
                page_info["word_count"] = len(text.split())

                # Extract links for further crawling
                for a_tag in soup.find_all("a", href=True):
                    link = _normalize_url(a_tag["href"], url)
                    if link and link not in visited and _is_same_domain(link, base_domain):
                        if link not in queue:
                            queue.append(link)

            results.append(page_info)

        except Exception as e:
            logger.debug("Crawl error for %s: %s", url, e)
            results.append({"url": url, "status": 0, "title": "", "word_count": 0})

    return results


def discover_all_urls(base_url: str, max_pages: int = MAX_PAGES) -> list[dict]:
    """Discover all pages on a site using sitemap + BFS crawl.

    Returns list of dicts: [{"url": ..., "title": ..., "status": ..., "word_count": ...}]
    """
    if not base_url:
        return []

    # Ensure scheme
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"

    logger.info("Starting site discovery for %s (max %d pages)", base_url, max_pages)

    # Step 1: Try sitemap
    sitemap_urls = set(_fetch_sitemap_urls(base_url))
    logger.info("Sitemap yielded %d URLs", len(sitemap_urls))

    # Step 2: BFS crawl with sitemap seeds
    results = _bfs_crawl(base_url, sitemap_urls, max_pages)

    logger.info("Discovered %d pages for %s", len(results), base_url)
    return results


def cross_reference_gsc(discovered_urls: list[dict], gsc_pages: list[dict]) -> dict:
    """Cross-reference discovered URLs with Google Search Console data.

    Returns summary of indexed vs not indexed pages.
    """
    discovered_set = {u["url"].rstrip("/").lower() for u in discovered_urls}
    gsc_set = {p.get("page", "").rstrip("/").lower() for p in gsc_pages if p.get("page")}

    in_both = discovered_set & gsc_set
    only_crawl = discovered_set - gsc_set
    only_gsc = gsc_set - discovered_set

    return {
        "total_discovered": len(discovered_set),
        "total_in_gsc": len(gsc_set),
        "indexed_and_found": len(in_both),
        "not_indexed": list(only_crawl)[:50],
        "in_gsc_but_not_found": list(only_gsc)[:50],
    }
