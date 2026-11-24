#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

docker compose ps --status running wdqs wikibase >/dev/null

rdf=$(mktemp "${TMPDIR:-/tmp}/wmco-wikibase-rdf.XXXXXXXX")
trap 'rm -f -- "$rdf"' EXIT

docker compose exec -T wikibase php /var/www/html/maintenance/run.php \
  /var/www/html/extensions/Wikibase/repo/maintenance/dumpRdf.php --format ttl > "$rdf"
if [[ ! -s "$rdf" ]]; then
  echo 'Wikibase generó un archivo RDF vacío.' >&2
  exit 1
fi

endpoint=http://localhost:9999/bigdata/namespace/wdq/sparql
docker compose exec -T wdqs curl -fsS -H 'Content-Type: text/turtle' \
  --data-binary @- "$endpoint" < "$rdf"

printf '\nDeclaraciones directas de Tierra y sistema solar en WDQS\n'
docker compose exec -T wdqs curl -fsSG -H 'Accept: text/tab-separated-values' \
  --data-urlencode 'query=SELECT ?entidad ?propiedad ?valor WHERE {
    ?entidad ?propiedad ?valor .
    FILTER(STRENDS(STR(?entidad), "/entity/Q5") || STRENDS(STR(?entidad), "/entity/Q4"))
    FILTER(CONTAINS(STR(?propiedad), "/prop/direct/"))
  } LIMIT 30' "$endpoint"
