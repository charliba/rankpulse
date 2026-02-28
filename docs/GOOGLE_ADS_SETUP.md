# Google Ads API — Guia Completo de Configuracao

> **Guia passo a passo** para configurar a integracao do RankPulse com o Google Ads API.
> Inclui todas as licoes aprendidas e problemas comuns.
> Ultima atualizacao: Fevereiro 2026

---

## Visao Geral

O RankPulse gerencia campanhas do Google Ads via API. A integracao requer:

1. **Conta MCC** (Manager Account) com Developer Token
2. **Projeto Google Cloud** com Google Ads API ativada
3. **Credenciais OAuth2** (Client ID + Client Secret)
4. **Refresh Token** (gerado via fluxo de consentimento)
5. **Developer Token com Basic Access** (aprovacao do Google)

---

## Pre-requisitos

| Item | Onde obter |
|------|-----------|
| Conta Google Ads | [ads.google.com](https://ads.google.com) |
| Conta MCC (Manager) | [ads.google.com/manager-accounts](https://ads.google.com/home/tools/manager-accounts/) |
| Projeto Google Cloud | [console.cloud.google.com](https://console.cloud.google.com) |
| Google Ads API ativada | [Biblioteca de APIs](https://console.cloud.google.com/apis/library/googleads.googleapis.com) |

---

## Passo 1: Conta MCC e Developer Token

1. Crie ou acesse sua conta MCC em [ads.google.com/manager-accounts](https://ads.google.com/home/tools/manager-accounts/)
2. No menu **Ferramentas e Configuracoes** (icone de chave inglesa) → **Centro de API**
3. O **Developer Token** aparece nesta pagina
4. Anote o **ID da conta MCC** (formato: `123-456-7890`) — aparece no canto superior direito

> **IMPORTANTE:** Tokens novos tem acesso de "Teste" (Test Account). Para operar contas reais, 
> voce precisa solicitar **Basic Access** (ver Passo 5).

---

## Passo 2: Projeto Google Cloud e OAuth

1. Acesse [console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials)
2. Selecione ou crie um projeto
3. **Ative a Google Ads API:** [Biblioteca de APIs](https://console.cloud.google.com/apis/library/googleads.googleapis.com) → Ativar
4. Vá em **Credenciais** → **+ Criar Credenciais** → **ID do cliente OAuth**
5. Tipo de aplicativo: **Aplicativo para computador** (Desktop app)
6. Nome: "RankPulse"
7. Copie o **Client ID** e o **Client Secret**

### Tela de Consentimento OAuth

1. Vá em **Tela de consentimento OAuth** (OAuth consent screen)
2. Preencha os campos obrigatorios (nome do app, email de suporte)
3. Adicione o scope: `https://www.googleapis.com/auth/adwords`
4. **PUBLIQUE O APP** — se ficar em modo "Teste", tokens expiram em 7 dias!

> **LICAO APRENDIDA:** App em modo "Teste" causa erro `invalid_grant` apos 7 dias.
> Sempre publique o app (botao "Publicar aplicativo" na tela de consentimento).

---

## Passo 3: Gerar Refresh Token

### Opcao A: Via Interface do RankPulse (Recomendado)

1. No RankPulse, va em **Integracoes** do seu site
2. Preencha: Customer ID, Developer Token, Client ID, Client Secret
3. Clique em **"Salvar Integracoes"**
4. Clique em **"Gerar Refresh Token Automaticamente"**
5. Uma nova aba abre no Google — faca login e autorize
6. Copie o codigo de autorizacao que aparece
7. Cole no campo e clique em **"Salvar Token"**

### Opcao B: Via Script Local

```powershell
cd trafic_provider
python _generate_refresh_token.py
```

O script:
- Abre o navegador para autorizacao
- Salva o token no banco de dados do RankPulse (VPS)
- Atualiza o `.env` no VPS
- Atualiza os `.env` locais

### Opcao C: Via Comando Manual

```powershell
pip install google-auth-oauthlib

python -c "
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_config(
    {'installed': {
        'client_id': 'SEU_CLIENT_ID',
        'client_secret': 'SEU_CLIENT_SECRET',
        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
        'token_uri': 'https://oauth2.googleapis.com/token'
    }},
    scopes=['https://www.googleapis.com/auth/adwords']
)
creds = flow.run_local_server(port=0)
print('Refresh Token:', creds.refresh_token)
"
```

> **VALIDACAO:** Um refresh token valido tem ~100+ caracteres e comeca com `1//`.
> Tokens com ~46 caracteres sao invalidos.

---

## Passo 4: Configurar no RankPulse

No RankPulse → **Integracoes**:

| Campo | Valor | Notas |
|-------|-------|-------|
| Customer ID | `329-436-3393` | ID da conta onde as campanhas rodam |
| Developer Token | `Nut3gTRDWPH...` | Do Centro de API da conta MCC |
| OAuth Client ID | `109036...` | Do Google Cloud Console |
| OAuth Client Secret | `GOCSPX-...` | Do Google Cloud Console |
| Refresh Token | `1//0han...` | Gerado no Passo 3 |
| Login Customer ID (MCC) | `259-958-1821` | ID da conta MCC (se aplicavel) |

> **LICAO APRENDIDA:** O campo "Login Customer ID" e obrigatorio quando a conta e gerenciada 
> por uma MCC. Sem ele, a API retorna `CUSTOMER_NOT_FOUND`.

---

## Passo 5: Basic Access (Acesso a Contas Reais)

Tokens novos so funcionam com **contas de teste**. Para operar contas reais:

1. Acesse [support.google.com/adspolicy/contact/new_token_application](https://support.google.com/adspolicy/contact/new_token_application)
2. Preencha o formulario:
   - MCC ID
   - Email de contato
   - URL do produto (https://rankpulse.cloud)
   - Descricao do negocio
   - Design Document (PDF descrevendo como a API e usada)
   - Tipo de campanha: Search
   - Funcionalidades: Campaign Creation, Campaign Management, Reporting
3. Aguarde aprovacao (1-3 dias uteis)
4. Verifique o status no **Centro de API** da conta MCC

> **DICA:** O Design Document pode ser gerado automaticamente. 
> Existe um template em `RankPulse_API_Design_Document.md` na raiz do projeto.

---

## Testar Conexao

### Via Interface
Na pagina de Integracoes, clique em **"Testar Conexao"**. O sistema verifica se o refresh token 
consegue obter um access token.

### Via Management Command
```powershell
python manage.py manage_ads account-info --site-id=1
```

---

## Troubleshooting

### Erro: `invalid_grant`
**Causa:** Token expirado, revogado, ou app em modo Teste.
**Solucao:**
1. Verifique se o app OAuth esta **publicado** (nao em Teste)
2. Gere novo refresh token
3. Se persistir, remova o app em [myaccount.google.com/permissions](https://myaccount.google.com/permissions) e refaca

### Erro: `DEVELOPER_TOKEN_NOT_APPROVED`
**Causa:** Token com acesso de Teste, nao pode operar contas reais.
**Solucao:** Solicite Basic Access (Passo 5 acima). Aguarde aprovacao.

### Erro: `GoogleAdsService does not exist in v18`
**Causa:** SDK `google-ads` atualizada mas codigo referencia versao antiga.
**Solucao:** O `ads_client.py` deve usar `v23` (ou superior). Verificar `_get_service()`.

### Erro: `CUSTOMER_NOT_FOUND`
**Causa:** Falta o Login Customer ID (MCC).
**Solucao:** Preencha o campo "Login Customer ID" com o ID da conta MCC.

### Client Secret desaparece ao salvar
**Causa:** PasswordInput do Django envia vazio quando usuario nao altera.
**Solucao:** Ja corrigido no `IntegrationsForm.save()` — preserva campos secretos quando vazios.

---

## Arquitetura

```
User (RankPulse UI)
    │
    ▼
IntegrationsForm ──► Site model (DB)
    │                     │
    │                     ├── google_ads_customer_id
    │                     ├── google_ads_developer_token
    │                     ├── google_ads_client_id
    │                     ├── google_ads_client_secret
    │                     ├── google_ads_refresh_token
    │                     └── google_ads_login_customer_id
    │
    ▼
GoogleAdsManager (ads_client.py)
    │
    ▼
Google Ads API v23 (gRPC via google-ads SDK v29.x)
    │
    ▼
Google Ads API Servers
```

---

## Management Commands

```powershell
# Info da conta
python manage.py manage_ads account-info --site-id=1

# Listar campanhas
python manage.py manage_ads list-campaigns --site-id=1

# Criar campanha completa para Beezle
python manage.py manage_ads setup-beezle --site-id=1

# Listar conversoes
python manage.py manage_ads list-conversions --site-id=1
```

---

## Credenciais Atuais (Beezle.io)

| Campo | Valor |
|-------|-------|
| Customer ID | `329-436-3393` |
| MCC (Login Customer ID) | `259-958-1821` |
| Developer Token | `Nut3gTRDWPHVoDxup2TXLA` |
| Status Token | **TEST ACCESS** (Basic Access solicitado) |
| OAuth Client | `1090368227157-sp2q4si5e3ea4cldjr844oej3d5gmtvs.apps.googleusercontent.com` |
| Refresh Token | Valido (103 chars), salvo no DB e `.env` |
| google-ads SDK | v29.2.0 (suporta API v20-v23) |
| API Version | v23 |

---

**Ultima atualizacao:** Fevereiro 2026
