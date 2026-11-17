# Inventario de figuras

Los assets de marca, portadas y fondos de apps/web son ilustraciones de interfaz, no evidencia científica. No se incorporan. No se crearon imágenes artificiales ni se regeneraron curvas. Sólo la ECDF E1 se incorpora en esta entrega; inspeccionada visualmente. Las demás son candidatas pendientes de lectura visual y cotejo específico de ejes antes de publicarse.

| Archivo (ruta desde raíz) | Sección | Representación, ejes y parámetros | Universo y límites |
|---|---|---|---|
| `reports/figures/E1/e1_letras_por_decada.png` | 04 | Barras: x década de year; y letras; años 1900–2022 | Metadato de fuente; excluye años dudosos; décadas no equilibradas |
| `reports/figures/E1/e1_longitud_letras.png` | 04 | Histograma de palabras por letra; x logarítmico, y letras; 70 bordes logarítmicos | Corpus canónico completo; cola y mediana; no prueba normalidad |
| `reports/figures/E1/e1_longitud_por_tag.png` | 04 | ECDF: x palabras por letra logarítmico; y proporción acumulada [0,1]; colores cinco tags; línea y=0,5 | Corpus completo por tag; no prueba significancia ni género validado |
| `reports/figures/E1/e1_repeticion_por_tag.png` | 04/05 | Distribución de proporción de versos repetidos; x [0,1]; series por tag | Corpus completo; depende del transcriptor; revisar unidades y barras antes de incluir |
| `reports/figures/E2/e2_difusion_repeticion.png` | 05 | x % letras con palabra; y ocurrencias por letra que la usa; escalas log; categorías | Palabras con ≥100000 ocurrencias, no todo vocabulario |
| `reports/figures/E2/e2_espectro.png` | 05 | Espectro V(m) por orden; frecuencias m≤200 | Corpus completo; sólo intervalo visible, no toda la cola |
| `reports/figures/E2/e2_logodds_tags.png` | 05 | Barras z de log-odds por tag contra resto; prior 10000; contenido ≥1000 | Corpus completo; prior descriptivo; etiquetas y desbalance condicionan contraste |
| `reports/figures/E2/e2_perplejidad_tags.png` | 05/10 | x tag; y perplejidad; curvas órdenes 2/3/4 KenLM | Ajuste train y evaluación validation con finales de verso; no relevancia |
| `reports/figures/E2/e2_top_palabras_politicas.png` | 05 | Ranking de frecuencias bajo tres políticas de filtrado | Corpus completo; lista de stopwords/vocablos modifica universo retenido |
| `reports/figures/E2/e2_zipf.png` | 05 | Rango–frecuencia; ajustes logarítmicos Zipf y Mandelbrot | Uni/bi/trigramas completos; tramos de ajuste distintos; R² no prueba ley universal |
| `reports/figures/E3/pos_decadas.png` | 06 | Evolución descriptiva POS por década y tag | Años válidos; umbral de soporte; no causalidad |
| `reports/figures/E3/pos_global.png` | 06 | Barras POS global; conteos y porcentajes en notebook | Tokens spaCy; especificar denominador al seleccionar |
| `reports/figures/E3/pos_tags.png` | 06 | Mapa de calor POS por tag | Excluir PUNCT/SYM/SPACE según código; no exactitud de anotación |
| `reports/figures/E4/arbol_coordination.png` | 07 | Árbol cabeza→dependiente; etiquetas de dependencia, token, POS e índice; sin ejes numéricos | Cuatro casos dirigidos del shard 0; ver e4_examples.json; no precisión del parser |
| `reports/figures/E4/arbol_fragment.png` | 07 | Árbol cabeza→dependiente; etiquetas de dependencia, token, POS e índice; sin ejes numéricos | Cuatro casos dirigidos del shard 0; ver e4_examples.json; no precisión del parser |
| `reports/figures/E4/arbol_subordinate.png` | 07 | Árbol cabeza→dependiente; etiquetas de dependencia, token, POS e índice; sin ejes numéricos | Cuatro casos dirigidos del shard 0; ver e4_examples.json; no precisión del parser |
| `reports/figures/E4/arbol_transitive.png` | 07 | Árbol cabeza→dependiente; etiquetas de dependencia, token, POS e índice; sin ejes numéricos | Cuatro casos dirigidos del shard 0; ver e4_examples.json; no precisión del parser |
| `reports/figures/E4/comparacion_decadas.png` | 07 | Métricas sintácticas por década y tag | Años válidos y composición variable; no seguimiento longitudinal |
| `reports/figures/E4/comparacion_tags.png` | 07 | Métricas sintácticas por tag | Medias por segmento y por arco; no complejidad artística |
| `reports/figures/E4/distribuciones.png` | 07 | Histogramas de longitud sin puntuación y profundidad | Segmentos completos; truncamiento visual declarado; medias no truncadas |
| `reports/figures/E5/pca_validation.png` | 08 | PCA: x componente 1, y componente 2; colores por tag; dos componentes | Muestra 2000 validation; 23,323 % y 9,852 % de varianza; no calidad semántica |

## Imágenes incrustadas y procedencia de celdas

Celdas base cero. El código íntegro de cada celda está en auditoria_notebooks.json y permite recuperar límites, leyenda y parámetros. No se presupone identidad binaria entre el PNG externo y el incrustado.
- `notebooks/evidencias/E1_construccion_exploracion.ipynb`, celda 27, output 0: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E1_construccion_exploracion.ipynb`, celda 28, output 0: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E1_construccion_exploracion.ipynb`, celda 29, output 0: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E1_construccion_exploracion.ipynb`, celda 30, output 0: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb`, celda 6, output 0: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb`, celda 15, output 0: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb`, celda 17, output 1: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb`, celda 20, output 0: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb`, celda 23, output 0: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb`, celda 26, output 1: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E3_morfosintaxis.ipynb`, celda 3, output 1: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E3_morfosintaxis.ipynb`, celda 5, output 6: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E3_morfosintaxis.ipynb`, celda 5, output 7: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E4_sintaxis_dependencias.ipynb`, celda 3, output 0: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E4_sintaxis_dependencias.ipynb`, celda 5, output 2: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E4_sintaxis_dependencias.ipynb`, celda 5, output 3: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E4_sintaxis_dependencias.ipynb`, celda 7, output 4: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E4_sintaxis_dependencias.ipynb`, celda 7, output 8: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E4_sintaxis_dependencias.ipynb`, celda 7, output 12: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E4_sintaxis_dependencias.ipynb`, celda 7, output 16: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E5_semantica.ipynb`, celda 5, output 1: PNG guardado; parámetros y fuente de datos en esa celda.

La copia seleccionada es figuras/e1_longitud_por_tag.png, procedente de reports/figures/E1/e1_longitud_por_tag.png; E1 celda 28. El hash de copia se registra en verificacion_entrega.json. La figura E5 procede de packages/sonora/src/sonora/nlp/semantic_analysis.py y e5_analysis.json, y también está incrustada en E5_semantica.ipynb, celda 5.
