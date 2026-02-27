"""SEO auditor service — Crawls pages and evaluates SEO health."""
from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from django.utils import timezone

from apps.core.models import Site

from .models import PageScore, SEOAudit

logger = logging.getLogger(__name__)


class SEOAuditor:
    """Crawls a site and generates SEO scores per page."""

    HEADERS = {
        "User-Agent": "RankPulse SEO Auditor/1.0 (+https://rankpulse.cloud)",
    }
    TIMEOUT = 15

    def __init__(self, site: Site, max_pages: int = 50) -> None:
        self.site = site
        self.max_pages = max_pages
        self.audit: SEOAudit | None = None

    def run(self) -> SEOAudit:
        """Execute full SEO audit for the site."""
        self.audit = SEOAudit.objects.create(
            site=self.site,
            status="running",
            started_at=timezone.now(),
        )
        logger.info("Starting SEO audit for %s (audit #%d)", self.site.domain, self.audit.pk)

        try:
            urls = self._discover_urls()
            scores: list[int] = []

            for url in urls[:self.max_pages]:
                page_score = self._audit_page(url)
                if page_score:
                    scores.append(page_score.score)

            # Calculate overall scores
            self.audit.pages_crawled = len(scores)
            self.audit.overall_score = int(sum(scores) / len(scores)) if scores else 0

            page_scores = self.audit.page_scores.all()
            self.audit.meta_score = self._avg_field(page_scores, "has_title", "has_meta_description", "has_canonical", "has_og_tags")
            self.audit.content_score = self._avg_field(page_scores, "has_h1", "has_images_alt")
            self.audit.technical_score = self._avg_field(page_scores, "has_structured_data", "is_indexable")
            self.audit.issues_critical = sum(1 for p in page_scores if p.score < 40)
            self.audit.issues_warning = sum(1 for p in page_scores if 40 <= p.score < 70)
            self.audit.issues_info = sum(1 for p in page_scores if p.score >= 70)

            self.audit.recommendations = self._generate_recommendations(page_scores)
            self.audit.status = "completed"
            self.audit.completed_at = timezone.now()
            self.audit.save()

            logger.info("Audit completed: %d pages, score %d/100", len(scores), self.audit.overall_score)

        except Exception as e:
            logger.exception("Audit failed for %s: %s", self.site.domain, e)
            self.audit.status = "failed"
            self.audit.completed_at = timezone.now()
            self.audit.save()

        return self.audit

    def _discover_urls(self) -> list[str]:
        """Discover URLs from sitemap or by crawling homepage."""
        urls: list[str] = [self.site.url]

        # Try sitemap first
        sitemap_url = self.site.sitemap_url or f"{self.site.url}/sitemap.xml"
        try:
            resp = requests.get(sitemap_url, headers=self.HEADERS, timeout=self.TIMEOUT)
            if resp.status_code == 200 and "xml" in resp.headers.get("content-type", ""):
                soup = BeautifulSoup(resp.text, "lxml")
                for loc in soup.find_all("loc"):
                    url = loc.text.strip()
                    if urlparse(url).netloc == urlparse(self.site.url).netloc:
                        urls.append(url)
                logger.info("Found %d URLs from sitemap", len(urls))
                return list(dict.fromkeys(urls))[:self.max_pages]
        except Exception:
            logger.debug("Sitemap not available at %s", sitemap_url)

        # Fallback: crawl homepage for links
        try:
            resp = requests.get(self.site.url, headers=self.HEADERS, timeout=self.TIMEOUT)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                base_domain = urlparse(self.site.url).netloc
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    full_url = urljoin(self.site.url, href)
                    if urlparse(full_url).netloc == base_domain:
                        urls.append(full_url)
        except Exception:
            pass

        return list(dict.fromkeys(urls))[:self.max_pages]

    def _audit_page(self, url: str) -> PageScore | None:
        """Audit a single page and return its score."""
        try:
            start = time.time()
            resp = requests.get(url, headers=self.HEADERS, timeout=self.TIMEOUT)
            load_time = int((time.time() - start) * 1000)

            if resp.status_code != 200:
                return PageScore.objects.create(
                    audit=self.audit,
                    url=url,
                    score=0,
                    http_status=resp.status_code,
                    load_time_ms=load_time,
                    issues=[{"severity": "critical", "msg": f"HTTP {resp.status_code}"}],
                )

            soup = BeautifulSoup(resp.text, "html.parser")
            issues: list[dict[str, str]] = []

            # Title
            title_tag = soup.find("title")
            has_title = bool(title_tag and title_tag.text.strip())
            title_length = len(title_tag.text.strip()) if has_title else 0
            if not has_title:
                issues.append({"severity": "critical", "msg": "Sem tag <title>"})
            elif title_length < 30 or title_length > 65:
                issues.append({"severity": "warning", "msg": f"Title com {title_length} chars (ideal: 30-65)"})

            # Meta description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            has_meta_description = bool(meta_desc and meta_desc.get("content", "").strip())
            meta_description_length = len(meta_desc["content"].strip()) if has_meta_description else 0
            if not has_meta_description:
                issues.append({"severity": "critical", "msg": "Sem meta description"})
            elif meta_description_length < 70 or meta_description_length > 160:
                issues.append({"severity": "warning", "msg": f"Meta description com {meta_description_length} chars (ideal: 70-160)"})

            # Canonical
            canonical = soup.find("link", attrs={"rel": "canonical"})
            has_canonical = bool(canonical)
            if not has_canonical:
                issues.append({"severity": "warning", "msg": "Sem tag canonical"})

            # OG Tags
            og_title = soup.find("meta", property="og:title")
            og_desc = soup.find("meta", property="og:description")
            has_og_tags = bool(og_title and og_desc)
            if not has_og_tags:
                issues.append({"severity": "info", "msg": "Sem Open Graph tags completas"})

            # H1
            h1_tags = soup.find_all("h1")
            h1_count = len(h1_tags)
            has_h1 = h1_count == 1
            if h1_count == 0:
                issues.append({"severity": "critical", "msg": "Sem tag H1"})
            elif h1_count > 1:
                issues.append({"severity": "warning", "msg": f"{h1_count} tags H1 (ideal: 1)"})

            # H2
            h2_count = len(soup.find_all("h2"))

            # Word count
            text = soup.get_text(separator=" ", strip=True)
            word_count = len(text.split())
            if word_count < 300:
                issues.append({"severity": "warning", "msg": f"Conteúdo curto ({word_count} palavras)"})

            # Images
            images = soup.find_all("img")
            images_total = len(images)
            images_missing_alt = sum(1 for img in images if not img.get("alt", "").strip())
            has_images_alt = images_missing_alt == 0 and images_total > 0
            if images_missing_alt > 0:
                issues.append({"severity": "warning", "msg": f"{images_missing_alt}/{images_total} imagens sem alt"})

            # Structured data (JSON-LD)
            json_ld = soup.find_all("script", type="application/ld+json")
            has_structured_data = len(json_ld) > 0
            structured_data_types: list[str] = []
            if has_structured_data:
                import json as json_module
                for script in json_ld:
                    try:
                        data = json_module.loads(script.string)
                        if isinstance(data, dict) and "@type" in data:
                            structured_data_types.append(data["@type"])
                    except Exception:
                        pass
            if not has_structured_data:
                issues.append({"severity": "info", "msg": "Sem dados estruturados (JSON-LD)"})

            # Robots meta
            robots_meta = soup.find("meta", attrs={"name": "robots"})
            has_robots_meta = bool(robots_meta)
            is_indexable = True
            if robots_meta:
                content = robots_meta.get("content", "").lower()
                is_indexable = "noindex" not in content

            # Calculate score
            score = self._calculate_score(
                has_title=has_title,
                title_length=title_length,
                has_meta_description=has_meta_description,
                has_canonical=has_canonical,
                has_og_tags=has_og_tags,
                has_h1=has_h1,
                word_count=word_count,
                has_images_alt=has_images_alt,
                has_structured_data=has_structured_data,
                load_time=load_time,
            )

            return PageScore.objects.create(
                audit=self.audit,
                url=url,
                score=score,
                has_title=has_title,
                title_length=title_length,
                has_meta_description=has_meta_description,
                meta_description_length=meta_description_length,
                has_canonical=has_canonical,
                has_og_tags=has_og_tags,
                has_h1=has_h1,
                h1_count=h1_count,
                h2_count=h2_count,
                word_count=word_count,
                has_images_alt=has_images_alt,
                images_total=images_total,
                images_missing_alt=images_missing_alt,
                has_structured_data=has_structured_data,
                structured_data_types=structured_data_types,
                has_robots_meta=has_robots_meta,
                is_indexable=is_indexable,
                http_status=resp.status_code,
                load_time_ms=load_time,
                issues=issues,
            )

        except Exception as e:
            logger.warning("Failed to audit %s: %s", url, e)
            return None

    @staticmethod
    def _calculate_score(**kwargs: Any) -> int:
        """Calculate page SEO score (0-100)."""
        score = 0
        # Meta tags (30 pts)
        if kwargs.get("has_title"):
            score += 10
            if 30 <= kwargs.get("title_length", 0) <= 65:
                score += 5
        if kwargs.get("has_meta_description"):
            score += 10
        if kwargs.get("has_canonical"):
            score += 5

        # Content (30 pts)
        if kwargs.get("has_h1"):
            score += 10
        wc = kwargs.get("word_count", 0)
        if wc >= 300:
            score += 10
        elif wc >= 100:
            score += 5
        if kwargs.get("has_images_alt"):
            score += 5
        if kwargs.get("has_og_tags"):
            score += 5

        # Technical (30 pts)
        if kwargs.get("has_structured_data"):
            score += 15
        lt = kwargs.get("load_time", 5000)
        if lt < 1000:
            score += 15
        elif lt < 2000:
            score += 10
        elif lt < 3000:
            score += 5

        # Bonus (10 pts)
        if score >= 80:
            score = min(score + 10, 100)

        return min(score, 100)

    @staticmethod
    def _avg_field(page_scores: Any, *bool_fields: str) -> int:
        """Average boolean fields as percentage score."""
        if not page_scores:
            return 0
        total = 0
        count = 0
        for ps in page_scores:
            for field in bool_fields:
                total += 1 if getattr(ps, field, False) else 0
                count += 1
        return int(total / count * 100) if count else 0

    @staticmethod
    def _generate_recommendations(page_scores: Any) -> list[dict[str, str]]:
        """Generate actionable recommendations from audit results."""
        recs: list[dict[str, str]] = []
        pages = list(page_scores)
        if not pages:
            return recs

        no_title = [p for p in pages if not p.has_title]
        if no_title:
            recs.append({
                "priority": "critical",
                "action": f"Adicionar <title> em {len(no_title)} página(s)",
                "pages": [p.url for p in no_title[:5]],
            })

        no_desc = [p for p in pages if not p.has_meta_description]
        if no_desc:
            recs.append({
                "priority": "critical",
                "action": f"Adicionar meta description em {len(no_desc)} página(s)",
                "pages": [p.url for p in no_desc[:5]],
            })

        no_h1 = [p for p in pages if not p.has_h1]
        if no_h1:
            recs.append({
                "priority": "high",
                "action": f"Corrigir H1 em {len(no_h1)} página(s)",
                "pages": [p.url for p in no_h1[:5]],
            })

        no_schema = [p for p in pages if not p.has_structured_data]
        if no_schema:
            recs.append({
                "priority": "medium",
                "action": f"Adicionar JSON-LD em {len(no_schema)} página(s)",
                "pages": [p.url for p in no_schema[:5]],
            })

        slow_pages = [p for p in pages if p.load_time_ms > 3000]
        if slow_pages:
            recs.append({
                "priority": "high",
                "action": f"Otimizar performance em {len(slow_pages)} página(s) (>3s)",
                "pages": [p.url for p in slow_pages[:5]],
            })

        return recs
