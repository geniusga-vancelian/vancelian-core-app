# 📘 VANCELIAN_SYSTEM.md
## Version 1.0 – Document fondateur de la plateforme Vancelian

---

## 1. 🎯 Vision & Positionnement

**Vancelian** est une plateforme d’investissement régulée spécialisée dans les crypto-actifs et les actifs réels tokenisés (RWA), conçue pour une clientèle patrimoniale.

### Objectifs stratégiques
- Offrir une expérience utilisateur simple, comparable à une néobanque privée
- Permettre l’investissement dans :
  - des coffres sécurisés à rendement faible à modéré
  - des offres exclusives (club deals, RWA, projets réels)
  - des portefeuilles crypto automatisés
- Garantir un haut niveau de conformité réglementaire (VARA, MiCA)
- Construire une infrastructure technique robuste, auditable, scalable et vendable

### Cible
- Clients disposant de **10 000 € à 250 000 €+** de capacité d’investissement
- Priorité à la **qualité des AUM**, non au volume d’utilisateurs

---

## 2. 🧱 Principes structurants NON négociables

1. **PostgreSQL est la source de vérité**
2. **Ledger financier immuable**
3. **Aucune suppression physique de données**
4. **Chaque mouvement financier est traçable, justifiable et rejouable**
5. **Séparation stricte entre logique métier et exécution technique**
6. **Tout événement critique est auditable**
7. **Cursor est un exécutant : il n’architecture rien**

---

## 3. 🏗️ Architecture globale

### 3.1 Choix structurants

| Élément | Choix |
|------|------|
| Backend | FastAPI (monolithe modulaire) |
| Base de données | PostgreSQL |
| Cache / Async | Redis |
| Workers | Python (RQ ou équivalent) |
| Frontend | Web (REST) + Mobile (FlutterFlow) |
| Admin | Web interne (maison) |
| Auth | OAuth2 / OpenID (Zitadel recommandé) |
| Infra | Docker (local + production) |

> Aucun microservice au départ.  
> Aucun bus d’événements type Kafka à ce stade.

---

### 3.2 Organisation du backend (monolithe sain)

```text
app/
├── core/                # Domaines métier purs
│   ├── ledger/
│   ├── accounts/
│   ├── investments/
│   ├── users/
│   ├── kyc/
│   └── compliance/
│
├── api/                 # Routes FastAPI
│   ├── public/
│   ├── auth/
│   ├── user/
│   ├── admin/
│   └── webhooks/
│
├── services/            # Logique applicative
├── workers/             # Jobs asynchrones
├── infrastructure/      # DB, Redis, email, providers
├── schemas/             # Pydantic
└── main.py
```

## 4. 💰 Modèle financier & Ledger (CŒUR DU SYSTÈME)

### 4.1 Concepts fondamentaux

#### Account
Représente une poche de valeur (ex. Wallet AED).

- Appartient à un utilisateur
- Associé à une devise
- N’est **jamais modifié directement**

---

#### LedgerEntry (IMMUTABLE)

Chaque mouvement financier crée une ligne de ledger.

| Champ | Description |
|---|---|
| id | UUID |
| account_id | Compte impacté |
| amount | Positif ou négatif |
| currency | Devise (ex. AED) |
| entry_type | CREDIT / DEBIT |
| operation_id | Lien métier |
| created_at | Timestamp |

> Le solde d’un compte = somme de ses ledger entries.

---

#### Operation (métier)

Représente le sens business d’une action.

Exemples :
- DEPOSIT_AED
- INVEST_EXCLUSIVE_OFFER
- RELEASE_FUNDS
- KYC_VALIDATION
- ADJUSTMENT (exceptionnel, audit renforcé)

Une Operation :
- regroupe plusieurs LedgerEntry
- porte le sens métier
- est toujours auditée

---

#### Transaction (technique)

- Notion technique (API, webhook, provider externe)
- Ne porte jamais la vérité financière

### 4.2 Règles comptables & invariants (audit-proof)

#### 4.2.1 Double-entry obligatoire
Toute **Operation** qui touche au ledger doit créer des **LedgerEntry** respectant :

- La somme des **CREDIT** = la somme des **DEBIT** (à la devise près)
- Aucune exception, même pour les frais
- Une Operation peut contenir plusieurs lignes (ex : wallet client → compte interne bloqué)

**Invariant :**
> Pour une Operation donnée, total_credits == total_debits

---

#### 4.2.2 Idempotence (anti-doublon)
Tout endpoint “qui crée” (deposit confirm, invest, adjustment) doit accepter une `idempotency_key` :

- Unique par type d’operation + user
- Stockée sur l’Operation
- Si la même `idempotency_key` revient : retourner le résultat existant (pas de double écriture)

---

#### 4.2.3 Immutabilité stricte du ledger
Les entrées `LedgerEntry` sont **write-once** :

- Pas d’UPDATE
- Pas de DELETE
- Toute correction se fait via une nouvelle Operation de type `ADJUSTMENT` ou `REVERSAL`

---

#### 4.2.4 Corrections / compensations (sans casser l’historique)
En cas d’erreur :

- On ne modifie jamais le passé
- On crée une Operation de correction :
  - `REVERSAL` (annulation exacte)
  - `ADJUSTMENT` (correction partielle avec justification)

Chaque correction doit contenir :
- `reason` obligatoire (texte)
- lien vers l’operation d’origine (`reversal_of_operation_id` ou `adjusts_operation_id`)

---

#### 4.2.5 Statuts d’Operation
Les statuts sont explicites :

- `PENDING` : initiée, pas finalisée
- `COMPLETED` : ledger écrit (final)
- `FAILED` : aucune écriture finale (ou compensation réalisée)
- `CANCELLED` : annulée avant écriture

Règle :
> Une Operation `COMPLETED` ne change plus jamais de statut.

---

#### 4.2.6 Concurrence & intégrité
Les écritures ledger doivent être réalisées :

- Dans une transaction DB
- Avec verrouillage logique si nécessaire (ex : SELECT … FOR UPDATE sur Operation)
- De manière atomique (operation + ledger entries + audit)

---

#### 4.2.7 Audit obligatoire sur actions sensibles
Toute action admin ou compliance qui déclenche une Operation doit écrire un `AuditLog` avec :

- actor_id / actor_role
- action
- entity_type / entity_id
- before / after (si applicable)
- reason obligatoire pour les actions sensibles
- timestamp

---

#### 4.2.8 Lecture de solde
Le solde n’est pas une colonne “source de vérité”.

- La vérité = SUM(ledger_entries.amount) par account
- On peut maintenir un cache (optionnel) **uniquement** comme optimisation

---

#### 4.2.9 Devise & précision
- `amount` stocké en `NUMERIC(24, 8)` (à confirmer par devise)
- Une Operation ne mélange pas plusieurs devises pour son invariant double-entry

---

## 5. 🧩 Flux métiers clés

### 5.1 Dépôt AED (simulation ZAND Bank)

1. L’utilisateur initie un dépôt
2. Création d’une `Operation = DEPOSIT_PENDING`
3. Réception d’un webhook (simulé ou réel)
4. Validation du dépôt
5. Création d’un `LedgerEntry +AED`
6. Passage de l’Operation à `COMPLETED`
7. Workers :
   - notification
   - email
   - audit trail

---

### 5.2 Investissement dans une Offre Exclusive

1. Vérification KYC + éligibilité
2. Création `Operation = INVEST_EXCLUSIVE`
3. Ledger :
   - `-AED` depuis wallet utilisateur
   - `+AED` vers compte interne bloqué
4. Création d’une `InvestmentPosition`
5. Fonds considérés comme illiquides
6. Reporting et audit

---

## 6. 🛂 KYC & Compliance (by design)

### Principes
- Parcours KYC modulaire selon la juridiction
- Scoring de risque dynamique
- Audit trail complet
- Décision humaine possible

### Entités clés
- KYCCase
- KYCCheck
- RiskScore
- ComplianceDecision
- AuditLog (transversal)

---

## 7. 🔐 Sécurité & gestion des droits

### Authentification
- OAuth2 / OpenID Connect
- Tokens courts + refresh tokens sécurisés

### RBAC
- USER
- ADMIN
- COMPLIANCE
- OPS
- READ_ONLY

Chaque endpoint est explicitement protégé.

---

## 8. ⚙️ Asynchrone & Workers

Redis est utilisé pour :
- emails
- notifications
- vérifications KYC
- webhooks
- reporting

> Aucune action critique ne dépend d’un worker pour être valide.

---

## 9. 🧰 Admin Web interne (Backoffice maison)

Le backoffice Vancelian est une application web interne dédiée aux équipes.

### Objectifs
- Gestion utilisateurs, KYC, compliance, opérations
- Supervision sans manipulation directe du ledger
- Traçabilité complète

### Sécurité
- Auth OpenID / OAuth2
- RBAC strict
- AuditLog obligatoire pour chaque action
- Justification textuelle requise pour toute action sensible
- Possibilité de double validation (4-eyes)

### Architecture
- Frontend : React / Next.js
- Backend : FastAPI `/admin/*`
- Base : PostgreSQL (même source de vérité)

### Modules minimum
- Dashboard global
- Utilisateurs
- KYC & Compliance
- Opérations
- Investissements
- Audit Trail
- Paramètres & rôles

> L’Admin Web ne modifie jamais directement le ledger.

---

## 10. 📊 Qualité, audit & discipline

- Naming clair et explicite
- Logs structurés
- Migrations SQL versionnées
- Tests unitaires sur le core
- Documentation maintenue
- Zéro logique métier dans le frontend

---

## 11. 🚫 Ce que le système NE fait PAS

- Pas de trading haute fréquence
- Pas de matching engine
- Pas de cartes bancaires à court terme
- Pas de suppression de données
- Pas de dépendance critique à un fournisseur unique

---

## 12. 🧠 Règle finale pour Cursor

> Si ce n’est pas explicitement défini dans ce document, Cursor ne l’invente pas.  
> Toute ambiguïté doit être remontée au CEO / Architecte.

---

## 13. 🔁 Gouvernance du document

- Ce document est la **référence unique**
- Toute modification doit être :
  - volontaire
  - versionnée
  - validée par le CEO
