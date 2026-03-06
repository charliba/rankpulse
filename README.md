# 🚀 RankPulse

**Sistema de Administração de Tráfego Orgânico & Analytics**

Gerencia SEO, Google Analytics 4, Search Console, geração de conteúdo via IA e KPIs para sites web.

---

## 📋 Stack

| Componente | Tecnologia |
|------------|-----------|
| **Backend** | Django 6.0.2 + REST Framework |
| **Database** | PostgreSQL (prod) / SQLite (dev) |
| **Server** | Gunicorn + Nginx |
| **Domain** | https://rankpulse.cloud |
| **VPS** | Hostinger 31.97.171.87 |
| **Analytics** | GA4 Measurement Protocol + Data API |
| **Search** | Google Search Console API |
| **AI** | OpenAI (geração de conteúdo) |

---

## 🏗️ Arquitetura

```
rankPulse/
├── config/                 ← Django settings, URLs, WSGI
├── apps/
│   ├── core/               ← Sites, GA4 events, KPIs, snapshots
│   ├── analytics/          ← GA4 MP, GSC API, GA4 Data API
│   ├── seo/                ← SEO auditor, page scores, keywords
│   ├── content/            ← AI content generator (OpenAI)
│   └── checklists/         ← Weekly/monthly checklists
├── templates/              ← HTML templates (dashboard)
├── static/                 ← CSS, images
├── docs/                   ← Documentação completa
├── deploy.py               ← Deploy via SSH (Paramiko)
├── setup_nginx.py          ← Config Nginx
├── setup_postgresql.py     ← Setup PostgreSQL
├── _setup_ssl.py           ← Certificado SSL (certbot)
├── restart_gunicorn.py     ← Reiniciar Gunicorn
├── verify_site.py          ← Health check
├── manage.py               ← Django management
└── requirements.txt        ← Dependências Python
```

---

## ⚡ Quick Start

### 1. Clone
```bash
git clone https://github.com/charliba/rankpulse.git
cd rankpulse
```

### 2. Virtual Environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 3. Dependências
```bash
pip install -r requirements.txt
```

### 4. Configuração
```bash
cp .env.example .env
# Editar .env com suas credenciais
```

### 5. Database
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. Executar
```bash
python manage.py runserver
# Acesse: http://localhost:8000/admin/
```

---

## 🚀 Deploy (Produção)

```powershell
# Primeiro deploy:
python setup_nginx.py       # Configura Nginx
python deploy.py            # Deploy do código
python setup_postgresql.py  # Configura PostgreSQL
python _setup_ssl.py        # SSL/HTTPS

# Deploys seguintes:
python deploy.py
```

Ver [docs/DEPLOY.md](docs/DEPLOY.md) para detalhes.

---

## 📊 Apps

### Core
Gerencia os sites monitorados. Cada site tem configuração GA4, GSC, eventos definidos, KPIs e snapshots semanais.

### Analytics
- **GA4 Measurement Protocol** — Envia eventos server-side
- **Search Console API** — Busca dados de performance (queries, pages, CTR)
- **GA4 Data API** — Relatórios de tráfego, conversões, páginas

### SEO Auditor
- Crawl de páginas via sitemap ou homepage
- Score por página (meta tags, conteúdo, técnico, performance)
- Tracking de posição de keywords via GSC
- Recomendações automáticas

### Content Generator
- Clusters de conteúdo (pillar + satellite)
- Geração de blog posts via OpenAI
- Workflow: Ideia → Planejado → Gerando → Revisão → Publicado

### Checklists
- Templates reutilizáveis (semanal, mensal)
- Instâncias por site e período
- Tracking de conclusão com progresso

---

## 📚 Documentação

| Documento | Descrição |
|-----------|-----------|
| [docs/DEPLOY.md](docs/DEPLOY.md) | Guia de deploy |
| [docs/ENV.md](docs/ENV.md) | Variáveis de ambiente |
| [docs/SCHEMA.md](docs/SCHEMA.md) | Schema do banco |
| [docs/SECURITY.md](docs/SECURITY.md) | Segurança |
| [docs/AGENTS.md](docs/AGENTS.md) | Instruções para agentes IA |
| [docs/REMEMBER_PROJECT.md](docs/REMEMBER_PROJECT.md) | Lições aprendidas |

---

## 🔧 API Endpoints

### Analytics
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/analytics/<site_id>/send-event/` | Enviar evento GA4 |
| GET | `/api/analytics/<site_id>/event-logs/` | Logs de eventos |
| GET | `/api/analytics/<site_id>/gsc-summary/` | Resumo GSC |

### SEO
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/seo/<site_id>/audit/` | Executar auditoria |
| GET | `/api/seo/<site_id>/audits/` | Histórico de auditorias |
| GET | `/api/seo/<site_id>/keywords/` | Keywords rastreadas |

### Content
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/content/<site_id>/generate/` | Gerar conteúdo |
| GET | `/api/content/<site_id>/topics/` | Listar tópicos |
| GET | `/api/content/<site_id>/posts/` | Posts gerados |

### Checklists
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/checklists/<site_id>/` | Listar checklists |
| POST | `/api/checklists/<site_id>/create/` | Criar checklist |
| POST | `/api/checklists/<site_id>/toggle/` | Toggle item |
| GET | `/api/checklists/<site_id>/<id>/` | Detalhe checklist |

---

## 📝 Licença

Projeto privado — © 2026 charliba
