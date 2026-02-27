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
│   ├── core/          ← Site, GA4 events, KPIs, snapshots
│   ├── analytics/     ← GA4 MP, Search Console, GA4 Data API
│   ├── seo/           ← SEO auditor, keyword tracking
│   ├── content/       ← Content generator (OpenAI)
│   └── checklists/    ← Weekly/monthly checklists
├── templates/         ← HTML templates
├── static/            ← CSS, images
├── docs/              ← Documentação
├── deploy.py          ← Deploy via Paramiko
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

## Documentação Útil

- [DEPLOY.md](DEPLOY.md) — Guia de deploy
- [ENV.md](ENV.md) — Variáveis de ambiente
- [SCHEMA.md](SCHEMA.md) — Schema do banco
- [SECURITY.md](SECURITY.md) — Segurança

---

## Primeiro Site Gerenciado

O RankPulse foi criado inicialmente para gerenciar o tráfego orgânico do **Beezle.io**:
- GA4 ID: `G-BCGGTGQJR9`
- GSC verificado: ✅
- Sitemap: https://beezle.io/sitemap.xml
- Blog com conteúdo IA

---

**Última atualização:** Fevereiro 2026
