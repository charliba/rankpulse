# 🧭 prompt.md — Orientações para Agentes IA (RankPulse)

> **LEIA ESTE ARQUIVO PRIMEIRO** ao iniciar uma nova sessão.
> Ele contém tudo que você precisa para trabalhar neste projeto de forma eficiente.

---

## 1. Visão Geral do Projeto

**RankPulse** é uma plataforma SaaS de gerenciamento de tráfego pago e orgânico.
O objetivo do dono do projeto é que seja **"o MELHOR app de gerenciamento de tráfego do mundo."**

| Item | Valor |
|------|-------|
| Framework | Django 6.0.2 + DRF |
| Frontend | Tailwind CSS (CDN) + Alpine.js 3.x + HTMX 2.0.4 + Chart.js 4.4.7 |
| Database | SQLite (dev e prod) |
| IA | OpenAI gpt-4.1-mini |
| Domínio | https://app.rankpulse.cloud |
| VPS | 31.97.171.87 — Hostinger (compartilhado com beezle.io e askjoel) |
| Porta | 8002 (Gunicorn) — beezle usa 8001, askjoel usa 8003 |
| Python | 3.12.3 |
| GitHub | github.com/charliba/rankpulse (branch: main) |

---

## 2. Regras de Ouro (NUNCA violar)

1. **Deploy:** SEMPRE `python deploy.py` — NUNCA SSH direto (trava pedindo senha)
2. **Porta 8002:** NUNCA alterar — coexiste com outros projetos no VPS
3. **Credenciais:** NUNCA hardcode — usar `.env` via `os.getenv()`
4. **Frontend:** Tailwind CSS + Alpine.js + HTMX — NUNCA Bootstrap, jQuery ou React
5. **Orçamento:** A auditoria IA NUNCA sugere alteração de orçamento (regra de negócio)
6. **Migrations:** SEMPRE verificar `showmigrations` no VPS antes de criar novas (risco de dessincronia)
7. **Overlays/modais:** NUNCA usar `fixed inset-0` com z-index alto sem condição estrita de ativação

---

## 3. Arquitetura

### Apps Django (7 apps)

| App | Responsabilidade |
|-----|-----------------|
| `core` | Modelos principais (Project, Site, AlertRule, AuditReport, etc.), 48 views, audit engine |
| `analytics` | Clientes API: GoogleAdsManager, MetaAdsManager, GA4, SearchConsoleClient |
| `channels` | Multi-plataforma: Channel + ChannelCredential |
| `seo` | Auditor SEO, keyword tracking |
| `content` | Gerador de conteúdo via OpenAI |
| `checklists` | Checklists semanais/mensais de tarefas |
| `chat_support` | Widget de chat IA (Aura) |

### Modelos Core (9 modelos)

Project → Site → GA4EventDefinition, KPIGoal, WeeklySnapshot
Project → AlertRule → AlertEvent
Project → AuditReport → AuditRecommendation

### API Clients

| Client | Arquivo | Capacidades |
|--------|---------|-------------|
| GoogleAdsManager | `apps/analytics/ads_client.py` | Campanhas, ad groups, keywords, assets, RSA ads (full CRUD) |
| MetaAdsManager | `apps/analytics/meta_ads_client.py` | Campanhas, ad sets, ads, insights (full CRUD) |
| SearchConsoleClient | `apps/analytics/search_console.py` | Queries, pages, indexing, sitemaps |
| GA4 | `apps/analytics/ga4_*.py` | MP events, admin, reports |

### Infraestrutura

```
Internet → Nginx (80/443) → Gunicorn :8002 → Django → SQLite
                          → Gunicorn :8001 → Beezle (PostgreSQL)
                          → Gunicorn :8003 → AskJoel (SQLite)
```

---

## 4. Status das Fases (Março 2026)

| Fase | Descrição | Status |
|------|-----------|--------|
| P1 | Fundação (modelos, views, templates, deploy) | ✅ Completo |
| P2 | Integrações (Google Ads, Meta Ads, GA4, GSC) | ✅ Completo |
| P3 | Automação (alertas, relatórios, checklists) | ✅ Completo |
| P4 | UX (sidebar, onboarding, responsividade) | ✅ Completo |
| AI Audit | Motor de auditoria IA com auto-apply | ✅ Completo |
| P5 | i18n (internacionalização) | 🔄 Parcial (settings prontos, sem locale files) |
| P6 | Multi-tenancy e billing | ⬜ Não iniciado |

---

## 5. Como Fazer Deploy

```powershell
cd rankPulse
python deploy.py
```

O `deploy.py` faz: backup DB → upload SFTP → stop Gunicorn → pip install → migrate → collectstatic → start Gunicorn → verify → git push.

**⚠️ Se der 502 após deploy:** pode ser race condition na porta 8002. Matar com `fuser -k 8002/tcp` via Paramiko, esperar 5s, reiniciar.

---

## 6. Como Trabalhar no Projeto

### Ao implementar nova feature:
1. Ler `docs/REMEMBER_PROJECT.md` para lições aprendidas
2. Ler `docs/SCHEMA.md` se precisar alterar modelos
3. Criar/alterar views em `apps/core/views.py`
4. Templates em `templates/core/` (extends `base.html`)
5. URLs em `apps/core/urls.py`
6. Testar localmente (`python manage.py runserver`)
7. Deploy com `python deploy.py`
8. Verificar no browser: https://app.rankpulse.cloud

### Ao debugar problemas no VPS:
1. Criar script Python que usa Paramiko para diagnóstico
2. Verificar: processos Gunicorn, porta 8002, logs Nginx, migrations
3. NUNCA editar arquivos diretamente no VPS — sempre deploy via script

### Ao criar migrations:
1. Verificar estado no VPS: `python manage.py showmigrations` (via Paramiko)
2. Comparar com estado local
3. Se houver dessincronia: criar migration manual com dependência correta
4. Deploy inclui `migrate` automaticamente

---

## 7. Projetos Gerenciados (clientes)

### Beezle (beezle.io)
- Google Ads Customer ID: 329-436-3393
- MCC: 259-958-1821
- Canais: Google Ads ✅

### MyFace (myfacestudio.com.br)
- Canais: Google Ads ✅, Meta Ads ✅

---

## 8. Problemas Conhecidos / Dívida Técnica

| Item | Descrição |
|------|-----------|
| Developer Token | Google Ads em modo TEST — Basic Access solicitado |
| SQLite em prod | Funciona mas pode ter problemas de concorrência com escala |
| i18n incompleto | `LANGUAGES` e `LOCALE_PATHS` definidos, falta middleware e locale files |
| Race condition deploy | `pkill gunicorn` pode não liberar porta imediatamente |

---

## 9. Documentação Completa

| Doc | Conteúdo |
|-----|----------|
| [AGENTS.md](AGENTS.md) | Instruções completas para agentes IA |
| [REMEMBER_PROJECT.md](REMEMBER_PROJECT.md) | Lições aprendidas (LEIA!) |
| [DEPLOY.md](DEPLOY.md) | Guia detalhado de deploy |
| [SCHEMA.md](SCHEMA.md) | Schema completo do banco de dados |
| [ENV.md](ENV.md) | Variáveis de ambiente necessárias |
| [SECURITY.md](SECURITY.md) | Configurações de segurança |
| [GOOGLE_ADS_SETUP.md](GOOGLE_ADS_SETUP.md) | Setup do Google Ads API |

---

## 10. Contexto do Dono do Projeto

- Fala português brasileiro
- Quer qualidade máxima — "o melhor do mundo"
- Prefere soluções que funcionem e sejam visualmente polidas
- Usa o RankPulse para gerenciar tráfego de seus próprios negócios (Beezle, MyFace)
- Planeja escalar para SaaS multi-tenant eventualmente

---

**Última atualização:** Março 2026
