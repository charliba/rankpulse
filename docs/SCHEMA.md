# 📊 SCHEMA.md — Modelos do Banco de Dados

> Schema completo do RankPulse. Atualizado em Março 2026.

---

## Apps e Modelos

### `apps.core` — Núcleo

| Modelo | Descrição |
|--------|-----------|
| `Project` | Projeto (contém sites e canais) |
| `Site` | Website gerenciado (GA4, GSC, SEO config) |
| `GA4EventDefinition` | Definição de evento GA4 (nome, JS snippet, server-side) |
| `KPIGoal` | Meta de KPI por período (mês 1/3/6/12) |
| `WeeklySnapshot` | Snapshot semanal de métricas (sessions, signups, GSC) |
| `AlertRule` | Regra de alerta (métrica, condição, threshold) |
| `AlertEvent` | Evento disparado por regra de alerta |
| `AuditReport` | Relatório de auditoria IA (score 0-100, análise, snapshot) |
| `AuditRecommendation` | Recomendação de auditoria (plataforma, categoria, impacto, ação auto-aplicável) |

### `apps.channels` — Canais de Tráfego

| Modelo | Descrição |
|--------|-----------|
| `Channel` | Canal de tráfego (google_ads, meta_ads) com flag ativo |
| `ChannelCredential` | Credenciais por canal (customer_id, OAuth tokens, ad account IDs) |

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
Project ──┬── Site (1:N)
          ├── AlertRule ──── AlertEvent (1:N)
          ├── AuditReport ──── AuditRecommendation (1:N)
          └── Channel ──── ChannelCredential (1:N)

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

## Detalhes: AuditReport

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `project` | FK → Project | Projeto auditado |
| `status` | CharField | running / done / error |
| `business_summary` | TextField | Resumo do negócio (scraping do site) |
| `overall_score` | IntegerField | Score 0-100 |
| `overall_analysis` | TextField | Análise geral da IA |
| `raw_data_snapshot` | JSONField | Quantidades de dados analisados |
| `error_message` | TextField | Mensagem de erro (se houver) |
| `duration_seconds` | FloatField | Tempo de execução |

## Detalhes: AuditRecommendation

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `report` | FK → AuditReport | Relatório pai |
| `platform` | CharField | google_ads / meta_ads / seo / general |
| `category` | CharField | 19 categorias (negative_keywords, sitelinks, targeting...) |
| `impact` | CharField | critical / high / medium / low |
| `title` | CharField | Título da recomendação |
| `explanation` | TextField | Explicação detalhada |
| `action_description` | TextField | Ação proposta |
| `action_payload` | JSONField | Dados estruturados para execução automática |
| `can_auto_apply` | BooleanField | Se pode ser aplicado automaticamente |
| `status` | CharField | pending / applied / dismissed / failed |
| `apply_result` | JSONField | Resultado da aplicação |
| `campaign_id` | CharField | ID da campanha relacionada |
| `campaign_name` | CharField | Nome da campanha |

---

**Última atualização:** Março 2026
