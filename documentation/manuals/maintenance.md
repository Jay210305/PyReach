# Manual de mantenimiento y soporte

## Estructura y contratos

- `parsers/`: manifiestos y registros OSV; nombres PEP 503, rangos y datos externos.
- `db/`: esquema, repositorio y migración compatible de caché heredada.
- `osv/`: importador local y selección de avisos/símbolos según versión instalada.
- `loaders/`, `ast/`: fuentes y paquetes, AST y resolución de símbolos sin ejecutar Python.
- `callgraph/`: nodos/aristas, herencia, constructores y llamadas de nivel de módulo.
- `reachability/`: BFS, clasificación conservadora y detección de puntos de entrada.
- `config.py`, `cli.py`: validación, precedencia y orquestación.
- `output/`: métricas, JSON/texto y SARIF; `tests/fixtures/` contiene oráculos sintéticos.
- `ci/` y `.github/workflows/`: compuertas y ejemplos; `scripts/validate_release.py`: evidencia.

Mantener argparse, NetworkX DiGraph y SQLite. Leer ADRs y especificaciones numeradas
antes de cambiar contratos. No añadir ejecución dinámica, descargas implícitas ni
líneas ficticias a los reportes. La caché JSON incluye hashes del contenido y versión
del formato; modifique su versión al cambiar la semántica del grafo. Para invalidarla,
quite sólo el directorio de caché PyReach del usuario afectado.

## Cambio correctivo reproducible

1. Reproducir con un fixture mínimo y escribir una regresión que falle.
2. Corregir la función compartida y revisar todos sus consumidores.
3. Ejecutar lint, formato, mypy, pytest con cobertura, Bandit y validación completa.
4. Comprobar compatibilidad Python 3.10 y generar wheel; registrar SHA y changelog.
5. Revisar impacto en los tres manuales; entregar al custodio un plan de reversión.
6. Actualizar el grafo de conocimiento con `graphify update .`.

## Soporte propuesto (requiere acuerdo de la organización)

Responsables propuestos: Julio Centeno, datos/ingesta; Alonso Yáñez, análisis/CLI/CI.
Canal: incidencia del repositorio para casos anonimizados; incidentes sensibles por
el canal interno que designe Lidercom. No publicar código privado, secretos o
volcados reales en una incidencia pública.

| Severidad | Ejemplo | Respuesta inicial propuesta | Tratamiento |
|---|---|---|---|
| Crítica | Falso negativo confirmado, pérdida de DB, compuerta inoperante | <=24 h | Suspender descarte automático y activar rollback; acordar recuperación |
| Media | Reporte incompleto con alternativa operativa | <=72 h | Reproducir, priorizar y proponer versión correctiva |
| Baja | Mejora de mensaje o documentación | <=5 días hábiles | Registrar y programar en mantenimiento |

Respuesta inicial no significa resolución ni servicio 24/7. El SLA es una propuesta,
no un compromiso aceptado. Conservar fecha de reporte, severidad, acuse, responsable,
solución, pruebas y cierre. Una vez por semana revisar catálogo y salud de jobs;
mensualmente revisar dependencias y respaldos; probar restauración antes de cada release.

## Validación por tercero

Pendiente: una persona ajena al autor debe instalar desde el manual, ejecutar ayuda,
importar fixture, generar SARIF y explicar 0/1/2 sin asistencia. Registrar persona,
fecha, pasos, obstáculos y correcciones reales. Una prueba automatizada o la revisión
por este asistente no reemplaza esa actividad.
