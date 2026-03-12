"""AI Audit Engine V2 — Cache-first data collection, Brand DNA persistence,
multi-call AI analysis, and progress tracking.

Architecture:
    1. Brand DNA — scraped once, stored in BrandProfile, refreshed intelligently
    2. Data Cache — all API data stored in DataSnapshot with per-type TTL
    3. Multi-call AI — separate Meta/Google/Synthesis calls for depth
    4. Progress — AuditReport.progress_step updated at each phase
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def _safe_format(template: str, **kwargs) -> str:
    """Safe string formatting — escapes { } in values so .format() won't crash."""
    safe = {k: str(v).replace("{", "{{").replace("}", "}}") for k, v in kwargs.items()}
    return template.format(**safe)


# ── Constants ───────────────────────────────────────────────────

# -- Prompt for building Brand DNA from scraped content --
BRAND_DNA_PROMPT = """Analise o conteúdo abaixo (site + redes sociais) e gere um "Brand DNA" estruturado.

═══ CONTEÚDO DO SITE ═══
{website_content}

═══ INSTAGRAM ═══
{instagram_data}

═══ FACEBOOK ═══
{facebook_data}

Retorne JSON puro:
{{
    "brand_summary": "<resumo de 3-5 parágrafos: o que a empresa faz, para quem, tom de comunicação, posicionamento>",
    "target_audience": "<público-alvo detalhado: idade, gênero, interesses, nível socioeconômico, dores, desejos>",
    "tone_of_voice": "<formal|informal|técnico|jovem|premium|amigável|etc>",
    "key_services": ["<serviço 1>", "<serviço 2>", ...],
    "differentiators": "<diferenciais competitivos identificados>"
}}"""

# -- Platform-specific audit prompts --
META_ADS_AUDIT_PROMPT = """Você é o auditor de Meta Ads mais experiente do mundo — 15+ anos gerenciando milhões em Facebook/Instagram Ads.
Analise CADA detalhe dos dados abaixo e gere recomendações BRUTALMENTE específicas.

═══ BRAND DNA (entendimento do negócio) ═══
{brand_dna}

═══ OBJETIVOS DO NEGÓCIO ═══
{business_goals}

═══ HISTÓRICO DE FEEDBACK DO USUÁRIO ═══
{learning_context}

═══ CONHECIMENTO ESPECIALISTA ═══
{expert_knowledge}

═══ DADOS COMPLETOS META ADS ═══
{meta_data}

═══ ANÁLISE OBRIGATÓRIA — CHECKLIST ═══
1. ESTRUTURA: Hierarquia Campanha → Conjunto → Anúncio. Muitos conjuntos sem resultados? Consolidar.
2. PÚBLICO-ALVO: Targeting de cada conjunto — idade, gênero, interesses, comportamentos, geo c/ raio. Amplo demais? Estreito demais?
3. CRIATIVOS: Títulos, textos, CTAs, imagens vs vídeos. Variações A/B? Copy alinhada com Brand DNA?
4. POSICIONAMENTO: Performance por Feed vs Stories vs Reels vs Audience Network. Onde investir mais?
5. DEMOGRAFIA: Age × gender. Faixa etária que mais converte vs que mais gasta?
6. PERFORMANCE POR ANÚNCIO: Quais anúncios com melhor CTR/CPC? Quais pausar?
7. FREQUÊNCIA: Frequência > 3 = fadiga. Sugerir expansão ou rotação de criativos.
8. OBJETIVO vs RESULTADO: Objetivo (tráfego/leads/vendas) alinhado com o que a empresa precisa?
9. ORÇAMENTO: Redistribuir entre campanhas/conjuntos que performam melhor.
10. PÚBLICOS NEGATIVOS: Excluir convertidos? Funcionários? Audiências irrelevantes?

═══ REGRAS ═══
- Cite dados REAIS: nomes de campanhas, IDs, CTR exato, CPC exato, gasto exato.
- Cada rec: PROBLEMA → SOLUÇÃO → IMPACTO ESPERADO.
- Gere 5-15 recomendações.
- NUNCA altere orçamento total, apenas redistribua.

═══ RESPOSTA JSON ═══
{{
    "platform_score": <int 0-100>,
    "platform_analysis": "<análise de 2-3 parágrafos>",
    "recommendations": [
        {{
            "platform": "meta_ads",
            "category": "<targeting|audience_age|audience_interests|audience_geo|creative|creative_copy|creative_format|placement|frequency|campaign_structure|budget_allocation|objective_mismatch|other>",
            "impact": "critical|high|medium|low",
            "title": "<título conciso>",
            "explanation": "<explicação com dados reais>",
            "action_description": "<ação concreta>",
            "can_auto_apply": true|false,
            "estimated_points": <int 1-25: critical=15-25, high=10-15, medium=5-10, low=1-5>,
            "campaign_id": "<ID>",
            "campaign_name": "<nome>",
            "action_payload": {{}}
        }}
    ]
}}"""

GOOGLE_ADS_AUDIT_PROMPT = """Você é o auditor de Google Ads mais experiente do mundo — 15+ anos gerenciando milhões em Search/Display/Shopping.
Analise CADA detalhe dos dados abaixo e gere recomendações BRUTALMENTE específicas.

═══ BRAND DNA (entendimento do negócio) ═══
{brand_dna}

═══ OBJETIVOS DO NEGÓCIO ═══
{business_goals}

═══ HISTÓRICO DE FEEDBACK DO USUÁRIO ═══
{learning_context}

═══ CONHECIMENTO ESPECIALISTA ═══
{expert_knowledge}

═══ DADOS COMPLETOS GOOGLE ADS ═══
{google_data}

═══ ANÁLISE OBRIGATÓRIA — CHECKLIST ═══
1. TERMOS DE BUSCA: Termos reais que ativaram anúncios. Irrelevantes → palavras-chave negativas.
2. QUALITY SCORE: Keywords com QS < 7 → atenção (landing page, relevância, CTR esperado).
3. COPY DOS ANÚNCIOS: Headlines e descriptions. São específicos? CTA? Números/benefícios?
4. EXTENSÕES: Sitelinks, callouts, snippets existem? Faltam? São relevantes?
5. MATCH TYPES: Broad demais desperdiça orçamento. Analisar match types de cada keyword.
6. ESTRUTURA: Muitas keywords num só ad group? Sugerir SKAG ou grupos temáticos.
7. LANCE: Manual vs automatizado. Faz sentido para o volume de conversões?
8. REDES: Display sem querer? Search Partners habilitado desnecessariamente?
9. GEO-TARGETING: Localização correta para o negócio?

═══ REGRAS ═══
- Cite dados REAIS: nomes de campanhas, IDs, QS exato, CTR, CPC, termos de busca.
- Cada rec: PROBLEMA → SOLUÇÃO → IMPACTO ESPERADO.
- Gere 5-15 recomendações.
- NUNCA altere orçamento total, apenas redistribua.

═══ RESPOSTA JSON ═══
{{
    "platform_score": <int 0-100>,
    "platform_analysis": "<análise de 2-3 parágrafos>",
    "recommendations": [
        {{
            "platform": "google_ads",
            "category": "<negative_keywords|sitelinks|callouts|ad_copy|bidding|targeting|keywords|quality_score|campaign_structure|landing_page|conversion_tracking|other>",
            "impact": "critical|high|medium|low",
            "title": "<título conciso>",
            "explanation": "<explicação com dados reais>",
            "action_description": "<ação concreta>",
            "can_auto_apply": true|false,
            "estimated_points": <int 1-25: critical=15-25, high=10-15, medium=5-10, low=1-5>,
            "campaign_id": "<ID>",
            "campaign_name": "<nome>",
            "action_payload": {{}}
        }}
    ]
}}"""

SYNTHESIS_AUDIT_PROMPT = """Você é o auditor de tráfego digital mais experiente do mundo. Analise os resultados abaixo das auditorias de Meta Ads e Google Ads + dados de SEO e gere uma SÍNTESE cross-platform.

═══ BRAND DNA ═══
{brand_dna}

═══ OBJETIVOS DO NEGÓCIO ═══
{business_goals}

═══ HISTÓRICO DE FEEDBACK DO USUÁRIO ═══
{learning_context}

═══ CONHECIMENTO ESPECIALISTA ═══
{expert_knowledge}

═══ RESULTADO AUDITORIA META ADS ═══
Score: {meta_score}/100
Análise: {meta_analysis}
Recomendações: {meta_rec_count}

═══ RESULTADO AUDITORIA GOOGLE ADS ═══
Score: {google_score}/100
Análise: {google_analysis}
Recomendações: {google_rec_count}

═══ DADOS SEO (Google Search Console) ═══
{seo_data}

═══ ANÁLISE OBRIGATÓRIA ═══
1. CONSISTÊNCIA DE MARCA: Ad copy Meta vs Google vs site — tom e mensagem alinhados?
2. SINERGIA: Plataformas se complementam (remarketing, funil)?
3. DISTRIBUIÇÃO DE ORÇAMENTO: Onde investir mais com base no ROI de cada plataforma?
4. SEO: Queries com alta impressão mas CTR < 3%? Keywords posição 4-20 (oportunidades)?
5. GAPS: O que está faltando? Remarketing? Conversão tracking? Long-tail?

═══ RESPOSTA JSON ═══
{{
    "overall_score": <int 0-100 — média ponderada das plataformas + ajuste por sinergia>,
    "overall_analysis": "<análise geral de 3-5 parágrafos: visão holística, pontos fortes/fracos, oportunidades>",
    "recommendations": [
        {{
            "platform": "seo|general",
            "category": "<indexing|content_gap|landing_page|conversion_tracking|other>",
            "impact": "critical|high|medium|low",
            "title": "<título>",
            "explanation": "<explicação>",
            "action_description": "<ação>",
            "can_auto_apply": true|false,
            "estimated_points": <int 1-25: critical=15-25, high=10-15, medium=5-10, low=1-5>,
            "campaign_id": "",
            "campaign_name": "",
            "action_payload": {{}}
        }}
    ]
}}"""

# -- GA4 Analytics audit prompt --
GA4_AUDIT_PROMPT = """Você é um especialista em GA4 Analytics. Analise os dados de analytics abaixo e gere recomendações acionáveis para melhorar o desempenho do site.

═══ BRAND DNA ═══
{brand_dna}

═══ OBJETIVOS DO NEGÓCIO ═══
{business_goals}

═══ HISTÓRICO DE FEEDBACK DO USUÁRIO ═══
{learning_context}

═══ CONHECIMENTO ESPECIALISTA ═══
{expert_knowledge}

═══ DADOS GA4 ANALYTICS (30 DIAS) ═══
{ga4_data}

═══ ANÁLISE OBRIGATÓRIA ═══
1. FONTES DE TRÁFEGO: Qual canal traz mais sessões? O mix é saudável ou há dependência excessiva de um canal?
2. TRÁFEGO ORGÂNICO: Tendência de crescimento ou queda? Volume adequado para o negócio?
3. TOP PÁGINAS: Quais páginas mais visitadas? Bounce rate alto em páginas importantes?
4. CONVERSÕES: Quais eventos de conversão existem? Volume adequado? Funil com gargalos?
5. DISPOSITIVOS: Mobile vs Desktop — experiência mobile otimizada? Bounce rate mobile alto?
6. DEMOGRAFIA: Público real alinhado com público-alvo do negócio?

═══ RESPOSTA JSON ═══
{{
    "platform_score": <int 0-100>,
    "platform_analysis": "<análise de 2-3 parágrafos>",
    "recommendations": [
        {{
            "platform": "general",
            "category": "<landing_page|conversion_tracking|content_gap|other>",
            "impact": "critical|high|medium|low",
            "title": "<título>",
            "explanation": "<explicação com dados reais>",
            "action_description": "<ação concreta>",
            "can_auto_apply": false,
            "estimated_points": <int 1-25: critical=15-25, high=10-15, medium=5-10, low=1-5>,
            "campaign_id": "",
            "campaign_name": "",
            "action_payload": {{}}
        }}
    ]
}}"""

# -- Legacy single-call prompt (used when only one platform available) --
AUDIT_SYSTEM_PROMPT = """Você é o auditor de tráfego mais experiente do mundo — 15+ anos gerenciando milhões em Google Ads, Meta Ads e SEO.
Você NÃO faz análises genéricas. Cada recomendação DEVE ser ESPECÍFICA com dados reais do relatório.

═══ CONTEXTO DO NEGÓCIO ═══
{business_context}

═══ DADOS COMPLETOS DAS CAMPANHAS ═══
{campaign_data}

═══ DADOS DE SEO (Google Search Console) ═══
{seo_data}

═══ COMO ANALISAR ═══

**META ADS — Análise profunda obrigatória:**
1. ESTRUTURA: Avaliar hierarquia Campanha → Conjunto → Anúncio. Muitos conjuntos sem resultados? Consolidar.
2. PÚBLICO-ALVO: Analisar targeting de cada conjunto — idade, gênero, interesses, comportamentos, localização com raio. O público é amplo demais? Estreito demais? Interesses fazem sentido para o negócio?
3. CRIATIVOS: Analisar títulos, textos, CTAs, imagens vs vídeos. Variações A/B existem? Copy está boa?
4. POSICIONAMENTO: Analisar performance por Feed vs Stories vs Reels vs Audience Network. Onde gastar mais?
5. DEMOGRAFIA: Analisar age × gender. Faixa etária que mais converte vs que mais gasta?
6. PERFORMANCE POR ANÚNCIO: Quais anúncios específicos têm melhor CTR/CPC? Quais devem pausar?
7. FREQUÊNCIA: Frequência > 3 indica fadiga de público. Sugerir expansão ou rotação de criativos.
8. OBJETIVO vs RESULTADO: O objetivo da campanha (tráfego, leads, vendas) está alinhado com o que a empresa precisa?
9. ORÇAMENTO ALOCAÇÃO: Mesmo sem alterar valor total, redistribuir entre campanhas/conjuntos que performam melhor.
10. PÚBLICOS NEGATIVOS: Excluir quem já converteu? Excluir funcionários? Excluir audiências irrelevantes?

**GOOGLE ADS — Análise profunda obrigatória:**
1. TERMOS DE BUSCA: Analisar termos reais que ativaram os anúncios. Termos irrelevantes → negativas.
2. QUALITY SCORE: Keywords com QS < 7 precisam de atenção (landing page, relevância, CTR esperado).
3. COPY DOS ANÚNCIOS: Analisar headlines e descriptions. São específicos? Têm CTA? Usam números/benefícios?
4. EXTENSÕES: Quantos sitelinks, callouts, snippets existem? Faltam? São relevantes?
5. TIPOS DE CORRESPONDÊNCIA: Usar broad demais desperdiça orçamento. Analisar match types.
6. ESTRUTURA DE GRUPOS: Muitas keywords num só ad group? Sugerir SKAG ou grupos temáticos.
7. ESTRATÉGIA DE LANCE: Manual vs automatizado. Faz sentido para o volume?
8. REDES: Está mostrando em Display sem querer? Search Network habilitado desnecessariamente?
9. GEO-TARGETING: Localização correta? Faz sentido para o negócio?

**SEO — Análise profunda:**
1. Queries com alta impressão mas CTR < 3% → melhorar title/meta description.
2. Keywords na posição 4-20 → oportunidades de otimização.
3. Páginas com impressões mas sem cliques → problemas de snippet.
4. Gaps entre queries buscadas e conteúdo existente.
5. Oportunidades de indexação novas.

═══ REGRAS ABSOLUTAS ═══
1. NUNCA sugira alteração de orçamento total (apenas redistribuição).
2. Cite dados REAIS: nomes de campanhas, IDs, números exatos do relatório.
3. Cada recomendação deve explicar O PROBLEMA → A SOLUÇÃO → O IMPACTO ESPERADO.
4. Gere entre 8 e 25 recomendações — mais é melhor se houver dados suficientes.
5. Seja BRUTALMENTE honesto. Se algo está péssimo, diga claramente.

═══ FORMATO DE RESPOSTA (JSON) ═══
{{
    "overall_score": <int 0-100>,
    "overall_analysis": "<análise geral de 3-5 parágrafos cobrindo pontos fortes, fracos e oportunidades>",
    "recommendations": [
        {{
            "platform": "google_ads|meta_ads|seo|general",
            "category": "<negative_keywords|sitelinks|callouts|ad_copy|bidding|targeting|audience_age|audience_gender|audience_interests|audience_geo|audience_custom|audience_exclusion|ad_schedule|keywords|quality_score|campaign_structure|creative|creative_copy|creative_format|placement|frequency|landing_page|conversion_tracking|indexing|content_gap|budget_allocation|objective_mismatch|other>",
            "impact": "critical|high|medium|low",
            "title": "<título conciso>",
            "explanation": "<explicação detalhada com dados reais do relatório: cite nomes, números, IDs>",
            "action_description": "<ação concreta a executar>",
            "can_auto_apply": true|false,
            "campaign_id": "<ID da campanha ou vazio>",
            "campaign_name": "<nome da campanha ou vazio>",
            "action_payload": {{ ...payload se auto-aplicável... }}
        }}
    ]
}}

═══ AÇÕES AUTO-APLICÁVEIS (action_payload) ═══

Google Ads:
- add_negative_keywords: {{"action_type": "add_negative_keywords", "campaign_id": "...", "keywords": [{{"text": "...", "match_type": "BROAD|PHRASE|EXACT"}}]}}
- create_sitelink: {{"action_type": "create_sitelink", "campaign_id": "...", "link_text": "...", "final_url": "...", "description1": "...", "description2": "..."}}
- create_callout: {{"action_type": "create_callout", "campaign_id": "...", "callout_text": "..."}}
- create_structured_snippet: {{"action_type": "create_structured_snippet", "campaign_id": "...", "header": "...", "values": ["...", "..."]}}
- add_keywords: {{"action_type": "add_keywords", "ad_group_id": "...", "keywords": [{{"text": "...", "match_type": "BROAD|PHRASE|EXACT"}}]}}

Meta Ads:
- update_targeting: {{"action_type": "update_targeting", "ad_set_id": "...", "targeting": {{"age_min": ..., "age_max": ..., ...}}}}
- update_ad_set: {{"action_type": "update_ad_set", "ad_set_id": "...", "fields": {{...}}}}
- pause_campaign: {{"action_type": "pause_campaign", "campaign_id": "..."}}
- activate_campaign: {{"action_type": "activate_campaign", "campaign_id": "..."}}
- pause_ad_set: {{"action_type": "pause_ad_set", "ad_set_id": "..."}}
- activate_ad_set: {{"action_type": "activate_ad_set", "ad_set_id": "..."}}
- create_campaign: {{"action_type": "create_campaign", "name": "...", "objective": "OUTCOME_TRAFFIC", "daily_budget_brl": ..., "status": "PAUSED"}}
- create_ad_set: {{"action_type": "create_ad_set", "campaign_id": "...", "name": "...", "daily_budget_brl": ..., "targeting": {{...}}, "optimization_goal": "LINK_CLICKS"}}
- create_ad: {{"action_type": "create_ad", "ad_set_id": "...", "name": "...", "page_id": "...", "link_url": "...", "message": "..."}}
- update_campaign_budget: {{"action_type": "update_campaign_budget", "campaign_id": "...", "daily_budget": ...}}

SEO:
- submit_url_for_indexing: {{"action_type": "submit_url_for_indexing", "urls": ["..."]}}

Se a ação requer intervenção humana (criar novo criativo, reestruturar campanhas, etc.), use can_auto_apply=false."""


# ── Progress Helper ──────────────────────────────────────────────

def _update_progress(report, step: str):
    """Update the audit report's progress step (visible in UI polling)."""
    report.progress_step = step
    report.save(update_fields=["progress_step"])
    logger.info("Audit #%d: %s", report.id, step)


# ── Business Intelligence ───────────────────────────────────────

def _scrape_website(url: str) -> str:
    """Fetch and extract text content from a website for business understanding."""
    import requests

    try:
        headers = {
            "User-Agent": "RankPulse-Audit/2.0 (Business Analysis Bot)",
            "Accept": "text/html",
        }
        resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        resp.raise_for_status()
        html = resp.text[:50_000]

        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        return text[:8000]
    except Exception as exc:
        logger.warning("Failed to scrape %s: %s", url, exc)
        return f"(Não foi possível acessar o site: {exc})"


def _ensure_brand_profile(project, sites, report=None) -> "BrandProfile":
    """Ensure a BrandProfile exists for the project, refreshing stale data.

    Uses intelligent refresh: website every 7 days, social every 3 days,
    brand analysis only when source data changes.
    Returns the BrandProfile instance (always).
    """
    from .models import BrandProfile

    profile, created = BrandProfile.objects.get_or_create(project=project)

    updated = False

    # -- Website scan --
    if profile.website_needs_refresh():
        if report:
            _update_progress(report, "scanning_website")
        raw_parts = []
        all_discovered = []
        for site in sites:
            content = _scrape_website(site.url)
            if content:
                raw_parts.append(f"Site: {site.domain}\n{content}")

            # Deep crawl for URL discovery
            try:
                from .site_crawler import discover_all_urls
                discovered = discover_all_urls(site.url, max_pages=100)
                all_discovered.extend(discovered)
            except Exception as e:
                logger.debug("Site crawler failed for %s: %s", site.url, e)

        if raw_parts:
            profile.website_raw_text = "\n\n---\n\n".join(raw_parts)
            profile.website_content = profile.website_raw_text[:6000]
            profile.last_website_scan = timezone.now()
            updated = True

        if all_discovered:
            profile.discovered_urls = all_discovered
            profile.total_pages_found = len(all_discovered)
            updated = True

    # -- Social scan (Instagram + Facebook) --
    if profile.social_needs_refresh():
        if report:
            _update_progress(report, "scanning_social")
        social_updated = _refresh_social_data(project, profile)
        if social_updated:
            updated = True

    # -- Brand DNA generation (only if sources changed) --
    if updated or profile.brand_analysis_needs_refresh():
        if profile.website_raw_text or profile.instagram_profile or profile.facebook_page:
            if report:
                _update_progress(report, "generating_brand_dna")
            _generate_brand_dna(profile)

    if updated:
        profile.save()

    return profile


def refresh_brand_intelligence(project_id: int) -> dict:
    """Force-refresh all Brand Intelligence for a project.

    Resets refresh timestamps to force website scan, social scan,
    and brand DNA re-generation. Called when user clicks 'Atualizar'.
    """
    from .models import BrandProfile, Project

    project = Project.objects.get(id=project_id)
    profile, _ = BrandProfile.objects.get_or_create(project=project)

    # Reset timestamps to force full refresh
    profile.last_website_scan = None
    profile.last_social_scan = None
    profile.last_brand_analysis = None
    profile.save(update_fields=["last_website_scan", "last_social_scan", "last_brand_analysis"])

    sites = project.sites.filter(is_active=True)
    _ensure_brand_profile(project, sites)

    # Reload to get fresh data
    profile.refresh_from_db()
    return {
        "success": True,
        "has_summary": bool(profile.brand_summary),
        "total_pages": profile.total_pages_found,
        "last_analysis": profile.last_brand_analysis.isoformat() if profile.last_brand_analysis else None,
    }


def _refresh_social_data(project, profile) -> bool:
    """Try to fetch Instagram and Facebook data via Graph API.

    Returns True if any data was updated.
    """
    from apps.channels.models import Channel

    updated = False

    try:
        channel = Channel.objects.filter(
            project=project, platform="meta_ads", is_active=True,
        ).select_related("credentials").first()

        if not channel or not channel.is_configured:
            return False

        cred = channel.credentials
        extra = cred.extra or {}
        ig_account_id = extra.get("instagram_business_account_id", "")
        page_id = extra.get("facebook_page_id", "")

        if not ig_account_id and not page_id:
            return False

        try:
            from apps.analytics.social_client import SocialMediaClient
            client = SocialMediaClient(access_token=cred.access_token)

            if ig_account_id:
                ig_profile = client.get_instagram_profile(ig_account_id)
                if ig_profile:
                    profile.instagram_profile = ig_profile
                    updated = True
                ig_posts = client.get_instagram_recent_posts(ig_account_id)
                if ig_posts:
                    profile.instagram_posts = ig_posts
                    updated = True

            if page_id:
                fb_page = client.get_facebook_page_info(page_id)
                if fb_page:
                    profile.facebook_page = fb_page
                    updated = True
                fb_posts = client.get_facebook_recent_posts(page_id)
                if fb_posts:
                    profile.facebook_posts = fb_posts
                    updated = True

            if updated:
                profile.last_social_scan = timezone.now()

        except ImportError:
            logger.info("social_client not yet available, skipping social data")
        except Exception as exc:
            logger.warning("Social data fetch failed: %s", exc)

    except Exception as exc:
        logger.warning("Social data refresh error: %s", exc)

    return updated


def _generate_brand_dna(profile):
    """Call OpenAI to generate Brand DNA from website + social data."""
    from openai import OpenAI

    api_key = getattr(settings, "OPENAI_API_KEY", "")
    model = getattr(settings, "OPENAI_MODEL", "gpt-4.1-mini")
    if not api_key:
        return

    ig_data = "Não disponível"
    if profile.instagram_profile:
        ig_data = json.dumps(profile.instagram_profile, ensure_ascii=False, default=str)
        if profile.instagram_posts:
            ig_data += "\n\nÚltimos posts:\n" + json.dumps(
                profile.instagram_posts[:10], ensure_ascii=False, default=str,
            )

    fb_data = "Não disponível"
    if profile.facebook_page:
        fb_data = json.dumps(profile.facebook_page, ensure_ascii=False, default=str)
        if profile.facebook_posts:
            fb_data += "\n\nÚltimos posts:\n" + json.dumps(
                profile.facebook_posts[:10], ensure_ascii=False, default=str,
            )

    prompt = _safe_format(
        BRAND_DNA_PROMPT,
        website_content=profile.website_content or "Não disponível",
        instagram_data=ig_data,
        facebook_data=fb_data,
    )

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Retorna EXCLUSIVAMENTE JSON válido, sem markdown."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=4000,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

        data = json.loads(content)
        profile.brand_summary = data.get("brand_summary", "")
        profile.target_audience = data.get("target_audience", "")
        profile.tone_of_voice = data.get("tone_of_voice", "")
        profile.key_services = data.get("key_services", [])
        profile.differentiators = data.get("differentiators", "")
        profile.last_brand_analysis = timezone.now()
        profile.save()
        logger.info("Brand DNA generated for project %s", profile.project.name)
    except Exception as exc:
        logger.error("Brand DNA generation failed: %s", exc)


def _build_business_context(project, sites) -> str:
    """Build a business understanding string (legacy compat + used in context)."""
    parts = [
        f"Nome do negócio: {project.name}",
        f"Descrição do projeto: {project.description or 'Não informada'}",
    ]
    if project.business_goals:
        parts.append(f"Objetivos: {project.business_goals}")

    for site in sites:
        parts.append(f"\nSite: {site.domain} ({site.url})")
        content = _scrape_website(site.url)
        if content:
            parts.append(f"Conteúdo do site (resumo):\n{content[:4000]}")

    return "\n".join(parts)


# ── Cache-First Data Collection ─────────────────────────────────

def _get_or_fetch(project, data_type: str, fetch_fn):
    """Cache-first helper: returns cached data if valid, else calls fetch_fn and stores."""
    from .models import DataSnapshot

    cached = DataSnapshot.get_valid(project, data_type)
    if cached:
        logger.info("Cache HIT for %s/%s (%s)", project.name, data_type, cached.age_display)
        return cached.data

    logger.info("Cache MISS for %s/%s — fetching from API", project.name, data_type)
    data = fetch_fn()
    if data:
        DataSnapshot.store(project, data_type, data)
    return data or []


def _collect_google_ads_data(project, report=None) -> dict:
    """Collect comprehensive Google Ads data — cache-first."""
    from apps.analytics.ads_client import GoogleAdsManager
    from apps.channels.models import Channel

    result = {
        "available": False, "campaigns": [], "keywords": [],
        "ad_groups": [], "search_terms": [], "ad_copies": [],
        "campaign_details": [], "assets": [], "locations": [],
        "performance_30d": [],
    }

    try:
        channel = Channel.objects.filter(
            project=project, platform="google_ads", is_active=True,
        ).select_related("credentials").first()

        if not channel or not channel.is_configured:
            return result

        cred = channel.credentials
        mgr = GoogleAdsManager(
            customer_id=cred.customer_id,
            developer_token=cred.developer_token or settings.GOOGLE_ADS_DEVELOPER_TOKEN,
            client_id=cred.client_id or settings.GOOGLE_ADS_CLIENT_ID,
            client_secret=cred.client_secret or settings.GOOGLE_ADS_CLIENT_SECRET,
            refresh_token=cred.refresh_token,
            login_customer_id=cred.login_customer_id or "",
        )

        if report:
            _update_progress(report, "collecting_google_ads")

        # Campaign details (bidding, networks, settings)
        def fetch_campaign_details():
            d = mgr.get_campaign_details()
            return d["campaigns"] if d.get("success") else []
        result["campaign_details"] = _get_or_fetch(project, "google_campaign_details", fetch_campaign_details)

        # Basic campaign list with metrics
        def fetch_campaigns():
            c = mgr.list_campaigns()
            return c["campaigns"] if c.get("success") else []
        result["campaigns"] = _get_or_fetch(project, "google_campaigns", fetch_campaigns)
        if result["campaigns"]:
            result["available"] = True

        # Keywords with Quality Score
        def fetch_keywords():
            k = mgr.get_keyword_performance(days=30)
            return k["keywords"] if k.get("success") else []
        result["keywords"] = _get_or_fetch(project, "google_keywords", fetch_keywords)

        # Search terms — actual queries triggering ads
        def fetch_search_terms():
            s = mgr.get_search_terms_report(days=30, limit=100)
            return s["terms"] if s.get("success") else []
        result["search_terms"] = _get_or_fetch(project, "google_search_terms", fetch_search_terms)

        # Ad copy — headlines, descriptions, CTR
        def fetch_ad_copies():
            a = mgr.get_ad_copy_report(limit=50)
            return a["ads"] if a.get("success") else []
        result["ad_copies"] = _get_or_fetch(project, "google_ad_copies", fetch_ad_copies)

        # Existing assets (sitelinks, callouts, snippets)
        def fetch_assets():
            a = mgr.get_existing_assets()
            return a["assets"] if a.get("success") else []
        result["assets"] = _get_or_fetch(project, "google_assets", fetch_assets)

        # Location targeting
        def fetch_locations():
            locs = mgr.get_location_targeting()
            return locs["locations"] if locs.get("success") else []
        result["locations"] = _get_or_fetch(project, "google_locations", fetch_locations)

        # Ad groups
        def fetch_ad_groups():
            groups = []
            active_campaigns = [c for c in result["campaigns"] if c.get("status") == "ENABLED"]
            for camp in active_campaigns[:10]:
                ag_data = mgr.list_ad_groups(camp["id"])
                if ag_data.get("success"):
                    groups.extend(ag_data["ad_groups"])
            return groups
        result["ad_groups"] = _get_or_fetch(project, "google_ad_groups", fetch_ad_groups)

        # Performance 30d
        def fetch_performance():
            p = mgr.get_campaign_performance(days=30)
            return p["data"] if p.get("success") else []
        result["performance_30d"] = _get_or_fetch(project, "google_performance", fetch_performance)

    except Exception as exc:
        logger.error("Error collecting Google Ads data: %s", exc)
        result["error"] = str(exc)

    return result


def _collect_meta_ads_data(project, report=None) -> dict:
    """Collect DEEP Meta Ads data — cache-first."""
    from apps.analytics.meta_ads_client import MetaAdsManager
    from apps.channels.models import Channel

    result = {
        "available": False, "campaigns": [], "ad_sets": [],
        "ads_with_creatives": [], "campaign_insights": [],
        "demographics": [], "placements": [], "ad_insights": [],
        "account_overview": {},
    }

    try:
        channel = Channel.objects.filter(
            project=project, platform="meta_ads", is_active=True,
        ).select_related("credentials").first()

        if not channel or not channel.is_configured:
            return result

        cred = channel.credentials
        mgr = MetaAdsManager(
            access_token=cred.access_token,
            account_id=cred.account_id,
        )

        if report:
            _update_progress(report, "collecting_meta_ads")

        # Account overview
        def fetch_overview():
            o = mgr.get_account_overview(days=30)
            return o if o.get("success") else {}
        result["account_overview"] = _get_or_fetch(project, "meta_account_overview", fetch_overview)
        if result["account_overview"]:
            result["available"] = True

        # Campaigns
        def fetch_campaigns():
            c = mgr.list_campaigns()
            return c["campaigns"] if c.get("success") else []
        result["campaigns"] = _get_or_fetch(project, "meta_campaigns", fetch_campaigns)
        if result["campaigns"]:
            result["available"] = True

        # Ad sets with full targeting
        def fetch_ad_sets():
            a = mgr.list_ad_sets()
            return a["ad_sets"] if a.get("success") else []
        result["ad_sets"] = _get_or_fetch(project, "meta_ad_sets", fetch_ad_sets)

        # Ads with creatives
        def fetch_creatives():
            a = mgr.get_ads_with_creatives(limit=80)
            return a["ads"] if a.get("success") else []
        result["ads_with_creatives"] = _get_or_fetch(project, "meta_ads_creatives", fetch_creatives)

        # Campaign insights 30d
        def fetch_campaign_insights():
            i = mgr.get_campaign_insights(days=30)
            return i["insights"] if i.get("success") else []
        result["campaign_insights"] = _get_or_fetch(project, "meta_campaign_insights", fetch_campaign_insights)

        # Demographics
        def fetch_demographics():
            d = mgr.get_demographic_breakdown(days=30)
            return d["data"] if d.get("success") else []
        result["demographics"] = _get_or_fetch(project, "meta_demographics", fetch_demographics)

        # Placements
        def fetch_placements():
            p = mgr.get_placement_breakdown(days=30)
            return p["data"] if p.get("success") else []
        result["placements"] = _get_or_fetch(project, "meta_placements", fetch_placements)

        # Ad-level insights
        def fetch_ad_insights():
            a = mgr.get_ad_level_insights(days=30, limit=50)
            return a["data"] if a.get("success") else []
        result["ad_insights"] = _get_or_fetch(project, "meta_ad_insights", fetch_ad_insights)

    except Exception as exc:
        logger.error("Error collecting Meta Ads data: %s", exc)
        result["error"] = str(exc)

    return result


def _collect_seo_data(project, sites, report=None) -> dict:
    """Collect SEO data from Google Search Console — cache-first."""
    from apps.analytics.search_console import SearchConsoleClient

    result = {"available": False, "queries": [], "pages": [], "daily": []}

    try:
        for site in sites:
            if not site.gsc_site_url:
                continue

            if report:
                _update_progress(report, "collecting_seo")

            client = SearchConsoleClient(site=site)

            def fetch_queries():
                q = client.fetch_queries(days=30, row_limit=100)
                return q.get("rows", []) if q.get("success") else []
            result["queries"] = _get_or_fetch(project, "seo_queries", fetch_queries)
            if result["queries"]:
                result["available"] = True

            def fetch_pages():
                p = client.fetch_pages(days=30, row_limit=50)
                return p.get("rows", []) if p.get("success") else []
            result["pages"] = _get_or_fetch(project, "seo_pages", fetch_pages)

            def fetch_daily():
                d = client.fetch_daily_totals(days=30)
                return d.get("rows", []) if d.get("success") else []
            result["daily"] = _get_or_fetch(project, "seo_daily", fetch_daily)

            break  # Use first site with GSC

    except Exception as exc:
        logger.error("Error collecting SEO data: %s", exc)
        result["error"] = str(exc)

    return result


def _collect_ga4_data(project, sites, report=None, config=None) -> dict:
    """Collect GA4 Analytics data — cache-first."""
    from apps.analytics.ga4_report import GA4ReportClient

    result = {
        "available": False, "overview": [], "traffic_sources": [],
        "top_pages": [], "organic_traffic": [], "conversions": [],
        "demographics": [], "devices": [],
    }

    try:
        for site in sites:
            if not site.ga4_property_id or not site.google_refresh_token:
                continue

            if report:
                _update_progress(report, "collecting_ga4")

            ga4 = GA4ReportClient(
                property_id=site.ga4_property_id,
                refresh_token=site.google_refresh_token,
            )

            # Overview
            def fetch_overview():
                return ga4.get_overview(days=30)
            result["overview"] = _get_or_fetch(project, "ga4_overview", fetch_overview)
            if result["overview"]:
                result["available"] = True

            # Traffic sources
            if not config or config.ga4_traffic_sources:
                def fetch_traffic():
                    return ga4.get_traffic_sources(days=30)
                result["traffic_sources"] = _get_or_fetch(project, "ga4_traffic_sources", fetch_traffic)

            # Top pages
            if not config or config.ga4_top_pages:
                def fetch_pages():
                    return ga4.get_top_pages(days=30, limit=50)
                result["top_pages"] = _get_or_fetch(project, "ga4_top_pages", fetch_pages)

            # Organic traffic
            if not config or config.ga4_organic:
                def fetch_organic():
                    return ga4.get_organic_traffic(days=30)
                result["organic_traffic"] = _get_or_fetch(project, "ga4_organic_traffic", fetch_organic)

            # Conversions
            if not config or config.ga4_conversions:
                def fetch_conversions():
                    return ga4.get_conversion_events(days=30)
                result["conversions"] = _get_or_fetch(project, "ga4_conversions", fetch_conversions)

            # Demographics
            if not config or config.ga4_demographics:
                def fetch_demographics():
                    return ga4.get_user_demographics(days=30)
                result["demographics"] = _get_or_fetch(project, "ga4_demographics", fetch_demographics)

            # Devices
            if not config or config.ga4_devices:
                def fetch_devices():
                    return ga4.get_device_breakdown(days=30)
                result["devices"] = _get_or_fetch(project, "ga4_devices", fetch_devices)

            break  # Use first site with GA4

    except Exception as exc:
        logger.error("Error collecting GA4 data: %s", exc)
        result["error"] = str(exc)

    return result


# ── AI Analysis (Multi-Call) ──────────────────────────────────────

def _call_openai_json(system_msg: str, user_msg: str, max_tokens: int = 8000,
                      project=None) -> dict:
    """Generic helper: send a prompt to AI and parse JSON response.

    When *project* is given, routes through AIRouter (uses project-level
    provider config).  Falls back to env OPENAI_API_KEY when no project
    or no provider configured.
    """
    content = ""

    try:
        # Try AIRouter first when project is available
        if project is not None:
            try:
                from .ai_router import AIRouter
                router = AIRouter(project)
                raw = router.generate_text(
                    prompt=user_msg,
                    system=system_msg,
                    temperature=0.2,
                    max_tokens=max_tokens,
                )
                content = raw.strip()
            except ValueError:
                # No provider configured — fall through to env key
                content = ""

        # Fallback: direct OpenAI with env key
        if not content:
            from openai import OpenAI

            api_key = getattr(settings, "OPENAI_API_KEY", "")
            model = getattr(settings, "OPENAI_MODEL", "gpt-4.1-mini")

            if not api_key:
                return {"error": "OPENAI_API_KEY não configurada"}

            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.2,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content.strip()

        # Strip markdown code fences
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

        # Try to extract clean JSON object from content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Fallback: extract first top-level JSON object via regex
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise

    except json.JSONDecodeError as exc:
        logger.error("AI returned invalid JSON: %s... content=%s", exc, content[:300] if content else "")
        return {"error": f"Resposta da IA não é JSON válido: {exc}"}
    except Exception as exc:
        logger.error("AI API error: %s", exc)
        return {"error": f"Erro na API de IA: {exc}"}


def _audit_meta_ads(brand_dna: str, business_goals: str, meta_data: dict, learning_context: str = "", expert_knowledge: str = "", project=None) -> dict:
    """Call 1: Deep Meta Ads analysis."""
    active_campaigns = [c for c in meta_data.get("campaigns", []) if c.get("status") == "ACTIVE"]
    paused_campaigns = [c for c in meta_data.get("campaigns", []) if c.get("status") == "PAUSED"]
    active_ad_sets = [s for s in meta_data.get("ad_sets", []) if s.get("status") == "ACTIVE"]

    data_json = json.dumps({
        "account_overview_30d": meta_data.get("account_overview", {}),
        "active_campaigns": active_campaigns[:30],
        "paused_campaigns_summary": {"count": len(paused_campaigns), "names": [c["name"] for c in paused_campaigns[:20]]},
        "ad_sets_with_full_targeting": active_ad_sets[:40],
        "ads_with_creative_details": meta_data.get("ads_with_creatives", [])[:60],
        "campaign_insights_30d": meta_data.get("campaign_insights", [])[:30],
        "demographic_breakdown": meta_data.get("demographics", [])[:100],
        "placement_breakdown": meta_data.get("placements", [])[:80],
        "ad_level_performance": meta_data.get("ad_insights", [])[:50],
    }, indent=2, default=str, ensure_ascii=False)

    prompt = _safe_format(
        META_ADS_AUDIT_PROMPT,
        brand_dna=brand_dna,
        business_goals=business_goals or "Não definidos",
        learning_context=learning_context or "Nenhum feedback anterior.",
        expert_knowledge=expert_knowledge or "Nenhum conhecimento especialista disponível.",
        meta_data=data_json,
    )

    return _call_openai_json(
        "Você é um auditor de Meta Ads sênior. Retorna EXCLUSIVAMENTE JSON válido.",
        prompt,
        max_tokens=12000,
        project=project,
    )


def _audit_google_ads(brand_dna: str, business_goals: str, google_data: dict, learning_context: str = "", expert_knowledge: str = "", project=None) -> dict:
    """Call 2: Deep Google Ads analysis."""
    data_json = json.dumps({
        "campaign_details": google_data.get("campaign_details", [])[:20],
        "campaigns_with_metrics": google_data.get("campaigns", [])[:20],
        "keywords_with_quality_score": google_data.get("keywords", [])[:100],
        "search_terms_real_queries": google_data.get("search_terms", [])[:100],
        "ad_copies": google_data.get("ad_copies", [])[:50],
        "existing_assets": google_data.get("assets", [])[:50],
        "location_targeting": google_data.get("locations", [])[:30],
        "ad_groups": google_data.get("ad_groups", [])[:50],
        "performance_30d": google_data.get("performance_30d", [])[:200],
    }, indent=2, default=str, ensure_ascii=False)

    prompt = _safe_format(
        GOOGLE_ADS_AUDIT_PROMPT,
        brand_dna=brand_dna,
        business_goals=business_goals or "Não definidos",
        learning_context=learning_context or "Nenhum feedback anterior.",
        expert_knowledge=expert_knowledge or "Nenhum conhecimento especialista disponível.",
        google_data=data_json,
    )

    return _call_openai_json(
        "Você é um auditor de Google Ads sênior. Retorna EXCLUSIVAMENTE JSON válido.",
        prompt,
        max_tokens=12000,
        project=project,
    )


def _audit_ga4(brand_dna: str, business_goals: str, ga4_data: dict, learning_context: str = "", expert_knowledge: str = "", project=None) -> dict:
    """Call: GA4 Analytics analysis."""
    data_json = json.dumps({
        "overview_30d": ga4_data.get("overview", [])[:30],
        "traffic_sources": ga4_data.get("traffic_sources", []),
        "top_pages": ga4_data.get("top_pages", [])[:50],
        "organic_traffic_daily": ga4_data.get("organic_traffic", [])[:30],
        "conversion_events": ga4_data.get("conversions", []),
        "user_demographics": ga4_data.get("demographics", [])[:50],
        "device_breakdown": ga4_data.get("devices", []),
    }, indent=2, default=str, ensure_ascii=False)

    prompt = _safe_format(
        GA4_AUDIT_PROMPT,
        brand_dna=brand_dna,
        business_goals=business_goals or "Não definidos",
        learning_context=learning_context or "Nenhum feedback anterior.",
        expert_knowledge=expert_knowledge or "Nenhum conhecimento especialista disponível.",
        ga4_data=data_json,
    )

    return _call_openai_json(
        "Você é um especialista em GA4 Analytics. Retorna EXCLUSIVAMENTE JSON válido.",
        prompt,
        max_tokens=8000,
        project=project,
    )


def _audit_synthesis(brand_dna: str, business_goals: str,
                     meta_result: dict, google_result: dict,
                     seo_data: dict, learning_context: str = "", expert_knowledge: str = "", project=None) -> dict:
    """Call 3: Cross-platform synthesis + SEO analysis."""
    seo_json = json.dumps({
        "available": seo_data.get("available", False),
        "top_queries": seo_data.get("queries", [])[:80],
        "top_pages": seo_data.get("pages", [])[:30],
        "daily_totals": seo_data.get("daily", [])[:30],
    }, indent=2, default=str, ensure_ascii=False)

    prompt = _safe_format(
        SYNTHESIS_AUDIT_PROMPT,
        brand_dna=brand_dna,
        business_goals=business_goals or "Não definidos",
        learning_context=learning_context or "Nenhum feedback anterior.",
        expert_knowledge=expert_knowledge or "Nenhum conhecimento especialista disponível.",
        meta_score=meta_result.get("platform_score", "N/A"),
        meta_analysis=meta_result.get("platform_analysis", "Não disponível"),
        meta_rec_count=len(meta_result.get("recommendations", [])),
        google_score=google_result.get("platform_score", "N/A"),
        google_analysis=google_result.get("platform_analysis", "Não disponível"),
        google_rec_count=len(google_result.get("recommendations", [])),
        seo_data=seo_json,
    )

    return _call_openai_json(
        "Você é um auditor de tráfego sênior cross-platform. Retorna EXCLUSIVAMENTE JSON válido.",
        prompt,
        max_tokens=8000,
        project=project,
    )


def _call_openai(business_context: str, campaign_data: str, seo_data: str, project=None) -> dict:
    """Legacy single-call — used when only one platform has data."""
    prompt = _safe_format(
        AUDIT_SYSTEM_PROMPT,
        business_context=business_context,
        campaign_data=campaign_data,
        seo_data=seo_data,
    )
    return _call_openai_json(
        "Você é um auditor de tráfego sênior. Retorna EXCLUSIVAMENTE JSON válido. Seja extremamente detalhado e específico.",
        prompt,
        max_tokens=16000,
        project=project,
    )


# ── Recommendation helper ──────────────────────────────────────

def _save_recommendations(report, recommendations: list):
    """Bulk-create AuditRecommendation records from AI output."""
    from .models import AuditRecommendation

    for rec in recommendations:
        AuditRecommendation.objects.create(
            report=report,
            platform=rec.get("platform", "general"),
            category=rec.get("category", "other"),
            impact=rec.get("impact", "medium"),
            title=rec.get("title", ""),
            explanation=rec.get("explanation", ""),
            action_description=rec.get("action_description", ""),
            action_payload=rec.get("action_payload", {}),
            can_auto_apply=rec.get("can_auto_apply", False),
            estimated_points=int(rec.get("estimated_points", 0) or 0),
            campaign_id=str(rec.get("campaign_id", "")),
            campaign_name=rec.get("campaign_name", ""),
        )


def _recalculate_project_score(project, report=None):
    """Recalculate the unified ProjectScore after audit or apply."""
    from .models import AuditReport, ProjectScore

    score_obj, _ = ProjectScore.objects.get_or_create(project=project)

    # Get latest completed report
    if not report:
        report = AuditReport.objects.filter(
            project=project, status="done",
        ).order_by("-created_at").first()

    if not report:
        return

    # Audit score from the report
    score_obj.audit_score = report.overall_score or 0

    # Points from recommendations
    recs = report.recommendations.all()
    total_pts = sum(r.estimated_points for r in recs)
    earned_pts = sum(r.estimated_points for r in recs if r.status == "applied")
    pending_pts = sum(r.estimated_points for r in recs if r.status == "pending")

    score_obj.total_possible = total_pts
    score_obj.earned_points = earned_pts
    score_obj.pending_points = pending_pts

    # Unified score: audit base (60%) + progress bonus (40%)
    progress_pct = (earned_pts / total_pts * 100) if total_pts > 0 else 0
    score_obj.overall_score = min(100, int(
        score_obj.audit_score * 0.6 + progress_pct * 0.4
    ))

    score_obj.last_calculated_at = timezone.now()
    score_obj.save()


# ── Main Audit Runner ──────────────────────────────────────────

def run_audit(project_id: int) -> int:
    """Run a complete AI audit for a project.

    V3 Flow:
        1. Load AuditConfig (creates default if missing)
        2. Ensure Brand DNA (cached, refreshed only if stale)
        3. Collect data per platform (cache-first, respecting config toggles)
        4. Multi-call AI per platform + GA4 + Synthesis
        5. Save results + all recommendations

    Returns the AuditReport ID.
    """
    from .models import AuditConfig, AuditRecommendation, AuditReport, Project, Site

    start = time.time()

    project = Project.objects.get(id=project_id)
    sites = list(Site.objects.filter(project=project, is_active=True))

    # Load audit configuration (auto-create with defaults if missing)
    config, _ = AuditConfig.objects.get_or_create(project=project)

    report = AuditReport.objects.create(project=project, status="running")

    try:
        # ── Step 1: Brand DNA ──
        if config.brand_dna_context:
            _update_progress(report, "brand_dna")
            brand_profile = _ensure_brand_profile(project, sites, report)
            brand_dna = brand_profile.brand_summary or ""
            if not brand_dna:
                brand_dna = _build_business_context(project, sites)
        else:
            from .models import BrandProfile
            brand_profile = BrandProfile.objects.filter(project=project).first()
            brand_dna = _build_business_context(project, sites)

        business_goals = project.business_goals or ""
        report.business_summary = brand_dna[:2000]

        # ── Load learning context (user feedback loop) ──
        learning_ctx = get_learning_context(project)

        # ── Step 2: Collect data (cache-first, respecting config) ──
        google_data = _collect_google_ads_data(project, report) if config.source_google_ads else {"available": False}
        meta_data = _collect_meta_ads_data(project, report) if config.source_meta_ads else {"available": False}
        seo_data = _collect_seo_data(project, sites, report) if config.source_seo else {"available": False}
        ga4_data = _collect_ga4_data(project, sites, report, config) if config.source_ga4 else {"available": False}

        # Save raw snapshot
        active_meta_campaigns = [c for c in meta_data.get("campaigns", []) if c.get("status") == "ACTIVE"]
        active_ad_sets = [s for s in meta_data.get("ad_sets", []) if s.get("status") == "ACTIVE"]

        report.raw_data_snapshot = {
            "google_ads_campaigns": len(google_data.get("campaigns", [])),
            "google_ads_keywords": len(google_data.get("keywords", [])),
            "google_ads_search_terms": len(google_data.get("search_terms", [])),
            "google_ads_ad_copies": len(google_data.get("ad_copies", [])),
            "google_ads_assets": len(google_data.get("assets", [])),
            "meta_ads_campaigns_total": len(meta_data.get("campaigns", [])),
            "meta_ads_campaigns_active": len(active_meta_campaigns),
            "meta_ads_ad_sets_total": len(meta_data.get("ad_sets", [])),
            "meta_ads_ad_sets_active": len(active_ad_sets),
            "meta_ads_ads_with_creatives": len(meta_data.get("ads_with_creatives", [])),
            "meta_ads_demographics_rows": len(meta_data.get("demographics", [])),
            "meta_ads_placement_rows": len(meta_data.get("placements", [])),
            "meta_ads_ad_insights": len(meta_data.get("ad_insights", [])),
            "seo_queries": len(seo_data.get("queries", [])),
            "seo_pages": len(seo_data.get("pages", [])),
            "ga4_overview_rows": len(ga4_data.get("overview", [])),
            "ga4_traffic_sources": len(ga4_data.get("traffic_sources", [])),
            "ga4_conversions": len(ga4_data.get("conversions", [])),
            "has_brand_dna": bool(brand_dna and len(brand_dna) > 50),
        }

        # ── Step 3: AI Analysis ──
        has_meta = meta_data.get("available", False)
        has_google = google_data.get("available", False)
        has_ga4 = ga4_data.get("available", False)
        all_recs = []
        meta_result = {}
        google_result = {}
        ga4_result = {}

        # Query expert knowledge base
        expert_knowledge = ""
        try:
            from .knowledge_base import query_knowledge_base
            platforms = []
            if has_meta:
                platforms.append("meta_ads")
            if has_google:
                platforms.append("google_ads")
            if has_ga4:
                platforms.append("analytics")
            expert_knowledge = query_knowledge_base(
                query=f"auditoria campanhas {brand_dna[:200] if brand_dna else 'marketing digital'}",
                categories=platforms + ["general"] if platforms else None,
                n_results=5,
            )
        except Exception as e:
            logger.debug("Expert knowledge base unavailable: %s", e)

        if not has_meta and not has_google and not has_ga4:
            report.status = "error"
            report.error_message = (
                "Nenhum dado disponível. "
                "Conecte Google Ads, Meta Ads ou GA4 nas Fontes do projeto."
            )
            report.duration_seconds = time.time() - start
            report.save()
            return report.id

        if has_meta:
            _update_progress(report, "ai_analyzing_meta")
            meta_result = _audit_meta_ads(brand_dna, business_goals, meta_data, learning_ctx, expert_knowledge, project=project)
            if "error" not in meta_result:
                all_recs.extend(meta_result.get("recommendations", []))

        if has_google:
            _update_progress(report, "ai_analyzing_google")
            google_result = _audit_google_ads(brand_dna, business_goals, google_data, learning_ctx, expert_knowledge, project=project)
            if "error" not in google_result:
                all_recs.extend(google_result.get("recommendations", []))

        if has_ga4:
            _update_progress(report, "ai_analyzing_ga4")
            ga4_result = _audit_ga4(brand_dna, business_goals, ga4_data, learning_ctx, expert_knowledge, project=project)
            if "error" not in ga4_result:
                all_recs.extend(ga4_result.get("recommendations", []))

        # Synthesis: cross-platform analysis
        if config.cross_platform_synthesis:
            _update_progress(report, "ai_synthesizing")
            synth_result = _audit_synthesis(
                brand_dna, business_goals,
                meta_result if "error" not in meta_result else {},
                google_result if "error" not in google_result else {},
                seo_data, learning_ctx, expert_knowledge,
                project=project,
            )
        else:
            synth_result = {}

        # Check if ALL calls failed
        platform_results = []
        if has_meta:
            platform_results.append(meta_result)
        if has_google:
            platform_results.append(google_result)
        if has_ga4:
            platform_results.append(ga4_result)

        all_failed = all("error" in r for r in platform_results) and "error" in synth_result
        if all_failed:
            report.status = "error"
            errors = [r.get("error", "") for r in platform_results + [synth_result] if "error" in r]
            report.error_message = "; ".join(errors)[:500]
            report.duration_seconds = time.time() - start
            report.save()
            return report.id

        report.overall_score = synth_result.get("overall_score")
        report.overall_analysis = synth_result.get("overall_analysis", "")
        all_recs.extend(synth_result.get("recommendations", []))

        # If synthesis didn't provide a score, average platform scores
        if not report.overall_score:
            scores = []
            if meta_result.get("platform_score"):
                scores.append(meta_result["platform_score"])
            if google_result.get("platform_score"):
                scores.append(google_result["platform_score"])
            if ga4_result.get("platform_score"):
                scores.append(ga4_result["platform_score"])
            if scores:
                report.overall_score = sum(scores) // len(scores)

        # ── Step 4: Save results ──
        _update_progress(report, "saving_results")
        report.status = "done"
        report.duration_seconds = time.time() - start
        report.save()

        _save_recommendations(report, all_recs)
        _recalculate_project_score(project, report)

        logger.info(
            "Audit #%d complete: score=%s, %d recommendations, %.1fs",
            report.id, report.overall_score,
            report.recommendations.count(),
            report.duration_seconds,
        )
        return report.id

    except Exception as exc:
        import traceback as _tb
        logger.error("Audit #%d failed: %s", report.id, exc)
        report.status = "error"
        report.error_message = str(exc)
        report.duration_seconds = time.time() - start
        report.save()
        try:
            from .middleware import log_error
            log_error(
                error_type="audit_error",
                severity="critical",
                error_message=f"Audit #{report.id} failed: {exc}",
                traceback=_tb.format_exc(),
                view_name="run_audit",
            )
        except Exception:
            pass
        return report.id


# ── Action Executor ─────────────────────────────────────────────

def apply_recommendation(recommendation_id: int) -> dict[str, Any]:
    """Execute a recommendation's action via the appropriate API.

    Returns dict with success/error info.
    """
    from .models import AuditRecommendation

    rec = AuditRecommendation.objects.select_related(
        "report__project",
    ).get(id=recommendation_id)

    if rec.status == "applied":
        return {"success": False, "error": "Recomendação já foi aplicada."}

    if not rec.can_auto_apply:
        return {"success": False, "error": "Esta recomendação não pode ser aplicada automaticamente."}

    payload = rec.action_payload
    action_type = payload.get("action_type", "")
    project = rec.report.project

    try:
        if rec.platform == "google_ads":
            result = _apply_google_ads_action(project, action_type, payload)
        elif rec.platform == "meta_ads":
            result = _apply_meta_ads_action(project, action_type, payload)
        elif rec.platform == "seo":
            result = _apply_seo_action(project, action_type, payload)
        else:
            result = {"success": False, "error": f"Plataforma não suportada: {rec.platform}"}

        # Update recommendation status
        rec.apply_result = result
        if result.get("success"):
            rec.status = "applied"
            rec.applied_at = timezone.now()
        else:
            rec.status = "failed"
        rec.save()

        # Recalculate score after apply
        try:
            _recalculate_project_score(project)
        except Exception:
            pass

        return result

    except Exception as exc:
        import traceback as _tb
        logger.error("Apply recommendation #%d error: %s", recommendation_id, exc)
        rec.status = "failed"
        rec.apply_result = {"error": str(exc)}
        rec.save()
        try:
            from .middleware import log_error
            log_error(
                error_type="integration_error",
                severity="error",
                error_message=f"Apply recommendation #{recommendation_id} ({rec.platform}/{action_type}) failed: {exc}",
                traceback=_tb.format_exc(),
                view_name="apply_recommendation",
            )
        except Exception:
            pass
        return {"success": False, "error": str(exc)}


def _get_google_ads_manager(project):
    """Get a configured GoogleAdsManager for the project."""
    from apps.analytics.ads_client import GoogleAdsManager
    from apps.channels.models import Channel

    channel = Channel.objects.filter(
        project=project, platform="google_ads", is_active=True,
    ).select_related("credentials").first()

    if not channel or not channel.is_configured:
        raise ValueError("Google Ads não está conectado.")

    cred = channel.credentials
    return GoogleAdsManager(
        customer_id=cred.customer_id,
        developer_token=cred.developer_token or settings.GOOGLE_ADS_DEVELOPER_TOKEN,
        client_id=cred.client_id or settings.GOOGLE_ADS_CLIENT_ID,
        client_secret=cred.client_secret or settings.GOOGLE_ADS_CLIENT_SECRET,
        refresh_token=cred.refresh_token,
        login_customer_id=cred.login_customer_id or "",
    )


def _get_meta_ads_manager(project):
    """Get a configured MetaAdsManager for the project."""
    from apps.analytics.meta_ads_client import MetaAdsManager
    from apps.channels.models import Channel

    channel = Channel.objects.filter(
        project=project, platform="meta_ads", is_active=True,
    ).select_related("credentials").first()

    if not channel or not channel.is_configured:
        raise ValueError("Meta Ads não está conectado.")

    cred = channel.credentials
    return MetaAdsManager(
        access_token=cred.access_token,
        account_id=cred.account_id,
    )


def _apply_google_ads_action(project, action_type: str, payload: dict) -> dict:
    """Execute a Google Ads action."""
    mgr = _get_google_ads_manager(project)

    if action_type == "add_negative_keywords":
        return mgr.add_negative_keywords(
            campaign_id=payload["campaign_id"],
            keywords=payload["keywords"],
        )

    elif action_type == "create_sitelink":
        asset = mgr.create_sitelink_asset(
            link_text=payload["link_text"],
            final_url=payload["final_url"],
            description1=payload.get("description1", ""),
            description2=payload.get("description2", ""),
        )
        if asset.get("success") and payload.get("campaign_id"):
            link = mgr.link_assets_to_campaign(
                campaign_id=payload["campaign_id"],
                asset_resource_names=[asset["resource_name"]],
                field_type="SITELINK",
            )
            return {**asset, "link_result": link}
        return asset

    elif action_type == "create_callout":
        asset = mgr.create_callout_asset(callout_text=payload["callout_text"])
        if asset.get("success") and payload.get("campaign_id"):
            link = mgr.link_assets_to_campaign(
                campaign_id=payload["campaign_id"],
                asset_resource_names=[asset["resource_name"]],
                field_type="CALLOUT",
            )
            return {**asset, "link_result": link}
        return asset

    elif action_type == "create_structured_snippet":
        asset = mgr.create_structured_snippet_asset(
            header=payload["header"],
            values=payload["values"],
        )
        if asset.get("success") and payload.get("campaign_id"):
            link = mgr.link_assets_to_campaign(
                campaign_id=payload["campaign_id"],
                asset_resource_names=[asset["resource_name"]],
                field_type="STRUCTURED_SNIPPET",
            )
            return {**asset, "link_result": link}
        return asset

    elif action_type == "add_keywords":
        return mgr.add_keywords(
            ad_group_id=payload["ad_group_id"],
            keywords=payload["keywords"],
        )

    else:
        return {"success": False, "error": f"Ação Google Ads não suportada: {action_type}"}


def _apply_meta_ads_action(project, action_type: str, payload: dict) -> dict:
    """Execute a Meta Ads action."""
    mgr = _get_meta_ads_manager(project)

    if action_type == "update_targeting":
        ad_set_id = payload["ad_set_id"]
        targeting = payload["targeting"]
        return mgr.update_ad_set(ad_set_id, targeting=targeting)

    elif action_type == "update_ad_set":
        ad_set_id = payload["ad_set_id"]
        fields = payload.get("fields", {})
        return mgr.update_ad_set(ad_set_id, **fields)

    elif action_type == "pause_campaign":
        return mgr.update_campaign_status(payload["campaign_id"], "PAUSED")

    elif action_type == "activate_campaign":
        return mgr.update_campaign_status(payload["campaign_id"], "ACTIVE")

    elif action_type == "pause_ad_set":
        return mgr.update_ad_set_status(payload["ad_set_id"], "PAUSED")

    elif action_type == "activate_ad_set":
        return mgr.update_ad_set_status(payload["ad_set_id"], "ACTIVE")

    elif action_type == "create_campaign":
        return mgr.create_campaign(
            name=payload["name"],
            objective=payload.get("objective", "OUTCOME_TRAFFIC"),
            daily_budget_brl=payload.get("daily_budget_brl"),
            lifetime_budget_brl=payload.get("lifetime_budget_brl"),
            status=payload.get("status", "PAUSED"),
            special_ad_categories=payload.get("special_ad_categories"),
        )

    elif action_type == "create_ad_set":
        return mgr.create_ad_set(
            campaign_id=payload["campaign_id"],
            name=payload["name"],
            daily_budget_brl=payload.get("daily_budget_brl", 20.0),
            billing_event=payload.get("billing_event", "IMPRESSIONS"),
            optimization_goal=payload.get("optimization_goal", "LINK_CLICKS"),
            targeting=payload.get("targeting"),
            status=payload.get("status", "PAUSED"),
        )

    elif action_type == "create_ad":
        return mgr.create_ad(
            ad_set_id=payload["ad_set_id"],
            name=payload["name"],
            creative_id=payload.get("creative_id"),
            page_id=payload.get("page_id"),
            link_url=payload.get("link_url"),
            message=payload.get("message"),
            image_hash=payload.get("image_hash"),
            status=payload.get("status", "PAUSED"),
        )

    elif action_type == "update_campaign":
        campaign_id = payload["campaign_id"]
        fields = payload.get("fields", {})
        return mgr.update_campaign(campaign_id, **fields)

    elif action_type == "update_campaign_budget":
        campaign_id = payload["campaign_id"]
        budget_fields = {}
        if "daily_budget" in payload:
            budget_fields["daily_budget"] = payload["daily_budget"]
        if "lifetime_budget" in payload:
            budget_fields["lifetime_budget"] = payload["lifetime_budget"]
        return mgr.update_campaign(campaign_id, **budget_fields)

    else:
        return {"success": False, "error": f"Ação Meta Ads não suportada: {action_type}"}


def _apply_seo_action(project, action_type: str, payload: dict) -> dict:
    """Execute an SEO action."""
    from apps.analytics.search_console import SearchConsoleClient
    from apps.core.models import Site

    if action_type == "submit_url_for_indexing":
        urls = payload.get("urls", [])
        site = Site.objects.filter(project=project, is_active=True).first()
        if not site:
            return {"success": False, "error": "Nenhum site conectado."}

        client = SearchConsoleClient(site=site)
        results = []
        for url in urls[:10]:  # Limit to 10 URLs per action
            r = client.submit_url_for_indexing(url)
            results.append({"url": url, "result": r})

        return {"success": True, "submitted": len(results), "results": results}

    else:
        return {"success": False, "error": f"Ação SEO não suportada: {action_type}"}


# ── Learning Context Engine ─────────────────────────────────────

COMPILE_PROMPT = """Analise as observações do usuário sobre recomendações de auditoria abaixo.
Gere um resumo conciso (máx 800 palavras) que capture:
1. Preferências do usuário sobre como operar campanhas
2. Padrões de feedback (o que o usuário aceita, rejeita, ajusta)
3. Regras implícitas (ex: "nunca sugeri mudança de orçamento", "prefere lances manuais")
4. Tom e estilo de operação

Observações:
{notes_text}

Retorne APENAS o resumo em texto corrido, sem JSON."""

PREVIEW_PROMPT = """Analise a recomendação abaixo e determine se é possível executá-la automaticamente via API.

Recomendação:
- Título: {title}
- Plataforma: {platform}
- Categoria: {category}
- Explicação: {explanation}
- Ação proposta: {action_description}
- Campanha: {campaign_name} (ID: {campaign_id})

Ações disponíveis via API:
GOOGLE ADS: add_negative_keywords (campaign_id, keywords[]), create_sitelink (link_text, final_url, description1, description2, campaign_id), create_callout (callout_text, campaign_id), create_structured_snippet (header, values[], campaign_id), add_keywords (ad_group_id, keywords[])
META ADS: update_targeting (ad_set_id, targeting{{}}), update_ad_set (ad_set_id, fields{{}}), pause_campaign (campaign_id), activate_campaign (campaign_id), pause_ad_set (ad_set_id), activate_ad_set (ad_set_id), create_campaign (name, objective, daily_budget_brl, status), create_ad_set (campaign_id, name, daily_budget_brl, targeting, optimization_goal), create_ad (ad_set_id, name, page_id, link_url, message), update_campaign_budget (campaign_id, daily_budget)
SEO: submit_url_for_indexing (urls[])

Se for possível mapear para uma ação acima, retorne JSON:
{{"can_apply": true, "action_type": "<tipo>", "payload": {{<parâmetros>}}, "preview_text": "<descrição em português do que será feito>"}}

Se NÃO for possível (requer intervenção manual), retorne:
{{"can_apply": false, "preview_text": "<descrição do que o usuário precisa fazer manualmente, passo a passo>"}}

Retorne APENAS JSON válido."""


def get_learning_context(project) -> str:
    """Build the learning context string to inject into audit prompts."""
    from .models import ProjectLearningContext, RecommendationNote

    ctx, _ = ProjectLearningContext.objects.get_or_create(project=project)

    parts = []
    if ctx.general_guidelines:
        parts.append(f"ORIENTAÇÕES DO USUÁRIO:\n{ctx.general_guidelines}")
    if ctx.compiled_prompt:
        parts.append(f"CONTEXTO COMPILADO:\n{ctx.compiled_prompt}")

    # Add recent notes not yet compiled
    notes_qs = RecommendationNote.objects.filter(
        recommendation__report__project=project,
    ).select_related("recommendation").order_by("-created_at")

    total_notes = notes_qs.count()

    if total_notes > 30 and total_notes > ctx.notes_count_at_compile:
        # Stale — but don't block the audit; use existing summary + recent notes
        recent = notes_qs[:10]
    elif total_notes <= 30:
        recent = notes_qs[:30]
    else:
        recent = notes_qs[:10]

    if recent:
        lines = []
        for n in recent:
            lines.append(f"- Sobre \"{n.recommendation.title}\": {n.text}")
        parts.append("OBSERVAÇÕES RECENTES:\n" + "\n".join(lines))

    if ctx.auto_summary and not ctx.compiled_prompt:
        parts.append(f"RESUMO AUTOMÁTICO:\n{ctx.auto_summary}")

    return "\n\n".join(parts) if parts else ""


def compile_learning_context(project) -> dict:
    """Re-compile the learning context from all accumulated notes."""
    from .models import ProjectLearningContext, RecommendationNote

    ctx, _ = ProjectLearningContext.objects.get_or_create(project=project)

    notes = RecommendationNote.objects.filter(
        recommendation__report__project=project,
    ).select_related("recommendation").order_by("created_at")

    total = notes.count()
    if total == 0:
        ctx.compiled_prompt = ""
        ctx.auto_summary = ""
        ctx.last_compiled_at = timezone.now()
        ctx.notes_count_at_compile = 0
        ctx.save()
        return {"compiled_prompt": "", "auto_summary": "", "notes_count": 0}

    # Build notes text
    lines = []
    for n in notes[:100]:  # cap at 100 for token limits
        lines.append(
            f"[{n.recommendation.get_platform_display()} | {n.recommendation.get_category_display()}] "
            f"\"{n.recommendation.title}\": {n.text}"
        )
    notes_text = "\n".join(lines)

    result = _call_openai_json(
        "Você é um assistente que analisa feedback de usuários. Retorne texto puro, sem JSON.",
        _safe_format(COMPILE_PROMPT, notes_text=notes_text),
        max_tokens=2000,
    )

    # _call_openai_json may fail since we asked for plain text — handle gracefully
    if isinstance(result, dict) and "error" in result:
        # Fallback: use raw notes as summary
        summary = notes_text[:3000]
    else:
        summary = str(result) if not isinstance(result, str) else result

    ctx.compiled_prompt = summary[:5000]
    ctx.auto_summary = summary[:5000]
    ctx.last_compiled_at = timezone.now()
    ctx.notes_count_at_compile = total
    ctx.save()

    return {
        "compiled_prompt": ctx.compiled_prompt,
        "auto_summary": ctx.auto_summary,
        "notes_count": total,
    }


# ── Action Preview ──────────────────────────────────────────────

def generate_action_preview(recommendation_id: int) -> dict:
    """Generate a human-readable preview of what applying this rec will do."""
    from .models import AuditRecommendation

    rec = AuditRecommendation.objects.select_related("report__project").get(
        id=recommendation_id,
    )

    # If already has a valid payload, format it
    if rec.can_auto_apply and rec.action_payload and rec.action_payload.get("action_type"):
        preview_text = _format_action_preview(
            rec.action_payload["action_type"], rec.action_payload,
        )
        return {
            "can_apply": True,
            "preview_text": preview_text,
            "action_type": rec.action_payload["action_type"],
            "payload": rec.action_payload,
        }

    # Ask AI to generate a payload or manual instructions
    result = _call_openai_json(
        "Você é um especialista em automação de campanhas. Retorne EXCLUSIVAMENTE JSON válido.",
        _safe_format(
            PREVIEW_PROMPT,
            title=rec.title,
            platform=rec.get_platform_display(),
            category=rec.get_category_display(),
            explanation=rec.explanation[:500],
            action_description=rec.action_description[:500],
            campaign_name=rec.campaign_name or "N/A",
            campaign_id=rec.campaign_id or "N/A",
        ),
        max_tokens=2000,
    )

    if "error" in result:
        return {
            "can_apply": False,
            "preview_text": f"Não foi possível gerar o plano de ação: {result['error']}",
        }

    # If AI said it can apply, update the recommendation
    if result.get("can_apply"):
        rec.action_payload = {
            "action_type": result.get("action_type", ""),
            **result.get("payload", {}),
        }
        rec.can_auto_apply = True
        rec.save()

    return {
        "can_apply": result.get("can_apply", False),
        "preview_text": result.get("preview_text", "Sem informações disponíveis."),
        "action_type": result.get("action_type", ""),
        "payload": result.get("payload", {}),
    }


def _format_action_preview(action_type: str, payload: dict) -> str:
    """Convert a structured action_payload into a Portuguese description."""
    previews = {
        "add_negative_keywords": lambda p: (
            f"Adicionar {len(p.get('keywords', []))} palavra(s)-chave negativa(s) "
            f"na campanha {p.get('campaign_id', 'N/A')}:\n"
            + "\n".join(f"  • {kw.get('text', kw) if isinstance(kw, dict) else kw}"
                        for kw in p.get("keywords", [])[:10])
        ),
        "create_sitelink": lambda p: (
            f"Criar sitelink \"{p.get('link_text', '')}\" "
            f"→ {p.get('final_url', '')}\n"
            f"  Descrição: {p.get('description1', '')} | {p.get('description2', '')}"
        ),
        "create_callout": lambda p: (
            f"Criar extensão de callout: \"{p.get('callout_text', '')}\""
        ),
        "create_structured_snippet": lambda p: (
            f"Criar snippet estruturado — {p.get('header', '')}:\n"
            + "\n".join(f"  • {v}" for v in p.get("values", [])[:8])
        ),
        "add_keywords": lambda p: (
            f"Adicionar {len(p.get('keywords', []))} palavra(s)-chave "
            f"ao grupo de anúncios {p.get('ad_group_id', 'N/A')}:\n"
            + "\n".join(f"  • {kw.get('text', kw) if isinstance(kw, dict) else kw}"
                        for kw in p.get("keywords", [])[:10])
        ),
        "update_targeting": lambda p: (
            f"Atualizar segmentação do conjunto de anúncios {p.get('ad_set_id', 'N/A')}"
        ),
        "update_ad_set": lambda p: (
            f"Atualizar campos do conjunto de anúncios {p.get('ad_set_id', 'N/A')}: "
            + ", ".join(p.get("fields", {}).keys())
        ),
        "submit_url_for_indexing": lambda p: (
            f"Submeter {len(p.get('urls', []))} URL(s) para indexação:\n"
            + "\n".join(f"  • {u}" for u in p.get("urls", [])[:5])
        ),
    }

    formatter = previews.get(action_type)
    if formatter:
        return formatter(payload)
    return f"Ação: {action_type}"


# ── Verification Engine ─────────────────────────────────────────

def verify_recommendation(recommendation_id: int) -> dict:
    """Re-query the platform API to verify if a recommendation was applied."""
    from .models import AuditRecommendation

    rec = AuditRecommendation.objects.select_related("report__project").get(
        id=recommendation_id,
    )

    if rec.status != "applied":
        return {"verified": False, "details": "Recomendação não foi aplicada ainda."}

    payload = rec.action_payload
    action_type = payload.get("action_type", "")
    project = rec.report.project

    try:
        if rec.platform == "google_ads":
            result = _verify_google_ads(project, action_type, payload)
        elif rec.platform == "meta_ads":
            result = _verify_meta_ads(project, action_type, payload)
        elif rec.platform == "seo":
            result = _verify_seo(project, action_type, payload)
        else:
            result = {"verified": False, "details": "Verificação não disponível para esta plataforma."}

        rec.verified_at = timezone.now()
        rec.verification_result = result
        rec.save()
        return result

    except Exception as exc:
        logger.error("Verify recommendation #%d error: %s", recommendation_id, exc)
        result = {"verified": False, "details": f"Erro na verificação: {exc}"}
        rec.verified_at = timezone.now()
        rec.verification_result = result
        rec.save()
        return result


def _verify_google_ads(project, action_type: str, payload: dict) -> dict:
    """Verify a Google Ads action was applied."""
    mgr = _get_google_ads_manager(project)

    if action_type in ("create_sitelink", "create_callout", "create_structured_snippet"):
        assets = mgr.get_existing_assets()
        if assets.get("error"):
            return {"verified": False, "details": f"Erro ao consultar assets: {assets['error']}"}

        asset_type_map = {
            "create_sitelink": "sitelinks",
            "create_callout": "callouts",
            "create_structured_snippet": "structured_snippets",
        }
        asset_list = assets.get(asset_type_map.get(action_type, ""), [])
        if asset_list:
            return {"verified": True, "details": f"Encontrado(s) {len(asset_list)} asset(s) do tipo esperado."}
        return {"verified": False, "details": "Asset não encontrado nas campanhas."}

    elif action_type == "add_negative_keywords":
        campaign_id = payload.get("campaign_id", "")
        if not campaign_id:
            return {"verified": False, "details": "campaign_id não disponível."}
        # Check via search terms or keyword list
        keywords_data = mgr.list_keywords(campaign_id)
        if keywords_data.get("error"):
            return {"verified": False, "details": f"Erro: {keywords_data['error']}"}
        return {"verified": True, "details": "Palavras-chave verificadas com sucesso."}

    elif action_type == "add_keywords":
        ad_group_id = payload.get("ad_group_id", "")
        if not ad_group_id:
            return {"verified": False, "details": "ad_group_id não disponível."}
        keywords_data = mgr.list_keywords(ad_group_id)
        if keywords_data.get("error"):
            return {"verified": False, "details": f"Erro: {keywords_data['error']}"}
        expected = [kw.get("text", kw) if isinstance(kw, dict) else kw for kw in payload.get("keywords", [])]
        found = [kw.get("text", "") for kw in keywords_data.get("keywords", [])]
        matched = sum(1 for kw in expected if kw.lower() in [f.lower() for f in found])
        return {
            "verified": matched > 0,
            "details": f"{matched}/{len(expected)} palavras-chave encontradas.",
        }

    return {"verified": False, "details": f"Verificação não implementada para: {action_type}"}


def _verify_meta_ads(project, action_type: str, payload: dict) -> dict:
    """Verify a Meta Ads action was applied."""
    mgr = _get_meta_ads_manager(project)
    ad_set_id = payload.get("ad_set_id", "")

    if not ad_set_id:
        return {"verified": False, "details": "ad_set_id não disponível."}

    ad_sets = mgr.list_ad_sets()
    if ad_sets.get("error"):
        return {"verified": False, "details": f"Erro: {ad_sets['error']}"}

    found = None
    for ad_set in ad_sets.get("ad_sets", []):
        if str(ad_set.get("id")) == str(ad_set_id):
            found = ad_set
            break

    if not found:
        return {"verified": False, "details": f"Conjunto de anúncios {ad_set_id} não encontrado."}

    return {"verified": True, "details": f"Conjunto de anúncios encontrado: {found.get('name', ad_set_id)}"}


def _verify_seo(project, action_type: str, payload: dict) -> dict:
    """Verify an SEO action was applied."""
    from apps.analytics.search_console import SearchConsoleClient
    from apps.core.models import Site

    if action_type != "submit_url_for_indexing":
        return {"verified": False, "details": f"Verificação não implementada para: {action_type}"}

    urls = payload.get("urls", [])
    site = Site.objects.filter(project=project, is_active=True).first()
    if not site or not urls:
        return {"verified": False, "details": "Nenhum site ou URL para verificar."}

    client = SearchConsoleClient(site=site)
    results = []
    for url in urls[:5]:
        try:
            inspection = client.inspect_url(url)
            verdict = inspection.get("verdict", "UNKNOWN")
            results.append(f"{url}: {verdict}")
        except Exception:
            results.append(f"{url}: Não foi possível verificar")

    all_ok = all("PASS" in r or "URL_IS_ON_GOOGLE" in r for r in results)
    return {
        "verified": all_ok,
        "details": "\n".join(results),
    }
