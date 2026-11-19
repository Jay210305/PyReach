# Registro de Cambios Técnicos y Editoriales (CAMBIOS.md)

**Artículo:** *Análisis Estático Interprocedimental de Alcanzabilidad mediante Grafos de Llamadas para la Mitigación de Alertas Espurias en Dependencias de Python (Caso de Estudio Industrial: PyReach en Lidercom Perú S.A.C.)*  
**Clase:** IEEEtran (`conference`)  
**Archivos modificados:** `PyReach/Article/articulo_ieee.tex`, `PyReach/Article/referencias.bib`  
**Copia de respaldo original:** `PyReach/Article/backup_20261116/`  
**Fecha de edición:** 16 de noviembre de 2026  
**Compilación final:** `latexmk -pdf -outdir=build articulo_ieee.tex` (12 páginas, 0 errores).

---

## 1. Resumen Ejecutivo y Balance Matemático

Todas las correcciones solicitadas en los Bloques A, B y C fueron aplicadas con rigor técnico, sin inventar datos ni referencias, preservando las etiquetas (`\label`) y claves de citación (`\cite`).

### Verificación de Consistencia Numérica y Métricas
- **Distribución de alertas (Total = 77):**
  - Positivos reales (*Ground Truth Positives*): **11**
  - Negativos reales (*Ground Truth Negatives* / Espurias reales): **66**
  - Clasificación PyReach:
    - `REACHABLE`: **11** (Verdaderos Positivos, TP = 11)
    - `POTENTIALLY_REACHABLE`: **3** (Falsos Positivos conservadores en compuerta CI/CD, FP = 3)
    - `NOT_REACHABLE`: **63** (Verdaderos Negativos, TN = 63)
    - Falsos Negativos observados: **0** (FN = 0)
    - Suma: $11 + 3 + 63 = 77$
- **Métricas derivadas:**
  - **Precisión:** $\frac{TP}{TP + FP} = \frac{11}{11 + 3} = \frac{11}{14} \approx 78.57\% \to \mathbf{78.6\%}$ (frente a $11/77 = 14.3\%$ en SCA tradicional, mejora de $\mathbf{5.5\times}$).
  - **Especificidad:** $\frac{TN}{TN + FP} = \frac{63}{63 + 3} = \frac{63}{66} \approx 95.45\% \to \mathbf{95.5\%}$.
  - **Reducción del total de alertas manifiestas:** $\frac{63}{77} \approx 81.81\% \to \mathbf{81.8\%}$ (63 de 77 alertas descartadas).
  - **Exhaustividad (*Recall*):** $\frac{TP}{TP + FN} = \frac{11}{11 + 0} = \mathbf{100.0\%}$ en el benchmark evaluado (11 positivos).
  - **Intervalo de Confianza exacto (Clopper-Pearson, 95%):** Calculado mediante la distribución Beta (`scipy.stats.beta.ppf(0.025, 11, 1)`):
    $$p_L = (0.025)^{1/11} \approx 0.7151 \implies \mathbf{[0.715, 1.000]} \quad (71.5\% - 100.0\%)$$
  - **Valor F1:** $2 \cdot \frac{0.7857 \cdot 1.000}{0.7857 + 1.000} \approx 0.8800 \to \mathbf{88.0\%}$.
- **Evaluación multicriterio de persistencia (Sección V-B y Fig. 5):**
  - $\text{Score}_{\text{SQLite}} = 1.50 + 1.25 + 1.25 + 0.80 = \mathbf{4.80} / 5.00$ (sin cambios, seleccionada).
  - $\text{Score}_{\text{DuckDB}} = 1.20 + 0.75 + 1.25 + 0.80 = \mathbf{4.00} / 5.00$ (corregido de 3.95).
  - $\text{Score}_{\text{TinyDB}} = 0.60 + 1.25 + 1.00 + 0.40 = \mathbf{3.25} / 5.00$ (corregido de 3.30).
- **Rendimiento temporal:**
  - Presupuesto máximo CI/CD: 45 s.
  - Tiempo E2E en `MS-Analytics`: 1.612 s.
  - Aceleración: $45 / 1.612 \approx \mathbf{27.9\times}$ (corregido de 28×). Tiempos 1.18 s (frío) y 0.84 s (caliente) identificados como propios de `MS-Analytics`.

---

## 2. Detalle de Cambios por Bloque y Sección

### BLOQUE A. Errores Objetivos

#### A1. Evaluación Multicriterio de Persistencia (Sección V-B y Figura 5)
- **Ubicación:** Líneas 540–541, 566–575 en `.tex`.
- **Texto Antes:**
  ```latex
  \text{Score}_{\text{DuckDB}} &= 1.20 + 0.75 + 1.25 + 0.80 = \mathbf{3.95} / 5.00 \\
  \text{Score}_{\text{TinyDB}} &= 0.60 + 1.25 + 1.00 + 0.40 = \mathbf{3.30} / 5.00
  ...
  % DuckDB (Gris / 3.95)
  \node[bar, fill=gray!60, minimum width=3.95cm] at (0, 1.4) {};
  \node[val, color=gray!80!black] at (4.00, 1.4) {3.95 / 5.0};
  % TinyDB (Naranja / 3.30)
  \node[bar, fill=orange!70, minimum width=3.30cm] at (0, 0.5) {};
  \node[val, color=orange!80!black] at (3.35, 0.5) {3.30 / 5.0};
  ```
- **Texto Después:**
  ```latex
  \text{Score}_{\text{DuckDB}} &= 1.20 + 0.75 + 1.25 + 0.80 = \mathbf{4.00} / 5.00 \\
  \text{Score}_{\text{TinyDB}} &= 0.60 + 1.25 + 1.00 + 0.40 = \mathbf{3.25} / 5.00
  ...
  % DuckDB (Gris / 4.00)
  \node[bar, fill=gray!60, minimum width=4.00cm] at (0, 1.4) {};
  \node[val, color=gray!80!black] at (4.05, 1.4) {4.00 / 5.0};
  % TinyDB (Naranja / 3.25)
  \node[bar, fill=orange!70, minimum width=3.25cm] at (0, 0.5) {};
  \node[val, color=orange!80!black] at (3.30, 0.5) {3.25 / 5.0};
  ```
- **Motivo:** Corrección de la suma aritmética ponderada ($1.20+0.75+1.25+0.80 = 4.00$; $0.60+1.25+1.00+0.40 = 3.25$) y ajuste geométrico de las barras y rótulos en la Figura 5 de TikZ.

#### A2. Referencia a Línea de Corte en Algoritmo 2 (Sección IV-D)
- **Ubicación:** Línea 406 en `.tex`.
- **Texto Antes:** `En la línea 10 del Algoritmo 2, el corte se comprueba con $d \ge k$ antes de abrir los sucesores del nodo $v$.`
- **Texto Después:** `En la línea 12 del Algoritmo \ref{alg:bounded_bfs}, el corte se evalúa mediante la condición $d \ge k$ antes de expandir los sucesores del nodo $v$, evitando encolar nodos con distancia $d=k+1$ ($d=6$ cuando $k=5$) y conteniendo el radio de exploración en grafos densos.`
- **Motivo:** En la estructura real del pseudocódigo en LaTeX, la comprobación `if d >= k` se sitúa en la línea 12 (verificado en el PDF compilado).

#### A3. Ratio de Rendimiento Temporal y Tiempos de MS-Analytics
- **Ubicación:** Abstract (línea 47), Resumen (línea 59), Sección V-D (línea 661), Conclusiones (línea 725).
- **Texto Antes:**
  - "28 veces", "$28\times$ más veloz"
  - "latencias de 1.18 s en frío y 0.84 s en caliente" (sin aclarar servicio).
- **Texto Después:**
  - "$\approx 27.9\times$ (45~s / 1.612~s)"
  - "latencias en el servicio más demandante (\texttt{MS-Analytics}) de 1.18~s en frío y 0.84~s en caliente".
- **Motivo:** Exactitud aritmética del ratio temporal ($45 / 1.612 = 27.9156\dots$) y precisión sobre el origen de los tiempos de 1.18 s y 0.84 s (pertenecientes a `MS-Analytics` en la Tabla V, no un promedio general).

#### A4. Rotulado de Idioma y Eliminación de Término Residual
- **Ubicación:** Bloque inicial (líneas 44–64), Sección V-A (línea 496).
- **Texto Antes:**
  - Bloque en inglés renderizaba como `Resumen—...` debido a la configuración de `babel[spanish]`.
  - Encabezado manual `RESUMEN` centrado.
  - "expanded benchmark suite", "Banco de Pruebas Extendido".
- **Texto Después:**
  - `\renewcommand{\abstractname}{Abstract}` y `\renewcommand{\IEEEkeywordsname}{Index Terms}` colocados antes de `\begin{abstract}` para garantizar que el bloque en inglés se rotule como `Abstract—` e `Index Terms—`.
  - Bloque en español rotulado con `\noindent\textbf{\textit{Resumen---}}` y `\noindent\textbf{\textit{Palabras clave---}}`.
  - Eliminado "expanded" / "Extendido" residual ("benchmark suite", "Banco de Pruebas").
- **Motivo:** Cumplimiento estricto del estándar IEEE para artículos con doble resumen en español e inglés y consistencia terminológica.

#### A5. Especificación de PEP 503 vs. PEP 440
- **Ubicación:** Contribuciones (línea 83), Fig. 1 (línea 157), Fig. 2 (línea 197), Sección III-C (línea 235, 239).
- **Texto Antes:** "índices B-Tree según PEP 503", "normalización PEP 503" para rangos.
- **Texto Después:** Distinción explícita: PEP 503 reservado exclusivamente para la normalización canónica de nombres de paquetes; PEP 440 especificado para la comparación, resolución y ordenamiento de versiones e intervalos afectados (`packaging.version`).
- **Motivo:** Rigor en estándares Python: PEP 503 normaliza nombres simples en repositorios; la especificación de esquemas de versionado y especificadores semánticos corresponde a PEP 440.

#### A6 y A4b. Terminología de Reducción, Especificidad y Cota de Recall
- **Ubicación:** Abstract, Resumen, Introducción (contribuciones), Tabla I, Tabla IV, Sección V-C, Conclusiones.
- **Texto Antes:** "poda de alertas espurias 81.8%", "recall 100% / exhaustividad del 100.0%".
- **Texto Después:** "reducción del 81.8% del total de alertas manifiestas (63 de 77; especificidad del 95.5%, descartando 63 de 66 alertas espurias reales)"; "exhaustividad del 100.0% en el benchmark evaluado (11 positivos)". Se mantuvo el rango por proyecto (80.0%–87.5%) con `\todo` para desglose.
- **Motivo:** Precisión estadística: 63/77 es la tasa de reducción global del total de alertas reportadas por manifiestos; sobre las 66 espurias reales, la tasa de eliminación es la especificidad del clasificador ($63/66 = 95.5\%$). Asimismo, se aclara que el recall de 100% está acotado al tamaño del oráculo analizado.

---

### BLOQUE B. Correcciones de Contenido

#### B1. Soundness y Formulación Empírica Conservadora
- **Ubicación:** Todo el documento (Abstract, Resumen, Intro, Sec IV-E, Tabla IV, Sec V-C, Sec VI-C, Conclusiones).
- **Texto Antes:** "strict soundness", "soundness estricta", "cero omisiones críticas", "garantiza", "certeza matemática". Fila de Tabla IV: `0 (Strict Soundness)`.
- **Texto Después:**
  - Sustituido por formulaciones empíricas: "ningún falso negativo observado en el benchmark (11/11)" y "diseño conservador (sobre-aproximación ante construcciones dinámicas)".
  - Fila en Tabla IV cambiada a: `\textbf{0} (\textit{observado})`.
  - Sección VI-C (Validez de constructo): reescrito como: *"la ausencia de ruta indica que no se encontró camino bajo el modelo de grafo construido, no una garantía formal de inalcanzabilidad"*.
  - Sección VI-C (Validez interna): agregada lista taxativa de fuentes de incompletitud: (1) cota $k=5$; (2) módulos compilados en extensiones C/Cython; (3) delimitación de entrypoints a `__main__`, scripts de consola y decoradores de rutas web (omitiendo Celery, señales, plugins y entry points de librerías); (4) código a nivel de módulo ejecutado al importar; (5) inyección de dependencias en frameworks como FastAPI; y (6) despacho polimórfico `obj.method()` sin inferencia estática de tipos.
  - Intervalo de confianza de Clopper-Pearson al 95%: incorporado explícitamente como $[0.715, 1.000]$ (calculado con `scipy.stats.beta` para 11/11).
- **Motivo:** Ningún análisis estático para Python puede garantizar solidez matemática estricta sin incurrir en falacias teóricas. La redacción refleja honestidad metodológica y rigor formal.

#### B2. Algoritmo 2: Caso Entrypoint No Resuelto ($u \notin V$) y Banderas de Dinamismo
- **Ubicación:** Algoritmo 2 (líneas 366–368) y Sección IV-F.
- **Texto Antes:**
  ```latex
  \IF{$u \notin V$}
      \RETURN $(\text{NOT\_REACHABLE}, \emptyset, \mathbf{false}, \mathbf{false})$
  \ENDIF
  ```
- **Texto Después:**
  ```latex
  \ENSURE Veredicto $\in \{\text{REACHABLE}, \dots\}$, testigo $P$, banderas $(\mathit{dyn\_edge}, \mathit{cut\_depth}, \mathit{unresolved\_entry})$.
  \IF{$u \notin V$}
      \RETURN $(\text{POTENTIALLY\_REACHABLE},$ \\ \hspace*{2.2em} $\emptyset, \mathbf{false}, \mathbf{false}, \mathbf{true})$
  \ENDIF
  ```
  En la explicación de IV-F se aclara: (1) que devolver `POTENTIALLY_REACHABLE` cuando $u \notin V$ previene falsos negativos derivados de fallos en el análisis sintáctico del entrypoint; (2) que las banderas $\mathit{dyn\_edge}$ y $\mathit{cut\_depth}$ se activan ante cualquier nodo visitado durante la exploración del componente, lo que constituye una política deliberada de sobre-aproximación ante incertidumbres estructurales.
- **Motivo:** Asumir que un objetivo es inalcanzable cuando ni siquiera se pudo resolver el nodo raíz del entrypoint es una condición insegura que viola el principio conservador.

#### B3. Complejidad Computacional de BFS Acotado
- **Ubicación:** Sección IV-D (línea 358).
- **Texto Antes:** `Una exploración ciega dispararía el espacio de estados a $O(b^d)$ al instante \cite{nielson1999principles}.`
- **Texto Después:** `Si bien un recorrido en anchura estándar con conjunto de visitados opera en tiempo lineal $O(|V| + |E|)$, la cota de profundidad $k=5$ no se introduce para evitar una explosión combinatoria exponencial clásica, sino para acotar el tiempo de cómputo sobre grafos densos y limitar la proliferación de clasificaciones ambiguas (\texttt{POTENTIALLY\_REACHABLE}) originadas por construcciones dinámicas lejanas en dependencias profundas \todo[color=orange]{DATO REQUERIDO: Aportar justificación empírica formal de la cota k=5 sobre grafos densos y distribución de llamadas}. Asimismo, el control de nodos visitados previene ciclos recursivos en el grafo (Algoritmo \ref{alg:bounded_bfs}).`
- **Motivo:** En grafos con control de estados visitados, la complejidad de BFS es $O(|V| + |E|)$, no exponencial $O(b^d)$. La cota $k$ tiene un propósito de control de latencia en dependencias densas y limitación de propagación de dinamismo.

#### B4. Grafo de Llamadas, Polimorfismo y Aristas Concurrentes
- **Ubicación:** Introducción (línea 81), Sección IV-A (línea 294), Sección IV-B (línea 344).
- **Texto Antes:** "Resuelve símbolos, cadenas de herencia y polimorfismo". Definición formal de aristas incluye $\text{IMPORT}$ sin pasadas de construcción. No menciona aristas paralelas en DiGraph.
- **Texto Después:**
  - Matizado: resuelve herencia y enlaces estáticos en módulos; no resuelve despacho polimórfico en receptores dinámicos al vuelo.
  - Insertado `\todo` respecto a si el tipo $\text{IMPORT}$ en $\Omega$ se genera en alguna pasada o debe eliminarse de la tupla formal.
  - Insertado `\todo` indicando que `networkx.DiGraph` admite una única arista dirigida por par $(u, v)$ y requiriendo especificar la política ante aristas concurrentes (¿conservar mayor certeza $c$ o migrar a `MultiDiGraph`?).
- **Motivo:** Precisión en la teoría de tipos y en las restricciones de la estructura de datos utilizada en la implementación.

#### B5. Tabla I: Coherencia de Falsos Positivos y Línea Base
- **Ubicación:** Tabla I (líneas 112–113) y Sección II-D (línea 122).
- **Texto Antes:** Tasa de FP para SaaS "<15% alertas espurias"; PyReach "Muy baja (poda determinista $\ge 80\%$)".
- **Texto Después:**
  - SaaS: `Baja \todo[color=orange]{DATO REQUERIDO: Cita o medición empírica comparable de la tasa de falsos positivos en escáneres SaaS en Python}`.
  - PyReach: `Reducción del 81.8\% del total de alertas (precisión 78.6\%, especificidad 95.5\%)`.
  - Insertado `\todo` solicitando incorporar una línea base cuantitativa de alcanzalibidad (e.g. PyCG/JARVIS + OSV) y una tabla por proyecto con TP, FP, TN, FN.
- **Motivo:** PyReach reporta una precisión del 78.6% (21.4% de alertas emitidas en compuerta CI/CD son FP/ambiguas), por lo que contrastarlo con un "<15%" atribuido a SaaS sin medición ni cita generaba una contradicción técnica.

#### B6. Análisis de Sensibilidad de $k$ y Riesgo de Sobreajuste
- **Ubicación:** Sección V-E (línea 664) y Sección VI-C.
- **Texto Antes:** Presentaba $k=5$ como óptimo absoluto sin limitaciones metodológicas.
- **Texto Después:** Se declara explícitamente que $k=5$ fue seleccionado sobre los mismos 11 casos positivos que se evalúan, identificándolo como una limitación con riesgo de sobreajuste (*overfitting*). Se agregó un `\todo` exhaustivo solicitando histograma de caminos testigo, validación en conjunto separado, aclaración sobre por qué los nodos explorados (hasta 5,840) superan el total de nodos (2,141), y qué dominó los 14.8 s con $k=\infty$.
- **Motivo:** Rigor metodológico en evaluación de hiperparámetros.

#### B7. Plausibilidad de Recursos y Módulos Analizados
- **Ubicación:** Sección V-D (línea 661).
- **Texto Antes:** No explicaba cómo un servicio como `MS-Analytics` con Pandas y Scikit-learn produce únicamente $|V|=421$ nodos, ni cómo se midió la memoria de 7.24 MB.
- **Texto Después:** Se incorporó un `\todo` solicitando aclarar: (a) qué módulos de `site-packages` se analizan realmente; (b) método de medición de memoria (tracemalloc, RSS o solo grafo); (c) equivalencia entre Tiempo Net. y E2E; (d) completar los 4 servicios omitidos en la Tabla V; y (e) especificar qué plataforma de hardware/SO produjo cada tabla.
- **Motivo:** Evitar objeciones de revisores expertos respecto a la representatividad y reproducibilidad de las mediciones de memoria y grafos en bibliotecas científicas de Python.

#### B8. Origen de Símbolos Vulnerables en SQLite OSV
- **Ubicación:** Sección III-C (línea 239).
- **Texto Después:** Se añadió un párrafo formal con `\todo` señalando que el esquema OpenSSF OSV para PyPI rara vez estructura funciones vulnerables, solicitando explicar el procedimiento de población de `vulnerable_functions` y el tratamiento de CVEs sin símbolo declarado.
- **Motivo:** Transparencia en la construcción de la base de conocimiento de seguridad.

#### B9. Protocolo de Auditoría del Ground Truth
- **Ubicación:** Sección V-C (línea 585) y Sección VI-C (Validez externa).
- **Texto Después:**
  - En V-C: se insertó `\todo` para documentar el acuerdo inter-evaluador (kappa de Cohen), protocolo formal de desempate y disponibilidad de repositorios, commits y CVEs.
  - En VI-C: se añadió la limitación explícita de que 6 de los 8 proyectos evaluados son internos y propietarios de Lidercom Perú S.A.C., lo que restringe la reproducibilidad externa directa.
- **Motivo:** Buenas prácticas de ingeniería de software empírica.

#### B10. Marco Normativo ISO/IEC 27001:2022
- **Ubicación:** Abstract (línea 45), Resumen (línea 59), Introducción (línea 70), Tabla I (línea 112), Sección V-F (línea 698).
- **Texto Antes:** Afirmaba que ISO/IEC 27001 prohíbe las herramientas SaaS en la nube de forma taxativa.
- **Texto Después:** Se reformuló indicando que la restricción proviene de la política interna de seguridad de Lidercom Perú S.A.C., derivada de su análisis de riesgos y alineada con los controles A.8.8, A.8.12 y A.8.28. Se suavizó la exigencia de transferencia de código ("muchos servicios SaaS requieren...").
- **Motivo:** La norma ISO/IEC 27001 no prohíbe tecnologías per se, sino que exige gestión de riesgos de acuerdo con los controles organizacionales.

#### B11. Impacto Operacional y Causalidad de Breaking Changes
- **Ubicación:** Sección VI-A (línea 707).
- **Texto Antes:** "10 h a <1.5 h semanales", "breaking changes bajaron a cero en producción", con atribución causal directa a PyReach.
- **Texto Después:** Reformulado como observaciones cualitativas preliminares reportadas por los desarrolladores con `\todo` para metodología de medición formal (muestra $n$, periodo de observación, instrumentos). Se eliminó la atribución causal exclusiva de breaking changes = 0 a PyReach, agregando `\todo` para métricas objetivas.
- **Motivo:** Un analizador estático no bloquea cambios de versión per se ni puede reclamar causalidad directa en la ausencia de errores en producción sin un diseño experimental controlado.

#### B12. Limitaciones de Completitud en PyCG
- **Ubicación:** Sección II-A (línea 93).
- **Texto Después:** Se introdujo la limitación de exhaustividad (*recall*) de PyCG ante patrones dinámicos complejos con `\todo` para verificar la cifra reportada en la literatura y su respectiva cita.
- **Motivo:** Evitar citas imprecisas de memoria y contextualizar adecuadamente el estado del arte.

#### B13. Verificación de Referencias Bibliográficas
- **Ubicación:** `referencias.bib` y menciones en `articulo_ieee.tex`.
- **Acción:**
  - En `referencias.bib`: se agregaron comentarios `% VERIFICAR` sobre las 9 referencias observadas sin alterar los campos bibliográficos.
  - En `articulo_ieee.tex`: se añadieron marcadores `\todo` junto a las citas correspondientes:
    1. Ref. [3] (`ladisa2023sok`): verificar respaldo de fuga de IP en SaaS.
    2. Ref. [6] (`pashchenko2022vuln4real`): verificar evidencia del 80%–90% en Python (paper enfocado en Java).
    3. Ref. [14] (`sadowski2018lessons`): verificar respaldo de las 10 h de triaje en Lidercom (paper de Google).
    4. Ref. [26] (`bhandari2022cvefixes`): verificar uso para difusión de código dañino y demora de parches.
    5. Refs. [7] (`dann2021identifying`), [8] (`duan2023towards`), [10] (`prana2022empirical`), [12] (`gutierrez2024auditoria`), [25] (`alexopoulos2026cross`): verificar existencia, título y venue.
- **Motivo:** Garantizar la integridad documental y prevenir alucinaciones de citas académicas.

---

### BLOQUE C. Estilo y Registro Académico

Se reemplazaron todas las expresiones coloquiales, enfáticas o fragmentadas por construcciones gramaticales técnicas en voz académica (primera persona del plural: *nosotros* / *evaluamos* / *presentamos*):

| Texto Original (Coloquial / Fragmentado) | Texto Corregido (Registro Académico Neutro) | Sección / Línea |
|---|---|---|
| "El desarrollo en Python descansa sobre paquetes ajenos." | "El desarrollo de software en Python depende extensamente de paquetes de terceros..." | Resumen / L60 |
| "Son falsas alarmas." | "...generando entre un 80% y un 90% de alertas espurias sobre rutinas transitivas inactivas." | Resumen / L60 |
| "Para desarmar este nudo creamos PyReach..." | "En este trabajo presentamos \textit{PyReach}..." | Resumen / L60 |
| "Mucho. Más del 80%..." | "...representan más del 80% del código ejecutable integrado en tuberías de CI/CD modernas..." | Intro / L66 |
| "Los riesgos viajan en paquetes ajenos. Nadie está a salvo." | "...facilitando la propagación de vulnerabilidades conocidas (CVE) a través de la cadena de suministro..." | Intro / L66 |
| "Solo cotejan versiones. Dan por sentado, sin embargo, algo falso..." | "...operan inspeccionando exclusivamente manifiestos declarativos y comparando cadenas de versiones, asumiendo implícitamente..." | Intro / L68 |
| "Rutinas muertas. Jamás corren en el servidor. Son simples alertas fantasma." | "...constituyendo código inerte que nunca llega a ejecutarse en producción." | Intro / L68 |
| "O esquemas sintácticos completos. Por culpa de esa restricción..." | "...debido a que muchos servicios SaaS requieren transferir código fuente o representaciones intermedias a servidores externos..." | Intro / L70 |
| "Descartaban falsas alarmas a mano. El desgaste era evidente." | "...reportó dedicar aproximadamente 10 horas semanales al triaje manual de falsas alarmas..." | Intro / L70 |
| "Registros abiertos y públicos. Así se verifica..." | "...se confronta contra una base de datos local de OpenSSF OSV para determinar la alcanzabilidad estática..." | Intro / L77 |
| "En Python, al contrario, la cosa va así... El código cambia en plena marcha. Todo es mutable." | "Por el contrario, en Python características dinámicas tales como la introspección reflexiva, el despacho tardío, decoradores dinámicos..." | Sec II-A / L91 |
| "Nada sale del servidor local. Cero fugas." | "...al ejecutar el análisis íntegramente en infraestructura local sin transferencia externa de datos." | Sec II-D / L122 |
| "Los datos fluyen sin tropiezos. Van desde... Es un cauce ordenado." | "...conduciendo los artefactos desde la lectura inicial de dependencias hasta la clasificación tri-estado y el veredicto final." | Sec III-B / L184 |
| "Buscábamos consultas ágiles. Sin salir a internet." | "Con el propósito de lograr consultas eficientes sin conectividad externa, estructuramos el repositorio..." | Sec III-C / L232 |
| "Todo en disco local. Es un tiro veloz." | "...permitiendo evaluar 50 dependencias en menos de 10~ms en almacenamiento local." | Sec III-C / L239 |
| "Cero contacto externo. Tan solo una tarea programada... Nada más que eso." | "...sin requerir servicios en la nube; periódicamente, una tarea programada actualiza la base de datos local..." | Sec III-D / L242 |
| "Resolver llamadas cruzadas exige orden. Mucho rigor. No hay atajos." | "La resolución de llamadas interprocedimentales requiere un procesamiento estructurado en múltiples etapas." | Sec IV-B / L298 |
| "Son las puertas de acceso." | "...representan las raíces del flujo de ejecución del aplicativo." | Sec IV-C / L349 |
| "Muy tupidas. Una exploración ciega dispararía..." | "...el recorrido interprocedimental afronta un volumen considerable de aristas. Si bien un recorrido en anchura estándar..." | Sec IV-D / L358 |
| "Todo marcha en orden." | "...conteniendo el radio de exploración en grafos densos." | Sec IV-D / L406 |
| "No reviste peligro. En cambio... Esa alerta cae por su propio peso. No requiere revisión manual." | "...resulta alcanzable pero inocua; la ruta hacia el símbolo vulnerable... representa una alerta crítica confirmada... y la función vulnerable... es podada de forma concluyente..." | Sec IV-E / L409 |
| "Son piezas reales." | "...conformando un banco experimental de 8 microservicios y proyectos... correspondientes a casos de uso reales." | Sec V-A / L498 |
| "No tenía sentido." | "...resultaban incompatibles con un runner ligero y aislado." | Sec V-B / L527 |
| "Ganó con margen." | "...superando a las alternativas evaluadas tanto en latencia por clave como en portabilidad nativa." | Sec V-B / L543 |
| "Un volumen considerable." | "...reportó un total agregado de 77 alertas de vulnerabilidad (CVE)." | Sec V-C / L583 |
| "Dos ingenieros sénior examinaron a fondo cada caso. Hicieron una auditoría minuciosa..." | "Dos ingenieros sénior llevaron a cabo una auditoría manual independiente analizando el código fuente, trazando las secuencias de importación..." | Sec V-C / L585 |
| "El analizador atrapó las 11 vulnerabilidades reales sin dejar escapar una sola. Ni una." | "El analizador identificó las 11 vulnerabilidades reales (11 positivos, 11/11), logrando un recall del 100.0% en el conjunto evaluado..." | Sec V-C / L625 |
| "Basura operacional." | "...carecían de viabilidad de ejecución en los proyectos analizados." | Sec V-C / L627 |
| "Ese era el límite admitido." | "La infraestructura de integración continua en Lidercom Perú S.A.C. estableció un presupuesto temporal máximo..." | Sec V-D / L631 |
| "Un margen enorme. Es un consumo mínimo." | "...lo cual representa una aceleración de $\approx 27.9\times$... facilitando la ejecución en contenedores y GitLab Runners..." | Sec V-D / L661 |
| "No fue un capricho. Tenía sustento numérico." | "La parametrización de la cota k=5 en el Algoritmo 2 se fundamentó en una evaluación empírica de sensibilidad." | Sec V-E / L664 |
| "Son rutas cortas." | "...dado que las cadenas de llamadas interprocedimentales analizadas no superaron cuatro saltos efectivos." | Sec V-E / L693 |
| "Es el punto justo." | "...validando que k=5 preserva la viabilidad operativa en CI/CD para este corpus." | Sec V-E / L695 |
| "Cero paquetes." | "...se verificó la transmisión de cero bytes (0 KB) hacia redes externas durante las fases de análisis y generación de reportes." | Sec V-F / L701 |
| "Hubo mejoras claras... Ya no hay fatiga frente a avisos inútiles. El equipo respira." | "La adopción de PyReach en los flujos de integración continua modificó la operativa del equipo de ingeniería. Según observaciones preliminares..." | Sec VI-A / L707 |

---

## 3. Estado de Compilación y Artefactos

- **Compilador:** `pdfTeX 3.141592653-2.6-1.40.29` (MiKTeX 26.5) con `latexmk` versión 4.88.
- **Salida:** `PyReach/Article/build/articulo_ieee.pdf` (12 páginas).
- **Log de compilación:** 0 errores fatales, todas las referencias cruzadas y bibliográficas resueltas correctamente.
