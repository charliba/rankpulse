# 🔒 SECURITY.md — Segurança RankPulse

---

## Configurações de Produção

Quando `DEBUG=False`, as seguintes configurações são ativadas:

| Setting | Valor | Propósito |
|---------|-------|-----------|
| `SECURE_SSL_REDIRECT` | `True` | Redireciona HTTP → HTTPS |
| `SECURE_PROXY_SSL_HEADER` | `('HTTP_X_FORWARDED_PROTO', 'https')` | Detecta HTTPS via Nginx |
| `SESSION_COOKIE_SECURE` | `True` | Cookies só via HTTPS |
| `CSRF_COOKIE_SECURE` | `True` | CSRF cookie só via HTTPS |
| `SECURE_HSTS_SECONDS` | `31536000` | HSTS 1 ano |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `True` | HSTS em subdomínios |
| `SECURE_HSTS_PRELOAD` | `True` | Preload HSTS |
| `X_FRAME_OPTIONS` | `DENY` | Previne clickjacking |

---

## Regras de Credenciais

1. **`.env`** contém TODAS as credenciais — NUNCA versionado
2. **`.env.example`** é o template — versionado, sem valores reais
3. Credenciais são carregadas via `python-dotenv` + `os.getenv()`
4. **NUNCA** hardcode no código

---

## API Security

- Endpoints `POST` requerem CSRF token (Django padrão)
- REST Framework usa session auth + API key
- CORS configurado via `CORS_ALLOWED_ORIGINS`

---

## Acesso ao Servidor

- SSH via **Paramiko** (nunca terminal direto)
- Apenas `root` via `deploy.py`
- Credenciais SSH no `.env` local

---

**Última atualização:** Fevereiro 2026
