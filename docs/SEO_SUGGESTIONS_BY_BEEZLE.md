# SEO Suggestions by Beezle Project

> **Referência**: Implementação completa de SEO realizada no projeto [beezle.io](https://beezle.io).
> Estas sugestões podem ser apresentadas ao usuário do RankPulse como checklist de implementação de SEO para seus sites.
> Última atualização: Julho 2025.

---

## 1. Fundação Técnica (Technical SEO)

### 1.1 robots.txt
- [ ] Arquivo `robots.txt` acessível em `https://seusite.com/robots.txt`
- [ ] `Allow` para páginas públicas (home, blog, landing pages)
- [ ] `Disallow` para áreas restritas (admin, dashboard, login, API)
- [ ] Referência ao `Sitemap: https://seusite.com/sitemap.xml`
- [ ] Regras específicas para AI crawlers (GPTBot, Google-Extended, ChatGPT-User, anthropic-ai, PerplexityBot)
- [ ] Referência ao RSS feed: `Allow: /blog/feed/`

**Exemplo implementado (Beezle):**
```
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /dashboard/
Disallow: /api/
Disallow: /login/
Sitemap: https://beezle.io/sitemap.xml

User-agent: GPTBot
Allow: /
Allow: /llms.txt
```

### 1.2 Sitemap XML
- [ ] `sitemap.xml` dinâmico gerado automaticamente
- [ ] Incluir todas as páginas públicas estáticas
- [ ] Incluir posts do blog com `lastmod`
- [ ] Incluir categorias e tags do blog
- [ ] Protocolo HTTPS forçado
- [ ] `changefreq` e `priority` configurados por tipo de página

### 1.3 Canonical URLs
- [ ] Tag `<link rel="canonical">` em todas as páginas
- [ ] Forçar HTTPS no canonical
- [ ] Evitar parâmetros de query no canonical
- [ ] Canonical correto em páginas paginadas

### 1.4 HTTPS e Performance
- [ ] Certificado SSL válido (Let's Encrypt ou similar)
- [ ] Redirecionamento HTTP → HTTPS
- [ ] Nginx: compressão gzip habilitada
- [ ] Nginx: cache headers para assets estáticos (CSS, JS, imagens)
- [ ] Nginx: security headers (X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
- [ ] Preconnect para recursos externos (fonts, CDNs)

---

## 2. Meta Tags e Open Graph

### 2.1 Meta Tags Básicas
- [ ] `<title>` único por página (50-60 caracteres)
- [ ] `<meta name="description">` único (150-160 caracteres)
- [ ] `<meta name="keywords">` com termos relevantes
- [ ] `<meta name="author">`
- [ ] `<meta name="theme-color">`
- [ ] `<meta name="viewport">` para responsividade

### 2.2 Open Graph (Facebook/LinkedIn)
- [ ] `og:type` (website, article)
- [ ] `og:site_name`
- [ ] `og:title` (único por página)
- [ ] `og:description` (único por página)
- [ ] `og:image` — imagem 1200x630px (**OBRIGATÓRIO para compartilhamento social**)
- [ ] `og:url` — URL canônica
- [ ] `og:locale` (ex: pt_BR)

### 2.3 Twitter Cards
- [ ] `twitter:card` (summary_large_image)
- [ ] `twitter:title`
- [ ] `twitter:description`
- [ ] `twitter:image`

### 2.4 Imagem OG Default
- [ ] Criar `og-default.png` (1200x630px) com logo e branding
- [ ] Colocar em `/static/images/og-default.png`
- [ ] Referenciar como fallback em todas as páginas
- [ ] Posts do blog devem ter imagem OG específica quando possível

---

## 3. JSON-LD (Dados Estruturados)

### 3.1 Organization Schema (todas as páginas)
```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Nome da Empresa",
  "url": "https://seusite.com",
  "logo": "https://seusite.com/static/images/logo.svg",
  "description": "Descrição da empresa",
  "contactPoint": {
    "@type": "ContactPoint",
    "email": "contato@seusite.com",
    "contactType": "customer service"
  }
}
```

### 3.2 WebSite Schema com SearchAction (todas as páginas)
```json
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "Nome do Site",
  "url": "https://seusite.com",
  "inLanguage": "pt-BR",
  "potentialAction": {
    "@type": "SearchAction",
    "target": {
      "@type": "EntryPoint",
      "urlTemplate": "https://seusite.com/busca/?q={search_term_string}"
    },
    "query-input": "required name=search_term_string"
  }
}
```

### 3.3 SoftwareApplication Schema (para SaaS/apps)
- [ ] Name, description, applicationCategory
- [ ] Offers com preços e planos
- [ ] AggregateRating quando disponível
- [ ] Presente em TODAS as landing pages (não esquecer nenhuma)

### 3.4 FAQPage Schema (landing pages)
- [ ] Perguntas frequentes da página em formato JSON-LD
- [ ] Mínimo 3-5 perguntas por página
- [ ] Respostas completas e informativas

### 3.5 BreadcrumbList Schema (navegação)
- [ ] Trilha de navegação em formato JSON-LD
- [ ] Home → Seção → Página atual
- [ ] URLs absolutas com HTTPS

### 3.6 Article Schema (blog posts)
- [ ] headline, description, url
- [ ] author (Organization ou Person)
- [ ] publisher com logo
- [ ] datePublished e dateModified
- [ ] image (imagem do post)

---

## 4. Google Analytics 4 (GA4)

### 4.1 Instalação Base
- [ ] Tag gtag.js no `<head>` de todas as páginas
- [ ] Measurement ID configurado (G-XXXXXXXXXX)
- [ ] Enhanced Measurement habilitado (page_view, scroll, outbound clicks)
- [ ] DebugView testado e funcionando

### 4.2 Eventos de Conversão por Funil

**TOPO (Descoberta):**
- [ ] `select_content` — cliques em CTAs da home e landing pages
  ```javascript
  gtag('event', 'select_content', {
    content_type: 'cta',
    content_id: 'home_criar_conta'
  });
  ```

**MEIO (Consideração):**
- [ ] `sign_up` — cadastro de novo usuário
  ```javascript
  gtag('event', 'sign_up', { method: 'email' });
  ```
- [ ] `generate_lead` — novo lead qualificado
  ```javascript
  gtag('event', 'generate_lead', {
    currency: 'BRL',
    value: 200.00,
    lead_source: 'direct'
  });
  ```
- [ ] `view_item_list` — visualização da página de planos/preços

**FUNDO (Decisão):**
- [ ] `begin_checkout` — clique em "Assinar plano"
  ```javascript
  gtag('event', 'begin_checkout', {
    currency: 'BRL',
    value: 99.00,
    items: [{ item_id: 'plano_pro', item_name: 'Pro', price: 99, quantity: 1 }]
  });
  ```
- [ ] `purchase` — pagamento confirmado
  ```javascript
  gtag('event', 'purchase', {
    transaction_id: 'TXN_123',
    currency: 'BRL',
    value: 99.00,
    items: [{ item_id: 'plano_pro', item_name: 'Pro', price: 99, quantity: 1 }]
  });
  ```

### 4.3 Marcar Conversões no GA4
No GA4 Admin → Events → marcar como "Key Event":

| Evento | Marcar? | Valor |
|--------|---------|-------|
| sign_up | ✅ SIM | — |
| generate_lead | ✅ SIM | Dinâmico |
| begin_checkout | ✅ SIM | — |
| purchase | ✅ SIM | Dinâmico |

### 4.4 Blog Analytics
- [ ] `search` — busca no blog
- [ ] `select_content` — cliques em CTAs dentro de posts
- [ ] `share` — compartilhamento de posts

---

## 5. Google Search Console (GSC)

### 5.1 Verificação
- [ ] Verificar propriedade do domínio (DNS TXT record ou HTML file)
- [ ] Adicionar versões www e sem www
- [ ] Definir domínio preferido

### 5.2 Configuração
- [ ] Submeter sitemap.xml
- [ ] Verificar cobertura de indexação
- [ ] Corrigir erros de rastreamento
- [ ] Solicitar indexação de páginas-chave

### 5.3 Monitoramento Semanal
- [ ] Verificar impressões e cliques (Performance)
- [ ] Verificar erros de rastreamento (Coverage)
- [ ] Monitorar Core Web Vitals
- [ ] Verificar mobile usability
- [ ] Checar links externos (Links report)

---

## 6. Conteúdo e Blog

### 6.1 Estratégia de Conteúdo
- [ ] Definir 4-6 clusters de palavras-chave
- [ ] 10+ tópicos por cluster
- [ ] Publicar 2-4 posts por semana
- [ ] Posts de 1500-3000 palavras para termos competitivos
- [ ] Internal linking entre posts do mesmo cluster

### 6.2 SEO On-Page para Posts
- [ ] Title com keyword principal (H1)
- [ ] Meta description com keyword + CTA
- [ ] Heading hierarchy (H2, H3) com keywords LSI
- [ ] Imagens com alt text descritivo
- [ ] URLs amigáveis (slug com keyword)
- [ ] Texto âncora interno relevante

### 6.3 RSS Feed
- [ ] RSS 2.0 feed em `/blog/feed/rss/`
- [ ] Atom 1.0 feed em `/blog/feed/atom/`
- [ ] Links `<link rel="alternate">` no `<head>`
- [ ] Feed incluído no robots.txt

### 6.4 Geração de Conteúdo com IA
- [ ] Usar IA (GPT-4) para gerar rascunhos de posts
- [ ] Revisar e personalizar antes de publicar
- [ ] Não publicar conteúdo 100% IA sem revisão
- [ ] Focar em valor único e experiência real

---

## 7. Otimização para IA (AI Search / GEO)

### 7.1 llms.txt
- [ ] Arquivo `llms.txt` na raiz do site
- [ ] Resumo claro do que o site faz
- [ ] Links para páginas principais
- [ ] Informações de contato

### 7.2 llms-full.txt
- [ ] Versão expandida com detalhes técnicos
- [ ] Especificações de produtos/serviços
- [ ] APIs e integrações disponíveis
- [ ] FAQ expandido

### 7.3 AI Crawler Rules
- [ ] Permitir GPTBot no robots.txt
- [ ] Permitir Google-Extended
- [ ] Permitir ChatGPT-User
- [ ] Permitir anthropic-ai
- [ ] Permitir PerplexityBot

---

## 8. Performance e Core Web Vitals

### 8.1 LCP (Largest Contentful Paint) < 2.5s
- [ ] Otimizar imagem hero/banner
- [ ] Preconnect para fonts e CDNs
- [ ] Lazy loading para imagens abaixo do fold
- [ ] Font display: swap

### 8.2 FID/INP (Interaction to Next Paint) < 200ms
- [ ] Scripts não-críticos com `defer` ou `async`
- [ ] Minimizar JavaScript de terceiros
- [ ] Evitar long tasks no main thread

### 8.3 CLS (Cumulative Layout Shift) < 0.1
- [ ] Width/height em todas as imagens
- [ ] Espaço reservado para ads/embeds
- [ ] Fonts com font-display: swap
- [ ] Evitar inserção dinâmica de conteúdo acima do viewport

### 8.4 Nginx Otimizado
```nginx
# Gzip
gzip on;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
gzip_min_length 1000;
gzip_comp_level 6;

# Cache headers para assets estáticos
location /static/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# Security headers
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header X-XSS-Protection "1; mode=block" always;
```

---

## 9. Link Building e Autoridade

### 9.1 Links Internos
- [ ] Página hub para cada cluster de conteúdo
- [ ] Links contextuais entre posts relacionados
- [ ] Breadcrumbs em todas as páginas
- [ ] Footer com links para páginas principais

### 9.2 Links Externos (Backlinks)
- [ ] Perfis em diretórios relevantes
- [ ] Guest posts em blogs do nicho
- [ ] Participação em fóruns e comunidades
- [ ] PR digital (menções em mídia)

---

## 10. Checklist Semanal de SEO

### Segunda-feira — Monitoramento
- [ ] Verificar GSC: erros de rastreamento
- [ ] Verificar GA4: tráfego orgânico
- [ ] Checar Core Web Vitals

### Quarta-feira — Conteúdo
- [ ] Publicar novo post no blog
- [ ] Atualizar post antigo com conteúdo fresco
- [ ] Verificar internal linking

### Sexta-feira — Otimização
- [ ] Analisar keywords com melhor CTR
- [ ] Identificar páginas com impressões mas poucos cliques
- [ ] Ajustar titles/descriptions para melhorar CTR

---

## 11. KPIs para Monitorar

| Métrica | Meta Mensal | Ferramenta |
|---------|-------------|------------|
| Impressões GSC | +20% m/m | Search Console |
| Cliques Orgânicos | +15% m/m | Search Console |
| CTR Médio | > 3% | Search Console |
| Posição Média | < 20 | Search Console |
| Sessões Orgânicas GA4 | +15% m/m | GA4 |
| Taxa de Conversão | > 2% | GA4 |
| Core Web Vitals | Todos "Good" | PageSpeed Insights |
| Páginas Indexadas | +10/mês | Search Console |
| Backlinks | +5/mês | Ahrefs/Semrush |

---

## 12. Ferramentas Recomendadas

| Ferramenta | Uso | Gratuita? |
|------------|-----|-----------|
| Google Search Console | Monitoramento de indexação e keywords | ✅ |
| Google Analytics 4 | Tráfego e conversões | ✅ |
| PageSpeed Insights | Core Web Vitals | ✅ |
| Schema Markup Validator | Validar JSON-LD | ✅ |
| Rich Results Test | Preview de rich snippets | ✅ |
| Ahrefs Webmaster Tools | Backlinks e keywords | ✅ (limitado) |
| Screaming Frog | Crawl completo do site | ✅ (500 URLs) |
| ChatGPT/Claude | Geração de conteúdo | Pago |

---

## Notas de Implementação

Estas sugestões são baseadas na implementação real do projeto Beezle (beezle.io), que inclui:
- Django + PostgreSQL + Gunicorn + Nginx + SSL
- Blog com geração automática via IA
- 6 template tags de JSON-LD reutilizáveis
- GA4 com eventos de conversão em todo o funil
- RSS/Atom feeds para distribuição de conteúdo
- llms.txt + llms-full.txt para AI search optimization

O RankPulse pode usar estas sugestões como base para gerar recomendações automáticas nas auditorias SEO dos sites dos usuários.
