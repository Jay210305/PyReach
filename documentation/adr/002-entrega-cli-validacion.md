# ADR-002 — Entrega CLI y validación técnica, 04/11/2026

Aceptado para la entrega técnica; aceptación organizacional pendiente.

1. Se entrega CLI con argparse, YAML seguro y precedencia explícita; se conserva
   el procesamiento offline. `pyreach.toml` era una propuesta de P1/P7; el contrato
   implementado es `.pyreach.yml`/`.yaml`, conforme a la especificación numerada.
2. Profundidad única 0..7 (default 5). El corte no demuestra inalcanzabilidad:
   devuelve potencial. Se migra transaccionalmente la caché heredada 1..5.
3. El grafo modela constructores e inicializadores, y llamadas de nivel de módulo.
   Las fuentes no se ejecutan. Las transitivas instaladas se obtienen de metadata.
4. El catálogo conserva el JSON OSV original y un índice normalizado de paquetes;
   la selección de símbolos usa paquete/rango aplicable. Se conserva el esquema
   previo y se amplía de forma compatible, sin inventar un historial SIEM.
5. Se entrega caché JSON de grafos por hash de contenido y versión de formato,
   bajo el usuario; no pickle ni ficheros ejecutables de caché del repositorio analizado.
6. Reportes con ubicaciones verificables; no rellenar líneas desconocidas. La métrica
   descarta un aviso sólo si todos sus símbolos son no alcanzables. El tiempo humano
   ahorrado queda como no medido, separado de reducción estática sintética.
7. GitLab genérico conserva SARIF como artefacto. La ingesta nativa, si existe en el
   servidor, requiere un productor exitoso y una compuerta separada; no declarar SARIF
   como reporte `dependency_scanning`. Validación específica de Lidercom pendiente.
8. El contenedor no root usa una instantánea SQLite publicada en journal DELETE
   para montar sólo el archivo en lectura, y ejecuta con `--network none`.
9. La suite técnica y los manuales no sustituyen UAT, capacitación, validación por
   tercero, acta de conformidad ni experimento industrial de OE4.

### Refinamiento de sincronización incremental

La marca global se actualiza al terminar el conjunto y sirve como registro. La decisión
de omitir se compara contra la fecha del aviso ya persistido, no sólo contra la marca
global. Un aviso aún no importado se incorpora aunque su fecha sea anterior a la última
sincronización; una regresión adicional conserva ese contrato.
