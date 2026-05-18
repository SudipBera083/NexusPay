# NexusPay — Hybrid INR-USDT Wallet Infrastructure Simulator

![NexusPay](https://img.shields.io/badge/NexusPay-Fintech%20Infrastructure-6366f1?style=for-the-badge)
![Django](https://img.shields.io/badge/Django-4.2-092E20?style=for-the-badge&logo=django)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192?style=for-the-badge&logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker)

A production-grade fintech infrastructure simulator built to demonstrate real-world wallet engineering — including dual-currency accounting, atomic transaction ledgers, real-time exchange rates, and WebSocket-powered live updates.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        NGINX (Port 80)                       │
│              Reverse Proxy + Static Asset Serving            │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  /api/v1/*        /ws/*         / (SPA)
   Django           Daphne        React
   REST API         ASGI WS      Frontend
        │              │
        └──────┬───────┘
               ▼
        ┌─────────────────┐
        │   PostgreSQL 16  │ ← Wallet ledger, transactions,
        │                  │   exchange rates, audit logs,
        └────────┬─────────┘   risk flags
                 │
        ┌────────▼─────────┐
        │   Redis 7        │ ← Celery broker, Django cache,
        │                  │   Channel layer (WebSocket groups)
        └────────┬─────────┘
                 │
        ┌────────▼─────────┐
        │ Celery Workers   │ ← Exchange rate refresh (60s)
        │ Celery Beat      │   Fraud scan (5 min)
        └──────────────────┘   OTP cleanup (5 min)
                               Daily audit report (midnight)
```

---

## Features

### 💼 Wallet Engine
- Dual-currency wallet (INR + USDT) per user
- Immutable ledger with `balance_before` / `balance_after` on every entry
- `select_for_update()` row-level locking inside `transaction.atomic` blocks
- Wallet lock/unlock by admin with reason tracking
- Reversal mechanism for any completed transaction

### 💱 INR ↔ USDT Conversion Engine
- Real-time USDT/INR rate from CoinGecko API
- Redis-cached for 60 seconds, refreshed by Celery
- Bid/ask spread (0.5%) + platform fee (0.1%) applied at conversion
- Atomic debit + credit pair — no partial state possible

### 💳 Smart Payment Engine
- Pay any INR amount to any merchant
- **Auto-conversion**: Uses INR balance first; converts only the required USDT shortfall on-the-fly
- Full ledger entry for every payment and any embedded conversion

### 🔐 Authentication
- JWT access + refresh tokens (SimpleJWT)
- Token blacklisting on logout
- OTP-based account verification (simulation mode shows OTP in UI)
- Role-based access: USER / ADMIN / SUPERADMIN

### 📡 Real-Time WebSocket
- Per-user group for live wallet balance updates after every transaction
- Global group for live exchange rate broadcast every 60s
- Frontend auto-reconnects on disconnect (exponential backoff)
- Live connection status indicator in navbar

### 🛡️ Fraud / Risk Engine
- **LARGE_TRANSACTION**: Flags any single tx ≥ ₹50,000 or 500 USDT
- **HIGH_FREQUENCY**: Flags wallets with ≥10 transactions in 10 minutes
- **RAPID_LARGE_SPENDING**: Flags wallets with >₹1,00,000 debited in 1 hour
- All flags stored in `risk_flags` table with severity (LOW/MEDIUM/HIGH/CRITICAL)
- Admin can review and dismiss flags

### 🧾 Audit Logs
- Every financial operation writes to `audit_logs` with actor, before/after state, IP address, and timestamp
- Admin-accessible, paginated

### 📊 Analytics Dashboard
- Daily spending chart (area chart)
- Category breakdown (pie + bar)
- 30d / 7d / 90d selectable windows
- Balance history timeline

### 🔧 Admin Panel
- Platform-wide stats (total users, balances, volumes, fraud signals)
- User management (search, update role/status)
- Wallet inspection + lock/unlock
- Transaction monitoring with reversal support
- Manual exchange rate override (invalidates Redis cache immediately)
- Audit log viewer

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 4.2, Django REST Framework 3.15 |
| Auth | SimpleJWT (access + refresh + blacklist) |
| Real-time | Django Channels 4 + Daphne (ASGI) |
| Task Queue | Celery 5.3 + Redis 7 |
| Database | PostgreSQL 16 |
| Cache | Redis 7 (Django cache backend) |
| Exchange Rates | CoinGecko Public API |
| API Docs | drf-spectacular (Swagger + ReDoc) |
| Frontend | React 18 + Vite + Tailwind CSS v3 |
| State | Zustand |
| Containers | Docker + Docker Compose |

---

## Quick Start (Docker Only)

**Prerequisites:** Docker Desktop installed.

```bash
# 1. Clone the repository
git clone https://github.com/SudipBera083/NexusPay.git
cd NexusPay/nexuspay

# 2. Copy environment file
cp .env.example .env

# 3. Start the entire stack
docker compose up --build -d

# 4. Check all services are running
docker compose ps
```

**Access points:**
| Service | URL |
|---|---|
| Application | http://localhost |
| API (direct) | http://localhost:8000/api/v1/ |
| Swagger Docs | http://localhost:8000/api/docs/ |
| ReDoc | http://localhost:8000/api/redoc/ |
| Frontend (direct) | http://localhost:3000 |

> ⚠️ **Use http://localhost (port 80) for full functionality.** Port 3000 serves the frontend directly and cannot route API calls.

---

## API Reference

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register/` | Register new user |
| POST | `/api/v1/auth/login/` | Login, get JWT tokens |
| POST | `/api/v1/auth/logout/` | Blacklist refresh token |
| GET/PATCH | `/api/v1/auth/profile/` | Get or update profile |
| POST | `/api/v1/auth/otp/request/` | Request OTP for email |
| POST | `/api/v1/auth/otp/verify/` | Verify OTP |
| POST | `/api/v1/auth/token/refresh/` | Refresh access token |

### Wallet
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/wallet/` | Get balances |
| POST | `/api/v1/wallet/deposit/` | Simulate deposit |
| GET | `/api/v1/wallet/transactions/` | List ledger entries |
| GET | `/api/v1/wallet/transactions/{id}/` | Get single entry |

### Exchange
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/exchange/rate/` | Get current USDT/INR rate |
| POST | `/api/v1/exchange/quote/` | Get conversion quote |
| GET | `/api/v1/exchange/history/` | Rate history |

### Transactions
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/transactions/convert/` | Execute conversion |
| GET | `/api/v1/transactions/conversions/` | Conversion history |
| POST | `/api/v1/transactions/pay/` | Make merchant payment |
| GET | `/api/v1/transactions/payments/` | Payment history |

### Dashboard
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/dashboard/overview/` | Wallet + 30d stats |
| GET | `/api/v1/dashboard/analytics/` | Chart data |

### Admin (ADMIN role required)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/admin-panel/stats/` | Platform statistics |
| GET | `/api/v1/admin-panel/users/` | User list |
| GET/PATCH | `/api/v1/admin-panel/users/{id}/` | User detail / update |
| GET/PATCH | `/api/v1/admin-panel/users/{id}/wallet/` | Wallet inspect / lock |
| GET | `/api/v1/admin-panel/transactions/` | All transactions |
| POST | `/api/v1/admin-panel/transactions/{id}/reverse/` | Reverse transaction |
| GET | `/api/v1/admin-panel/audit-logs/` | Audit log |
| POST | `/api/v1/admin-panel/exchange-rate/override/` | Override rate |

### WebSocket
| URL | Description |
|---|---|
| `ws://localhost/ws/wallet/?token=<JWT>` | Per-user balance + transaction events |
| `ws://localhost/ws/rates/` | Live exchange rate broadcast |

---

## Database Schema

```
users              ← Custom AbstractBaseUser (UUID PK)
wallets            ← OneToOne → User; INR + USDT balances
wallet_transactions ← Immutable ledger; balance_before/after per entry
exchange_rates     ← Rate history; bid/ask/spread per record
conversion_history ← INR↔USDT conversion records with fee accounting
payment_transactions ← Merchant payment records with USDT conversion tracking
risk_flags         ← Fraud/risk signals with severity and review status
audit_logs         ← Full actor/before/after audit trail
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | dev key | Django secret key |
| `DEBUG` | `False` | Debug mode |
| `DB_NAME` | `nexuspay` | PostgreSQL database name |
| `DB_USER` | `nexuspay_user` | PostgreSQL user |
| `DB_PASSWORD` | `nexuspay_password` | PostgreSQL password |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `COINGECKO_API_KEY` | `""` | Optional CoinGecko Pro API key |
| `CONVERSION_SPREAD_PERCENT` | `0.5` | Market maker spread % |
| `CONVERSION_FEE_PERCENT` | `0.1` | Platform fee % |
| `OTP_SIMULATION_MODE` | `True` | Show OTP in response (dev only) |

---

## Engineering Design Decisions

**Why `select_for_update()` inside `transaction.atomic`?**  
PostgreSQL advisory locking prevents race conditions on wallet balances. Without it, two concurrent payments could both read the same balance and both succeed, creating an overdraft.

**Why is `get_wallet()` a plain fetch (no lock)?**  
`select_for_update()` requires an active transaction. The getter is a read-only helper; locking happens inside `credit()` and `debit()` which are always inside `@transaction.atomic`.

**Why `on_commit()` for WebSocket notifications?**  
Firing a Celery task before the transaction commits means the task might read stale data if it runs before PostgreSQL commits. `transaction.on_commit()` ensures the task fires only after the write is durable.

**Why store `balance_before` and `balance_after` on every ledger entry?**  
Enables independent verification of the ledger without replaying the full transaction history. Any discrepancy between consecutive `balance_after`→`balance_before` entries immediately indicates tampering or a bug.
