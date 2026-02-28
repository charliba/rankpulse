# REMEMBER_PROJECT.md — Licoes Aprendidas (RankPulse)

> **AGENTE IA:** Este documento contem licoes aprendidas **ESPECIFICAS** do projeto RankPulse.
> Consulte **ANTES** de resolver problemas deste projeto.
> Apos resolver um problema novo, adicione aqui.

---

## Informacoes do Projeto

| Item | Valor |
|------|-------|
| **Projeto** | RankPulse — Admin de Trafego Organico |
| **VPS** | Hostinger 31.97.171.87 |
| **Dominio** | https://rankpulse.cloud |
| **Framework** | Django 6.0.2 |
| **Repositorio** | github.com/charliba/rankpulse (branch: `main`) |
| **Database** | PostgreSQL (prod) / SQLite (dev) |
| **Porta** | 8002 (Gunicorn) |
| **VPS Path** | `/root/rankpulse` |

---

## Deploy e Servidor

### LICAO: Coexistencia com Beezle no mesmo VPS
**Data:** Fev/2026

RankPulse e Beezle.io compartilham o mesmo VPS (31.97.171.87):
- **Beezle:** Gunicorn porta 8001, PostgreSQL DB `beezle`, path `/root/beezle_project`
- **RankPulse:** Gunicorn porta 8002, PostgreSQL DB `rankpulse`, path `/root/rankpulse`
- **Nginx:** Server blocks separados, cada um fazendo proxy para sua porta

**NUNCA** mudar a porta 8002 sem atualizar: `.env`, `deploy.py`, `restart_gunicorn.py`, `verify_site.py`, Nginx config.

---

### LICAO: SSH via Paramiko
**Data:** Fev/2026

Mesma regra do Beezle: NUNCA usar SSH direto via terminal (trava pedindo senha).
SEMPRE usar `python deploy.py` ou os scripts de setup que usam Paramiko.

---

### LICAO: DNS
**Data:** Fev/2026

DNS configurado:
- `A @ → 31.97.171.87` (TTL 3600)
- `CNAME www → rankpulse.cloud` (TTL 300)

---

## Google Ads API

### LICAO: invalid_grant — Token invalido
**Data:** Fev/2026

**Problema:** Refresh token de 46 caracteres retornava `invalid_grant`.
**Causa:** Token gerado com app OAuth em modo "Teste" expira em 7 dias.
**Solucao:**
1. Publicar o app OAuth (Google Cloud Console → Tela de consentimento OAuth → Publicar)
2. Gerar novo refresh token (token valido tem 100+ chars, comeca com `1//`)
3. Validar com `_test_token.py` — deve retornar status 200

**Script:** `_generate_refresh_token.py` — gera token e salva automaticamente no DB + .env

---

### LICAO: API Version mismatch
**Data:** Fev/2026

**Problema:** `GoogleAdsService does not exist in Google Ads API v18`
**Causa:** SDK `google-ads` v29.2.0 suporta v20-v23, nao v18.
**Solucao:** Alterar `_get_service()` em `ads_client.py` para usar versao `v23`.
**Verificar:** `pip show google-ads` mostra a versao instalada.

---

### LICAO: DEVELOPER_TOKEN_NOT_APPROVED
**Data:** Fev/2026

**Problema:** Token de desenvolvedor com acesso de "Teste" nao pode operar contas reais.
**Solucao:** Solicitar **Basic Access** via formulario:
- URL: https://support.google.com/adspolicy/contact/new_token_application
- Necessita: MCC ID, descricao, PDF de design document
- Tempo de aprovacao: 1-3 dias uteis
- Template do PDF: `RankPulse_API_Design_Document.md` na raiz do projeto

**Status atual:** Basic Access SOLICITADO (aguardando aprovacao em Fev/2026).

---

### LICAO: MCC (Login Customer ID) obrigatorio
**Data:** Fev/2026

**Problema:** API retorna `CUSTOMER_NOT_FOUND` sem o Login Customer ID.
**Causa:** Conta 329-436-3393 e gerenciada pela MCC 259-958-1821.
**Solucao:** Sempre preencher o campo `google_ads_login_customer_id` no Site model.

---

### LICAO: PasswordInput apaga secrets no form
**Data:** Fev/2026

**Problema:** Ao salvar o IntegrationsForm, os campos Client Secret e Refresh Token (PasswordInput) eram enviados vazios se o usuario nao os alterasse.
**Causa:** O widget `PasswordInput` nao mostra o valor existente.
**Solucao:** Override no `IntegrationsForm.save()` para preservar campos secretos quando vazios:
```python
_SECRET_FIELDS = ("google_ads_client_secret", "google_ads_refresh_token")

def save(self, commit=True):
    instance = super().save(commit=False)
    if self.instance.pk:
        for field in self._SECRET_FIELDS:
            if not self.cleaned_data.get(field):
                setattr(instance, field, getattr(Site.objects.get(pk=self.instance.pk), field))
    if commit:
        instance.save()
    return instance
```

---

### LICAO: OAuth Refresh Token via browser (UX melhorada)
**Data:** Fev/2026

**Problema:** Gerar refresh token exigia rodar script Python local no terminal.
**Solucao implementada:** Fluxo OAuth integrado na pagina de Integracoes:
1. Views `google_ads_oauth_start` e `google_ads_oauth_exchange` em `apps/core/views.py`
2. UI com Alpine.js no `site_integrations.html`: botao "Gerar Refresh Token", input para codigo, feedback em tempo real
3. View `google_ads_test_connection` para testar se as credenciais estao funcionando
4. Sessao de troubleshooting expandivel com solucoes para erros comuns

---

## SEO e Conteudo

### LICAO: SEO Suggestions existem no projeto
**Data:** Fev/2026

O arquivo `docs/SEO_SUGGESTIONS_BY_BEEZLE.md` contem um checklist completo de SEO baseado na implementacao do beezle.io. Pode ser usado como referencia ao auditar outros sites.

---

## Frontend

### LICAO: Stack do RankPulse
**Data:** Fev/2026

- **CSS:** Tailwind CSS (nao Bootstrap como o Beezle)
- **JS Interativo:** Alpine.js
- **HTMX:** Para partial updates (quando necessario)
- **Templates:** Django template engine com `{% extends "base.html" %}`

---

## Estrutura de Contas Google

```
Projeto Google Cloud: gen-lang-client-0146009396 ("Gemini API")
├── OAuth App: Publicado em producao
├── Google Ads API: Ativada
├── OAuth Client: Desktop app (1090368227157-...)
│
MCC Account: 259-958-1821 (rankPulse)
├── Developer Token: Nut3gTRDWPHVoDxup2TXLA (Test → Basic Access pendente)
└── Client Account: 329-436-3393 (beezle)
    └── Campanhas do Google Ads para beezle.io
```

---

## Apps Django do RankPulse

| App | Descricao | Modelos Principais |
|-----|-----------|-------------------|
| `core` | Sites, KPIs, eventos, snapshots, integracoes | Site, GA4EventDefinition, KPIGoal, WeeklySnapshot |
| `analytics` | GA4 MP, Search Console, Google Ads | GA4EventLog, SearchConsoleData, GA4Report |
| `seo` | Auditor SEO, keyword tracking | SEOAudit, PageScore, KeywordTracking |
| `content` | Gerador de conteudo IA | ContentCluster, ContentTopic, GeneratedPost |
| `checklists` | Checklists semanais/mensais | ChecklistTemplate, ChecklistInstance |
| `chat_support` | Chat de suporte IA (Aura) | — |

---

## Management Commands

| Comando | App | Descricao |
|---------|-----|-----------|
| `manage_ads` | analytics | Criar/listar campanhas, ads, keywords, conversoes |
| `fetch_gsc_data` | analytics | Buscar dados do Search Console |
| `mark_key_events` | analytics | Marcar eventos como Key Events no GA4 |
| `request_indexing` | analytics | Solicitar indexacao de URLs via GSC |
| `submit_sitemaps` | analytics | Submeter sitemaps ao GSC |
| `generate_content` | content | Gerar conteudo via IA |
| `seed_beezle` | core | Popular dados iniciais do beezle.io |
| `seed_checklists` | core | Popular templates de checklists |
| `audit_seo` | seo | Rodar auditoria SEO |

---

## Helper Scripts (raiz do projeto)

| Script | Funcao |
|--------|--------|
| `deploy.py` | Deploy completo via Paramiko |
| `deploy_integrations.py` | Deploy apenas dos arquivos de integracoes |
| `deploy_google_apis.py` | Deploy dos clientes Google APIs |
| `restart_gunicorn.py` | Reiniciar Gunicorn sem deploy |
| `setup_nginx.py` | Configurar Nginx |
| `_setup_ssl.py` | Gerar certificado SSL |
| `setup_postgresql.py` | Instalar/criar banco PostgreSQL |
| `verify_site.py` | Verificar saude do servidor |
| `verify_deploy.py` | Verificar deploy |
| `_generate_refresh_token.py` | Gerar OAuth refresh token (salva DB + .env) |
| `_test_token.py` | Testar validade do refresh token |
| `_check_sdk_version.py` | Verificar versao da SDK google-ads no VPS |
| `_check_db.py` | Verificar campos do DB no VPS |
| `_fix_db_secret.py` | Corrigir campos vazios no DB |
| `_save_mcc.py` | Salvar MCC ID no DB e .env |
| `_deploy_and_run_ads.py` | Deploy + rodar manage_ads |
| `_deploy_fixes.py` | Deploy de correcoes pontuais |
| `_run_campaign_setup.py` | Rodar setup de campanha no VPS |
| `_fetch_creds.py` | Buscar credenciais do VPS |

---

**Ultima atualizacao:** Fevereiro 2026
