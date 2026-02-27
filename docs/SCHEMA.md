# 📊 SCHEMA.md — Modelos do Banco de Dados

> Schema completo do RankPulse. Atualizado em Fevereiro 2026.

---

## Apps e Modelos

### `apps.core` — Núcleo

| Modelo | Descrição |
|--------|-----------|
| `Site` | Website gerenciado (GA4, GSC, SEO config) |
| `GA4EventDefinition` | Definição de evento GA4 (nome, JS snippet, server-side) |
| `KPIGoal` | Meta de KPI por período (mês 1/3/6/12) |
| `WeeklySnapshot` | Snapshot semanal de métricas (sessions, signups, GSC) |

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
