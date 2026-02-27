# 🧠 REMEMBER_PROJECT.md — Lições Aprendidas (RankPulse)

> **⚠️ AGENTE IA:** Este documento contém lições aprendidas **ESPECÍFICAS** do projeto RankPulse.
> Consulte **ANTES** de resolver problemas deste projeto.
> Após resolver um problema novo, adicione aqui.

---

## 📋 Informações do Projeto

| Item | Valor |
|------|-------|
| **Projeto** | RankPulse — Admin de Tráfego Orgânico |
| **VPS** | Hostinger 31.97.171.87 |
| **Domínio** | https://rankpulse.cloud |
| **Framework** | Django 6.0.2 |
| **Repositório** | github.com/charliba/rankpulse (branch: `main`) |
| **Database** | PostgreSQL (prod) / SQLite (dev) |
| **Porta** | 8002 (Gunicorn) |

---

## 🚀 Deploy e Servidor

### ✅ LIÇÃO: Coexistência com Beezle no mesmo VPS
**Data:** Fev/2026

RankPulse e Beezle.io compartilham o mesmo VPS (31.97.171.87):
- **Beezle:** Gunicorn porta 8001, PostgreSQL DB `beezle`
- **RankPulse:** Gunicorn porta 8002, PostgreSQL DB `rankpulse`
- **Nginx:** Server blocks separados, cada um fazendo proxy para sua porta

**NUNCA** mudar a porta 8002 sem atualizar: `.env`, `deploy.py`, `restart_gunicorn.py`, `verify_site.py`, Nginx config.

---

### ✅ LIÇÃO: SSH via Paramiko
**Data:** Fev/2026

Mesma regra do Beezle: NUNCA usar SSH direto via terminal (trava pedindo senha).
SEMPRE usar `python deploy.py` ou os scripts de setup que usam Paramiko.

---

### ✅ LIÇÃO: DNS
**Data:** Fev/2026

DNS configurado:
- `A @ → 31.97.171.87` (TTL 3600)
- `CNAME www → rankpulse.cloud` (TTL 300)

---

**Última atualização:** Fevereiro 2026
