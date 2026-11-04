# Manual técnico / instalación

## Requisitos y entorno

Python >=3.10; uv >=0.5; SQLite de la biblioteca estándar; disco para catálogo y
reportes. Referencia propuesta para piloto: 2 núcleos, 4 GB RAM y 2 GB libres,
a confirmar con el tamaño real del catálogo. El ensayo local mide otro hardware;
no equivale a certificar este mínimo. El análisis no requiere un servidor HTTP.

## Instalación reproducible para desarrollo

1. Instale Python y uv desde el canal aprobado.
2. Clone `git clone https://github.com/Jay210305/PyReach.git` y entre a `PyReach`.
3. Seleccione la revisión aprobada y ejecute `uv sync --locked`.
4. Ejecute `uv run pyreach --version` y `uv run pyreach --help`.
5. Importe un catálogo local con `uv run pyreach sync-osv --source ARCHIVO -d DB`.
6. Ejecute `uv run python scripts/validate_release.py --output release-evidence`.
   Debe finalizar con `passed: true`; no confundir sus datos sintéticos con producción.

Para entrega: `uv build`; calcule SHA-256 del wheel y consérvelo junto a `uv.lock`.
Instale en un entorno limpio usando `uv venv ENTORNO --python 3.10` y
`uv pip install --python ENTORNO/bin/python dist/pyreach-0.1.0-py3-none-any.whl`.
Para instalación aislada de Internet preaprovisione los wheels aprobados y use
`--no-index --find-links /wheels`; compruebe todas las dependencias transitivas.

## Rutas y variables

No hay secretos de aplicación ni variables obligatorias para el CLI local.
`HOME` determina `~/.pyreach/config.yml` y `~/.cache/pyreach`; no se modifica en
la instalación normal. `PYREACH_DB_PATH`, `PYREACH_MANIFEST`, `PYREACH_OSV_SOURCE`
son variables de las plantillas CI, no un mecanismo oculto de configuración del CLI.
Precedencia y ejemplos: README. Proteja permisos del DB y destino de reportes.

## Actualización, migración y reversión

1. Detenga nuevos jobs y cierre lectores durante la ventana acordada.
2. Copie wheel anterior y haga respaldo SQLite consistente con `Connection.backup`.
3. En una copia del DB, importe datos aprobados; la inicialización crea el índice de
   paquetes OSV y migra el dominio de caché antiguo 1..5 al dominio 0..7 conservando filas.
4. Compruebe `PRAGMA integrity_check`, conteos, aviso conocido y una ejecución de humo.
5. Cambie la ruta del runner a la copia validada y habilite un solo proyecto piloto.
6. Ante salida 2 persistente, pérdida de integridad o regresión crítica, restaure el
   wheel y DB anteriores; repita humo y documente el incidente antes de reabrir jobs.

No aplicar `cp` a una base SQLite abierta con WAL como único respaldo.
El uso de contenedor sin red se documenta en `ci/README.md`.

## Catálogo SQLite montado como sólo lectura

Para un montaje del archivo individual en un contenedor, publicar una copia consistente
con `PRAGMA journal_mode=DELETE` después de respaldar y antes de montarla como lectura.
Una base persistida en WAL puede requerir archivos `-wal`/`-shm`; montar sólo `osv.db`
como lectura no garantiza que SQLite pueda abrirla. No usar `immutable=1` sobre una base
viva que pueda cambiar. La sincronización trabaja sobre una copia nueva y el piloto
cambia a la instantánea validada. El ensayo de contenedor usa esta publicación.
