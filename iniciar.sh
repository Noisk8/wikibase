#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

docker compose config --quiet
if ! docker info >/dev/null 2>&1; then
  echo 'No se puede acceder a Docker. Ejecuta este script desde una terminal con acceso al servicio Docker.' >&2
  exit 1
fi

# Recreate the wiki before the proxy takes over its previous host port.
docker compose up -d --wait --wait-timeout 900 wikibase
docker compose up -d --wait --wait-timeout 900 traefik wdqs wdqs-frontend wdqs-updater

# Existing installations did not create a QuickStatements OAuth consumer.
if ! docker compose exec -T wikibase test -s /quickstatements/data/oauth.ini; then
  echo 'Configurando OAuth para QuickStatements…'
  if ! docker compose exec -T wikibase bash /var/www/html/extensions/WikibaseSuite/setup/scripts/setup-quickstatements-oauth.sh >/dev/null 2>&1 ||
     ! docker compose exec -T wikibase test -s /quickstatements/data/oauth.ini; then
    echo 'No se pudo generar la configuración OAuth de QuickStatements. Verifica que la cuenta administradora configurada exista en la wiki.' >&2
    exit 1
  fi
fi

docker compose up -d --wait --wait-timeout 900

if [[ ! -f data/config/.opensearch-indexed ]]; then
  docker compose exec -T wikibase php maintenance/run.php CirrusSearch:UpdateSearchIndexConfig
  docker compose exec -T wikibase php maintenance/run.php CirrusSearch:ForceSearchIndex
  touch data/config/.opensearch-indexed
fi

wiki_url=$(docker compose config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["wikibase"]["environment"]["MW_WG_SERVER"])')
query_url=$(docker compose config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["wikibase"]["environment"]["WDQS_PUBLIC_FRONTEND_URL"])')
curl -fsS "$wiki_url/w/api.php?action=query&meta=siteinfo&format=json" >/dev/null
curl -fsS "$wiki_url/tools/quickstatements/" >/dev/null
if ! curl -fsS "$wiki_url/tools/quickstatements/api.php?action=is_logged_in" |
  python3 -c 'import json,sys; response=json.load(sys.stdin); sys.exit(not (response.get("status") == "OK" and response.get("data", {}).get("is_logged_in") is False))'; then
  echo 'QuickStatements sirve la interfaz, pero su API de sesión no responde correctamente. Revisa docker compose logs --tail=50 quickstatements.' >&2
  exit 1
fi
curl -fsS "$query_url/" >/dev/null
curl -fsSG -H 'Accept: application/sparql-results+json' --data-urlencode 'query=ASK {}' "$query_url/sparql" |
  python3 -c 'import json,sys; sys.exit(json.load(sys.stdin).get("boolean") is not True)'
printf '\nWikibase         %s\nQuickStatements  %s/tools/quickstatements/\nConsultas SPARQL %s/\nAPI SPARQL       %s/sparql\n' "$wiki_url" "$wiki_url" "$query_url" "$query_url"
