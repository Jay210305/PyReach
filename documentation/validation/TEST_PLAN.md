# Plan de pruebas P9 — versión 1, 4 de noviembre de 2026

Responsables técnicos propuestos: Julio Centeno (datos/OSV) y Alonso Yáñez
(grafo, CLI, reportes). La ejecución automatizada que acompaña esta entrega no
acredita sesiones de usuarios ni dedicación registrada de los autores.

## Objetivo y alcance (estructura de referencia IEEE 829)

Verificar RF-01 a RF-10 y RNF-01 a RNF-07 a partir de las prácticas 1–8.
Las reproducciones de P8 y la ejecución base de 358 pruebas son diagnóstico previo;
la validación de entrega se ejecuta después de este plan.

- Caja negra: consola, entradas válidas/erróneas, códigos 0/1/2, configuración,
  importación offline y reportes SARIF/JSON/texto.
- Caja blanca: BFS acotado, precedencia del clasificador, constructores, rangos OSV,
  transacciones/marca incremental y rutas de archivo.
- Niveles: unitario, integración y sistema/E2E. Aceptación: requiere persona real;
  no se reemplaza por una prueba automatizada.
- Entorno: Linux local; Python 3.14 y comprobación de compatibilidad 3.10;
  bases SQLite desechables, avisos sintéticos y proyectos de fixtures versionados.
- Carga: 50 dependencias, 102 archivos, 2 003 funciones; tres ejecuciones seriadas
  y doce con cuatro trabajadores, sin caché. Medir P50, P95 nearest-rank y máximo.
- Seguridad: Bandit, auditoría de dependencias, rechazo de path traversal,
  YAML seguro, fuentes sin ejecutar y conexiones de red denegadas en subprocesos.
- Cobertura: líneas ejecutadas/ejecutables, incluyendo subprocesos; global >=80%,
  parsers >=90%, AST/grafo/alcanzabilidad >=85%, SARIF >=80%.
- Aceptación técnica: todos los casos críticos automatizados aprobados, cero
  regresiones críticas abiertas, SARIF válido y cada corrida de carga <=45 s.
  La reducción >=70% se contrasta únicamente en un oráculo sintético; confirmar
  efectividad industrial exige corpus real y línea base emparejada.
- Suspensión: pérdida de datos, reporte inválido, salida 0 que oculte fallo de
  configuración, conexión de red o descarte injustificado por incertidumbre.

## Casos y trazabilidad previa a la ejecución formal

| Caso | RF/RNF | Técnica | Entrada / esperado |
|---|---|---|---|
| CP09-01 | RF01-02, RNF05 | Negra/blanca | requirements/Pipfile + JSONL: catálogo consultable offline |
| CP09-02 | RF03-05, RNF06 | Blanca | cadena, constructor, ciclo, dinamismo y corte k: ruta o incertidumbre |
| CP09-03 | RF06-07, RNF04 | Negra | reporte SARIF: esquema OASIS válido, ubicaciones verificables |
| CP09-04 | RF08-09 | Negra | configuración, límites, flags: precedencia y códigos 0/1/2 |
| CP09-05 | RF10, RNF02 | Negra | 10 avisos controlados: 2 alcanzables, 8 descartados (80%) |
| CP09-06 | RNF01, RNF05 | Negra/blanca | fuente con efecto lateral/red denegada: fuente no ejecutada |
| CP09-07 | RNF03 | Negra | carga local de 50 dependencias: cada corrida <=45 s |
| CP09-08 | RNF06-07 | Blanca/negra | UTF-8 inválido y Python 3.10: diagnóstico y compatibilidad |
| CP09-09 | CU01-CU07 | Aceptación | representante recorre ayuda, escaneo y CI: pendiente de sesión real |

## Calendario de la semana

4/11: congelación del plan, correcciones, regresión y evidencia automatizada.
5/11: revisión del paquete y presentación P9. La sesión real se coordina para
esta ventana; mientras no exista registro, CP09-09 permanece pendiente.
Las semanas siguientes corresponden a P10 (12/11), P11 (19/11) y P12 (26/11).
No se simulan resultados ni aprobaciones futuras.
