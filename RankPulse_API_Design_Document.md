# RankPulse — Google Ads API Design Document

## 1. Product Overview

**RankPulse** (https://rankpulse.cloud) is an internal marketing automation platform built with Django. It manages SEO, Google Analytics, Google Search Console, and Google Ads for websites owned and operated by our organization.

**MCC Account:** 259-958-1821 (rankPulse)  
**Primary Use:** Managing Google Ads campaigns for our own websites

## 2. Google Ads API Usage

### 2.1 Features Using the API

| Feature | API Service | Purpose |
|---------|------------|---------|
| Campaign Management | CampaignService, CampaignBudgetService | Create, update, pause/enable campaigns |
| Ad Group Management | AdGroupService | Create and organize ad groups within campaigns |
| Keyword Management | AdGroupCriterionService | Add/remove keywords with match types |
| Ad Creation | AdGroupAdService | Create Responsive Search Ads (RSAs) |
| Conversion Tracking | ConversionActionService | Create and manage conversion actions |
| Performance Reporting | GoogleAdsService (Search) | Retrieve campaign and keyword performance metrics |
| Account Info | CustomerService | Fetch account details (currency, timezone) |

### 2.2 API Operations

- **Read operations:** Account info, list campaigns, list ad groups, list keywords, list conversion actions, performance reports
- **Write operations:** Create campaigns with budgets, create ad groups, add keywords, create responsive search ads, create conversion actions, update campaign status, update budget amounts

### 2.3 OAuth2 Flow

RankPulse uses the **installed application** OAuth2 flow:
1. Administrator generates a refresh token via one-time browser-based consent
2. Refresh token is stored securely in the database (encrypted field) and server .env
3. API calls use the refresh token to obtain short-lived access tokens
4. No end-user OAuth interaction — only platform administrators

## 3. Architecture

```
┌─────────────────────────────────────────┐
│            RankPulse Platform           │
│         (https://rankpulse.cloud)       │
├─────────────────────────────────────────┤
│                                         │
│  Django Web App (Python 3.12)           │
│  ├── apps/analytics/ads_client.py       │
│  │   └── GoogleAdsManager class         │
│  │       ├── Campaign CRUD              │
│  │       ├── Ad Group CRUD              │
│  │       ├── Keyword management         │
│  │       ├── RSA creation               │
│  │       ├── Conversion actions         │
│  │       └── Performance reporting      │
│  ├── apps/core/models.py               │
│  │   └── Site model (credentials)       │
│  └── management/commands/manage_ads.py  │
│      └── CLI for campaign operations    │
│                                         │
├─────────────────────────────────────────┤
│  Credentials Storage:                   │
│  - Per-site DB fields (encrypted)       │
│  - Server .env fallback                 │
│  - OAuth2 refresh token                 │
└──────────────┬──────────────────────────┘
               │
               │ Google Ads API v23 (gRPC)
               │ google-ads Python SDK v29.x
               │
               ▼
┌─────────────────────────────────────────┐
│         Google Ads API                  │
│  MCC: 259-958-1821                      │
└─────────────────────────────────────────┘
```

## 4. Rate Limiting & Compliance

- **Request frequency:** Low volume — typically < 100 API calls/day
- **Caching:** Campaign data cached locally; reports fetched on-demand
- **No automated bidding changes:** Budget/bid changes require admin action
- **No scraping or data harvesting:** Only reads data for accounts we own
- **Single MCC:** All managed accounts are under our own MCC

## 5. Data Handling

- Credentials stored in server-side database and environment variables
- No credentials exposed to frontend/browser
- API responses displayed only to authenticated administrators
- No sharing of Google Ads data with third parties

## 6. User Access

- **Internal only:** Only company administrators access the platform
- **Authentication:** Django session-based auth with login required
- **No public API:** All endpoints require authentication
- **Single tenant:** Platform manages only our own Google Ads accounts

## 7. Technology Stack

- Python 3.12
- Django 6.0.2
- google-ads SDK v29.2.0
- Google Ads API v23
- Deployed on VPS (Ubuntu/Gunicorn/Nginx)

## 8. Contact

- **Company:** RankPulse
- **Website:** https://rankpulse.cloud
- **Email:** dmendes629@gmail.com
- **MCC ID:** 259-958-1821
