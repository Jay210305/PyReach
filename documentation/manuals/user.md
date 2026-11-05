# Manual de usuario — PyReach 0.1.0

## Rol Backend: diagnosticar un hallazgo

1. Asegure que el catálogo local ya está preparado y que el entorno de dependencias
   corresponde al proyecto. No ejecute `sync-osv` como parte implícita de un escaneo.
2. Consulte `uv run pyreach --help`. El comando termina con 0 sin analizar archivos.
3. Ejecute `uv run pyreach /proyecto -d /datos/osv.db -f text --include-all`.
4. Lea el estado y su explicación. Una cadena `main -> cliente -> biblioteca.funcion`
   es evidencia estática; `POTENTIALLY_REACHABLE` exige revisión, no descarte.
5. Si no se detecta entrada, indique `-e paquete.modulo:funcion`; el nombre debe
   existir en las fuentes. Ajuste `-k 0..7`; no use un k menor para ocultar alertas.
6. Localice archivo y región reales en SARIF. Cuando faltan metadatos de ubicación,
   el reporte conserva el símbolo y omite la región, sin fabricar líneas.
7. Corrija la dependencia o investigue la llamada; vuelva a ejecutar el mismo caso.
   Un descarte estático nunca sustituye la evaluación humana de riesgo.

## Rol DevOps: integrar una compuerta

1. Instale el wheel aprobado y verifique su huella.
2. Monte el catálogo local como lectura. Ejecute con `--include-potentially` y
   `-o /artefactos/resultados.sarif`; descargue el artefacto incluso si el job falla.
3. Interprete 0/1/2: 1 bloquea por política; 2 requiere reparar una entrada, ruta,
   configuración o problema operativo. Nunca transforme todos los errores en éxito.
4. Para JSON utilice `-f json`, sin capturar mensajes de stderr como parte del JSON.
5. Registre toda excepción temporal con `--no-fail`; esta bandera no silencia un
   error operativo. Revise `ci/README.md` antes de habilitar dashboard GitLab.

## Rol custodio del catálogo

1. Reciba JSON/JSONL del canal autorizado. PyReach no descarga el volcado.
2. Conserve respaldo antes de `pyreach sync-osv --source /datos -d /datos/osv.db
   --incremental`.
3. Revise importados, omitidos, malformados y ecosistema; compare conteos y consulte
   un aviso conocido. La marca incremental cambia al terminar el conjunto.
4. No trate una importación parcial como un reemplazo atómico del catálogo completo:
   el importador confirma lotes. Para un cambio de versión use una copia nueva del DB.

## Diagnóstico

| Mensaje / síntoma | Acción |
|---|---|
| DB ausente | Preparar catálogo con `sync-osv --source`, luego reintentar |
| Entrada no detectada | Verificar `-e modulo:funcion` contra las fuentes |
| Archivo inválido | Corregir codificación/sintaxis; el reporte señala análisis parcial |
| Ruta fuera del proyecto | Copiar manifiesto dentro del proyecto; no usar `../` |
| Corte de profundidad | Investigar incertidumbre; ampliar k sin exceder 7 |
| Reporte sin ubicación | Consultar símbolo y código; no inventar un `startLine` |

Las salidas capturadas para los documentos académicos se conservan en las evidencias
P9/P11. Son ejecuciones del software, no wireframes ni pruebas de aceptación humana.
La validación de este manual por una persona distinta al autor está pendiente.
