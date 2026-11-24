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

## Trasladar la instalación a otro ordenador

El repositorio contiene el despliegue, el código wiki y los recursos de diseño.
Para migrar la wiki existente, restaura por separado una copia privada de MariaDB,
`.env`, `data/config/`, `data/images/` y el volumen `quickstatements-data`.
La base de datos conserva los IDs, el contenido y el historial de MediaWiki.
Arranca la copia con `./iniciar.sh` y carga el RDF existente con
`./cargar-rdf-wdqs.sh` si el índice SPARQL es nuevo.

Los archivos de `interfaz/` permiten reutilizar el diseño en una wiki nueva.
Copia `wmco-interface.css` a `data/config/` y `wmco-brand.png` a `data/images/`.
Consulta `LocalSettings.example.php` para integrar el registro del CSS y del
logo en la configuración local. El ajuste de formato de URL presupone que
`P4` es la propiedad local con ese significado. Ajusta los identificadores de
la portada y sus enlaces según las entidades y páginas de la nueva wiki.

[Copias de seguridad y restauración de Wikibase Suite](https://github.com/wmde/wikibase-suite/blob/main/docs/operate/backup-and-restore.md)
