# Registro de Tareas Pendientes y Datos Requeridos (PENDIENTES.md)

**Artículo:** *Análisis Estático Interprocedimental de Alcanzabilidad mediante Grafos de Llamadas para la Mitigación de Alertas Espurias en Dependencias de Python*  
**Instrucción general:** En cumplimiento de la regla de no inventar datos, cifras, referencias ni metodologías, se insertaron marcadores visibles `\todo[color=orange]{DATO REQUERIDO: ...}` en el código fuente LaTeX (`articulo_ieee.tex`).  
A continuación se presenta la lista consolidada de los **23 pendientes**, clasificados por área temática y numerados para facilitar su resolución por los autores.

---

## Índice Rápido de Pendientes

| ID | Categoría | Sección / Línea | Resumen de Requerimiento |
|---|---|---|---|
| **PEND-01** | Metodología | Sec. IV-A (L296) | Aclarar si tipo de arista `IMPORT` en $\Omega$ se construye o se elimina de la tupla formal. |
| **PEND-02** | Metodología | Sec. IV-A (L296) | Definir política de aristas concurrentes entre $u$ y $v$ en `networkx.DiGraph`. |
| **PEND-03** | Metodología | Sec. IV-D (L358) | Justificación empírica formal de la cota $k=5$ sobre grafos densos. |
| **PEND-04** | Metodología | Sec. III-C (L239) | Procedimiento de población de `vulnerable_functions` y tratamiento de avisos sin símbolo. |
| **PEND-05** | Metodología | Sec. V-C (L585) | Protocolo de ground truth: acuerdo inter-evaluador ($\kappa$), desempate y lista de CVEs. |
| **PEND-06** | Metodología | Sec. II-D (L122) | Línea base experimental de alcanzabilidad (e.g., PyCG/JARVIS + OSV). |
| **PEND-07** | Metodología | Sec. II-A (L93) | Cifra exacta de recall/completitud de PyCG reportada en la literatura con su cita. |
| **PEND-08** | Metodología | Sec. VI-A (L707) | Clarificar métricas operativas de estabilidad y descartar causalidad exclusiva de breaking changes = 0. |
| **PEND-09** | Datos Exp. | Sec. I (L113) / V-C (L630) | Tabla desglosada por proyecto con alertas manifiestas, TP, FP, TN, FN y tasa individual. |
| **PEND-10** | Datos Exp. | Tabla I (L113) | Cita o medición empírica comparable de tasa de falsos positivos en SaaS para Python. |
| **PEND-11** | Datos Exp. | Sec. V-D (L661) | Módulos reales de `site-packages` analizados en `MS-Analytics` ($|V|=421$). |
| **PEND-12** | Datos Exp. | Sec. V-D (L661) | Metodología de medición de memoria (7.24 MB: ¿tracemalloc, RSS o estructuras del grafo?). |
| **PEND-13** | Datos Exp. | Sec. V-D (L661) | Aclarar si "Tiempo Net." equivale a E2E o excluye carga de runtime. |
| **PEND-14** | Datos Exp. | Sec. V-D (L661) | Completar en Tabla V los 4 microservicios restantes del banco de pruebas. |
| **PEND-15** | Datos Exp. | Sec. V-D (L661) | Especificar plataforma de hardware/SO exacta que produjo cada tabla de resultados. |
| **PEND-16** | Datos Exp. | Sec. V-E (L664) | Histograma o distribución de longitudes de caminos testigo en el grafo. |
| **PEND-17** | Datos Exp. | Sec. V-E (L664) | Validación de la cota $k$ sobre un conjunto independiente y separado de proyectos. |
| **PEND-18** | Datos Exp. | Sec. V-E (L664) | Aclarar por qué "nodos explorados" (hasta 5,840) supera el total de nodos (2,141). |
| **PEND-19** | Datos Exp. | Sec. V-E (L664) | Desglose de componentes que dominaron los 14.80 s con $k=\infty$. |
| **PEND-20** | Datos Exp. | Sec. VI-A (L707) | Metodología de medición del tiempo de triaje semanal (muestra $n$, semanas, instrumentos). |
| **PEND-21** | Referencias | Sec. I (L70) / II-C (L99) | Verificar [3] (`ladisa2023sok`) como respaldo de fuga de IP en herramientas SaaS. |
| **PEND-22** | Referencias | Sec. I (L68) | Verificar [6] (`pashchenko2022vuln4real`, Java/Maven) para el 80%–90% en Python. |
| **PEND-23** | Referencias | Sec. I (L70) / II (varias) | Verificar [14], [26], [7], [8], [10], [12], [25] (citas y metadatos bibliográficos). |

---

## 1. Grupo 1: Metodología y Modelo Teórico

### [PEND-01] Definición formal del tipo de arista `IMPORT` en $\Omega$
- **Ubicación en .tex:** Sección IV-A, Línea 296 (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: Aclarar si el tipo de arista IMPORT se construye en alguna pasada del análisis o debe eliminarse de la definición formal de Omega}`
- **Qué falta:** La tupla formal define $\omega \in \{\text{STATIC}, \text{DYNAMIC}, \text{INHERITANCE}, \text{IMPORT}\}$, pero en el Algoritmo 1 solo se instancian aristas de tipo $\text{STATIC}$, $\text{INHERITANCE}$ y $\text{DYNAMIC}$.
- **Acción requerida por el autor:** Confirmar si en la pasada 3 (o en el módulo `ImportResolver`) se crean efectivamente aristas etiquetadas como `IMPORT` que vinculen el módulo importador con el importado, o si se debe eliminar `IMPORT` del conjunto $\Omega$.

### [PEND-02] Política de resolución de aristas concurrentes en `networkx.DiGraph`
- **Ubicación en .tex:** Sección IV-A, Línea 296 (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: Especificar la política de resolución cuando existen múltiples aristas concurrentes entre u y v (¿se conserva la arista con mayor certeza c, o se migra el modelo a MultiDiGraph?)}`
- **Qué falta:** La clase `networkx.DiGraph` es un grafo simple dirigido que admite a lo sumo una arista entre el par ordenado $(u, v)$. Si una función $u$ invoca a $v$ tanto de forma directa estática como a través de un decorador o llamada dinámica, un atributo sobreescribe al otro.
- **Acción requerida por el autor:** Aclarar si la implementación de PyReach sobreescribe la arista conservando la de mayor certeza estática ($c$), si mantiene la arista dinámica por principio de sobre-aproximación, o si internamente utiliza `networkx.MultiDiGraph`.

### [PEND-03] Justificación formal de la cota de profundidad $k=5$
- **Ubicación en .tex:** Sección IV-D, Línea 358 (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: Aportar justificación empírica formal de la cota k=5 sobre grafos densos y distribución de llamadas}`
- **Qué falta:** Dado que la complejidad temporal del BFS con conjunto de visitados es lineal $O(|V| + |E|)$, la cota $k$ no previene una explosión combinatoria teórica exponencial, sino que acota el tiempo sobre dependencias complejas y evita acumular alertas dudosas (`POTENTIALLY_REACHABLE`). Se requiere una argumentación formal respaldada en datos.
- **Acción requerida por el autor:** Proporcionar la fundamentación basada en la topología de llamadas observada en microservicios Python.

### [PEND-04] Población de la tabla `vulnerable_functions` en SQLite OSV
- **Ubicación en .tex:** Sección III-C, Línea 239 (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: Explicar el procedimiento exacto mediante el cual se pobló la tabla vulnerable_functions (¿extracción de affected_functions, análisis estático de parches/commits, o curación manual asistida?) y definir la política de clasificación ante avisos de seguridad que carecen de símbolos específicos (¿se clasifican como REACHABLE por defecto, se marcan como POTENTIALLY_REACHABLE, o se excluyen del análisis?)}`
- **Qué falta:** Los advisories de OpenSSF OSV para el ecosistema PyPI provienen fundamentalmente de GitHub Security Advisories (GHSA), PyPA y NVD, donde los metadatos de versiones son exhaustivos pero el campo de funciones afectadas rara vez está normalizado a nivel de función/clase.
- **Acción requerida por el autor:** Explicar cómo el comando `pyreach sync-osv` pobla dicha tabla (¿parser de GHSA, análisis de commits/diffs de fixes, curación manual?) y cuál es la heurística cuando un CVE no tiene símbolos listados.

### [PEND-05] Protocolo de auditoría del Ground Truth y acuerdo inter-evaluador
- **Ubicación en .tex:** Sección V-C, Línea 585 (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: Documentar el acuerdo inter-evaluador (coeficiente kappa de Cohen o porcentaje de concordancia inicial), el protocolo formal de resolución de discrepancias / desempate, y proveer la disponibilidad de repositorios, hashes de commits y lista detallada de CVEs evaluados}`
- **Qué falta:** Se menciona que dos ingenieros sénior realizaron la auditoría manual de las 77 alertas, pero no se reporta el grado de acuerdo inicial ni cómo se resolvieron discrepancias.
- **Acción requerida por el autor:** Proveer el valor de concordancia (e.g., Cohen's $\kappa \ge 0.85$ o % de acuerdo), método de desempate (revisión conjunta con un tercer evaluador o consenso) y enlace a repositorio/anexo con los hashes de commits y lista de CVEs.

### [PEND-06] Línea base experimental de alcanzabilidad
- **Ubicación en .tex:** Sección II-D, Línea 122 (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: Incluir una línea base experimental de alcanzabilidad (p. ej. pipeline PyCG/JARVIS + OSV u otra herramienta de reachability en Python) y una tabla desglosada por proyecto con alertas totales, TP, FP, TN, FN}`
- **Qué falta:** En la literatura de ingeniería de software (IEEE/ACM), los revisores exigen comparar una herramienta propuesta frente a al menos una técnica existente del estado del arte que realice análisis contextual o alcanzabilidad, no únicamente contra escáneres superficiales de manifiestos (pip-audit).
- **Acción requerida por el autor:** Evaluar si es factible armar una línea base empírica con PyCG + OSV o citar un estudio comparable.

### [PEND-07] Cifra exacta de completitud / recall de PyCG en la literatura
- **Ubicación en .tex:** Sección II-A, Línea 93 (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: Verificar la cifra exacta de recall/completitud de PyCG reportada en la literatura y su respectiva cita bibliográfica}`
- **Qué falta:** En el texto se menciona el 99.2% de precisión reportado por Salis et al. (ICSE 2021), pero se debe indicar el dato numérico de recall o completitud registrado para PyCG.
- **Acción requerida por el autor:** Extraer la cifra de recall de PyCG del paper original [18] (o de estudios independientes como JARVIS) e insertarla.

### [PEND-08] Métricas de estabilidad operativa y atribución causal
- **Ubicación en .tex:** Sección VI-A, Línea 707 (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: Clarificar métricas operativas de estabilidad y descartar atribución causal estricta de breaking changes a PyReach}`
- **Qué falta:** Se eliminó la afirmación de que PyReach causó que los breaking changes bajaran a cero en producción, pero se requiere matizar cómo la reducción de actualizaciones innecesarias coadyuvó a la estabilidad del entorno.
- **Acción requerida por el autor:** Validar la redacción y proveer contexto operativo del equipo de DevOps de Lidercom.

---

## 2. Grupo 2: Datos Experimentales y Resultados

### [PEND-09] Tabla desglosada por proyecto con métricas individuales
- **Ubicación en .tex:** Tabla I (L113) y Sección V-C (L630) (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: Incluir tabla desglosada por proyecto con alertas totales, TP, FP, TN, FN y tasa de reducción individual}`
- **Qué falta:** El texto reporta un rango de reducción por proyecto del 80.0% al 87.5%, pero no existe una tabla que desglose los 8 proyectos (`MS-Analytics`, `MS-NLP-Extract`, etc.) con sus respectivas alertas manifiestas, TP, FP, TN, FN y tasas individuales.
- **Acción requerida por el autor:** Proveer la matriz numérica de 8 filas $\times$ 6 columnas para incorporar la tabla en la sección V-C.

### [PEND-10] Medición o cita empírica de tasa de falsos positivos en escáneres SaaS
- **Ubicación en .tex:** Tabla I, Línea 113 (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: Cita o medición empírica comparable de la tasa de falsos positivos en escáneres SaaS en Python}`
- **Qué falta:** La Tabla I atribuía "<15% alertas espurias" a SaaS sin respaldo bibliográfico ni medición directa en Python, lo que generaba una contradicción frente a la precisión del 78.6% de PyReach (21.4% de alertas FP/ambiguas).
- **Acción requerida por el autor:** Aportar una cita de la literatura que mida la tasa de falsos positivos de Snyk/Endor Labs en Python, o reemplazar el valor por una caracterización cualitativa documentada.

### [PEND-11] Módulos reales de `site-packages` analizados en `MS-Analytics`
- **Ubicación en .tex:** Sección V-D, Línea 661 (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: Aclarar (a) qué módulos de site-packages se analizan realmente (¿solo los alcanzables desde imports?), dado que MS-Analytics depende de Pandas/Scikit-learn pero cuenta con solo |V|=421 nodos...}`
- **Qué falta:** Pandas y Scikit-learn poseen decenas de miles de funciones y métodos. Si el grafo de `MS-Analytics` tiene únicamente $|V|=421$ nodos y $|E|=808$ aristas en la Tabla II, es indispensable explicar el criterio de poda/carga de librerías.
- **Acción requerida por el autor:** Confirmar si PyReach realiza carga bajo demanda únicamente de los submódulos de paquetes efectivamente referenciados por sentencias `import` en el código huésped.

### [PEND-12] Metodología de medición de consumo de memoria RAM (7.24 MB)
- **Ubicación en .tex:** Sección V-D, Línea 661 (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: ... (b) metodología de medición de memoria (7.24 MB: ¿tracemalloc, RSS del proceso, o solo estructuras de datos del grafo?)...}`
- **Qué falta:** Un proceso de CPython 3.10+ suele ocupar más de 15–20 MB de RSS en memoria física nada más arrancar con NetworkX importado. El valor de 7.24 MB debe justificarse técnicamente.
- **Acción requerida por el autor:** Aclarar si la medición se realizó con `tracemalloc.get_traced_memory()` (memoria neta asignada por el intérprete a las estructuras del grafo) o mediante qué mecanismo específico.

### [PEND-13] Equivalencia de "Tiempo Net." vs. tiempo de escaneo E2E
- **Ubicación en .tex:** Sección V-D, Línea 661 (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: ... (c) si la columna 'Tiempo Net.' equivale al tiempo E2E o excluye la carga del runtime...}`
- **Qué falta:** En la Tabla V se lista "Tiempo Net." de 1.176 s (frío) para `MS-Analytics`, mientras que en la última fila se indica "CLI E2E Máximo: 1.612 s".
- **Acción requerida por el autor:** Precisar qué operaciones abarca "Tiempo Net." (tiempo de AST + Call Graph + Bounded BFS) frente al tiempo E2E (invocación de CLI, lectura de disco, validación y escritura de archivo SARIF).

### [PEND-14] Completar los 4 microservicios restantes en la Tabla V de Benchmarks
- **Ubicación en .tex:** Sección V-D, Línea 661 (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: ... (d) completar los 4 servicios restantes del banco en la Tabla V...}`
- **Qué falta:** La Tabla V (`tab:benchmarks`) solo lista 4 servicios (`MS-Analytics`, `MS-NLP-Extract`, `MS-Auth-Gate`, `MS-Report-Svc`), omitiendo los otros 4 presentados en la Tabla II (`MS-Data-Sync`, `MS-Notif-Hub`, `OS-DocParser`, `OS-RateLimit`).
- **Acción requerida por el autor:** Aportar los tiempos (frío/caliente) y memoria pico de los 4 servicios restantes para completar la tabla.

### [PEND-15] Especificación de hardware/SO por tabla de resultados
- **Ubicación en .tex:** Sección V-D, Línea 661 (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: ... (e) especificar la plataforma exacta de hardware/SO (Intel vs. AMD Ryzen, CPython 3.10 vs. 3.14) empleada para cada tabla de resultados}`
- **Qué falta:** La Sección V-A menciona que se utilizaron equipos Intel Core i7 y AMD Ryzen con CPython 3.10 y 3.14. Se debe detallar con precisión qué máquina ejecutó cada benchmark.
- **Acción requerida por el autor:** Definir las especificaciones exactas del host de prueba para las Tablas V y VI.

### [PEND-16] Histograma o distribución de longitudes de caminos testigo
- **Ubicación en .tex:** Sección V-E, Línea 664 (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: Aportar (a) histograma o distribución de longitudes de los caminos testigo...}`
- **Qué falta:** Para justificar empíricamente por qué la convergencia de recall ocurre en $k=5$, se requiere presentar la distribución de saltos observada en las 11 rutas de los positivos reales.
- **Acción requerida por el autor:** Proveer el conteo de caminos con longitud $d=1, 2, 3, 4, 5$.

### [PEND-17] Validación de la cota $k$ en conjunto independiente de proyectos
- **Ubicación en .tex:** Sección V-E, Línea 664 (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: ... (b) validación de la cota k en un conjunto independiente/separado de proyectos...}`
- **Qué falta:** Elegir $k=5$ y evaluar sobre los mismos 11 casos constituye un sesgo metodológico de sobreajuste. Se requiere contrastar la cota en proyectos ajenos al set de entrenamiento.
- **Acción requerida por el autor:** Indicar si se dispone de pruebas en proyectos adicionales o registrar la limitación en la discusión.

### [PEND-18] Explicación de nodos explorados acumulados (hasta 5,840) vs. nodos del banco (2,141)
- **Ubicación en .tex:** Sección V-E, Línea 664 (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: ... (c) justificación de por qué la métrica de 'nodos explorados' (hasta 5,840) excede el total de nodos del banco (2,141), indicando si se acumula sobre múltiples consultas BFS o repeticiones...}`
- **Qué falta:** La Tabla VI muestra 5,840 nodos explorados para $k=\infty$, mientras que la Tabla II reporta que todo el banco de pruebas sumado tiene 2,141 nodos.
- **Acción requerida por el autor:** Confirmar si el número representa la sumatoria de nodos visitados en múltiples búsquedas individuales de cada CVE evaluado (o por cada entrypoint analizado).

### [PEND-19] Desglose de factores que dominaron los 14.80 s con $k=\infty$
- **Ubicación en .tex:** Sección V-E, Línea 664 (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: ... (d) desglose del tiempo de ejecución de 14.80 s con k=inf (tiempo en grafo vs. resolución de llamadas)}`
- **Qué falta:** Explicar si el tiempo estuvo dominado por el recorrido del grafo en Python puro o por la serialización de rutas y resolución de llamadas.
- **Acción requerida por el autor:** Proveer el perfilado (*profiling*) de ejecución de esa corrida.

### [PEND-20] Metodología de medición del tiempo de triaje semanal en Lidercom
- **Ubicación en .tex:** Sección VI-A, Línea 707 (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: Detallar la metodología de medición del tiempo de triaje (tamaño de la muestra de desarrolladores n, periodo de observación en semanas, instrumentos de registro y línea base formal previa)}`
- **Qué falta:** Afirmar que el tiempo de triaje cayó de "10 h a <1.5 h semanales" requiere respaldo cuantitativo formal.
- **Acción requerida por el autor:** Indicar número de ingenieros participantes, semanas monitoreadas y método de captura (e.g. Jira/GitLab time tracking).

---

## 3. Grupo 3: Referencias Bibliográficas a Verificar

Todas estas referencias han sido marcadas con `% VERIFICAR` en `PyReach/Article/referencias.bib` y con `\todo` junto a la cita en el `.tex`:

### [PEND-21] Ref. [3] `ladisa2023sok`: Fuga de IP en herramientas SaaS
- **Ubicación en .tex:** Sección I (L70) y Sección II-C (L99).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: Verificar cita [3] (ladisa2023sok) como respaldo de fuga de IP en escáneres SaaS}`
- **Qué falta:** El paper de Ladisa et al. en IEEE S&P 2023 es una taxonomía de ataques a la cadena de suministro de código abierto (typosquatting, inyección maliciosa en paquetes). Es necesario comprobar si el texto de Ladisa et al. respalda explícitamente la afirmación de fuga de propiedad intelectual o exposición de código en herramientas SaaS, o si debe citarse una fuente especializada en confidencialidad de código en la nube.

### [PEND-22] Ref. [6] `pashchenko2022vuln4real`: Código inerte en Python
- **Ubicación en .tex:** Sección I, Línea 68 (`articulo_ieee.tex`).
- **Texto en marcador:** `\todo[color=orange]{DATO REQUERIDO: Verificar cita [6] (Vuln4Real, centrada en Java/Maven) como evidencia del 80\%--90\% de código inerte en el ecosistema Python}`
- **Qué falta:** *Vuln4Real* (IEEE TSE 2022) evaluó 200 proyectos de la biblioteca central de Java/Maven. Usarlo para sustentar que en Python el 80%–90% de las alertas corresponden a código inerte requiere matizar o complementar con literatura empírica centrada en Python (e.g., Alfadel et al. [4] o Chinthanet et al. [5]).

### [PEND-23] Citas y metadatos de referencias [14], [26], [7], [8], [10], [12], [25]
- **Ref. [14] `sadowski2018lessons` (Sección I, L70):** Usada para respaldar las 10 horas semanales de triaje manual en Lidercom. Sadowski et al. trata sobre lecciones de análisis estático en Google (Tricorder). Se debe verificar si se pretendía citar como antecedente general de fatiga de alertas o si se requiere un dato interno de Lidercom.
- **Ref. [26] `bhandari2022cvefixes` (Sección II-C, L99):** Usada para respaldar la afirmación de "difusión de librerías dañinas y demora al aplicar parches". *CVEfixes* (MSR 2022) es un dataset curado de vulnerabilidades y commits de fijación; verificar si sustenta la tasa de difusión o retraso de parches.
- **Ref. [7] `dann2021identifying` (Sección II-B, L96):** Verificar título y venue: *Identifying method-level dependencies for vulnerability reachability analysis*, ISSTA 2021, pp. 627–639.
- **Ref. [8] `duan2023towards` (Sección II-B, L96):** Verificar título y venue: *Towards Automated Reachability Analysis of Software Vulnerabilities in Open Source Packages*, IEEE EuroS&P 2023, pp. 334–349.
- **Ref. [10] `prana2022empirical` (Sección II-B, L96):** Verificar título y venue: *Categorizing the Reachability of Software Vulnerabilities in Open-Source Dependencies*, IEEE TSE, vol. 48, no. 11, 2022.
- **Ref. [12] `gutierrez2024auditoria` (Sección I, L70):** Verificar existencia, indexación y datos de publicación de la revista *Ciencia y Desarrollo Informático*, vol. 11, no. 1, 2024.
- **Ref. [25] `alexopoulos2026cross` (Sección II-A, L91):** Verificar existencia y estado del preprint arXiv:2603.18693 (con fecha 2026).
