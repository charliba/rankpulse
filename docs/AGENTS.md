# 🤖 AGENTS.md — Instruções para Agentes IA

> Instruções para agentes IA trabalhando no projeto RankPulse.
> **LEIA TAMBÉM:** [prompt.md](prompt.md) para orientações de sessão e [REMEMBER_PROJECT.md](REMEMBER_PROJECT.md) para lições aprendidas.

---

## Sobre o Projeto

| Item | Valor |
|------|-------|
| **Projeto** | RankPulse — Plataforma SaaS de Gerenciamento de Tráfego Pago e Orgânico |
| **Objetivo** | Ser "o MELHOR app de gerenciamento de tráfego do mundo" |
| **Framework** | Django 6.0.2 + DRF |
| **Frontend** | Tailwind CSS (CDN) + Alpine.js 3.x + HTMX 2.0.4 + Chart.js 4.4.7 |
| **Database** | SQLite (dev e prod atual) |
| **Domínio** | https://app.rankpulse.cloud |
| **VPS** | 31.97.171.87 (Hostinger) — compartilhado com beezle.io e askjoel |
| **Porta** | 8002 (Gunicorn) — beezle.io usa 8001 |
| **Python** | 3.12.3 |
| **OpenAI** | gpt-4.1-mini (OPENAI_API_KEY no .env) |
| **GitHub** | https://github.com/charliba/rankpulse |

---

## Estrutura do Projeto

```
rankPulse/
├── config/                ← Django settings, urls, wsgi
├── apps/
│   ├── core/              ← Modelos principais, views (48 views), audit engine
│   │   ├── models.py      ← Project, Site, AlertRule, AuditReport, etc. (9 modelos)
│   │   ├── views.py       ← 48 views + 7 helpers (~1900 linhas)
│   │   ├── urls.py        ← 45 URL patterns
│   │   └── audit_engine.py ← Motor de auditoria IA (~450 linhas)
│   ├── analytics/         ← Clientes API para Google Ads, Meta Ads, GA4, GSC
│   │   ├── ads_client.py       ← GoogleAdsManager (~1200 linhas, full CRUD)
│   │   ├── meta_ads_client.py  ← MetaAdsManager (~600 linhas, full CRUD)
│   │   ├── ga4_client.py       ← GA4 Measurement Protocol
│   │   ├── ga4_admin.py        ← GA4 Admin API
│   │   ├── ga4_report.py       ← GA4 Data API (reporting)
│   │   └── search_console.py   ← GSC API (indexing, sitemaps, queries)
│   ├── channels/          ← Channel + ChannelCredential (multi-plataforma)
│   ├── seo/               ← Auditor SEO, keyword tracking
│   ├── content/           ← Gerador de conteúdo IA
│   ├── checklists/        ← Checklists semanais/mensais
│   └── chat_support/      ← Aura AI chat widget
├── templates/             ← 36+ templates HTML (Tailwind + Alpine.js)
│   ├── base.html          ← Layout base com sidebar
│   ├── core/              ← Dashboard, onboarding, audit, campanhas, alertas
│   └── components/        ← Sidebar, cards, tabelas parciais
├── static/                ← CSS (style.css, aura-chat.css) + JS (app.js, aura-chat.js)
├── docs/                  ← Documentação completa
├── deploy.py              ← Deploy completo via Paramiko (NUNCA SSH direto)
├── manage.py
└── requirements.txt
```

---

## Regras Críticas

1. **Deploy:** SEMPRE usar `python deploy.py` — NUNCA SSH direto (trava pedindo senha)
2. **Credenciais:** NUNCA hardcode — usar `.env` via `os.getenv()`
3. **Porta:** RankPulse = 8002, Beezle = 8001 (NUNCA alterar)
4. **Migrations:** Cuidado com dessincronia local vs servidor — verificar `showmigrations` no VPS antes de criar novas
5. **Frontend:** Usar Tailwind CSS + Alpine.js. NUNCA Bootstrap nem jQuery
6. **Logging:** Usar `logging` (NUNCA `print` em código de produção)
7. **Orçamento:** O sistema de audit NUNCA sugere alteração de orçamento (regra de negócio)

---

## Funcionalidades Implementadas (Março 2026)

| Funcionalidade | Status | Descrição |
|---------------|--------|-----------|
| Dashboard Multi-Projeto | ✅ | Score de saúde, métricas orgânicas, Google Ads, Meta Ads |
| Campanhas Google Ads | ✅ | Listagem, performance, keywords, ad groups |
| Campanhas Meta Ads | ✅ | Listagem, performance, ad sets, insights |
| Fontes de Dados | ✅ | GA4, GSC, Google Ads, Meta Ads — conexão e sync |
| Alertas Inteligentes | ✅ | Regras configuráveis por métrica com threshold |
| Relatório Semanal | ✅ | Export PDF/HTML com comparativo semanal |
| Onboarding Wizard | ✅ | 4 steps: site → analytics → ads → done |
| Auditoria IA | ✅ | OpenAI analisa campanhas + site → recomendações auto-aplicáveis |
| Chat Suporte (Aura) | ✅ | Widget flutuante com IA |
| OAuth Google Ads | ✅ | Fluxo de autorização integrado na interface |

---

## API Clients — Capacidades

### GoogleAdsManager (ads_client.py)
- **Leitura:** list_campaigns, list_ad_groups, list_keywords, get_keyword_performance, get_campaign_performance
- **Escrita:** create_campaign, create_ad_group, add_keywords, add_negative_keywords, create_sitelink_asset, create_callout_asset, create_structured_snippet_asset, link_assets_to_campaign, create_responsive_search_ad

### MetaAdsManager (meta_ads_client.py)
- **Leitura:** list_campaigns, list_ad_sets, list_ads, get_campaign_insights, get_ad_set_insights
- **Escrita:** create_campaign, create_ad_set, create_ad, update_ad_set, update_campaign_status

### SearchConsoleClient (search_console.py)
- **Leitura:** fetch_queries, fetch_pages, fetch_daily_totals, inspect_url, batch_inspect_urls
- **Escrita:** submit_url_for_indexing, batch_submit_urls, submit_sitemap

---

## Auditoria IA (audit_engine.py)

Sistema de inteligência artificial que:
1. Faz scraping do site do negócio para entender o contexto
2. Coleta dados de Google Ads, Meta Ads e SEO/GSC
3. Envia tudo ao OpenAI com prompt de especialista 15+ anos
4. Gera recomendações estruturadas com score 0-100
5. Permite aplicar recomendações em 1 clique (auto-apply)

**Ações auto-aplicáveis:** negative keywords, sitelinks, callouts, structured snippets, keywords, targeting Meta, indexação GSC
**Regra #1:** NUNCA sugere alteração de orçamento

---

## Projetos Gerenciados (Produção)

### Beezle
- Site: beezle.io
- Canais: Google Ads ✅
- Google Ads Customer ID: 329-436-3393

### MyFace
- Site: myfacestudio.com.br
- Canais: Google Ads ✅, Meta Ads ✅

---

## Documentação

- [prompt.md](prompt.md) — Prompt de orientação para novos agentes
- [DEPLOY.md](DEPLOY.md) — Guia de deploy
- [ENV.md](ENV.md) — Variáveis de ambiente
- [SCHEMA.md](SCHEMA.md) — Schema do banco
- [SECURITY.md](SECURITY.md) — Segurança
- [GOOGLE_ADS_SETUP.md](GOOGLE_ADS_SETUP.md) — Guia completo Google Ads API
- [REMEMBER_PROJECT.md](REMEMBER_PROJECT.md) — Lições aprendidas (LEIA PRIMEIRO)

---

**Última atualização:** Março 2026
