# 🤖 AGENTS.md — Instruções para Agentes IA

> Instruções para agentes IA trabalhando no projeto RankPulse.

---

## Sobre o Projeto

| Item | Valor |
|------|-------|
| **Projeto** | RankPulse — Sistema de Administração de Tráfego Orgânico |
| **Framework** | Django 6.0.2 + Django REST Framework |
| **Database** | PostgreSQL (produção), SQLite (dev) |
| **Domínio** | https://rankpulse.cloud |
| **VPS** | 31.97.171.87 (Hostinger) — compartilhado com beezle.io |
| **Porta** | 8002 (Gunicorn) — beezle.io usa 8001 |
| **GitHub** | https://github.com/charliba/rankpulse |
| **Propósito** | Gerenciar SEO, GA4, conteúdo e KPIs para sites web |

---

## Estrutura do Projeto

```
trafic_provider/
├── config/            ← Django settings, urls, wsgi
├── apps/
│   ├── core/          ← Site, GA4 events, KPIs, snapshots, OAuth flows
│   ├── analytics/     ← GA4 MP, Search Console, GA4 Data API, Google Ads
│   │   ├── ads_client.py     ← GoogleAdsManager (1128 lines, full CRUD)
│   │   ├── ga4_client.py     ← GA4 Measurement Protocol
│   │   ├── ga4_admin.py      ← GA4 Admin API (key events)
│   │   ├── ga4_report.py     ← GA4 Data API (reporting)
│   │   └── search_console.py ← GSC API (sitemap, indexing)
│   ├── seo/           ← SEO auditor, keyword tracking
│   ├── content/       ← Content generator (OpenAI)
│   ├── checklists/    ← Weekly/monthly checklists
│   └── chat_support/  ← Aura AI chat
├── templates/         ← HTML templates (Tailwind + Alpine.js)
├── static/            ← CSS, JS
├── docs/              ← Documentacao
├── deploy.py          ← Deploy completo via Paramiko
├── manage.py          ← Django manage
└── requirements.txt
```

---

## Regras Críticas

1. **Deploy:** SEMPRE usar `python deploy.py` — NUNCA SSH direto
2. **Credenciais:** NUNCA hardcode — usar `.env` via `os.getenv()`
3. **Porta:** RankPulse = 8002, Beezle = 8001 (NUNCA alterar)
4. **Type hints:** Obrigatório em todas as funções
5. **Docstrings:** Obrigatório em classes e métodos públicos
6. **Logging:** Usar `logging` (NUNCA `print` em código de produção)

---

## Documentacao Util

- [DEPLOY.md](DEPLOY.md) — Guia de deploy
- [ENV.md](ENV.md) — Variaveis de ambiente
- [SCHEMA.md](SCHEMA.md) — Schema do banco
- [SECURITY.md](SECURITY.md) — Seguranca
- [GOOGLE_ADS_SETUP.md](GOOGLE_ADS_SETUP.md) — Guia completo Google Ads API
- [REMEMBER_PROJECT.md](REMEMBER_PROJECT.md) — Licoes aprendidas (LEIA PRIMEIRO)
- [SEO_SUGGESTIONS_BY_BEEZLE.md](SEO_SUGGESTIONS_BY_BEEZLE.md) — Checklist SEO

---

## Primeiro Site Gerenciado: Beezle.io

| Item | Valor |
|------|-------|
| GA4 ID | `G-BCGGTGQJR9` |
| Google Ads Tag | `AW-17981883243` |
| Google Ads Customer ID | `329-436-3393` |
| Google Ads MCC | `259-958-1821` |
| GSC | Verificado |
| Sitemap | https://beezle.io/sitemap.xml |
| Blog | 20+ posts com conteudo IA |
| RSS | https://beezle.io/blog/feed/ |

---

## Google Ads API — Status Atual

| Item | Status |
|------|--------|
| OAuth Refresh Token | VALIDO (103 chars) |
| API Version | v23 |
| SDK Version | google-ads v29.2.0 |
| Developer Token | TEST ACCESS (Basic Access solicitado) |
| Fluxo OAuth no site | IMPLEMENTADO (Integracoes page) |
| Teste de conexao | IMPLEMENTADO (botao na Integracoes page) |

> **BLOQUEIO ATUAL:** Developer Token com acesso de Teste. Basic Access solicitado
> em Fev/2026. Quando aprovado, rodar `python manage.py manage_ads setup-beezle`
> para criar a primeira campanha.

---

## Management Commands Disponiveis

| Comando | Descricao |
|---------|----------|
| `manage_ads account-info` | Info da conta Google Ads |
| `manage_ads list-campaigns` | Listar campanhas |
| `manage_ads setup-beezle` | Criar campanha completa para beezle.io |
| `fetch_gsc_data` | Buscar dados do Search Console |
| `mark_key_events` | Marcar Key Events no GA4 |
| `request_indexing` | Solicitar indexacao no GSC |
| `submit_sitemaps` | Submeter sitemaps ao GSC |
| `generate_content` | Gerar conteudo via IA |
| `audit_seo` | Auditoria SEO completa |

---

**Ultima atualizacao:** Fevereiro 2026
