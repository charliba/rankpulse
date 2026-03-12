# 🚀 DEPLOY.md — Guia de Deploy RankPulse

> **⚠️ AGENTE IA:** NUNCA use SSH direto. SEMPRE use `python deploy.py`.
> O SSH via terminal trava pedindo senha. Paramiko resolve isso.

---

## 📋 Informações do Servidor

| Item | Valor |
|------|-------|
| **Provedor** | Hostinger VPS |
| **IP** | `31.97.171.87` |
| **Domínio** | `rankpulse.cloud` / `www.rankpulse.cloud` |
| **Sistema** | Ubuntu (Linux) |
| **Usuário** | `root` |
| **Caminho** | `/root/rankpulse` |
| **Web Server** | Nginx (porta 80/443) → Gunicorn (porta 8002) |
| **Python** | venv em `/root/rankpulse/venv` |
| **Database** | SQLite (`/root/rankpulse/db.sqlite3`) |
| **Static** | `/root/rankpulse/staticfiles` |
| **Git Branch** | `main` |

> **NOTA:** Beezle.io roda no mesmo servidor na porta 8001.
> RankPulse usa porta 8002 para coexistir.

---

## 🔄 Workflow de Deploy

```
┌─────────────────┐     git push     ┌─────────────┐   deploy.py    ┌─────────────┐
│  LOCAL (venv)   │ ───────────────► │   GitHub    │ ───────────────► │  VPS (prod) │
│  Windows        │     main         │  charliba/  │   Paramiko SSH  │  Hostinger  │
│  SQLite (dev)   │                  │  rankpulse  │                  │  31.97...   │
└─────────────────┘                  └─────────────┘                  └─────────────┘
```

### Comando Único:
```powershell
cd rankPulse
python deploy.py
```

---

## 📦 O que `deploy.py` Faz

| # | Etapa | Descrição |
|---|-------|-----------|
| 1 | **SSH Connect** | Conecta via Paramiko usando `.env` |
| 1.5 | **Backup DB** | Cópia do SQLite (mantém últimos 10) |
| 1.6 | **Backup Code** | `tar.gz` do projeto (mantém últimos 5) |
| 2 | **Upload Code** | Transfere arquivos Python via SFTP recursivo |
| 3 | **Upload .env** | Transfere `.env` local |
| 4 | **Stop Gunicorn** | `pkill gunicorn` (porta 8002) |
| 5 | **Dependencies** | `pip install -r requirements.txt` + `migrate` |
| 6 | **Collectstatic** | `collectstatic --noinput` |
| 7 | **Start Gunicorn** | `gunicorn --bind=127.0.0.1:8002 --workers=2 --daemon` |
| 8 | **Verify** | Processo, porta, curl local |
| 9 | **Test HTTP** | curl local → 200 |
| 10 | **Test HTTPS** | curl externo → 200 |
| 11 | **Git Push** | `git add . && commit && push origin main` |

---

## 🔧 Arquitetura do Servidor

```
Internet
    │
    ▼
┌─────────────────────────────────┐
│  Nginx (80/443)                 │
│  ├── beezle.io → 127.0.0.1:8001 │
│  └── rankpulse.cloud → :8002    │
└────────────┬────────────────────┘
             │
    ┌────────┴────────┐
    ▼                 ▼
┌──────────┐   ┌──────────┐
│ Gunicorn │   │ Gunicorn │
│ :8001    │   │ :8002    │
│ Beezle   │   │ RankPulse│
└──────────┘   └──────────┘
    │                 │
    ▼                 ▼
┌────────────┐   ┌───────────┐
│ PostgreSQL │   │  SQLite   │
│  beezle    │   │ rankpulse │
└────────────┘   └───────────┘
```

---

## 🔧 Scripts de Infraestrutura

| Script | Função |
|--------|--------|
| `python deploy.py` | Deploy completo |
| `python restart_gunicorn.py` | Reiniciar Gunicorn sem deploy |
| `python setup_nginx.py` | Configurar Nginx (primeira vez) |
| `python _setup_ssl.py` | Gerar certificado SSL (certbot) |
| `python setup_postgresql.py` | *(legacy — não necessário, usa SQLite)* |
| `python verify_site.py` | Verificar saúde do servidor |

### Ordem para primeiro deploy:
```powershell
# 1. Configurar Nginx
python setup_nginx.py

# 2. Deploy do código
python deploy.py

# 3. Configurar PostgreSQL
python setup_postgresql.py

# 4. SSL
python _setup_ssl.py

# 5. Verificar
python verify_site.py
```

---

## 🔒 Segurança em Produção

| Setting | Valor | Propósito |
|---------|-------|-----------|
| `SECURE_SSL_REDIRECT` | `True` | HTTP → HTTPS |
| `SESSION_COOKIE_SECURE` | `True` | Cookie HTTPS only |
| `CSRF_COOKIE_SECURE` | `True` | CSRF HTTPS only |
| `SECURE_HSTS_SECONDS` | `31536000` | HSTS 1 ano |
| `X_FRAME_OPTIONS` | `DENY` | Anti-clickjacking |

---

## 🐛 Troubleshooting

### 502 Bad Gateway
```powershell
python restart_gunicorn.py
```
> **NOTA (Mar/2026):** Se o `restart_gunicorn.py` não resolver, pode ser race condition:
> o `pkill gunicorn` nem sempre libera a porta 8002 imediatamente. Nesse caso,
> mate com `fuser -k 8002/tcp`, aguarde 3-5 segundos, e reinicie.

### SSH trava pedindo senha
```powershell
# NUNCA:
ssh root@31.97.171.87 "..."  # VAI TRAVAR!

# SEMPRE:
python deploy.py  # Paramiko
```

### Porta 8002 em uso
```powershell
# Via deploy.py já mata o processo anterior
# Se precisar manualmente:
python -c "
import paramiko, os; from dotenv import load_dotenv; load_dotenv()
c=paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(os.getenv('VPS_HOST'), username='root', password=os.getenv('VPS_PASSWORD'))
c.exec_command('fuser -k 8002/tcp')
c.close()
"
```

---

**Última atualização:** Março 2026
