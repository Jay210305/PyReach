# Estado de entrega — 04/11/2026

Base revisada: `2cf90a8e098fea03fa252112322c5e996e33b0a1`.

| Tarea | Estado verificable |
|---|---|
| S4-T1/T2 | SARIF 2.1.0, esquema OASIS local, codeFlows, ubicaciones reales y pruebas |
| S4-T3/T4 | CLI, formatos, políticas 0/1/2, excepciones y wheel instalable |
| S4-T5 | YAML seguro, claves/tipos, precedencia y uniones; pruebas |
| S4-T6 | GitHub workflow y templates GitLab/Jenkins/cron/Docker; réplica local |
| S4-T7 | Benchmark sintético y contenedor sin red verificados; piloto Lidercom, dashboard y corpus industrial PENDIENTES |
| S4-T8 | README y tres manuales; validación por una persona distinta al autor PENDIENTE |
| A8-01/H8-01 | Constructor y límite conservador corregidos con regresiones |
| A8-02 | Marca inicial común en incremental multiarchivo |
| A8-03 | Unicode inválido produce omisión advertida/análisis parcial |
| A8-04 | 0..7 unificado y migración de caché heredada preservando filas |
| H8-02 | Símbolos filtrados por versión y paquetes secundarios consultables |
| Integración | Llamadas de módulo, transitivas instaladas, destino protegido y caché JSON |
| Dependencias | Black vulnerable actualizado; auditoría repetida sin hallazgos conocidos |

Evidencia de entrega: `documentation/validation/results.json`, JUnit, cobertura y
logs resumidos. `scripts/validate_release.py` reproduce escenarios y carga local.
Los datos son sintéticos; ninguna firma, hora de autor, aprobación ni ahorro industrial
se deduce de este estado técnico. UAT, capacitación, acta y acuerdo SLA requieren
participación real y no se marcan completados.
