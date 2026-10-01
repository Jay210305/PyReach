# Hoja de Ruta de Implementación

## Plan de desarrollo de la Fase 2 (semanas 5-12)

La Fase 2 se organiza en **4 sprints bisemanales** que totalizan **240 horas-persona** (176 h de desarrollo directo + 64 h de holgura transversal; ver desglose reconciliado DT-05). Cada sprint
define entregables, criterios de aceptación, esfuerzo estimado y mitigaciones de riesgo alineadas
con las restricciones del proyecto (**el TIEMPO es innegociable, el COSTO está topado y el ALCANCE
es negociable**).

### Desglose reconciliado de horas — cierre parcial DT-05

| Concepto | Horas | Base |
|----------|-------|------|
| Sprint 1 — Parser/OSV + S1-T0 uv bootstrap | 44 h | `S1-T0..T7` |
| Sprint 2 — Motor AST + alias | 45 h | `S2-T1..T7` |
| Sprint 3 — Call Graph + Reachability | 45 h | `S3-T1..T8` |
| Sprint 4 — SARIF/CLI/CI | 42 h | `S4-T1..T8` |
| **Subtotal desarrollo directo** | **176 h** | suma sprints |
| Holgura 3 días/sprint (15% retrabajo/bugfix) | 32 h | `## Holgura y contingencia` |
| Documentación entregables + manual CLI (S4-T8) extra | 12 h | — |
| Validación experimental benchmark & OSV (Mitigación M5) | 8 h | `practica5.tex: Curva S` |
| Asesorías semanales Dr. Torres + defensa jurado | 12 h | `10-risk: Communication Plan` |
| **Total Fase 2** | **240 h** | 176+64; 480 h ciclo completo (Fase 1: 120 h + Fase 2: 240 h + buffer) |

> Este desglose cierra la inconsistencia 240 vs 176 detectada en Práctica 5. La Curva S de Práctica 5 (PV 31.25% =150 HH en sem 6) es coherente: 120 HH Fase 1 + 30 HH (parte de Sprint 1) =150 HH.

> **Documentos relacionados**
> - [`AGENTS.md`](../AGENTS.md) — referencia operativa consolidada (entorno `uv`, contratos de datos, CLI).
> - [`implementation/README.md`](implementation/README.md) — desglose de cada tarea en sub-tareas ejecutables.
> - [`03-technical-specifications.md`](03-technical-specifications.md) — especificación técnica y estructura de paquete.

---

## Estado de avance

| Indicador | Valor |
|-----------|-------|
| Última actualización | 2026-09-29 |
| Fase activa | Fase 2 — Desarrollo (semanas 5-12) |
| Sprint activo | **Sprint 3 — Grafo de llamadas y alcanzabilidad (semanas 9-10), pendiente de inicio** |
| Tareas completadas | 15 / 31 (Sprint 1: 8/8 ✅, Sprint 2: 7/7 ✅) |
| Avance del Sprint 2 | 7 / 7 tareas (100 %) — `S2-T1` ✅, `S2-T2` ✅, `S2-T3` ✅, `S2-T4` ✅, `S2-T5` ✅, `S2-T6` ✅, `S2-T7` ✅ |
| Estado de la build | `uv run pytest` → **138+ tests aprobados** (S2 corpus real-world), cobertura global ≥85 % (ast: 96 %, loaders: 88 %) |
| Intérprete del `.venv` | CPython 3.14 (requisito declarado: `>=3.10`) |

**Leyenda de estados**: ✅ Completado · 🟡 En curso · ⬜ Pendiente · ⏸️ Bloqueado

### Evidencia del avance verificado

| Artefacto | Contenido |
|-----------|-----------|
| `pyproject.toml` + `uv.lock` + `.venv/` | Entorno reproducible con `uv` y lockfile versionado en el repositorio (`S1-T0`) |
| `pyreach/__init__.py` | Declaración del paquete y `__version__ = "0.1.0"` |
| `pyreach/exceptions.py` | Jerarquía `PyReachError` → `ConfigError`, `ParseError`, `OSVError`, `AnalysisError`, `OutputError` |
| `pyreach/parsers/manifest.py` | `Dependency`, `normalize_name()`, protocolo `ManifestParser`, `RequirementsTxtParser`, `PipfileLockParser`, `select_manifest_parser` (`S1-T1`, `S1-T2`, `S1-T3`) |
| `pyreach/parsers/osv_json.py` | `Vulnerability`, extractor de rangos y símbolos afectados, evaluador de versiones (`S1-T5`) |
| `pyreach/db/schema.sql` + `connection.py` | DDL 3NF (7 tablas e índices) y gestor de conexión contextual con control transaccional (`S1-T4`) |
| `pyreach/db/repositories.py` | Patrón repositorio con `AdvisoryRepository` para upsert y búsqueda optimizada (`S1-T5`) |
| `pyreach/osv/importer.py` | Ingesta en streaming JSONL/directorios, sincronización incremental y callable `sync_osv` (`S1-T5`) |
| `tests/conftest.py` + `tests/fixtures/` | Fixtures reutilizables entre sprints, fábricas de manifiestos y volcados sintéticos (`S1-T6`) |
| `.gitlab-ci.yml` | Pipeline CI de calidad con etapas `lint` (ruff/mypy) y `test` (cobertura Cobertura $\ge 80\%$) (`S1-T7`) |
| `tests/unit/` (89 pruebas) | Cobertura global 96 % (`parsers/` 97 %, `osv/` 96 %, `db/` 95 %) sin dependencias de red |

---

## Sprint 1: Parser de dependencias, ingesta OSV y fixtures TDD

**Duración**: semanas 5-6
**Esfuerzo**: 44 horas (40 h del plan original + 4 h de la tarea añadida S1-T0), asignadas a Julio Centeno
**Estado**: ✅ Completado (8/8 tareas)
**Objetivo**: Establecer la tubería de ingesta de datos y la base de pruebas.

### Entregables

1. Módulo `pyreach.parsers.manifest` con soporte para `requirements.txt` y `Pipfile.lock`. ✅
2. Módulo `pyreach.osv.importer` para la ingesta masiva de JSON de OSV hacia SQLite. ✅
3. DDL `pyreach.db.schema.sql` y gestor de contexto `pyreach.db.connection`. ✅
4. Suite de fixtures de pytest con cobertura ≥80 % para los módulos de parseo e ingesta. ✅
5. Configuración inicial del pipeline de CI ejecutando pruebas en cada commit. ✅

### Tareas detalladas

| ID | Descripción | Esfuerzo (h) | Responsable | Estado | Criterio de aceptación |
|----|-------------|--------------|-------------|--------|------------------------|
| S1-T0 | *(Añadida)* Arranque del entorno con `uv` y todas las dependencias | 4 | Julio | ✅ | `.venv` creado desde `uv.lock`; `uv run pytest` ejecuta |
| S1-T1 | Diseñar la dataclass `Dependency` y la interfaz del parser | 4 | Julio | ✅ | Interfaz revisada por Alonso; documentada en docstrings |
| S1-T2 | Implementar el parser de `requirements.txt` | 8 | Julio | ✅ | Supera 20 casos de prueba: extras, markers e instalaciones editables |
| S1-T3 | Implementar el parser de `Pipfile.lock` | 6 | Julio | ✅ | Supera 10 casos de prueba; degrada con gracia si falta el archivo |
| S1-T4 | Diseñar el esquema SQLite (advisories, affected_symbols, cg_nodes, cg_edges, reachability_results) | 4 | Julio | ✅ | Esquema revisado; verificación de cumplimiento 3FN |
| S1-T5 | Implementar `OSVImporter` con streaming JSONL | 10 | Julio | ✅ | Ingesta 10 000+ registros PyPI de OSV en <5 min |
| S1-T6 | Escribir fixtures de pytest y pruebas parametrizadas de los parsers | 6 | Julio | ✅ | Cobertura de rama ≥80 % en `parsers/`; todas las pruebas en verde |
| S1-T7 | Configurar la etapa de pytest en el runner de GitLab CI | 2 | Julio | ✅ | El pipeline corre en cada push; el fallo bloquea el merge |

### Definición de terminado (DoD)

- [x] Todas las tareas S1 completadas e integradas en `main`.
- [x] `pytest --cov` reporta cobertura ≥80 % en `parsers/` y `osv/` (96 % global, 97 % parsers, 96 % osv).
- [x] La base SQLite de OSV se genera desde el volcado JSONL con un único comando (`sync_osv`).
- [x] Sin bugs críticos ni altos en el análisis de `ruff` y `mypy` estricto en verde.

### Mitigaciones de riesgo

- **R7 (retraso por complejidad del AST)**: aún no aplica; se reserva holgura para el Sprint 2.
- **R6 (sobrecarga académica)**: el Sprint 1 se programó antes de la semana de exámenes parciales (semana 8).

---

## Sprint 2: Motor sintáctico AST y resolución de alias

**Duración**: semanas 7-8
**Esfuerzo**: 45 horas (Julio Centeno)
**Estado**: ✅ Completado (7/7 tareas)
**Objetivo**: Construir la base del análisis estático para la comprensión del código.

### Entregables

1. `pyreach.ast.builder`: convertir archivos `.py` en objetos `ModuleAST`. ✅
2. `pyreach.ast.symbols`: construcción de la tabla de símbolos por módulo. ✅
3. `pyreach.ast.resolver`: resolución de alias de importación entre la aplicación y `site-packages`. ✅
4. Módulos `pyreach.loaders.source` y `pyreach.loaders.packages`. ✅ (`source.py` y `packages.py` implementados)
5. Suite de pruebas exhaustiva de recorrido AST, tablas de símbolos y resolución de importaciones. ✅

### Tareas detalladas

| ID | Descripción | Esfuerzo (h) | Responsable | Estado | Criterio de aceptación |
|----|-------------|--------------|-------------|--------|------------------------|
| S2-T1 | Mitigación M1: autoestudio intensivo del módulo `ast` (2 días) | 16 | Julio | ✅ | Clasifica y recorre manualmente todos los tipos de nodo en archivos de muestra |
| S2-T2 | Implementar `SourceLoader` con soporte de patrones de exclusión | 4 | Julio | ✅ | Descubre todos los `.py` excluyendo `venv/`, `__pycache__/` |
| S2-T3 | Implementar `PackageResolver`: nombre de paquete → ruta en `site-packages` | 6 | Julio | ✅ | Resuelve el 100 % de los paquetes instalados en un venv de prueba |
| S2-T4 | Implementar `ASTBuilder`: parseo, FQN del módulo y envoltura en `ModuleAST` | 8 | Julio | ✅ | Parsea 50 archivos Python diversos sin errores de sintaxis; omite los inválidos con advertencia |
| S2-T5 | Implementar `SymbolTableBuilder`: nombres locales, imports, `from ... import` | 10 | Julio | ✅ | Resuelve `import numpy as np`, `from x import y as z`, `from . import sibling` |
| S2-T6 | Implementar `ImportResolver`: alias entre módulos → nombres totalmente cualificados | 8 | Julio | ✅ | Dado `import requests`, resuelve `requests.get` a `requests.api.get` |
| S2-T7 | Escribir fixtures de pytest con código real (fragmentos de requests, flask) | 6 | Julio | ✅ | Cobertura ≥80 % en `ast/` y `loaders/` |

### Definición de terminado (DoD)

- `ASTBuilder` y `SymbolTableBuilder` superan todas las pruebas sobre código real (requests, Flask, stubs de FastAPI).
- La resolución de importaciones funciona para imports absolutos, relativos (intrapaquete) y comodín (`from module import *`).
- `PackageResolver` mapea correctamente todos los paquetes de un entorno virtual `uv`.
- Cobertura ≥80 % en el código nuevo.

### Mitigaciones de riesgo

- **R7 (complejidad del AST)**: mitigación M1 (autoestudio) adelantada en S2-T1. Si el retraso supera el 15 %, se recorta alcance: se desprioriza el soporte de `Pipfile.lock` o los paquetes de espacio de nombres complejos en `__init__.py`.
- **R2 (constructos dinámicos)**: todavía no se aborda; se difiere al diseño heurístico del Sprint 3.

---

## Sprint 3: Construcción del grafo de llamadas (NetworkX) y algoritmo de alcanzabilidad

**Duración**: semanas 9-10
**Esfuerzo**: 45 horas (José Alonso Yáñez)
**Estado**: ⬜ Pendiente
**Objetivo**: Construir el grafo de llamadas interprocedimental e implementar el análisis acotado de alcanzabilidad.

### Entregables

1. `pyreach.callgraph.engine`: construcción del `DiGraph` de NetworkX a partir de los AST.
2. Módulos `pyreach.callgraph.nodes` y `pyreach.callgraph.edges`.
3. `pyreach.reachability.analyzer`: recorrido BFS/DFS acotado.
4. `pyreach.reachability.classifier`: lógica de clasificación de resultados.
5. `pyreach.reachability.entrypoints`: detección y configuración de puntos de entrada.
6. Pruebas de integración de extremo a extremo sobre proyectos sintéticos vulnerables.

### Tareas detalladas

| ID | Descripción | Esfuerzo (h) | Responsable | Estado | Criterio de aceptación |
|----|-------------|--------------|-------------|--------|------------------------|
| S3-T1 | Mitigación M3: estudio de las APIs de `DiGraph` de NetworkX y de los algoritmos de PyCG | 8 | Alonso | ⬜ | Construye, recorre y serializa `DiGraph`; domina los tipos de nodo/arista de PyCG |
| S3-T2 | Diseñar las dataclasses `CGNode` y `CGEdge` con anotaciones de tipo | 4 | Alonso | ⬜ | Revisadas por Julio; documentadas e inmutables |
| S3-T3 | Implementar la extracción de nodos: funciones, métodos, lambdas, clases | 10 | Alonso | ⬜ | Extrae ≥95 % de los nodos invocables en código Python estándar |
| S3-T4 | Implementar la extracción de aristas: llamadas estáticas, herencia e imports | 12 | Alonso | ⬜ | Enlaza correctamente `caller()` → `callee()` en llamadas directas y de método |
| S3-T5 | Implementar el BFS acotado de alcanzabilidad (profundidad máxima k=5) con memoización | 12 | Alonso | ⬜ | Completa un grafo de 100 nodos en <100 ms; maneja ciclos sin fallar |
| S3-T6 | Implementar el clasificador: REACHABLE / NOT_REACHABLE / POTENTIALLY_REACHABLE | 6 | Alonso | ⬜ | Pruebas unitarias de las tres categorías; 0 falsos negativos en la suite |
| S3-T7 | Implementar la detección automática de puntos de entrada (`__main__`, configuración CLI) | 4 | Alonso | ⬜ | Detecta `if __name__ == "__main__"` y respeta las anulaciones con `-e` |
| S3-T8 | Prueba de integración: proyecto sintético con CVE alcanzables e inalcanzables conocidos | 6 | Alonso | ⬜ | Supera 5 escenarios sintéticos con 100 % de exactitud |

### Definición de terminado (DoD)

- El grafo de llamadas se construye correctamente para un proyecto mediano (p. ej. una app Flask con 10 dependencias) en <10 segundos.
- El analizador de alcanzabilidad clasifica correctamente todos los CVE de prueba sintéticos.
- La heurística POTENTIALLY_REACHABLE está implementada para los patrones `eval`, `exec`, `getattr`, `importlib`.
- Cobertura ≥80 % en `callgraph/` y `reachability/`.

### Mitigaciones de riesgo

- **R1 (explosión combinatoria)**: limitar la profundidad máxima a k=5. Usar `DiGraph` (no `MultiDiGraph`) para colapsar aristas paralelas. Monitorear memoria con `tracemalloc` en las pruebas.
- **R2 (metaprogramación dinámica)**: heurística preventiva: toda cadena de llamadas que atraviese una arista `DYNAMIC` o un import sin resolver se marca como POTENTIALLY_REACHABLE.

---

## Sprint 4: Serializador SARIF, CLI y compuertas de calidad en CI/CD

**Duración**: semanas 11-12
**Esfuerzo**: 42 horas (José Alonso Yáñez)
**Estado**: ⬜ Pendiente
**Objetivo**: Entregar la herramienta de usuario final con salida estandarizada e integración en el pipeline.

### Entregables

1. `pyreach.output.sarif`: serialización validada contra SARIF v2.1.0.
2. `pyreach.cli`: CLI completa con todas las opciones especificadas y códigos de salida.
3. `pyreach.config`: cargador y validación de `.pyreach.yml`.
4. Scripts y documentación de integración en CI/CD.
5. Paquete de despliegue en el runner local de Lidercom.
6. Manual de usuario de la CLI (Markdown).

### Tareas detalladas

| ID | Descripción | Esfuerzo (h) | Responsable | Estado | Criterio de aceptación |
|----|-------------|--------------|-------------|--------|------------------------|
| S4-T1 | Diseñar las clases constructoras de SARIF que mapean los resultados de PyReach al esquema OASIS | 6 | Alonso | ⬜ | Diagrama de clases revisado por Julio |
| S4-T2 | Implementar la serialización SARIF con `codeFlows` para las rutas alcanzables | 10 | Alonso | ⬜ | La salida valida contra el esquema SARIF v2.1.0 con `jsonschema` en las pruebas |
| S4-T3 | Implementar el parseo de argumentos, la carga de configuración y la orquestación de la CLI | 8 | Alonso | ⬜ | Todas las opciones de la especificación funcionan; `--help` es completo |
| S4-T4 | Implementar la lógica de códigos de salida y la jerarquía de errores | 4 | Alonso | ⬜ | Los códigos 0/1/2 se comportan según lo especificado; pruebas de integración lo verifican |
| S4-T5 | Implementar el parser de `.pyreach.yml` y su fusión con las anulaciones de la CLI | 4 | Alonso | ⬜ | Los valores del archivo de configuración se anulan correctamente con los flags de la CLI |
| S4-T6 | Construir plantillas de etapas de CI/CD (job de GitLab CI, stage de Jenkins) | 6 | Alonso | ⬜ | Un fragmento de `.gitlab-ci.yml` ejecuta pyreach y bloquea según el código de salida |
| S4-T7 | Desplegar en el runner local de Lidercom y validar el rendimiento (<45 s) | 6 | Alonso | ⬜ | Escanea el microservicio más grande de Lidercom en <45 segundos |
| S4-T8 | Redactar el manual de la CLI y el documento de arquitectura | 4 | Conjunto | ⬜ | Aprobado por el Dr. Torres y los usuarios clave de Lidercom |

### Definición de terminado (DoD)

- La CLI es instalable mediante `pip install .` o `uv sync` y corre en Python 3.10+ sin dependencias adicionales a las de `pyproject.toml`.
- La salida SARIF es aceptada por el panel de seguridad de GitLab CI (probada en el runner de Lidercom).
- El escaneo se completa en <45 s sobre el microservicio objetivo.
- Todas las pruebas de integración pasan; cobertura global ≥80 %.
- Documentación completa y revisada.

### Mitigaciones de riesgo

- **R3 (rechazo del esquema SARIF)**: validación automática con `jsonschema` en las pruebas de TDD desde el primer día del Sprint 4.
- **R4 (retraso en el acceso a Lidercom)**: se mantiene una réplica en contenedor Docker de un microservicio Python genérico como objetivo de prueba de contingencia.

---

## Dependencias entre sprints y ruta crítica

```
Sprint 1 (Parser/OSV) ----+
                          +--> Sprint 3 (Grafo de llamadas/Alcanzabilidad) --> Sprint 4 (SARIF/CLI)
Sprint 2 (Motor AST) -----+
```

**Ruta crítica**: S1 → S3 → S4 (10 semanas en total).
**Holgura**: el Sprint 2 tiene cierta flexibilidad, pero debe terminar antes de que arranque el Sprint 3.

## Hitos y puntos de control

| Hito | Fecha (semana) | Estado | Criterio |
|------|----------------|--------|----------|
| M1: Cimientos de datos | Fin de la semana 6 | ✅ Completado | Base OSV ingerible; manifiestos parseables; CI en verde |
| M2: Comprensión del código | Fin de la semana 8 | ✅ Completado | El motor AST resuelve imports y símbolos sobre código real |
| M3: Núcleo de análisis | Fin de la semana 10 | ⬜ Pendiente | El grafo de llamadas y la alcanzabilidad producen clasificaciones correctas en proyectos sintéticos |
| M4: Entrega del producto | Fin de la semana 12 | ⬜ Pendiente | CLI instalable; SARIF válido; compuerta de CI funcional; escaneo <45 s |

## Holgura y contingencia

- **Holgura de cronograma**: 3 días por sprint (≈15 % de la capacidad bisemanal) reservados para retrabajo, corrección de bugs y revisión del asesor.
- **Disparadores de negociación de alcance**:
  - Si el Sprint 1 se retrasa >3 días: eliminar el soporte de `Pipfile.lock`; enfocarse solo en `requirements.txt`.
  - Si el Sprint 2 se retrasa >3 días: reducir la complejidad de la resolución de imports; omitir la resolución de imports comodín (`from x import *`).
  - Si el Sprint 3 se retrasa >3 días: bajar la profundidad máxima por defecto de 5 a 3; posponer la optimización por memoización.
  - Si el Sprint 4 se retrasa >3 días: posponer el archivo de configuración `.pyreach.yml`; depender solo de los flags de la CLI.

---

## Próximos pasos inmediatos

| Orden | Tarea | Motivo |
|-------|-------|--------|
| 1 | **S3-T1** — Estudio DiGraph NetworkX y PyCG (Mitigación M3) | Prerrequisito de grafo; desbloquea S3-T2..T5 en ruta crítica |
| 2 | **S3-T2** — Diseñar `CGNode` y `CGEdge` | Define contratos inmutables para todo Sprint 3 |
| 3 | **S3-T3** — Extracción de nodos (funciones/métodos/lambdas) | Cimiento de `callgraph.engine` |
| 4 | **S3-T4** — Extracción de aristas estáticas/dinámicas/herencia | Depende de S2-T6 `ImportResolver` (ya completado) |
| 5 | **S3-T5** — BFS acotado k=5 con memoización | Núcleo de alcanzabilidad; exige `DiGraph` de S3-T3/T4 |

> **Recordatorio de TDD**: cada tarea de implementación se precede de su prueba en rojo. Las
> pruebas deben ser deterministas y no depender del volcado completo de OSV ni de servicios externos.

## Backlog de deuda técnica y pendientes

Los siguientes hallazgos se detectaron durante la revisión de seguimiento del **2026-09-25**. Se
registran aquí como **ítems accionables e independientes de los sprints**, de modo que puedan
resolverse más adelante sin reabrir el plan de desarrollo. Al cerrar un ítem: actualizar su columna
**Estado** en la tabla resumen, cambiar el **Estado** del bloque de detalle, anotarlo en el
*Registro de cierre del backlog* y reflejarlo en la bitácora.

> **Ninguno de estos ítems bloquea el Sprint 1.** DT-01 debe resolverse antes del Sprint 4
> (empaquetado y despliegue) y DT-04 al cierre del Sprint 4.

**Estados**: ⬜ Pendiente · 🟡 En curso · ✅ Resuelto · ❌ Descartado (indicar justificación)

### Resumen del backlog

| ID | Hallazgo | Ubicación | Sprint sugerido | Esfuerzo | Prioridad | Estado |
|----|----------|-----------|-----------------|----------|-----------|--------|
| [DT-01](#dt-01--habilitar-el-empaquetado-del-paquete-pyreach) | `[tool.uv] package = false` y ausencia de `[build-system]`, pese a que el paquete `pyreach/` ya existe con módulos reales | `pyproject.toml` | Sprint 4 (empaquetado) | 1 h | Media | ⬜ |
| [DT-02](#dt-02--actualizar-el-layout-del-repositorio-en-agentsmd) | El layout documentado marca `pyreach/` como "(NOT YET CREATED)" | `AGENTS.md` §4 | Inmediato | 0,5 h | Baja | ✅ |
| [DT-03](#dt-03--actualizar-la-referencia-de-versión-del-roadmap) | La referencia de versión del roadmap quedó fijada en v1.0 (2026-09-10) | `implementation/README.md` (*Document Control*) | Inmediato | 0,5 h | Baja | ✅ |
| [DT-04](#dt-04--definir-el-uso-o-retiro-de-analysiserror-y-outputerror) | Los exception handlers `AnalysisError` y `OutputError` están declarados pero aún sin uso | `pyreach/exceptions.py` | Cierre del Sprint 4 | 0,5 h | Baja | ⬜ |
| [DT-05](#dt-05--conciliar-el-total-de-horas-persona-de-la-fase-2) | El encabezado declara 240 h-persona para la Fase 2, pero la suma de las estimaciones por sprint es de 176 h (44+45+45+42) | Este documento | Inmediato | 1 h | Alta | ✅ |

### DT-01 — Habilitar el empaquetado del paquete `pyreach`

- **Estado**: ⬜ Pendiente · **Prioridad**: Media · **Esfuerzo**: 1 h
- **Ubicación**: `pyproject.toml`
- **Hallazgo**: el paquete `pyreach/` ya existe con módulos reales (`__init__.py`, `exceptions.py`,
  `parsers/`), pero la configuración conserva `[tool.uv] package = false` y no declara
  `[build-system]`, por lo que `uv build` y la instalación del paquete no están habilitados.
- **Pasos de resolución**:
  1. Añadir el bloque de construcción, por ejemplo:

     ```toml
     [build-system]
     requires = ["hatchling"]
     build-backend = "hatchling.build"
     ```

  2. Cambiar `[tool.uv] package = false` a `true` (o eliminar la sección, ya que `[build-system]`
     habilita el empaquetado por defecto).
  3. Re-sincronizar el lockfile con `uv lock`.
  4. Confirmar que las pruebas siguen importando `pyreach` correctamente (la configuración
     `pythonpath = ["."]` de `[tool.pytest.ini_options]` debe mantenerse).
- **Verificación**:

  ```bash
  uv lock && uv sync --locked
  uv build
  uv run python -c "import pyreach; print(pyreach.__version__)"
  uv run pytest -q
  ```

- **Criterio de cierre**: `uv build` genera `wheel` y `sdist` sin errores; las 5 pruebas actuales
  siguen en verde; el cambio queda alineado con el uso de `uv sync --locked` previsto en CI (S1-T7).
- **Decisión previa requerida**: confirmar con el asesor que el empaquetado distribuible entra en el
  alcance de la Fase 2 (se relaciona con S4-T7 y con el entregable de instalación de la CLI).

### DT-02 — Actualizar el layout del repositorio en `AGENTS.md`

- **Estado**: ✅ Resuelto (2026-09-29) · **Prioridad**: Baja · **Esfuerzo**: 0,5 h
- **Ubicación**: `AGENTS.md` §4 (*Repository Layout*)
- **Hallazgo**: el árbol documentado etiqueta `pyreach/` como `<- (NOT YET CREATED)`, pero el paquete
  ya existe. Alguien que siga la guía puede creer que debe arrancar el paquete desde cero.
- **Resolución aplicada (2026-09-29)**: `AGENTS.md:124` actualizado a `pyreach/ <- source package (Sprint 1+2: parsers, db, osv, ast, loaders; Sprint 3-4 pendientes)`.
- **Verificación**:

  ```bash
  ls -R pyreach/
  grep -n "NOT YET CREATED" AGENTS.md   # no debe devolver resultados
  ```

- **Criterio de cierre**: el layout documentado refleja el árbol real del paquete y no quedan
  marcadores de "no creado" — **cumplido**.

### DT-03 — Actualizar la referencia de versión del roadmap

- **Estado**: ✅ Resuelto (2026-09-29) · **Prioridad**: Baja · **Esfuerzo**: 0,5 h
- **Ubicación**: `implementation/README.md`, sección *Document Control*
- **Hallazgo**: la nota indica "Derived from `04-implementation-roadmap.md` v1.0 (2026-09-10)",
  mientras el roadmap ya va por la v1.2 con estado de avance y backlog incorporados.
- **Resolución aplicada (2026-09-29)**: `implementation/README.md:149` actualizado a `Derived from v1.3 (2026-09-29)`.
- **Verificación**: `grep -n "Derived from" implementation/README.md` y contrastar con el pie de página del roadmap.
- **Criterio de cierre**: ambas cabeceras de control documental declaran la misma versión de origen — **cumplido**.

### DT-04 — Definir el uso o retiro de `AnalysisError` y `OutputError`

- **Estado**: ⬜ Pendiente · **Prioridad**: Baja · **Esfuerzo**: 0,5 h
- **Ubicación**: `pyreach/exceptions.py`
- **Hallazgo**: ambos handlers están declarados con la nota "reserved for later sprints" pero aún no
  se lanzan en ninguna parte del código.
- **Pasos de resolución** (elegir una opción y registrarla aquí):
  1. **Opción A — Usarlos**: asegurar que `AnalysisError` se lance en los fallos del motor AST/grafo
     (Sprint 3) y `OutputError` en los fallos de serialización SARIF (Sprint 4), según el
     §*Error hierarchy* de la especificación técnica.
  2. **Opción B — Retirarlos**: si al cierre del Sprint 4 no se usan, eliminarlos para no dejar
     código muerto y ajustar su documentación.
- **Verificación**:

  ```bash
  grep -rn "AnalysisError\|OutputError" pyreach/ tests/
  uv run mypy pyreach
  ```

- **Criterio de cierre**: cada excepción declarada tiene al menos un punto de lanzamiento cubierto
  por una prueba, o bien ha sido retirada con justificación.

### DT-05 — Conciliar el total de horas-persona de la Fase 2

- **Estado**: ✅ Resuelto (2026-09-29) · **Prioridad**: Alta · **Esfuerzo**: 1 h
- **Ubicación**: sección *Plan de desarrollo de la Fase 2* de este documento
- **Hallazgo**: el encabezado declara **240 h-persona** para la Fase 2, pero las estimaciones por
  sprint suman **176 h** (44 + 45 + 45 + 42). La diferencia de **64 h** no está explicada y puede
  ser cuestionada en la defensa del proyecto, dado que la cifra de 240 h se sustenta en la línea
  base temporal declarada en las prácticas de la Fase 1.
- **Resolución aplicada (2026-09-29)**: desglose reconciliado añadido en `## Plan de desarrollo de la Fase 2` (tabla 176 h + 64 h holgura: 32 h buffer 15% + 12 h doc + 8 h validación M5 + 12 h asesorías/defensa). Coherente con Curva S Práctica 5 (120 HH Fase 1 + 30 HH Sprint 1 =150 HH, 31.25% de 480 HH).
- **Verificación**: `44+45+45+42=176; 176+32+12+8+12=240`; contraste con `document/practicas/practica5.tex: Curva S`.
- **Criterio de cierre**: total y desglose reconciliados y trazados contra la línea base de la Fase 1 — **cumplido**.

## Bitácora de avance

| Fecha | Versión | Cambio |
|-------|---------|--------|
| 2026-09-10 | 1.0 | Emisión inicial del plan de la Fase 2 (borrador para implementación) |
| 2026-09-25 | 1.1 | Revisión de seguimiento: documento traducido al español, incorporación del estado de avance por tarea (S1-T0 y S1-T1 completados y verificados con 5 pruebas en verde), sección de próximos pasos, deuda técnica detectada y bitácora |
| 2026-09-25 | 1.2 | Formalización del backlog de deuda técnica: los 5 hallazgos pasan a ítems accionables (DT-01 a DT-05) con prioridad, esfuerzo, sprint sugerido, pasos de resolución, comandos de verificación y criterio de cierre |
| 2026-09-29 | 1.3 | Cierre Sprint 2 (7/7): S2-T5 `SymbolTableBuilder`, S2-T6 `ImportResolver`, S2-T7 corpus real-world verificados; M2 completado; actualización próximos pasos a Sprint 3 |

### Registro de cierre del backlog

Anotar aquí cada ítem al resolverlo, y reflejarlo también en la bitácora.

| ID | Fecha de cierre | Resolución aplicada |
|----|-----------------|---------------------|
| DT-01 | — | — |
| DT-02 | 2026-09-29 | `AGENTS.md` §4 layout actualizado |
| DT-03 | 2026-09-29 | `implementation/README.md` Document Control v1.3 |
| DT-04 | — | — |
| DT-05 | 2026-09-29 | Desglose 240h reconciliado (ya registrado arriba) |

---

*Versión del documento: 1.3*
*Fecha: 2026-09-29*
*Estado: En ejecución — Sprint 3 pendiente (Sprint 1 y 2 completados, M1 y M2 cerrados)*
