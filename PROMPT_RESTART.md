# PROMPT CURSOR - Redémarrage après reboot Mac

TU ES CURSOR.

## RÈGLE ABSOLUE (anti-erreur de dossier)
- Travaille UNIQUEMENT dans ce repo:
  `/Users/gael/Documents/Cursor/vancelian-core-app`
- Avant toute commande, affiche `pwd` et refuse d'exécuter si ce n'est pas ce chemin.

## OBJECTIF
Après redémarrage Mac, remettre TOUT en route proprement:
- postgres + redis + backend + frontends
- migrations alembic
- smoke checks (health, docs, front)
- logs utiles si quelque chose casse
Sans rien casser / sans reset DB par défaut.

## ÉTAPE 0 — Vérifier l'environnement
Exécuter:
- `cd /Users/gael/Documents/Cursor/vancelian-core-app`
- `pwd`
- `git status`
- `docker --version`
- `docker compose version`

## ÉTAPE 1 — Démarrage "safe" (ne PAS supprimer les volumes)
1) Stop/restart soft:
- `docker compose -f docker-compose.dev.yml down`
2) Rebuild + start:
- `docker compose -f docker-compose.dev.yml up -d --build`
3) Afficher l'état:
- `docker compose -f docker-compose.dev.yml ps`

## ÉTAPE 2 — Attendre la DB + backend
Attendre jusqu'à OK (avec retries):
- `curl http://localhost:8000/health`
- `curl http://localhost:8000/ready`
Si ça échoue:
- afficher les 200 dernières lignes:
  - `docker compose -f docker-compose.dev.yml logs --tail=200 backend`
  - `docker compose -f docker-compose.dev.yml logs --tail=200 postgres`
  - `docker compose -f docker-compose.dev.yml logs --tail=200 redis`

## ÉTAPE 3 — Migrations (IMPORTANT)
Appliquer les migrations dans le conteneur backend:
- `docker compose -f docker-compose.dev.yml exec backend alembic upgrade head`
Puis re-tester:
- `curl http://localhost:8000/health`
- `curl http://localhost:8000/ready`

## ÉTAPE 4 — Smoke check URLs (doivent répondre)
- `curl -I http://localhost:3000`
- `curl -I http://localhost:3001`
- `curl -I http://localhost:8000/docs`
- `curl http://localhost:8000/openapi.json | head -c 2000`

## ÉTAPE 5 — Résumé clair à afficher
Afficher:
- Backend: http://localhost:8000
- Docs: http://localhost:8000/docs
- Client: http://localhost:3000
- Admin: http://localhost:3001

## ÉTAPE 6 — Mode "repair" si un frontend renvoie 404 partout
- `docker compose -f docker-compose.dev.yml logs --tail=200 frontend-client`
- `docker compose -f docker-compose.dev.yml logs --tail=200 frontend-admin`
- Vérifier que `NEXT_PUBLIC_API_BASE_URL` pointe sur `http://localhost:8000`
- Vérifier que les scripts dev Next bind sur `0.0.0.0`

## OPTION: MODE RESET COMPLET (À NE PAS FAIRE PAR DÉFAUT)
Uniquement si je dis explicitement "RESET_DB=YES":
- `docker compose -f docker-compose.dev.yml down -v`
- `docker compose -f docker-compose.dev.yml up -d --build`
- `docker compose -f docker-compose.dev.yml exec backend alembic upgrade head`

## LIVRABLE
- Exécute ces commandes proprement dans le bon dossier
- Si une étape échoue: donne le diagnostic + la correction minimale
- Ne change pas de code sans expliquer quel fichier et pourquoi

