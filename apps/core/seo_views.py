"""SEO views — robots.txt and sitemap.xml for RankPulse."""
from django.http import HttpResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET


@require_GET
@cache_page(3600)
def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "Allow: /privacy/",
        "Allow: /terms/",
        "",
        "Disallow: /admin/",
        "Disallow: /api/",
        "Disallow: /chat/",
        "Disallow: /login/",
        "Disallow: /register/",
        "Disallow: /logout/",
        "Disallow: /dashboard/",
        "",
        f"Sitemap: https://app.rankpulse.cloud/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


@require_GET
@cache_page(3600)
def sitemap_xml(request):
    urls = [
        ("https://app.rankpulse.cloud/", "1.0", "monthly"),
        ("https://app.rankpulse.cloud/privacy/", "0.5", "yearly"),
        ("https://app.rankpulse.cloud/terms/", "0.5", "yearly"),
    ]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for loc, priority, changefreq in urls:
        xml += f"  <url>\n    <loc>{loc}</loc>\n    <priority>{priority}</priority>\n    <changefreq>{changefreq}</changefreq>\n  </url>\n"
    xml += "</urlset>"
    return HttpResponse(xml, content_type="application/xml")
