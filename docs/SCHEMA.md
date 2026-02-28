# 📊 SCHEMA.md — Modelos do Banco de Dados

> Schema completo do RankPulse. Atualizado em Fevereiro 2026.

---

## Apps e Modelos

### `apps.core` — Nucleo

| Modelo | Descricao |
|--------|-----------|
| `Site` | Website gerenciado (GA4, GSC, Google Ads, SEO config) |
| `GA4EventDefinition` | Definicao de evento GA4 (nome, JS snippet, server-side) |
| `KPIGoal` | Meta de KPI por periodo (mes 1/3/6/12) |
| `WeeklySnapshot` | Snapshot semanal de metricas (sessions, signups, GSC) |

#### Campos Google Ads no modelo `Site`:
| Campo | Tipo | Descricao |
|-------|------|----------|
| `google_ads_customer_id` | CharField(30) | ID da conta (123-456-7890) |
| `google_ads_developer_token` | CharField(100) | Token do Centro de API |
| `google_ads_client_id` | CharField(200) | OAuth Client ID |
| `google_ads_client_secret` | CharField(200) | OAuth Client Secret |
| `google_ads_refresh_token` | CharField(500) | OAuth Refresh Token |
| `google_ads_login_customer_id` | CharField(30) | MCC Account ID (opcional) |
| `gsc_service_account_key` | TextField | JSON da Service Account GSC |
| `ga4_service_account_key` | TextField | JSON da Service Account GA4 |
| `google_ads_configured` | Property | True se 5 campos obrigatorios preenchidos |

### `apps.analytics` — Analytics

| Modelo | Descrição |
|--------|-----------|
| `GA4EventLog` | Log de eventos enviados via Measurement Protocol |
| `SearchConsoleData` | Dados diários do GSC (queries, pages, clicks) |
| `GA4Report` | Relatórios agregados GA4 Data API |

### `apps.seo` — SEO Auditor

| Modelo | Descrição |
|--------|-----------|
| `SEOAudit` | Auditoria SEO completa (score geral, issues) |
| `PageScore` | Score SEO por página (meta, content, technical) |
| `KeywordTracking` | Rastreamento de posição de keywords |

### `apps.content` — Content Generator

| Modelo | Descrição |
|--------|-----------|
| `ContentCluster` | Cluster de conteúdo (pillar + satellites) |
| `ContentTopic` | Tópico individual com keyword alvo |
| `GeneratedPost` | Post gerado por IA (HTML, meta, score) |

### `apps.checklists` — Checklists

| Modelo | Descrição |
|--------|-----------|
| `ChecklistTemplate` | Template reutilizável (semanal, mensal) |
| `ChecklistTemplateItem` | Item de template com categoria e ordem |
| `ChecklistInstance` | Checklist instanciada para um site/período |
| `ChecklistCompletedItem` | Tracking de conclusão de cada item |

---

## Relações Principais

```
Site ──┬── GA4EventDefinition (1:N)
       ├── KPIGoal (1:N)
       ├── WeeklySnapshot (1:N)
       ├── GA4EventLog (1:N)
       ├── SearchConsoleData (1:N)
       ├── GA4Report (1:N)
       ├── SEOAudit ──── PageScore (1:N)
       ├── KeywordTracking (1:N)
       ├── ContentCluster ──── ContentTopic ──── GeneratedPost (1:N)
       └── ChecklistInstance ──── ChecklistCompletedItem (1:N)

ChecklistTemplate ──── ChecklistTemplateItem (1:N)
ChecklistTemplate ──── ChecklistInstance (1:N)
```

---

**Última atualização:** Fevereiro 2026
