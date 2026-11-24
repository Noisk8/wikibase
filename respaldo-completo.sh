#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
umask 077

docker compose ps >/dev/null
mkdir -p backups
work=$(mktemp -d "$PWD/backups/wmco-completo.XXXXXXXX")
running=$(docker compose ps --services --status running)

resume() {
  if [[ -n "$running" ]]; then
    local services
    readarray -t services <<< "$running"
    docker compose start "${services[@]}"
  fi
}

trap resume EXIT
docker compose stop

tar --exclude='__pycache__' -czf "$work/proyecto.tar.gz" \
  .env .gitignore compose.yaml README.md iniciar.sh cargar-rdf-wdqs.sh \
  respaldo-completo.sh config interfaz
docker compose images --format json > "$work/imagenes.json"

docker compose run --rm --no-deps -T --user 0 --entrypoint tar database \
  -czf - -C /var/lib/mysql . > "$work/mariadb.tar.gz"
docker compose run --rm --no-deps -T --user 0 --entrypoint tar wikibase \
  -czf - -C / config var/www/html/images quickstatements/data > "$work/wikibase.tar.gz"
docker compose run --rm --no-deps -T --user 0 --entrypoint tar wdqs \
  -czf - -C /wdqs/data . > "$work/wdqs.tar.gz"
docker compose run --rm --no-deps -T --user 0 --entrypoint tar elasticsearch \
  -czf - -C /usr/share/opensearch/data . > "$work/opensearch.tar.gz"

for archive in "$work"/*.tar.gz; do
  tar -tzf "$archive" >/dev/null
done

resume
trap - EXIT
printf 'Copia completa en %s\n' "$work"
