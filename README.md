# Wikibase WMCO local

Adaptación local de Wikibase Suite con MediaWiki en español, MariaDB, ejecutor de
tareas, OpenSearch, WDQS con su interfaz y actualizador, QuickStatements y Traefik.
Traefik publica las interfaces por HTTP solo en este equipo.

## Iniciar

Con Docker, Docker Compose, Python 3 y curl disponibles. Para una instalación
nueva, copia `.env.example` a `.env`, completa las tres contraseñas con valores
propios y limita la lectura del archivo a tu cuenta con `chmod 600 .env`.
Para restaurar una instalación, usa su copia privada de `.env`.

```bash
./iniciar.sh
```

La primera ejecución descarga las imágenes, prepara OAuth e indexa la wiki.
El script reutiliza la base de datos y los archivos existentes. Abre http://localhost:8080. Usuario: `Admin`.
La contraseña de la cuenta se configura con `MW_ADMIN_PASSWORD` en `.env`.
El correo `admin@example.org` es un marcador: puedes cambiarlo antes de iniciar.
Si el puerto está ocupado, modifica `WIKIBASE_PORT` en `.env` antes del primer arranque.

- QuickStatements: http://localhost:8080/tools/quickstatements/
- Interfaz SPARQL: http://localhost:8834/
- API SPARQL: http://localhost:8834/sparql

El puerto de consultas se configura con `WDQS_PORT` en `.env`. QuickStatements
usa la cuenta local de MediaWiki y permite ejecutar lotes en el navegador.

Crear elementos: http://localhost:8080/w/index.php?title=Special:NewItem
Crear propiedades: http://localhost:8080/w/index.php?title=Special:NewProperty

## Administrar

```bash
docker compose ps
docker compose logs --tail=100 wikibase jobrunner elasticsearch wdqs wdqs-updater wdqs-frontend quickstatements traefik
docker compose stop
./iniciar.sh
```

`data/database/` guarda la base de datos, `data/config/` la configuración y
`data/images/` los archivos subidos. No borres estas carpetas si quieres conservar
la instancia. Docker puede crear archivos con propietario distinto a tu usuario.
Para una copia consistente, detén los servicios y copia `data/`, `.env` y
`compose.yaml`; vuelve a iniciarlos después. Guarda la copia en un lugar privado.

Personaliza MediaWiki en `data/config/LocalSettings.php` después del primer inicio.
No edites `InstanceSettings.php`. Las variables de instalación de `.env` no cambian
la cuenta de administrador ni la URL de una instancia ya inicializada.

Los volúmenes `quickstatements-data`, `wdqs-data` y `opensearch-data` guardan
las credenciales OAuth locales, el grafo SPARQL y el índice de búsqueda.
Incluye el volumen de QuickStatements en la copia de seguridad.

El actualizador de WDQS incorpora entidades presentes en los cambios recientes.
Si hay entidades anteriores al historial disponible, el primer índice necesita
una carga RDF del repositorio. Consulta la [documentación de WDQS](https://github.com/wmde/wikibase-suite/tree/main/development/images/wdqs#upgrading).

[Configuración oficial de Wikibase Suite](https://github.com/wmde/wikibase-suite/blob/main/docker-compose.yml)

## Migrar la instancia completa a otro ordenador

Usa la [Release del respaldo de Wikibase WMCO](https://github.com/Noisk8/wikibase/releases/tag/respaldo-wmco-20vqy1).
Esta copia conserva los IDs locales, declaraciones, páginas, historial, cuentas, logo
y configuración. Incluye los índices de búsqueda y SPARQL. Restaura en una
carpeta vacía y conserva la instalación original hasta verificar la copia.

### Dependencias

- Docker Engine con Docker Compose v2 y acceso al daemon. En Linux, ejecuta
  `docker info` y `docker compose version` para comprobarlo.
- Bash, `tar` con soporte gzip, Python 3 y `curl`.
- Acceso a GitHub para descargar el respaldo y a un registro Docker para descargar
  las imágenes. Git y GitHub CLI son opcionales.
- Un equipo x86-64 con al menos 8 GB de RAM disponible como referencia para la
  suite. En ARM, verifica primero que existan variantes compatibles de todas las
  imágenes. [Requisitos de Wikibase Suite](https://github.com/wmde/wikibase-suite/blob/main/docs/install/installer.md)
- Puertos locales 8080 y 8834 disponibles, o los valores configurados en el
  `.env` del respaldo. Conserva esas direcciones para mantener las IRIs locales
  del grafo y las URL de OAuth de QuickStatements.

### 1. Descargar la copia

Descarga los seis archivos adjuntos de la Release y guárdalos en una misma
carpeta. Si usas GitHub CLI, puedes descargarlos de una vez:

```bash
copia="$HOME/Descargas/wmco-respaldo"
mkdir -p "$copia"
gh release download respaldo-wmco-20vqy1 \
  --repo Noisk8/wikibase --dir "$copia"
```

| Archivo | Contenido |
|---|---|
| `proyecto.tar.gz` | Compose, scripts, archivos del diseño y el `.env` original. |
| `mariadb.tar.gz` | Directorio físico de MariaDB, con el contenido, los usuarios y el historial. |
| `wikibase.tar.gz` | Configuración, imágenes, logo y datos de QuickStatements, incluido OAuth. |
| `wdqs.tar.gz` | Índice RDF de Blazegraph. |
| `opensearch.tar.gz` | Índice de búsqueda de OpenSearch. |
| `imagenes.json` | Inventario de imágenes y plataformas del respaldo. |

Los archivos contienen las claves de esta instancia educativa. La restauración
usa el `.env` original para mantener la conexión entre los servicios.

### 2. Preparar un proyecto vacío

Cambia la ruta de `copia` si descargaste los archivos en otro lugar. Ejecuta
los bloques siguientes en la misma terminal de Bash para conservar la variable
y el nombre del proyecto.

```bash
copia="$HOME/Descargas/wmco-respaldo"
destino=$(mktemp -d "$HOME/wmco-restaurado.XXXXXXXX")
cd "$destino"

umask 077
tar -xzf "$copia/proyecto.tar.gz"
chmod 600 .env
mkdir -p data/database data/config data/images

# Usar un nombre nuevo evita reutilizar volúmenes de otro despliegue.
export COMPOSE_PROJECT_NAME="wmco-restaurado-$(date +%Y%m%d%H%M%S)"
docker compose config --quiet
docker compose pull
```

Como la copia de MariaDB y los índices son físicos, usa las mismas versiones
y la misma plataforma que en `imagenes.json`. Las etiquetas de Docker pueden
cambiar. Si tienes las imágenes originales en el otro equipo y las versiones
del registro ya son distintas, puedes trasladarlas con `docker image save`
y cargarlas con `docker image load` antes de restaurar. Si ya las cargaste,
omite `docker compose pull` para conservar las versiones originales.

### 3. Restaurar los archivos y volúmenes

Ejecuta este bloque antes de iniciar los servicios. Cada comando usa un
contenedor temporal para escribir el respaldo en el volumen correcto y mantener
los permisos guardados. El bloque se detiene ante el primer error.

```bash
(
  set -e
  docker compose run --rm --no-deps -T --user 0 --entrypoint tar database \
    -xzf - -C /var/lib/mysql < "$copia/mariadb.tar.gz"

  docker compose run --rm --no-deps -T --user 0 --entrypoint tar wikibase \
    -xzf - -C / < "$copia/wikibase.tar.gz"

  docker compose run --rm --no-deps -T --user 0 --entrypoint tar wdqs \
    -xzf - -C /wdqs/data < "$copia/wdqs.tar.gz"

  docker compose run --rm --no-deps -T --user 0 --entrypoint tar elasticsearch \
    -xzf - -C /usr/share/opensearch/data < "$copia/opensearch.tar.gz"
)
```

Guarda el nombre del proyecto en el `.env` de esta copia para que Docker Compose
use los mismos volúmenes cuando abras otra terminal. Este comando presupone que
el `.env` del respaldo no traía otra línea `COMPOSE_PROJECT_NAME`:

```bash
printf '\nCOMPOSE_PROJECT_NAME=%s\n' "$COMPOSE_PROJECT_NAME" >> .env
./iniciar.sh
```

### 4. Comprobar la copia

1. Abre la [portada](http://localhost:8080/) y comprueba el logo y los enlaces a
   Crear, Tutoriales, Federación y RDF.
2. Abre [Tierra](http://localhost:8080/wiki/Item:Q5) y verifica que conserva
   `Q5` en WMCO, `Q2` como ID de Wikidata y su relación con el sistema solar.
   Comprueba también el historial de una guía.
3. Abre [QuickStatements](http://localhost:8080/tools/quickstatements/) e inicia
   sesión con una cuenta del respaldo.
4. En el [editor SPARQL](http://localhost:8834/), ejecuta la consulta siguiente.
   Debe devolver el sistema solar local con el ID de Wikidata `Q544`.

```sparql
PREFIX wmco: <http://localhost:8080/entity/>
PREFIX wmcodt: <http://localhost:8080/prop/direct/>

SELECT ?sistema ?idWikidata WHERE {
  wmco:Q5 wmcodt:P2 ?sistema .
  ?sistema wmcodt:P3 ?idWikidata .
}
```

Si el servicio SPARQL responde pero faltan las declaraciones de la wiki,
ejecuta `./cargar-rdf-wdqs.sh` y vuelve a probar. Si un servicio no arranca,
usa `docker compose ps` y `docker compose logs --tail=80 <servicio>`.

### Generar un respaldo actualizado

En el ordenador que contiene la instancia en funcionamiento, ejecuta
`./respaldo-completo.sh`. El script detiene los servicios para obtener una
copia consistente, escribe los seis archivos en `backups/` y vuelve a iniciar
los servicios que estaban activos.

[Copias de seguridad y restauración de Wikibase Suite](https://github.com/wmde/wikibase-suite/blob/main/docs/operate/backup-and-restore.md)

## Reutilizar solo el diseño

Los archivos de `interfaz/` permiten reutilizar el diseño en una wiki nueva.
Copia `wmco-interface.css` a `data/config/` y `wmco-brand.png` a `data/images/`.
Consulta `LocalSettings.example.php` para integrar el registro del CSS y del
logo. Si usas el formato de URL, ajusta el identificador de la propiedad al
asignado en la nueva wiki. Revisa también los IDs y enlaces de la portada.
