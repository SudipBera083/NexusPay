# NexusPay — ER Diagram

## Entity Relationship Overview

```mermaid
erDiagram
    USER {
        uuid id PK
        string email UK
        string first_name
        string last_name
        string phone UK
        string role "USER|ADMIN|SUPERADMIN"
        bool is_verified
        string kyc_status "PENDING|VERIFIED|REJECTED"
        string otp_secret
        datetime otp_created_at
        bool is_active
        datetime date_joined
    }

    WALLET {
        uuid id PK
        uuid user_id FK
        decimal inr_balance "15,2"
        decimal usdt_balance "15,8"
        bool is_active
        bool is_locked
        string lock_reason
        datetime created_at
        datetime updated_at
    }

    WALLET_TRANSACTION {
        uuid id PK
        uuid wallet_id FK
        string transaction_type "CREDIT|DEBIT"
        string currency "INR|USDT"
        string category "DEPOSIT|WITHDRAWAL|CONVERSION|PAYMENT|REFUND|FEE|REVERSAL"
        decimal amount "15,8"
        decimal balance_before "15,8"
        decimal balance_after "15,8"
        string description
        string reference_id
        uuid related_transaction_id FK
        string status "PENDING|COMPLETED|FAILED|REVERSED"
        json metadata
        datetime created_at
    }

    CONVERSION_HISTORY {
        uuid id PK
        uuid user_id FK
        uuid wallet_id FK
        string from_currency
        string to_currency
        decimal from_amount "15,8"
        decimal to_amount "15,8"
        decimal rate "20,8"
        decimal gross_amount "15,8"
        decimal fee_amount "15,8"
        decimal spread_percent "5,4"
        decimal fee_percent "5,4"
        string status "PENDING|COMPLETED|FAILED"
        string reference_id UK
        uuid debit_tx
        uuid credit_tx
        uuid exchange_rate_id
        datetime created_at
    }

    PAYMENT_TRANSACTION {
        uuid id PK
        uuid user_id FK
        uuid wallet_id FK
        string merchant_name
        string merchant_category
        decimal amount_inr "15,2"
        decimal inr_from_balance "15,2"
        decimal usdt_converted "15,8"
        decimal inr_from_conversion "15,2"
        decimal conversion_rate "20,8"
        string description
        string status "PENDING|COMPLETED|FAILED|REFUNDED"
        string reference_id UK
        uuid related_conversion_id FK
        uuid wallet_tx
        datetime created_at
    }

    EXCHANGE_RATE {
        uuid id PK
        string currency_pair "e.g. USDT_INR"
        decimal rate "20,8"
        decimal bid "20,8"
        decimal ask "20,8"
        decimal spread "10,4"
        string source "CoinGecko"
        bool is_live
        datetime fetched_at
    }

    AUDIT_LOG {
        uuid id PK
        uuid actor_id FK
        string action
        string resource_type
        string resource_id
        json before_state
        json after_state
        string ip_address
        string user_agent
        datetime timestamp
    }

    USER ||--o| WALLET : "has one"
    WALLET ||--o{ WALLET_TRANSACTION : "has many"
    USER ||--o{ CONVERSION_HISTORY : "has many"
    WALLET ||--o{ CONVERSION_HISTORY : "has many"
    USER ||--o{ PAYMENT_TRANSACTION : "has many"
    WALLET ||--o{ PAYMENT_TRANSACTION : "has many"
    CONVERSION_HISTORY ||--o{ PAYMENT_TRANSACTION : "may link to"
    WALLET_TRANSACTION ||--o| WALLET_TRANSACTION : "related_transaction"
    USER ||--o{ AUDIT_LOG : "actor"
```

## Key Design Decisions

### Decimal Precision
- **INR balances**: `DecimalField(max_digits=15, decimal_places=2)` — supports up to ₹9,999,999,999,999.99
- **USDT balances**: `DecimalField(max_digits=15, decimal_places=8)` — 8 decimal places for crypto precision
- **Exchange rates**: `DecimalField(max_digits=20, decimal_places=8)` — high precision for rate calculations
- **NO float fields** anywhere in financial data

### Immutable Ledger
- `WalletTransaction` records are never updated after creation
- `balance_before` and `balance_after` are stored for every transaction (point-in-time snapshot)
- Reversals create a **new** transaction (REVERSAL type) and mark original as `REVERSED`
- Cascade is `PROTECT` — transactions cannot be deleted if wallet exists

### Atomic Operations
- All balance updates use `select_for_update()` to acquire row-level locks
- Multi-step operations (e.g., USDT→INR + INR payment) wrapped in `transaction.atomic()`
- Failed conversions roll back all DB changes automatically
