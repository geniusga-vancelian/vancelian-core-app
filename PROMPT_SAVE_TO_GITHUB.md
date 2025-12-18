# PROMPT CURSOR - Sauvegarde sur GitHub

TU ES CURSOR.

## RÈGLE ABSOLUE (ANTI-ERREUR DE DOSSIER)
- Travaille UNIQUEMENT dans ce repo :
  `/Users/gael/Documents/Cursor/vancelian-core-app`
- Avant toute action, exécute `pwd`
- SI le chemin est différent → STOP et alerte.

## OBJECTIF
- Sauvegarder TOUT le travail actuel sur GitHub
- Sans perdre d'état
- Avec un commit clair, traçable et exploitable plus tard
- Sans rebase dangereux

## ÉTAPE 1 — Vérifications de sécurité
Exécuter :
- `pwd`
- `git status`
- `git branch`
- `git remote -v`

Afficher clairement :
- Branche courante
- Fichiers modifiés / nouveaux
- Fichiers non trackés

**NE RIEN MODIFIER à cette étape.**

## ÉTAPE 2 — Vérification des fichiers sensibles
Avant commit :
- Vérifier qu'aucun secret n'est commité :
  - JWT_SECRET
  - DB passwords
  - API keys
- Si présents :
  - Les exclure via .env / .gitignore
  - NE PAS les supprimer du système, seulement du commit

Lister explicitement les fichiers exclus si nécessaire.

## ÉTAPE 3 — Ajout contrôlé au staging
Ajouter uniquement ce qui est pertinent :
- backend/
- frontend-client/
- frontend-admin/
- frontend/
- scripts/
- docs/
- docker-compose.dev.yml
- alembic/
- README / docs techniques

Commandes :
- `git add backend frontend-client frontend-admin frontend scripts docs docker-compose.dev.yml alembic README*`

Afficher ensuite :
- `git status` (doit être clean sauf fichiers volontairement exclus)

## ÉTAPE 4 — Commit structuré
Créer un commit UNIQUE avec un message clair :

**Message de commit EXACT (à utiliser tel quel) :**

```
feat(dev): stabilize full stack (backend, auth, admin, front)

- Restore and stabilize backend routers (auth, wallet, admin, compliance, webhooks)
- Fix local auth (bcrypt) and JWT dev flow
- Consolidate single PostgreSQL database (vancelian_core)
- Restore and wire frontend-client and frontend-admin
- Fix admin compliance and ZAND webhook tooling
- Add dev bootstrap & smoke scripts
- Ensure stack survives reboot without reconfiguration
```

Commande :
- `git commit -m "<message ci-dessus>"`

## ÉTAPE 5 — Push sécurisé
- Vérifier la branche distante
- Push sans force

Commande :
- `git push origin HEAD`

**SI le push échoue :**
- Afficher l'erreur
- NE PAS faire de force push
- Attendre instructions

## ÉTAPE 6 — Confirmation finale
Afficher :
- Hash du commit
- Lien GitHub du commit
- Branche pushée

FIN.

