# NexusPay — Production-Grade Fintech Application

[![CI/CD](https://github.com/your-org/nexuspay/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/your-org/nexuspay)
[![Django](https://img.shields.io/badge/Django-4.2-green)](https://djangoproject.com)
[![React](https://img.shields.io/badge/React-18.3-blue)](https://react.dev)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://docker.com)

> **Hybrid INR-USDT Wallet Infrastructure Simulator** — A production-grade fintech platform featuring real-time currency conversion, ledger-based transactions, WebSocket live updates, and a full admin panel.

---

## ✨ Features

| Feature | Details |
|---------|---------|
| **Authentication** | JWT + SimpleJWT, Refresh Tokens, OTP verification, RBAC |
| **Dual Wallet** | INR + USDT with Decimal precision (15,2 and 15,8) |
| **Ledger Engine** | Immutable credit/debit records, balance before/after, rollback |
| **Conversion Engine** | CoinGecko live rates, 0.5% spread, 0.1% fee, atomic |
| **Smart Payment** | Auto USDT→INR conversion when INR insufficient |
| **Real-Time** | Django Channels WebSocket, live balance updates |
| **Rate Refresh** | Celery Beat every 60s, broadcast via channels groups |
| **Admin Panel** | User management, fraud monitoring, rate override, audit logs |
| **API Docs** | Swagger UI at `/api/docs/` via drf-spectacular |
| **Docker** | Full Compose stack: Postgres, Redis, Daphne, Celery, Nginx |
| **CI/CD** | GitHub Actions: lint → test → build → push → deploy |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Nginx (Port 80)                       │
│    /api/* → Backend:8000    /ws/* → WS    / → Frontend:80   │
└───────────────────┬─────────────────┬───────────────────────┘
                    │                 │
        ┌───────────▼───┐     ┌───────▼────────┐
        │  Daphne/ASGI  │     │  React + Vite  │
        │  Django REST  │     │  Tailwind CSS  │
        │  Channels WS  │     │  Zustand       │
        └───────┬───────┘     └────────────────┘
                │
    ┌───────────┼────────────┐
    │           │            │
┌───▼───┐ ┌────▼────┐ ┌─────▼──────┐
│ Celery│ │  Redis  │ │ PostgreSQL  │
│ Worker│ │  Cache  │ │  Database   │
│  Beat │ │  Queue  │ │             │
└───────┘ └─────────┘ └─────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Docker + Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.12+ (for local backend dev)

### Docker Setup (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/nexuspay.git
cd nexuspay

# 2. Copy environment file
cp .env.example .env
# Edit .env with your values

# 3. Start all services
docker-compose up -d

# 4. Create superuser
docker-compose exec backend python manage.py createsuperuser

# 5. Access the app
# Frontend: http://localhost
# API: http://localhost/api/v1/
# Swagger: http://localhost/api/docs/
# Django Admin: http://localhost/admin/
```

### Local Development Setup

#### Backend
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements/development.txt

# Set environment variables
cp ../.env.example .env
# Edit .env: set DEBUG=True, use SQLite by removing DB_* settings

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver 8000
```

#### Frontend
```bash
cd frontend

# Install dependencies
npm install

# Start dev server (proxies /api to localhost:8000)
npm run dev
```

#### Celery (optional, for async tasks)
```bash
# In separate terminals from backend/ directory:
celery -A celery_app worker --loglevel=info
celery -A celery_app beat --loglevel=info
```

---

## 📁 Project Structure

```
nexuspay/
├── backend/
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py          # Core settings
│   │   │   ├── development.py   # Dev overrides (SQLite)
│   │   │   └── production.py    # Production security
│   │   ├── urls.py
│   │   └── asgi.py              # Channels ASGI
│   ├── apps/
│   │   ├── authentication/      # JWT auth, OTP, RBAC
│   │   ├── wallet/              # Ledger engine
│   │   ├── exchange/            # CoinGecko + rates
│   │   ├── transactions/        # Conversion + Payment
│   │   ├── dashboard/           # Analytics APIs
│   │   ├── admin_panel/         # Admin APIs
│   │   └── notifications/       # WebSocket consumers
│   ├── core/                    # Shared utilities
│   │   ├── response.py          # APIResponse envelope
│   │   ├── exceptions.py        # Custom exceptions
│   │   ├── middleware.py        # Logging, security headers
│   │   ├── permissions.py       # RBAC
│   │   └── pagination.py
│   ├── celery_app.py            # Celery + beat schedule
│   ├── requirements/
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/client.js        # Axios + interceptors
│   │   ├── store/               # Zustand state
│   │   ├── hooks/               # WebSocket hook
│   │   ├── pages/               # 8 full pages
│   │   ├── components/          # Layout, shared components
│   │   └── utils/               # Formatters
│   ├── tailwind.config.js       # Custom design system
│   └── Dockerfile
├── nginx/                       # Reverse proxy
├── docker-compose.yml
├── .github/workflows/ci-cd.yml
└── docs/
    ├── er_diagram.md
    └── architecture.md
```

---

## 🔌 API Reference

Base URL: `http://localhost/api/v1/`
Swagger UI: `http://localhost/api/docs/`

### Authentication
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register/` | ❌ | Register new user |
| POST | `/auth/login/` | ❌ | Login → JWT tokens |
| POST | `/auth/logout/` | ✅ | Blacklist refresh token |
| POST | `/auth/token/refresh/` | ❌ | Refresh access token |
| GET/PATCH | `/auth/profile/` | ✅ | Get/update profile |
| POST | `/auth/otp/request/` | ❌ | Request OTP |
| POST | `/auth/otp/verify/` | ❌ | Verify OTP |

### Wallet
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/wallet/` | Get wallet + balances |
| POST | `/wallet/deposit/` | Simulate deposit |
| GET | `/wallet/transactions/` | List transactions (paginated) |
| GET | `/wallet/transactions/{id}/` | Transaction detail |

### Exchange
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/exchange/rate/` | Current USDT/INR rate |
| POST | `/exchange/quote/` | Get conversion quote |
| GET | `/exchange/history/` | Rate history |

### Transactions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/transactions/convert/` | Convert INR ↔ USDT |
| GET | `/transactions/conversions/` | Conversion history |
| POST | `/transactions/pay/` | Merchant payment |
| GET | `/transactions/payments/` | Payment history |

### WebSocket Endpoints
| URL | Auth | Description |
|-----|------|-------------|
| `ws://host/ws/wallet/?token=<jwt>` | ✅ | Live balance + notifications |
| `ws://host/ws/rates/` | ❌ | Live exchange rates |

---

## 🔐 Security

- JWT access tokens (60 min) + refresh tokens (7 days) with blacklisting
- Rate limiting: 30 req/min anonymous, 120 req/min authenticated
- Scoped throttles for auth (10/min), conversion (20/min), payment (30/min)
- Password validation with Django validators
- OTP verification (TOTP-based, 5-minute expiry)
- All financial operations wrapped in `transaction.atomic()`
- `select_for_update()` to prevent race conditions on wallet balance
- Security headers middleware (X-Frame-Options, HSTS, etc.)
- Audit logs for every admin action

---

## 🧪 Testing

```bash
cd backend
pytest -v --tb=short
```

---

## 📊 Database Schema

See [docs/er_diagram.md](docs/er_diagram.md)

## 🏛️ Architecture

See [docs/architecture.md](docs/architecture.md)
