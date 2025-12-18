# Sécurité & Authentification

## RBAC (Role-Based Access Control)

Le système utilise un modèle RBAC avec les rôles suivants:

- `USER`: Utilisateur standard
- `ADMIN`: Administrateur (accès complet)
- `COMPLIANCE`: Équipe compliance (gestion KYC, audit)
- `OPS`: Opérations (gestion opérationnelle)
- `READ_ONLY`: Lecture seule (consultation uniquement)

### Utilisation dans les endpoints

```python
from app.security.rbac import require_admin_role, require_compliance_role

@router.get("/admin/users")
async def list_users(_: None = Depends(require_admin_role)):
    # Endpoint accessible uniquement aux admins
    pass
```

**Status actuel**: Stub implémenté. Les dépendances RBAC sont présentes mais retournent toujours 401 (non implémenté).

## Zitadel OIDC Integration (Placeholder)

Le système est conçu pour utiliser Zitadel (OpenID Connect) pour l'authentification.

### Structure prévue

Le module `app/security/zitadel.py` contient un placeholder pour:

1. **Configuration OIDC**
   - Endpoint de découverte OIDC
   - Client ID et Client Secret
   - Scopes requis

2. **Validation de token**
   - Validation JWT
   - Vérification de signature
   - Vérification d'expiration

3. **Extraction des informations utilisateur**
   - User ID
   - Email
   - Rôles (claims)

### TODO: Implémentation

```python
# app/security/zitadel.py

def validate_token(token: str) -> UserInfo:
    """
    Validate JWT token from Zitadel
    Returns UserInfo with user_id, email, roles
    """
    pass

def get_user_roles(token: str) -> List[Role]:
    """
    Extract roles from JWT token claims
    """
    pass
```

### Intégration avec RBAC

Une fois Zitadel implémenté, les dépendances RBAC (`require_admin_role`, etc.) devront:

1. Extraire le token JWT du header `Authorization: Bearer <token>`
2. Valider le token via `validate_token()`
3. Extraire les rôles via `get_user_roles()`
4. Vérifier que le rôle de l'utilisateur est dans `allowed_roles`
5. Ajouter l'utilisateur au `request.state` pour usage dans les endpoints

## Audit Trail

Toutes les actions critiques sont enregistrées dans `AuditLog` avec:

- `actor_user_id`: ID de l'utilisateur qui a effectué l'action
- `actor_role`: Rôle de l'acteur
- `action`: Type d'action (ex: "user.created", "operation.approved")
- `entity_type`, `entity_id`: Entité concernée
- `before`, `after`: État avant/après (JSONB)
- `reason`: Justification textuelle (obligatoire pour actions sensibles)
- `ip`: Adresse IP de la requête
- `created_at`: Timestamp

## Sécurité du Ledger

Le ledger financier est protégé par:

1. **Immutabilité applicative**: Les modèles ne permettent pas UPDATE/DELETE sur LedgerEntry
2. **Audit obligatoire**: Toute modification via Operation doit créer un AuditLog
3. **Double-entry**: Invariants comptables vérifiés au niveau service
4. **Idempotence**: Protection contre les doublons via `idempotency_key`

## Recommandations de production

1. **SECRET_KEY**: Utiliser une clé forte et unique (générée avec `openssl rand -hex 32`)
2. **CORS**: Limiter `ALLOWED_ORIGINS` aux domaines autorisés uniquement
3. **HTTPS**: Toujours utiliser HTTPS en production
4. **Rate limiting**: Implémenter un rate limiting sur les endpoints sensibles
5. **Logs**: Ne pas logger les tokens JWT ou secrets dans les logs
6. **Database**: Utiliser des credentials forts et rotation régulière
7. **Redis**: Sécuriser Redis avec authentification et TLS si accessible depuis l'extérieur

