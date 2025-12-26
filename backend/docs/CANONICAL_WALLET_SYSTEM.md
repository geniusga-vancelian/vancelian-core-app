# CANONICAL WALLET & SUB-WALLET ARCHITECTURE — Vancelian

> **SOURCE OF TRUTH** — This document defines the authoritative, unambiguous specification for how wallets and sub-wallets work in Vancelian.
>
> **Last Updated:** 2025-01-26
>
> **Purpose:** Enable developers (and AI) to fully understand wallet types, states, accounting rules, money flows, and the differences between AED wallet, Offer wallets, and Vault wallets without reading code.

---

## 1. CORE PRINCIPLES

### 1.1 Multi-Bucket Wallet Architecture

Vancelian uses a **multi-bucket wallet system** to enforce business rules and compliance at the data model level. Each wallet is split into three distinct states: `AVAILABLE`, `LOCKED`, and `BLOCKED`.

**Why multi-bucket?**
- **Business logic enforcement**: Prevents users from withdrawing money that is invested or pending compliance review
- **Compliance safety**: BLOCKED funds cannot be moved until compliance review completes
- **Investment safety**: LOCKED funds represent commitments (investments, vesting) and cannot be withdrawn until maturity
- **Audit clarity**: Each bucket serves a distinct purpose, making financial auditing straightforward

### 1.2 Ledger-Based Double-Entry Accounting

All money movements are recorded as **immutable ledger entries** using double-entry bookkeeping principles.

**Why ledger-based?**
- **Audit trail**: Every movement is permanently recorded and cannot be modified
- **Balance accuracy**: Account balances are computed from ledger entries, not stored fields
- **Transaction history**: Full history of all operations is preserved
- **Compliance**: Regulatory bodies require immutable, auditable financial records

**Double-entry rule**: Every operation must create at least two ledger entries (DEBIT and CREDIT) that sum to zero.

### 1.3 System Wallets for Offers and Vaults

Each **Offer** and each **Vault** has its own **system wallet** (owned by SYSTEM, `user_id=None`). These wallets track the pool of funds managed by the platform for that specific product.

**Why system wallets?**
- **Separation of concerns**: User money (in user wallets) vs. platform-managed money (in system wallets)
- **Product isolation**: Each offer/vault manages its own liquidity pool independently
- **Scalability**: System wallets enable future features like interest distribution, yield generation, and cross-product operations
- **Admin visibility**: Operations teams can monitor product-level balances independently of user positions

### 1.4 USER vs. SYSTEM Money Separation

**USER wallets** (`user_id != NULL`):
- Owned by individual users
- Track personal balances (AVAILABLE, LOCKED, BLOCKED)
- Money can be moved by user actions (invest, withdraw, etc.)

**SYSTEM wallets** (`user_id = NULL`):
- Owned by the platform (SYSTEM)
- Scoped to a specific product (`offer_id` or `vault_id`)
- Track product-level liquidity pools
- Money movement is controlled by business logic (not direct user action)

---

## 2. WALLET TYPES (HIGH LEVEL)

### 2.1 User Wallet (Wallet AED)

**Owner:** User (`user_id` = authenticated user UUID)  
**Scope:** Per-currency, per-user  
**Example:** User's AED wallet with 3 buckets (AVAILABLE, LOCKED, BLOCKED)

**Purpose:**
- Primary wallet for user's liquid funds
- Entry point for deposits (via ZAND webhook)
- Source of funds for investments and vault subscriptions
- Destination for withdrawals and investment returns

**Key Rule:** The AED wallet's `LOCKED` bucket should **NEVER** contain funds directly. Locked funds are represented by user positions in Offers/Vaults, not in the AED wallet itself.

### 2.2 Offer Wallet (System Wallet per Offer)

**Owner:** SYSTEM (`user_id = NULL`)  
**Scope:** Per-offer, per-currency (`offer_id` + `currency`)  
**Example:** Offer "Real Estate Investment" has its own system wallet with 3 buckets

**Purpose:**
- Tracks the total pool of funds invested in a specific offer
- Enables future interest/yield distribution from the offer to investors
- Provides admin visibility into offer-level liquidity
- Separates offer-specific operations from user wallets

**Key Rule:** When a user invests in an offer:
- USER wallet: `WALLET_AVAILABLE` → `WALLET_LOCKED` (user commits funds)
- SYSTEM offer wallet: `OFFER_POOL_AVAILABLE` receives the funds (offer receives capital)

### 2.3 Vault Wallet (System Wallet per Vault)

**Owner:** SYSTEM (`user_id = NULL`)  
**Scope:** Per-vault, per-currency (`vault_id` + `currency`)  
**Example:** Vault "FLEX" has its own system wallet with 3 buckets

**Purpose:**
- Tracks the mutualized cash pool for a vault
- Enables FIFO withdrawal processing when cash is limited
- Provides liquidity management for vault operations
- Enables future yield distribution to vault subscribers

**Key Rule:** When a user subscribes to a vault:
- USER wallet: `WALLET_AVAILABLE` → `VAULT_POOL_CASH` (funds move to vault pool)
- SYSTEM vault wallet: `VAULT_POOL_CASH` increases (vault liquidity increases)
- User position tracked separately in `vault_accounts.principal`

---

## 3. SUB-WALLET STATES (CRITICAL SECTION)

### 3.1 AVAILABLE

**Definition:** Funds that can be freely moved by the user or system logic.

**What it means:**
- Money is "liquid" and ready for use
- No restrictions on withdrawal, investment, or transfer
- User has full control (subject to sufficient balance checks)

**What money is allowed/forbidden:**
- ✅ **Allowed:** Withdrawal, investment in offers, subscription to vaults, transfers
- ❌ **Forbidden:** Nothing — AVAILABLE is the most permissive state

**Who can move money out:**
- **User wallets:** User (via API calls) or system (on user's behalf, e.g., auto-investment)
- **System wallets:** System logic only (no direct user control)

**Typical use cases:**
- User deposits after compliance release
- Withdrawal proceeds
- Investment returns/maturity payouts
- Vault subscription funds (before being moved to vault pool)

**AccountType mappings:**
- User wallets: `WALLET_AVAILABLE`
- Offer system wallets: `OFFER_POOL_AVAILABLE`
- Vault system wallets: `VAULT_POOL_CASH` (backward compatibility note: this is the "available" bucket)

---

### 3.2 LOCKED (≡ vested / invested)

**Definition:** Funds that are committed to a specific product or vesting schedule and cannot be withdrawn until maturity or product completion.

**What it means:**
- Money is "immobilized" for a business purpose
- Represents a commitment (investment in an offer, vesting in a vault)
- Cannot be withdrawn until the lock period expires or the product matures

**What money is allowed/forbidden:**
- ✅ **Allowed:** Maturation (automatic transition to AVAILABLE when lock expires)
- ❌ **Forbidden:** Withdrawal, transfer, any movement except maturation

**Who can move money out:**
- **System logic only:** Automatic maturation based on `locked_until` timestamp or product completion

**Typical use cases:**
- Investment in an offer (funds locked until offer completion or maturity)
- AVENIR vault vesting (funds locked for 1 year)
- Future: Locked allocations in multi-phase offers

**Important distinction:** LOCKED ≠ BLOCKED
- LOCKED = business/product commitment (user chose to lock funds)
- BLOCKED = compliance/regulatory hold (system/regulatory requirement)

**AccountType mappings:**
- User wallets: `WALLET_LOCKED`
- Offer system wallets: `OFFER_POOL_LOCKED`
- Vault system wallets: `VAULT_POOL_LOCKED`

---

### 3.3 BLOCKED (compliance, AML, webhook pending)

**Definition:** Funds that are temporarily held pending compliance review, AML checks, or external payment rail confirmation.

**What it means:**
- Money is "frozen" by system/regulatory logic
- Cannot be moved until compliance review completes
- Represents a temporary hold, not a user commitment

**What money is allowed/forbidden:**
- ✅ **Allowed:** Compliance release (admin action) or deposit rejection (admin action)
- ❌ **Forbidden:** Any user-initiated movement, investment, withdrawal

**Who can move money out:**
- **Admin/Compliance only:** Authorized compliance officers via admin API
- **System logic:** Automatic rejection after timeout (future feature)

**Typical use cases:**
- ZAND deposit webhook received → funds go to BLOCKED pending compliance review
- Compliance officer reviews → releases funds to AVAILABLE
- Compliance officer rejects → funds reversed (DEBIT BLOCKED, CREDIT INTERNAL_OMNIBUS)

**Important distinction:** BLOCKED ≠ LOCKED
- BLOCKED = compliance/regulatory hold (temporary, system-controlled)
- LOCKED = business/product commitment (longer-term, user-initiated)

**AccountType mappings:**
- User wallets: `WALLET_BLOCKED`
- Offer system wallets: `OFFER_POOL_BLOCKED`
- Vault system wallets: `VAULT_POOL_BLOCKED`

---

## 4. WALLET BY CATEGORY (DETAILED TABLES)

### 4.1 Wallet AED (User Wallet)

**Initial Creation:**
- Created automatically on first deposit or user action requiring a wallet
- Three buckets created simultaneously: `WALLET_AVAILABLE`, `WALLET_LOCKED`, `WALLET_BLOCKED`
- Idempotent operation: `ensure_wallet_accounts(db, user_id, currency)`

**Sub-wallets:**
1. `WALLET_AVAILABLE` — Liquid funds, withdrawable
2. `WALLET_LOCKED` — Committed funds (investments, vesting)
3. `WALLET_BLOCKED` — Compliance hold funds

**Key Rule:** The AED wallet's `WALLET_LOCKED` bucket should **NEVER** show a balance in the user-facing UI. Locked funds are represented by user positions in Offers/Vaults, not in the AED wallet itself. The wallet matrix endpoint enforces this by always returning `locked = "0.00"` for the AED (USER) row.

---

#### Operations Moving Funds Between AED Sub-Wallets

| Operation | From | To | OperationType | Reason | Who Triggers |
|-----------|------|-----|---------------|--------|--------------|
| ZAND deposit webhook | INTERNAL_OMNIBUS | WALLET_BLOCKED | `DEPOSIT_AED` | External deposit received | System (webhook) |
| Compliance release | WALLET_BLOCKED | WALLET_AVAILABLE | `RELEASE_FUNDS` | Compliance approved | Admin |
| Deposit rejection | WALLET_BLOCKED | INTERNAL_OMNIBUS | `REVERSAL_DEPOSIT` | Compliance rejected | Admin |
| Offer investment | WALLET_AVAILABLE | WALLET_LOCKED | `INVEST_EXCLUSIVE` | User invests in offer | User |
| Vault subscription (FLEX) | WALLET_AVAILABLE | VAULT_POOL_CASH | `VAULT_DEPOSIT` | User subscribes to vault | User |
| Vault subscription (AVENIR) | WALLET_AVAILABLE | WALLET_LOCKED | `VAULT_DEPOSIT` (future: `VAULT_SUBSCRIBE_AVENIR`) | User subscribes to AVENIR (vesting) | User |
| Vault withdrawal (executed) | VAULT_POOL_CASH | WALLET_AVAILABLE | `VAULT_WITHDRAW_EXECUTED` | Withdrawal executed | Admin (FIFO processing) |

**Note:** Vault withdrawals move funds from the vault system wallet (`VAULT_POOL_CASH`) back to the user wallet (`WALLET_AVAILABLE`), not between AED sub-wallets.

---

### 4.2 Offer Wallet (System Wallet per Offer)

**Why each offer has its own system wallet:**
- Isolates offer-specific liquidity from other offers
- Enables future interest distribution to investors
- Provides admin visibility into offer-level capital management
- Allows cross-offer operations (future feature)

**How `OFFER_POOL_AVAILABLE` works:**
- Receives funds when users invest in the offer
- Balance represents total capital available to the offer
- Used for future interest/yield distribution (not yet implemented)

**Relationship with users' LOCKED balances:**
- When user invests: `USER WALLET (WALLET_AVAILABLE)` → `USER WALLET (WALLET_LOCKED)` + `OFFER WALLET (OFFER_POOL_AVAILABLE)`
- User's locked balance represents commitment to the offer
- Offer's available balance represents capital received from all investors

**How future interest distribution will work:**
- Interest/yield generated by the offer (external to this system)
- Admin credits interest to `OFFER_POOL_AVAILABLE`
- System distributes interest proportionally to investors
- Each investor receives: `USER WALLET (WALLET_LOCKED)` → `USER WALLET (WALLET_AVAILABLE)` + interest amount

---

#### Ledger Flows for Offer Investment

```
User Investment Flow:
┌─────────────────────────────────────────────────────────────┐
│ 1. User invests 1000 AED in Offer "Real Estate Investment" │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────┐
    │ Operation: INVEST_EXCLUSIVE (COMPLETED)             │
    │ Operation ID: <op_id>                               │
    └─────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
        ▼                                   ▼
┌──────────────────────┐        ┌──────────────────────┐
│ LedgerEntry 1:       │        │ LedgerEntry 2:       │
│ DEBIT                │        │ CREDIT               │
│ Account: USER        │        │ Account: USER        │
│   WALLET_AVAILABLE   │        │   WALLET_LOCKED      │
│ Amount: -1000.00     │        │ Amount: +1000.00     │
└──────────────────────┘        └──────────────────────┘
        │                                   │
        └─────────────────┬─────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│ Future: Credit to OFFER_POOL_AVAILABLE              │
│ (Currently: funds remain in USER WALLET_LOCKED)     │
└─────────────────────────────────────────────────────┘
```

**Visibility from admin:**
- Admin can query `GET /api/v1/admin/offers/{offer_id}/system-wallet` to see offer-level balances
- Response includes: `available`, `locked`, `blocked` for the offer's system wallet

**Relationship summary:**
- `USER WALLET (WALLET_LOCKED)` with reason `OFFER_INVEST` = user's commitment
- `SYSTEM OFFER WALLET (OFFER_POOL_AVAILABLE)` = offer's received capital pool
- Currently, investment locks user funds but doesn't move them to offer wallet (future enhancement)

---

### 4.3 Vault Wallet (System Wallet per Vault)

**Mutualized fund behavior:**
- All users' subscriptions are pooled into a single `VAULT_POOL_CASH` account
- Vault operates like a mutual fund: users own "shares" (tracked in `vault_accounts.principal`)
- Withdrawals depend on vault cash availability, not individual user positions

**VAULT_POOL_CASH as AVAILABLE liquidity:**
- `VAULT_POOL_CASH` is the vault's "available" bucket (backward compatibility)
- Represents liquid funds available for immediate withdrawal
- Withdrawals are executed FIFO when cash is sufficient

**Why vaults behave like funds:**
- Users subscribe by depositing into the pool
- Users withdraw by requesting withdrawal (subject to pool availability)
- Pool balance determines withdrawal capacity (not individual user balances)
- Future: Pool generates yield, distributed proportionally to subscribers

**How deposits and withdrawals are absorbed by the cash pool:**

**Deposit flow:**
1. User calls `POST /api/v1/vaults/{vault_code}/deposits` with amount
2. System debits `USER WALLET (WALLET_AVAILABLE)`
3. System credits `VAULT WALLET (VAULT_POOL_CASH)`
4. System updates `vault_accounts.principal` for the user
5. Vault cash balance increases → more withdrawal capacity

**Withdrawal flow (executed):**
1. User calls `POST /api/v1/vaults/{vault_code}/withdrawals` with amount
2. If vault cash sufficient:
   - System debits `VAULT WALLET (VAULT_POOL_CASH)`
   - System credits `USER WALLET (WALLET_AVAILABLE)`
   - System updates `vault_accounts.principal` and `available_balance`
   - Operation status: `EXECUTED`
3. If vault cash insufficient:
   - System creates `withdrawal_request` with status `PENDING`
   - No ledger movement (funds remain in vault pool)
   - Operation status: `PENDING`

**Withdrawal flow (FIFO processing):**
1. Admin calls `POST /api/v1/admin/vaults/{vault_code}/withdrawals/process`
2. System locks vault row `FOR UPDATE`
3. System selects pending requests FIFO with `FOR UPDATE SKIP LOCKED`
4. For each pending request:
   - Re-check vault cash balance
   - If sufficient: execute withdrawal (debit vault, credit user)
   - If insufficient: break (stop processing)

---

#### Split: FLEX vs. AVENIR Vault

**FLEX Vault:**
- **Behavior:** Liquid vault, immediate withdrawal available (subject to cash pool)
- **Deposit:** `WALLET_AVAILABLE` → `VAULT_POOL_CASH`
- **Withdrawal:** `VAULT_POOL_CASH` → `WALLET_AVAILABLE`
- **No vesting:** No lock period

**AVENIR Vault:**
- **Behavior:** Vesting vault, 1-year lock period
- **Deposit:** `WALLET_AVAILABLE` → `WALLET_LOCKED` (user wallet, not vault wallet)
- **Vesting period:** 365 days from deposit
- **Maturity:** Automatic transition `WALLET_LOCKED` → `WALLET_AVAILABLE` (after 1 year)
- **After maturity:** Behaves like FLEX vault (withdrawal from `VAULT_POOL_CASH`)
- **Lock enforcement:** Withdrawal endpoint returns `403 LOCKED` if `locked_until > now()`

**Key Difference:**
- **FLEX:** Funds go directly to vault pool (`VAULT_POOL_CASH`)
- **AVENIR:** Funds stay in user wallet (`WALLET_LOCKED`) until vesting matures, then move to vault pool

---

## 5. VAULT-SPECIFIC RULES (IMPORTANT)

### 5.1 FLEX Vault

#### Deposit Flow

```
User → POST /api/v1/vaults/FLEX/deposits
  │
  ├─ Check: vault.status == ACTIVE
  ├─ Check: user WALLET_AVAILABLE balance >= amount
  │
  ├─ Lock: vault row FOR UPDATE
  ├─ Lock: user WALLET_AVAILABLE account FOR UPDATE
  ├─ Lock: vault VAULT_POOL_CASH account FOR UPDATE
  │
  ├─ Create: Operation (VAULT_DEPOSIT, COMPLETED)
  │
  ├─ Ledger:
  │   ├─ DEBIT: USER WALLET_AVAILABLE (-amount)
  │   └─ CREDIT: VAULT VAULT_POOL_CASH (+amount)
  │
  ├─ Update: vault_accounts.principal += amount
  ├─ Update: vault_accounts.available_balance += amount
  │
  └─ Commit transaction
```

#### Withdrawal Flow

**Case A: Cash pool sufficient**
```
User → POST /api/v1/vaults/FLEX/withdrawals
  │
  ├─ Check: vault.status == ACTIVE
  ├─ Check: vault_accounts.available_balance >= amount
  ├─ Check: vault VAULT_POOL_CASH balance >= amount
  │
  ├─ Lock: vault row FOR UPDATE
  ├─ Lock: vault_accounts row FOR UPDATE
  ├─ Lock: user WALLET_AVAILABLE account FOR UPDATE
  ├─ Lock: vault VAULT_POOL_CASH account FOR UPDATE
  │
  ├─ Create: Operation (VAULT_WITHDRAW_EXECUTED, COMPLETED)
  │
  ├─ Ledger:
  │   ├─ DEBIT: VAULT VAULT_POOL_CASH (-amount)
  │   └─ CREDIT: USER WALLET_AVAILABLE (+amount)
  │
  ├─ Update: vault_accounts.principal -= amount
  ├─ Update: vault_accounts.available_balance -= amount
  │
  └─ Commit transaction
```

**Case B: Cash pool insufficient**
```
User → POST /api/v1/vaults/FLEX/withdrawals
  │
  ├─ Check: vault.status == ACTIVE
  ├─ Check: vault_accounts.available_balance >= amount
  ├─ Check: vault VAULT_POOL_CASH balance < amount
  │
  ├─ Create: withdrawal_request (status: PENDING)
  │
  ├─ Update: vault_accounts.available_balance -= amount
  │   (reserve the amount, but don't move funds yet)
  │
  └─ Commit transaction
  │
  └─ Return: { status: "PENDING", request_id: "..." }
```

#### Cash Availability Constraint

- **Rule:** Withdrawals can only be executed if `VAULT_POOL_CASH balance >= withdrawal amount`
- **Reason:** Vault operates as a mutual fund — withdrawals depend on pool liquidity, not individual positions
- **Enforcement:** Withdrawal endpoint checks vault cash balance before executing

#### FIFO Withdrawal Queue

- **Purpose:** Fair processing when multiple users request withdrawals exceeding vault cash
- **Implementation:** `withdrawal_request` table with `status = PENDING`, ordered by `created_at ASC`
- **Processing:** Admin endpoint `POST /api/v1/admin/vaults/{vault_code}/withdrawals/process` processes pending requests in order
- **Concurrency:** Uses `FOR UPDATE SKIP LOCKED` to handle concurrent admin processing safely

---

### 5.2 AVENIR Vault

#### Vesting Period (1 Year)

- **Rule:** All AVENIR subscriptions are locked for 365 days from deposit date
- **Enforcement:** `vault_accounts.locked_until = max(locked_until, now() + 365 days)` on deposit
- **API Response:** Withdrawal endpoint returns `403 LOCKED` if `locked_until > now()`

#### Deposit Flow

```
User → POST /api/v1/vaults/AVENIR/deposits
  │
  ├─ Check: vault.status == ACTIVE
  ├─ Check: user WALLET_AVAILABLE balance >= amount
  │
  ├─ Lock: vault row FOR UPDATE
  ├─ Lock: user WALLET_AVAILABLE account FOR UPDATE
  ├─ Lock: user WALLET_LOCKED account FOR UPDATE
  │
  ├─ Create: Operation (VAULT_DEPOSIT, COMPLETED)
  │
  ├─ Ledger:
  │   ├─ DEBIT: USER WALLET_AVAILABLE (-amount)
  │   └─ CREDIT: USER WALLET_LOCKED (+amount)
  │
  ├─ Update: vault_accounts.principal += amount
  ├─ Update: vault_accounts.available_balance += amount
  ├─ Update: vault_accounts.locked_until = max(locked_until, now() + 365 days)
  │
  └─ Commit transaction
```

**Key Difference from FLEX:**
- Funds stay in `USER WALLET (WALLET_LOCKED)`, not moved to `VAULT_POOL_CASH` yet
- Funds will move to vault pool after vesting matures (future enhancement)

#### No Withdrawal Before Vesting Maturity

- **Enforcement:** Withdrawal endpoint checks `vault_accounts.locked_until > now()`
- **Response:** `403 LOCKED` error with message "AVENIR vault withdrawals are locked until {locked_until}"

#### Automatic Transition at Maturity

**Future Enhancement (not yet implemented):**
```
When: vault_accounts.locked_until <= now()
  │
  ├─ Create: Operation (VAULT_VESTING_MATURE, COMPLETED)
  │
  ├─ Ledger:
  │   ├─ DEBIT: USER WALLET_LOCKED (-vested_amount)
  │   └─ CREDIT: VAULT VAULT_POOL_CASH (+vested_amount)
  │     OR
  │   └─ CREDIT: USER WALLET_AVAILABLE (+vested_amount)
  │     (Decision: move to vault pool or return to user available?)
  │
  ├─ Update: vault_accounts.locked_until = NULL
  │
  └─ Commit transaction
```

**Current Behavior:**
- Funds remain in `USER WALLET (WALLET_LOCKED)` after maturity
- User can request withdrawal (subject to vault cash pool availability)
- System should check `locked_until` before allowing withdrawal

#### After Maturity: Behaves Like FLEX Vault

- Once `locked_until <= now()`, AVENIR withdrawals follow the same FIFO queue logic as FLEX
- Withdrawal moves funds from `VAULT_POOL_CASH` to `USER WALLET (WALLET_AVAILABLE)`

---

## 6. INTEREST & YIELD FLOW (FUTURE-PROOF)

### 6.1 Where Daily Yield is Generated

**External to this system:**
- Yield is generated by external investment strategies (managed by operations team)
- Yield calculation is opaque to the wallet/ledger system
- Operations team receives yield reports/confirmations from external sources

### 6.2 Where Yield is Credited

**For Vaults:**
- Yield is credited to `VAULT_POOL_CASH` (increases vault liquidity)
- Operation type: `VAULT_YIELD_DISTRIBUTION` (future)
- Ledger: `CREDIT VAULT_POOL_CASH (+yield_amount)`, counterparty `INTERNAL_OMNIBUS` or `EXTERNAL_YIELD_SOURCE`

**For Offers:**
- Yield is credited to `OFFER_POOL_AVAILABLE` (increases offer capital)
- Operation type: `OFFER_YIELD_DISTRIBUTION` (future)
- Ledger: `CREDIT OFFER_POOL_AVAILABLE (+yield_amount)`, counterparty `INTERNAL_OMNIBUS` or `EXTERNAL_YIELD_SOURCE`

### 6.3 How Yield Increases Liquidity

**Vault yield:**
- `VAULT_POOL_CASH` balance increases → more withdrawal capacity
- All vault subscribers benefit indirectly (pool value increases)
- Future: Yield distributed proportionally to subscribers (credits to user wallets)

**Offer yield:**
- `OFFER_POOL_AVAILABLE` balance increases → offer has more capital
- Future: Yield distributed proportionally to investors (credits to `USER WALLET (WALLET_LOCKED)` or `WALLET_AVAILABLE`)

### 6.4 How Users Indirectly Benefit

**Current (not yet implemented):**
- Users see increased vault/offer value through increased pool balances
- Admin visibility shows yield accumulation in system wallets

**Future:**
- Yield distributed to users proportionally:
  - Vault: based on `vault_accounts.principal` / `total_aum` ratio
  - Offer: based on `investment.allocated_amount` / `total_offer_capital` ratio
- Distribution credits user wallets: `SYSTEM_WALLET` → `USER WALLET (WALLET_AVAILABLE)`

---

## 7. INVARIANTS & NON-NEGOTIABLE RULES

### 7.1 AVAILABLE is the Only Withdrawable State

**Rule:** Users can only withdraw funds from `WALLET_AVAILABLE`.

**Enforcement:**
- Withdrawal endpoints check `WALLET_AVAILABLE` balance before allowing withdrawal
- `WALLET_LOCKED` and `WALLET_BLOCKED` are non-withdrawable by design

**Exception:** Admin/compliance actions can move funds from BLOCKED (release or reject), but these are not "withdrawals" — they are compliance operations.

---

### 7.2 BLOCKED is Compliance-Only

**Rule:** Funds in `WALLET_BLOCKED` can only be moved by compliance/admin actions.

**Enforcement:**
- User-facing APIs cannot move funds from `WALLET_BLOCKED`
- Only admin endpoints (`POST /api/v1/admin/compliance/release-funds`, `POST /api/v1/admin/compliance/reject-deposit`) can modify `WALLET_BLOCKED`

**Typical flow:**
1. Deposit webhook → funds go to `WALLET_BLOCKED`
2. Compliance review → admin releases or rejects
3. Release → `WALLET_BLOCKED` → `WALLET_AVAILABLE`
4. Reject → `WALLET_BLOCKED` → `INTERNAL_OMNIBUS` (reversal)

---

### 7.3 LOCKED is Investment/Vesting-Only

**Rule:** Funds in `WALLET_LOCKED` represent commitments and cannot be withdrawn until maturity.

**Enforcement:**
- Lock expiration based on `locked_until` timestamp or product completion
- Automatic maturation (future) or manual admin release (exceptional cases)

**Typical flows:**
- Offer investment: `WALLET_AVAILABLE` → `WALLET_LOCKED` (until offer completes)
- AVENIR vesting: `WALLET_AVAILABLE` → `WALLET_LOCKED` (until 365 days pass)

---

### 7.4 Double-Entry Must Always Balance

**Rule:** Every operation must create ledger entries that sum to zero.

**Enforcement:**
- `validate_double_entry_invariant(db, operation_id)` called before commit
- Function computes: `SUM(ledger_entries.amount) WHERE operation_id = <op_id>` must equal 0
- If invariant violated: transaction rolls back, operation fails

**Example:**
```
Operation: DEPOSIT_AED
  LedgerEntry 1: CREDIT WALLET_BLOCKED +1000.00
  LedgerEntry 2: DEBIT INTERNAL_OMNIBUS -1000.00
  Sum: +1000.00 + (-1000.00) = 0 ✅
```

---

### 7.5 System Wallets Must Reflect User Locked Totals

**Rule:** The sum of all users' `WALLET_LOCKED` balances for a specific offer should equal (or be related to) the offer's system wallet balance.

**Enforcement:**
- Audit queries can verify: `SUM(user WALLET_LOCKED WHERE reason=OFFER_INVEST AND offer_id=X)` should correlate with `OFFER_POOL_AVAILABLE`
- Currently: Investment locks user funds but doesn't move to offer wallet (future enhancement will enforce this)

**For Vaults:**
- `SUM(vault_accounts.principal)` should correlate with `VAULT_POOL_CASH` balance
- Enforcement: Vault deposit/withdrawal operations update both user positions and vault pool balances atomically

---

## 8. COMMON CONFUSIONS TO AVOID

### 8.1 Why AED Wallet Must NEVER Have LOCKED Balance

**Confusion:** "Why does the wallet matrix show `locked = 0.00` for AED (USER) when I have investments?"

**Answer:** Locked funds are represented by user positions in Offers/Vaults, not in the AED wallet itself. The AED wallet's `WALLET_LOCKED` bucket exists for AVENIR vesting (which locks funds in the user wallet), but the wallet matrix endpoint enforces that the AED row always shows `locked = 0.00` because:
- Offer investments: Funds are locked in the user's wallet, but the UI shows them as "OFFER <name>" rows, not in the AED row
- Vault AVENIR: Funds are locked in the user's wallet (`WALLET_LOCKED`), but the UI shows them as "VAULT AVENIR" rows with `locked > 0`, not in the AED row

**Rule:** The AED row in the wallet matrix is a "liquid wallet" view — it should only show AVAILABLE and BLOCKED balances. All locked/vested amounts are shown in instrument-specific rows (Offers, Vaults).

---

### 8.2 Why Deposits Never Go Directly to AVAILABLE

**Confusion:** "Why does my deposit go to BLOCKED first? Can't it go directly to AVAILABLE?"

**Answer:** Compliance and regulatory requirements mandate that all deposits be reviewed before funds become available for withdrawal. This prevents money laundering and ensures KYC compliance.

**Flow:**
1. Deposit webhook → `WALLET_BLOCKED` (pending compliance)
2. Compliance officer reviews → approves
3. Compliance release → `WALLET_BLOCKED` → `WALLET_AVAILABLE`

**Why not direct to AVAILABLE:**
- Regulatory requirement: All deposits must be reviewed
- Fraud prevention: BLOCKED state prevents immediate withdrawal of suspicious deposits
- Audit trail: Compliance review is recorded in audit logs

---

### 8.3 Why Vault Balances are Not Per-User

**Confusion:** "Why can't I see my exact vault balance? Why is it a 'position' instead of a wallet balance?"

**Answer:** Vaults operate as mutual funds — all users' subscriptions are pooled into a single cash pool. Users own "shares" (tracked in `vault_accounts.principal`), but the actual cash is managed at the vault level.

**Why mutualized:**
- Liquidity management: Vault can manage cash efficiently across all subscribers
- Withdrawal fairness: FIFO queue ensures fair processing when cash is limited
- Future yield distribution: Yield is generated at the pool level and distributed proportionally

**User sees:**
- `vault_accounts.principal` — their subscription amount (shares)
- `vault_accounts.available_balance` — their withdrawable amount (may be less than principal if pending withdrawals exist)
- `vault_snapshot.cash_balance` — vault's total liquidity (pool-level, not per-user)

---

### 8.4 Why System Wallets Exist Even If Users Don't See Them

**Confusion:** "Why do we have system wallets if users can't see them? Why not just track everything in user wallets?"

**Answer:** System wallets enable product-level operations, admin visibility, and future features that require separating user money from product-managed money.

**Benefits:**
1. **Product isolation:** Each offer/vault manages its own liquidity independently
2. **Admin visibility:** Operations team can monitor product-level balances without aggregating user wallets
3. **Future features:** Yield distribution, cross-product operations, interest calculations require system wallets
4. **Audit clarity:** System wallets provide clear separation between user funds and product-managed funds

**User doesn't need to see system wallets:**
- User sees their own positions: `vault_accounts.principal`, `investment.allocated_amount`
- User doesn't need to see pool-level balances (that's operational/administrative data)

---

## 9. MAPPING TO CURRENT CODE

### 9.1 fund_services.py

**Key Functions:**
- `record_deposit_blocked()` — ZAND deposit webhook handler
  - Creates `Operation (DEPOSIT_AED, COMPLETED)`
  - Ledger: `CREDIT WALLET_BLOCKED`, `DEBIT INTERNAL_OMNIBUS`
  - Reference: Lines 30-160

- `release_compliance_funds()` — Compliance release handler
  - Creates `Operation (RELEASE_FUNDS, COMPLETED)`
  - Ledger: `DEBIT WALLET_BLOCKED`, `CREDIT WALLET_AVAILABLE`
  - Reference: Lines 160-270

- `lock_funds_for_investment()` — Offer investment handler
  - Creates `Operation (INVEST_EXCLUSIVE, COMPLETED)`
  - Ledger: `DEBIT WALLET_AVAILABLE`, `CREDIT WALLET_LOCKED`
  - Reference: Lines 273-383

- `reject_deposit()` — Compliance rejection handler
  - Creates `Operation (REVERSAL_DEPOSIT, COMPLETED)`
  - Ledger: `DEBIT WALLET_BLOCKED`, `CREDIT INTERNAL_OMNIBUS`
  - Reference: Lines 385-520

---

### 9.2 ZAND Webhook Deposit Logic

**File:** `backend/app/api/webhooks/zand.py`

**Flow:**
1. Webhook receives deposit notification
2. Creates `Transaction (DEPOSIT, INITIATED)`
3. Calls `record_deposit_blocked()` to record funds in `WALLET_BLOCKED`
4. Returns transaction_id for tracking

**Reference:** Lines 26-90

---

### 9.3 LedgerEntry / Account / Operation Models

**File:** `backend/app/core/ledger/models.py`

**Models:**
- `Operation` — Business-level operation (groups ledger entries)
  - Fields: `type` (OperationType), `status` (OperationStatus), `idempotency_key`
  - Immutable after COMPLETED
- `LedgerEntry` — Double-entry ledger line
  - Fields: `account_id`, `amount`, `entry_type` (CREDIT/DEBIT), `operation_id`
  - Immutable (write-once)

**File:** `backend/app/core/accounts/models.py`

**Models:**
- `Account` — Wallet compartment or system account
  - Fields: `user_id`, `account_type` (AccountType), `currency`, `vault_id`, `offer_id`
  - Immutable (balance computed from ledger entries)

---

### 9.4 Vault Service

**File:** `backend/app/services/vault_service.py`

**Key Functions:**
- `deposit_to_vault()` — Vault subscription handler
  - Creates `Operation (VAULT_DEPOSIT, COMPLETED)`
  - Ledger: `DEBIT WALLET_AVAILABLE`, `CREDIT VAULT_POOL_CASH`
  - Updates `vault_accounts.principal`
  - Reference: Lines 93-220

- `request_withdrawal()` — Vault withdrawal request handler
  - If cash sufficient: Creates `Operation (VAULT_WITHDRAW_EXECUTED, COMPLETED)`
  - If cash insufficient: Creates `withdrawal_request (status: PENDING)`
  - Reference: Lines 222-350

- `process_pending_withdrawals()` — Admin FIFO processing handler
  - Locks vault `FOR UPDATE`
  - Selects pending requests FIFO with `FOR UPDATE SKIP LOCKED`
  - Executes withdrawals when cash sufficient
  - Reference: Lines 352-450

---

### 9.5 System Wallet Helpers

**File:** `backend/app/services/system_wallet_helpers.py`

**Key Functions:**
- `ensure_offer_system_wallet()` — Creates/retrieves offer system wallet (3 buckets)
- `ensure_vault_system_wallet()` — Creates/retrieves vault system wallet (3 buckets)
- `get_offer_system_wallet_balances()` — Returns offer wallet balances
- `get_vault_system_wallet_balances()` — Returns vault wallet balances

---

## 10. FINAL SUMMARY (ONE PAGE MENTAL MODEL)

**Vancelian Wallet System — Mental Model:**

1. **Every user has a Wallet AED** with 3 buckets: AVAILABLE (liquid), LOCKED (invested/vested), BLOCKED (compliance hold).

2. **Every Offer has a System Wallet** (owned by SYSTEM) with 3 buckets tracking the offer's capital pool.

3. **Every Vault has a System Wallet** (owned by SYSTEM) with 3 buckets tracking the vault's cash pool.

4. **AVAILABLE = withdrawable** (user or system can move funds). **LOCKED = committed** (cannot withdraw until maturity). **BLOCKED = frozen** (compliance/admin only).

5. **Deposits always go to BLOCKED first** (compliance review required), then released to AVAILABLE.

6. **Offer investments** lock funds in user wallet (`WALLET_LOCKED`) and credit offer system wallet (`OFFER_POOL_AVAILABLE`).

7. **Vault FLEX subscriptions** move funds from user wallet (`WALLET_AVAILABLE`) to vault system wallet (`VAULT_POOL_CASH`).

8. **Vault AVENIR subscriptions** lock funds in user wallet (`WALLET_LOCKED`) for 365 days (vesting).

9. **All money movements use double-entry ledger** (DEBIT + CREDIT must sum to zero). Ledger entries are immutable (write-once).

10. **Account balances are computed from ledger entries** (not stored fields). `balance = SUM(ledger_entries.amount) WHERE account_id = X`.

11. **Vault withdrawals depend on vault cash pool** (mutual fund model), not individual user balances. FIFO queue when cash insufficient.

12. **System wallets enable product-level operations** (yield distribution, liquidity management) and admin visibility.

13. **The wallet matrix endpoint** shows user exposure: AED row (available/blocked only), Offer rows (locked = invested amount), Vault rows (available/locked based on vault type).

14. **Never break invariants:** AVAILABLE only withdrawable, BLOCKED compliance-only, LOCKED investment-only, double-entry must balance.

---

**End of Document**


