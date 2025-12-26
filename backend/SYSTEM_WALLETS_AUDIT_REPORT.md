# SYSTEM WALLETS — AUDIT REPORT

**Date**: 2025-01-26  
**Objectif**: Comprendre l'architecture existante des comptes/wallets avant d'implémenter les System Wallets pour Offers et Vaults.

---

## PHASE 1 — AUDIT (READ ONLY)

### 1. Tables/Entités existantes pour modéliser les comptes

#### Table: `accounts`

**Fichier**: `backend/app/core/accounts/models.py`

**Structure actuelle**:
```python
class Account(BaseModel):
    __tablename__ = "accounts"
    
    user_id = Column(UUID, ForeignKey("users.id"), nullable=True, index=True)
    currency = Column(String(3), nullable=False, index=True)  # ISO 4217 (AED, USD)
    account_type = Column(SQLEnum(AccountType), nullable=False, index=True)
    vault_id = Column(UUID, ForeignKey("vaults.id"), nullable=True, index=True)  # Pour VAULT_POOL_CASH
    
    # Relationships
    user = relationship("User", back_populates="accounts")
    vault = relationship("Vault", foreign_keys=[vault_id], lazy="select")
    ledger_entries = relationship("LedgerEntry", back_populates="account")
    
    # Index composite pour vault pool accounts
    __table_args__ = (
        Index('ix_accounts_type_vault_currency', 'account_type', 'vault_id', 'currency'),
    )
```

**Caractéristiques**:
- ✅ Table existe déjà
- ✅ Supporte `user_id=None` pour comptes système
- ✅ Supporte `vault_id` pour scoping vault (déjà utilisé pour VAULT_POOL_CASH)
- ❌ Pas de colonnes `owner_type`, `scope_type`, `scope_id` (pas nécessaires si on réutilise le pattern existant)
- ✅ Balance calculée dynamiquement depuis `ledger_entries` (SUM des amounts)

**Immutable**: Les comptes sont immutables (pas de `updated_at` utilisé). La balance est toujours calculée depuis le ledger.

---

### 2. AccountType Enum — Types de comptes existants

**Fichier**: `backend/app/core/accounts/models.py`

```python
class AccountType(str, enum.Enum):
    WALLET_AVAILABLE = "WALLET_AVAILABLE"      # User's available balance
    WALLET_BLOCKED = "WALLET_BLOCKED"          # User's blocked balance (compliance)
    WALLET_LOCKED = "WALLET_LOCKED"            # User's locked balance (investment)
    INTERNAL_OMNIBUS = "INTERNAL_OMNIBUS"      # System-wide omnibus account (global, pas scoped)
    VAULT_POOL_CASH = "VAULT_POOL_CASH"        # Vault pool cash account (system, scoped par vault_id)
```

**Patterns observés**:
- **User wallets**: `user_id != None`, `account_type` ∈ {WALLET_AVAILABLE, WALLET_BLOCKED, WALLET_LOCKED}
- **System accounts**: `user_id = None`
  - `INTERNAL_OMNIBUS`: global (pas de scope)
  - `VAULT_POOL_CASH`: scoped par `vault_id`

---

### 3. Comment "pool cash" est représenté aujourd'hui

#### 3.1 Vault Pool Cash

**Pattern existant**: `VAULT_POOL_CASH` account type

**Helper**: `get_or_create_vault_pool_cash_account()` dans `backend/app/services/vault_helpers.py`

```python
def get_or_create_vault_pool_cash_account(db: Session, vault_id: UUID, currency: str) -> UUID:
    """
    Get or create vault pool cash account (VAULT_POOL_CASH account type).
    
    Vault pool accounts are system accounts (user_id=None) with vault_id set.
    """
    account = db.query(Account).filter(
        Account.account_type == AccountType.VAULT_POOL_CASH,
        Account.vault_id == vault_id,
        Account.currency == currency,
        Account.user_id.is_(None),  # System account
    ).first()
    
    if account:
        return account.id
    
    # Create new vault pool cash account
    account = Account(
        user_id=None,  # System account
        currency=currency,
        account_type=AccountType.VAULT_POOL_CASH,
        vault_id=vault_id,
    )
    db.add(account)
    db.flush()
    return account.id
```

**Caractéristiques**:
- ✅ Compte système (`user_id=None`)
- ✅ Scoped par `vault_id`
- ✅ Un seul compte par vault/currency (pas de buckets AVAILABLE/LOCKED/BLOCKED)
- ✅ Utilisé uniquement pour la poche cash du vault (équivalent à "AVAILABLE" dans le modèle canonique)

#### 3.2 INTERNAL_OMNIBUS

**Pattern existant**: Compte système global (pas scoped)

**Usage**: 
- Contrepartie pour les dépôts fiat (DEBIT INTERNAL_OMNIBUS, CREDIT WALLET_BLOCKED)
- Contrepartie pour les rejets de dépôt (DEBIT WALLET_BLOCKED, CREDIT INTERNAL_OMNIBUS)

**Création**: Dans `record_deposit_blocked()` et `reject_deposit()` dans `backend/app/services/fund_services.py`

```python
omnibus_account = db.query(Account).filter(
    Account.account_type == AccountType.INTERNAL_OMNIBUS,
    Account.currency == currency,
).first()

if not omnibus_account:
    omnibus_account = Account(
        id=uuid4(),
        user_id=None,  # System account
        currency=currency,
        account_type=AccountType.INTERNAL_OMNIBUS,
    )
    db.add(omnibus_account)
    db.flush()
```

**Caractéristiques**:
- ✅ Compte système global (`user_id=None`, pas de `vault_id`, pas de `offer_id`)
- ✅ Un seul compte par currency (pas de scope)

---

### 4. Helpers existants

#### 4.1 User Wallet Helpers

**Fichier**: `backend/app/services/wallet_helpers.py`

**`ensure_wallet_accounts(db, user_id, currency) -> Dict[str, UUID]`**:
- Crée les 3 buckets pour un utilisateur: WALLET_AVAILABLE, WALLET_BLOCKED, WALLET_LOCKED
- Retourne un dict `{account_type: account_id}`

**`get_account_balance(db, account_id) -> Decimal`**:
- Calcule la balance depuis le ledger: `SUM(ledger_entries.amount) WHERE account_id = account_id`

**`get_wallet_balances(db, user_id, currency) -> Dict[str, Decimal]`**:
- Retourne les balances des 3 buckets + total_balance

#### 4.2 Vault Helpers

**Fichier**: `backend/app/services/vault_helpers.py`

**`get_or_create_vault_pool_cash_account(db, vault_id, currency) -> UUID`**:
- Crée un compte VAULT_POOL_CASH pour un vault
- Pattern: `user_id=None`, `vault_id=vault_id`, `account_type=VAULT_POOL_CASH`

**`get_vault_cash_balance(db, vault_id, currency) -> Decimal`**:
- Calcule la balance du vault pool cash account depuis le ledger

---

### 5. Offers — État actuel

**Observation**: Les Offers n'ont **PAS** de compte système dédié.

**Invest Flow** (existant):
- DEBIT: `WALLET_AVAILABLE` (user)
- CREDIT: `WALLET_LOCKED` (user)
- OperationType: `INVEST_EXCLUSIVE`
- Aucun mouvement vers un compte système d'offer

**Fichiers**:
- `backend/app/services/offers/service_v1_1.py` (invest_in_offer_v1_1)
- `backend/app/services/fund_services.py` (lock_funds_for_investment)

**Conclusion**: Les offers sont purement user-level. Les fonds restent dans le wallet de l'utilisateur (LOCKED), pas dans un pool système.

---

### 6. Gaps vs Design Requis

#### 6.1 Design Requis (selon specs)

**System Wallet par Offer et par Vault**:
- `owner_type = SYSTEM`
- `owner_id = NULL`
- `scope_type = OFFER ou VAULT`
- `scope_id = offer_id ou vault_id`
- `currency = 'AED'`
- Buckets: AVAILABLE / LOCKED / BLOCKED (même si certains non utilisés)

#### 6.2 Gaps identifiés

| Exigence | État Actuel | Gap |
|----------|-------------|-----|
| **System wallet par Vault** | ✅ Existe (VAULT_POOL_CASH) | ⚠️ Pas de buckets multiples (un seul compte, pas AVAILABLE/LOCKED/BLOCKED) |
| **System wallet par Offer** | ❌ N'existe pas | ✅ Gap: Pas de compte système pour offers |
| **Buckets multiples pour system wallets** | ❌ Pas implémenté | ✅ Gap: Pas de séparation AVAILABLE/LOCKED/BLOCKED pour system wallets |
| **owner_type / scope_type columns** | ❌ N'existent pas | ⚠️ Peut être évité en réutilisant le pattern existant (user_id=None + vault_id/offer_id) |
| **Unique constraint** | ⚠️ Partiel (index composite pour vault) | ⚠️ Besoin d'unique constraint explicite pour éviter doublons |

#### 6.3 Décision d'architecture

**Option A: Réutiliser le modèle existant (RECOMMANDÉ)**:
- Utiliser `user_id=None` pour system accounts (déjà fait)
- Utiliser `vault_id` pour scoping vault (déjà fait)
- Ajouter `offer_id` (nullable) pour scoping offer
- Créer de nouveaux AccountType pour system wallets: `OFFER_POOL_AVAILABLE`, `OFFER_POOL_LOCKED`, `OFFER_POOL_BLOCKED`, `VAULT_POOL_AVAILABLE`, `VAULT_POOL_LOCKED`, `VAULT_POOL_BLOCKED`
- **Alternative plus simple**: Garder `VAULT_POOL_CASH` mais ajouter des buckets (OFFER_POOL_AVAILABLE, etc.) seulement si nécessaire

**Option B: Refactor complet**:
- Ajouter colonnes `owner_type`, `scope_type`, `scope_id`
- Migration complexe
- Risque de breaking changes

**Recommandation**: **Option A avec extension minimale**

Pour les Vaults:
- Garder `VAULT_POOL_CASH` comme "AVAILABLE" bucket (rétrocompatibilité)
- Optionnellement, ajouter `VAULT_POOL_LOCKED` et `VAULT_POOL_BLOCKED` si nécessaire

Pour les Offers:
- Ajouter `offer_id` colonne (nullable) à la table `accounts`
- Créer `OFFER_POOL_AVAILABLE`, `OFFER_POOL_LOCKED`, `OFFER_POOL_BLOCKED` si nécessaire
- Si les offers n'ont pas besoin de buckets multiples, un seul `OFFER_POOL_AVAILABLE` suffit

---

### 7. Contraintes d'unicité existantes

**Index composite existant**:
```python
Index('ix_accounts_type_vault_currency', 'account_type', 'vault_id', 'currency')
```

**Gaps**:
- Pas d'unique constraint explicite (seulement index pour performance)
- Pas d'unique constraint pour offers (offer_id n'existe pas encore)
- Besoin d'unique constraint: `(account_type, user_id, vault_id, offer_id, currency)` pour éviter doublons

---

### 8. Migration existante

**Migration Vaults**: `2025_12_25_1700-create_vaults_tables_and_extend_enums.py`
- ✅ Ajoute `VAULT_POOL_CASH` à `AccountType` enum
- ✅ Ajoute `vault_id` colonne à `accounts` table
- ✅ Ajoute index composite `ix_accounts_type_vault_currency`

**Conclusion**: Le pattern de migration existe déjà. On peut suivre le même pattern pour offers.

---

## RÉSUMÉ — ÉTAT ACTUEL

### Ce qui existe ✅

1. **Table `accounts`** avec support système (`user_id=None`)
2. **AccountType enum** avec `VAULT_POOL_CASH` et `INTERNAL_OMNIBUS`
3. **Vault pool cash** implémenté via `VAULT_POOL_CASH` avec `vault_id`
4. **Helpers** pour user wallets et vault pool cash
5. **Pattern de migration** pour ajouter des AccountType et colonnes

### Ce qui manque ❌

1. **System wallet pour Offers** (pas de compte système dédié)
2. **Buckets multiples pour system wallets** (AVAILABLE/LOCKED/BLOCKED)
3. **Colonne `offer_id`** dans la table `accounts`
4. **AccountType pour offer pools** (OFFER_POOL_*)
5. **Unique constraints explicites** pour éviter doublons
6. **Helpers pour system wallets** (ensure_system_wallet, get_system_account)

### Design Decision Required

**Question**: Les Offers ont-elles besoin de buckets multiples (AVAILABLE/LOCKED/BLOCKED) ou un seul bucket suffit-il?

**Hypothèse**: 
- Si les offers n'ont pas besoin de gestion de pool cash (fonds restent dans user wallets), on peut ne pas implémenter de system wallet pour offers du tout.
- Si les offers ont besoin d'un pool cash, un seul bucket AVAILABLE suffira probablement.

**Pour les Vaults**:
- Garder `VAULT_POOL_CASH` comme bucket AVAILABLE (rétrocompatibilité)
- Optionnellement, ajouter LOCKED/BLOCKED si nécessaire

---

## PROCHAINES ÉTAPES

### Phase 2 — Implémentation minimale (à faire)

1. **Décider**: Offers ont-elles besoin d'un system wallet?
   - Si oui: Ajouter `offer_id` colonne + AccountType `OFFER_POOL_AVAILABLE`
   - Si non: Skip offers, focus sur Vaults

2. **Pour les Vaults** (si buckets multiples nécessaires):
   - Ajouter `VAULT_POOL_LOCKED`, `VAULT_POOL_BLOCKED` à AccountType
   - Helper: `ensure_vault_system_wallet()` crée 3 buckets
   - Migration: Compatible avec `VAULT_POOL_CASH` existant

3. **Unique constraints**:
   - Ajouter `UniqueConstraint` sur `(account_type, user_id, vault_id, offer_id, currency)`

4. **Helpers**:
   - `ensure_system_wallet(scope_type, scope_id, currency) -> Dict[str, UUID]`
   - `get_system_account(scope_type, scope_id, currency, bucket) -> UUID`

5. **Admin API**:
   - Endpoints pour voir les balances des system wallets

---

**Fichiers clés référencés**:
- `backend/app/core/accounts/models.py` (Account model, AccountType enum)
- `backend/app/services/wallet_helpers.py` (ensure_wallet_accounts)
- `backend/app/services/vault_helpers.py` (get_or_create_vault_pool_cash_account)
- `backend/app/services/fund_services.py` (INTERNAL_OMNIBUS usage)
- `backend/alembic/versions/2025_12_25_1700-create_vaults_tables_and_extend_enums.py` (migration pattern)

