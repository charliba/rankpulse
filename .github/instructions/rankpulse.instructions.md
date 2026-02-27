---
applyTo: "**/*.py"
---

# RankPulse — Contexto do Projeto

## Visão Geral
RankPulse v1.0.0 é um sistema de administração de tráfego orgânico e analytics.
Gerencia SEO, GA4, Google Search Console, geração de conteúdo via IA e KPIs
para sites web. Inicialmente desenvolvido para gerenciar o tráfego do Beezle.io.

## Stack Técnica
- **Backend**: Django 6.0.2 + Django REST Framework
- **Database**: PostgreSQL (produção), SQLite (dev)
- **Server**: Gunicorn (porta 8002) + Nginx no VPS Hostinger
- **Domain**: https://rankpulse.cloud
- **VPS**: 31.97.171.87 (compartilhado com beezle.io na porta 8001)

## Apps Django
- `apps.core` — Sites gerenciados, eventos GA4, KPIs, snapshots semanais
- `apps.analytics` — GA4 Measurement Protocol, Search Console, GA4 Data API
- `apps.seo` — Auditor SEO, scores por página, keyword tracking
- `apps.content` — Gerador de conteúdo via OpenAI (blog posts, landing pages)
- `apps.checklists` — Templates e instâncias de checklists (semanais, mensais)

## Integrações
- **Google Analytics 4** — Measurement Protocol + Data API
- **Google Search Console** — Performance data + Index API
- **OpenAI** — Geração de conteúdo SEO-otimizado

## Padrões de Código
- Type hints em todas as funções
- Docstrings em classes e métodos públicos
- Imports organizados (stdlib, third-party, local)
- Tratamento de erros com logging adequado
- Sem secrets no código (usar .env)
- Deploy SEMPRE via `python deploy.py` (Paramiko)
- NUNCA usar SSH direto (trava pedindo senha)

## Primeiro Site Gerenciado
- **Beezle.io** — GA4 ID: G-BCGGTGQJR9, GSC verificado
