# 🔐 ENV.md — Referência de Variáveis de Ambiente

> **⚠️ AGENTE IA:** Todas as credenciais estão no arquivo `.env`.
> **NUNCA** peça credenciais ao usuário — consulte `.env` diretamente.
> **NUNCA** hardcode credenciais no código.

---

## 📍 Localização do `.env`

```
trafic_provider/.env          ← Arquivo principal (NÃO versionado)
trafic_provider/.env.example  ← Template de referência (versionado)
```

**No servidor VPS:**
```
/root/rankpulse/.env
```

---

## 📋 Variáveis Completas

### 🖥️ VPS Hostinger
| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `VPS_HOST` | IP do servidor | `31.97.171.87` |
| `VPS_USER` | Usuário SSH | `root` |
| `VPS_PASSWORD` | Senha SSH | `****` |
| `VPS_PROJECT_PATH` | Caminho no VPS | `/root/rankpulse` |

### 🐙 GitHub
| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `GITHUB_REPO` | Repositório | `charliba/rankpulse` |
| `GITHUB_TOKEN` | Token de acesso | `ghp_****` |

### 🎯 Django
| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `SECRET_KEY` | Chave secreta | `change-me-*****` |
| `DEBUG` | Modo debug | `False` (prod) / `True` (dev) |
| `ALLOWED_HOSTS` | Hosts | `rankpulse.cloud,www.rankpulse.cloud,31.97.171.87` |

### 🏷️ App Identity
| Variável | Descrição | Valor |
|----------|-----------|-------|
| `APP_NAME` | Nome da app | `RankPulse` |
| `APP_DOMAIN` | Domínio | `rankpulse.cloud` |
| `APP_URL` | URL completa | `https://rankpulse.cloud` |
| `GUNICORN_PORT` | Porta Gunicorn | `8002` |

### 🗄️ Database
| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `DB_ENGINE` | Engine | `postgresql` |
| `DB_NAME` | Nome | `rankpulse` |
| `DB_USER` | Usuário | `rankpulse_user` |
| `DB_PASSWORD` | Senha | `****` |
| `DB_HOST` | Host | `localhost` |
| `DB_PORT` | Porta | `5432` |

### 📊 Google Analytics 4
| Variável | Descrição |
|----------|-----------|
| `GA4_MEASUREMENT_ID` | ID do stream (ex: `G-BCGGTGQJR9`) |
| `GA4_API_SECRET` | Measurement Protocol secret |
| `GA4_PROPERTY_ID` | Property ID (Data API) |
| `GA4_SERVICE_ACCOUNT_KEY_PATH` | JSON da service account |

### 🔍 Google Search Console
| Variável | Descrição |
|----------|-----------|
| `GSC_SERVICE_ACCOUNT_KEY_PATH` | JSON da service account |
| `GSC_SITE_URL` | URL do site no GSC |

### 🤖 OpenAI
| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `OPENAI_API_KEY` | Chave API | `sk-****` |
| `OPENAI_MODEL` | Modelo | `gpt-4.1-mini` |

### 🌐 Target Site
| Variável | Descrição | Valor padrão |
|----------|-----------|--------------|
| `SITE_NAME` | Site gerenciado | `Beezle` |
| `SITE_DOMAIN` | Domínio | `beezle.io` |
| `SITE_URL` | URL | `https://beezle.io` |

---

## ⚠️ Regras de Segurança

1. **NUNCA** commitar `.env` no Git (está no `.gitignore`)
2. **NUNCA** hardcode credenciais em código Python
3. **SEMPRE** usar `os.getenv()` via `python-dotenv`
4. **SEMPRE** usar `.env.example` como template (sem valores reais)

---

## 🔄 Diferenças Local vs Servidor

| Variável | Local | Servidor |
|----------|-------|----------|
| `DEBUG` | `True` | `False` |
| `DB_ENGINE` | `sqlite3` | `postgresql` |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | `rankpulse.cloud,www.rankpulse.cloud,31.97.171.87` |

---

**Última atualização:** Fevereiro 2026
