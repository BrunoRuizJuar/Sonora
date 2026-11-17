# Continuación — API de recomendación textual e integración web

## Continuación implementada (2026-11-16)

### Ampliación posterior: letras frente a frente

Solicitud adicional del usuario implementada: sección con la letra original de
partida y la del resultado seleccionado, dos columnas en escritorio y paneles
apilados en móvil, manteniendo versos/estrofas y scroll independiente.
Acceso: «Comparar letras» en cada tarjeta o «Ver letras lado a lado» en su detalle.
Para texto libre, el panel izquierdo conserva la consulta. Cambiar de semilla
limpia la comparación; cerrar/cambiar de selección cancela cargas anteriores.

Nuevo endpoint `GET /api/v1/tracks/{track_id}/lyrics`; índice local completo en
`artifacts/releases/lyrics-original-v1/lyrics.sqlite`, construido con
`scripts/build_lyric_index.py`. Guarda ubicaciones por ID y grupo Parquet;
no copia/reconstruye letras ni repite PLN. Constructor comprueba hashes contra
inputs E5; lectura comprueba identidad y que el original no cambió.
`SONORA_LYRIC_INDEX` configurable. Sin índice responde 503 sólo esta ruta;
recomendaciones continúan disponibles. Guía ampliada en `docs/API_TEXTO_WEB.md`.

Verificación posterior: **53 passed**; Edge escritorio 1440/móvil 390, ambas
letras reales verificadas contra API, consulta libre, cierre y disposición de
paneles. Sin errores JS ni overflow. Capturas `runtime/text_lyrics_{1440,390}.png`.
Servidor local reiniciado con la ampliación, mismo puerto 8010. Sin commit/push.

### Integración previa

El plan de abajo se conserva como contexto histórico. **API textual y conexión web
ya implementadas y verificadas**. Guía vigente: `docs/API_TEXTO_WEB.md` y
`apps/web/docs/CONECTAR_RECOMENDADOR.md`. Arranque conjunto:
`scripts/Start-SONORA-Web.ps1`, http://127.0.0.1:8010/ (un worker, mismo origen).

- Release local `artifacts/releases/lyrics-serving-v1`: 3 155 772 letras,
  128 dimensiones, 5 091 268 993 bytes aprox. SQLite FTS5, metadatos, vectores
  float32 y CSR mapeados; incluye vocabulario/IDF y vectores de palabras congelados.
  Constructor reanudable `scripts/build_text_release.py`; no reentrenó ni exportó E5.
- API `/api/v1`: salud, readiness, estadísticas/capacidades, búsqueda de título/artista,
  detalle, ranking por exactamente `track_id` o `text`. `track_id=lyrics_id` como
  alias de letra canónica, sin correspondencia verificada a grabación/FMA.
- Ranking exacto SGNS o TF-IDF, sin fusión/LDA. Semilla/no disponibles excluidos,
  splits explícitos, top_k 1–50, límite por artista y términos compartidos reales.
  La web usa todo el catálogo; protocolo experimental conserva validation→train.
- Web existente conectada por fetch; escritorio/móvil, guardados locales persistentes,
  detalle, errores/OOV/503 y texto libre. Sin muestras, portadas ficticias ni audio.
  Música/Mixto, covers y exploración adicional quedan deshabilitados.
- Suite: **52 passed** (48 previas + 4 nuevas con fixtures sintéticos).
  Auditoría real `scripts/verify_text_release.py --hashes --reference`:
  todos los hashes de shards verificados; top-10 SGNS coincide íntegramente con
  referencia exacta para semilla validation `lyr_edc300ca1b86e86572b2` y train;
  diferencia máxima de coseno 5,96e-8. No es relevancia/accuracy.
- Medición final local: arranque 0,518 s; consulta SGNS 0,203 s y TF-IDF 1,151 s
  contra train. Pico RSS del proceso de auditoría 5 011 976 192 bytes (incluye
  páginas mapeadas y ejecución posterior de referencia). Release ID:
  `6eeefb93e016f2982470d08465ac0da0305355c630a1cacd8ea22f02418f5b3b`.
- Edge real automatizado con Playwright, 1440 y 390 px: diez resultados, sin
  errores JS ni desbordamiento, detalle, guardados tras recarga, texto TF-IDF,
  OOV y fallo API sin resultados ficticios; móvil con iframe conectado.
  Scripts/resultados/capturas: `scripts/verify_text_web.py`,
  `runtime/text_{catalog_benchmark,web_browser}.json`, `runtime/text_web_*.png`.
  Playwright instalado en el venv; se reutilizó Edge existente.
- No se modificaron los archivos del artículo ni TODO-human; H12 pendiente.
  Sin commit/push ni despliegue público. Mejoras posteriores: juicios humanos de
  validation, calidad de recuperación, audio/identidad verificada y comparación
  multimodal. No repetir E5 para arrancar la web.

---

## Objetivo vigente del usuario

El usuario quiere dejar lista la parte PLN y recomendación por texto de la página:
usar los artefactos existentes para una API real que devuelva canciones que
**hablen de lo mismo o presenten vocabulario similar**. Esta prioridad sustituye
el siguiente paso propuesto de audio. No se requiere audio para recomendar letras.
La petición de esta sesión fue preparar este handoff para reiniciarla; la siguiente
sesión debe implementar y comprobar la integración, no detenerse en un plan.

Interpretación operativa: conservar el flujo web de buscar título/artista y elegir
una canción semilla; permitir además texto libre como consulta textual. La segunda
entrada es una interpretación útil de «por texto», no una exigencia previamente
confirmada: implementarla como entrada adicional sin romper el flujo por canción.
Las recomendaciones deben ser ítems reales con título, artista e ID, no sólo palabras
similares ni ejemplos prefijados. El corpus/modelo es inglés; la interfaz es española.
No prometer comprensión semántica multilingüe ni traducción con SGNS inglés.

## Estado comprobado y límites

- Raíz `B:\SONORA`, Windows/PowerShell. `.venv` Python 3.14.10; spaCy 3.8.18,
  en_core_web_sm 3.8.0; Gensim 4.4.0 nativo ya instalado. No reinstalar el entorno.
- Base Git de esta continuación: `b2da9798ab2bb7fc7c61a8f531604d2d2a1e32ff`,
  `main`, publicado en `https://github.com/BrunoRuizJuar/Sonora.git`.
  Comprobar HEAD y cambios actuales: otra sesión trabaja en `reports/articulo_nlp/`.
  No sobrescribir cambios ajenos. La autorización anterior de push ya se consumó;
  esta petición no pide un nuevo commit/push ni despliegue público.
- E5 terminó: `runtime/e5_status.json`, `complete=true`, `stage=done`.
  Train, export, analysis y embedding_retrieval completos. No relanzar coordinador,
  ingesta, idioma, spaCy, entrenamiento ni exportación para integrar la API.
- Todo el corpus: 3 155 772 letras; train 2 208 832, validation 315 289,
  test 631 651. Vocabulario/IDF y modelos ajustados sólo en train.
- SGNS propio: 128 dimensiones, tres épocas, candidatos ventana 5/10;
  seleccionada 5. Pooling de palabras distintas con TF-IDF sublineal y L2.
  Se exportaron embeddings utilizables de todas las letras; cobertura de tokens ~81,9 %.
- LDA entrenado y revisado, pero dominado por funcionales y formas tipográficas,
  estabilidad limitada. **No utilizar LDA en el score por defecto** ni aplicar los
  pesos provisionales de `config/ranking.yaml` como si estuvieran validados.
- La proyección/contextos de E5 usa 2 000 letras de validation; los modelos y
  representaciones cubren todo el corpus. La auditoría del artículo señala el alcance
  de esa muestra; mantener esa distinción y no modificar evidencias para ocultarla.
- E1/E2 cerradas; E3/E4/E5 con revisión personal pendiente en `TODO-human.md`.
  No aprobar casillas por el autor. No hay accuracy ni relevancia medidas todavía.
- 48 pruebas pasaron en la entrega publicada. Son fixtures sintéticos; se dispone
  además de auditoría de integridad real y una consulta real del nuevo recuperador.

## Lecturas iniciales y artefactos que se deben reutilizar

1. `CLAUDE.md`, `TODO-human.md`, `docs/REQUIREMENTS.md` (especialmente §§6–10),
   `docs/CONTRATO_API.md`, `docs/E5_METODO.md`, `docs/E5_RESULTADOS.md`,
   `docs/E5_RECOMMENDATIONS.md`. Los contratos viejos de la web son propuestas,
   no un segundo contrato que deba mantenerse incompatible.
2. `apps/api/src/sonora_api/main.py`: FastAPI con salud solamente;
   `schemas/recommendations.py`: contrato preliminar por track_id.
3. `packages/sonora/src/sonora/recommendation/lyrics.py`,
   `pipelines/nlp/recommend_e5.py`, `tests/test_lyrics_recommendation.py`.
   Recuperación exacta por lyrics_id, con exclusión de semilla/no disponibles,
   filtros de split, coseno, versión y metadatos. **Recorre los Parquet dos veces
   por consulta: referencia de exactitud, no solución interactiva final.**
4. `packages/sonora/src/sonora/nlp/{semantics,semantic_export,semantic_retrieval}.py`:
   tokenización, TF-IDF, pooling y esquema existentes. Reutilizar la política exacta;
   no introducir una tokenización diferente para texto libre.
5. Datos: `data/processed/nlp/lyrics_full_v1/semantics/e5-surface-v2/`:
   `baseline/vocabulary.parquet`, `baseline/fit.json`, `documents/`,
   `representations/{config,complete}.json` y diez Parquet de representaciones.
6. Modelos: `artifacts/models/lyrics_full_v1/e5-surface-v2/trained.json`,
   `sgns_selection.json`; resolver el modelo seleccionado desde esos manifiestos.
   No cargar checkpoints ajenos; son pickles locales propios.
7. Reportes: `reports/nlp/lyrics_full_v1/e5_{verification,analysis,embedding_retrieval,tfidf_retrieval}.json`.
8. Web existente: `apps/web/public/{index.html,mobile.html,app.js,styles.css}`, assets;
   `apps/web/docs/CONECTAR_RECOMENDADOR.md`, `apps/web/serve.py`, lanzadores.
   El arreglo `songs` y `render()` usan datos de muestra. Ya hay interfaz estática:
   no sustituirla con una aplicación nueva por asumir el README histórico de Next.js.

Espacio E5: `ec76a8c38600ad837729631f95a54d58ac2c983ae46c7259aded6897235d9479`.
Datos/modelos/índices generados/logs/ZIP fuera de Git. No servir la raíz del repo;
el navegador sólo debe recibir API y assets públicos.

## Trabajo de la siguiente sesión

1. Inspeccionar estado real del código y web antes de editar. Preparar el entorno con
   `. .\scripts\Enter-SONORA.ps1`. Git: `C:\Program Files\Git\cmd\git.exe`.
   Probar primero ejecución normal; si falla `setup refresh had errors`, usar la
   escalación normal. No confundir ese fallo del ejecutor con dependencias rotas.
2. Preparar un release local de recuperación que vincule metadatos, IDs y vectores
   ya exportados, con manifiesto, hashes, dimensiones y versión. Construcción por
   lotes, atómica/reanudable; un escritor por salida. No construir N×N. Estimar RAM
   y medirla; no cargar varias copias de 3,16 millones de vectores por worker.
   Considerar matriz float32 mapeada a disco/índice de lectura y estructura léxica
   apropiada. Cargar/reutilizar recursos en el ciclo de vida de la API, sin releer
   todo el corpus ni recalcular hashes masivos en cada petición. No imponer
   OpenSearch/Redis/CouchDB si no son necesarios para una primera integración real.
3. Mantener dos señales: TF-IDF/coseno para vocabulario compartido y SGNS/coseno
   para proximidad semántica. Ofrecer comparación o estrategia textual explícita;
   una fusión debe declarar pesos y calibración y probarse en validation. Un coseno
   alto no garantiza mismo tema. No generar explicaciones temáticas que el sistema
   no pueda respaldar; mostrar términos compartidos cuando existan y afinidad del
   embedding como tal. No llamar «sinónimos» a toda asociación temática.
4. Resolver identidad: el corpus canónico usa lyrics_id y no prueba correspondencia
   a una grabación. Para el catálogo textual, definir un ID público estable y su
   relación con lyrics_id; si se conserva track_id del contrato, documentar el
   mapeo/alcance sin inventar FMA IDs. Conservar variantes/metadatos de procedencia.
   El catálogo textual no debe restringirse a las 886 coincidencias de audio.
5. Implementar API canónica `/api/v1`: búsqueda por título/artista, detalle y
   capacidades, estadísticas/versiones, recomendación por semilla en modo `lyrics`.
   Añadir contrato explícito para texto libre (ruta propia o entrada discriminada;
   exigir exactamente una entrada válida). Actualizar esquemas y documentación,
   con ejemplos reales y ruta de arranque reproducible. No decidir por accidente
   que el texto de búsqueda de títulos sea una consulta semántica.
6. Para texto libre: aplicar tokenización E5 y vocabulario/IDF congelados, pooling
   SGNS existente; gestionar vacío, longitud máxima, OOV total/parcial y norma cero.
   No ajustar IDF/vocabulario por consultas. Títulos/artistas pueden buscarse como
   metadatos, pero no incorporarse al vector de la letra sin variante documentada.
7. Integrar la web existente mediante fetch a la API. Mantener diseño aprobado,
   assets, responsive, navegación y guardados locales. Sustituir resultados ficticios
   por catálogo real; estados de carga, error, sin resultados y artefactos no listos.
   Exponer Letras como modo funcional; Música/Mixto claramente no disponibles en
   esta etapa. No inventar portadas, audio ni licencias. No mostrar placeholders como
   identidad real de una canción. Conectar también móvil si usa HTML independiente.
8. Aplicar top_k 1–50, excluir semilla y tratar no disponibles explícitamente.
   Añadir límite por artista y exclusión de covers sólo con evidencia disponible;
   documentar duplicados textuales frente a covers musicales no verificados.
   Texto igual ya fue consolidado; no afirmar detección completa de covers.
   Usar una misma versión para recomendar, comparar y explicar.
9. Preferir mismo origen para frontend/API o CORS local explícito. Evitar choque
   de puertos: el servidor web actual usa 8000 y el API también lo propone.
   Liveness no equivale a readiness: responder 503 mientras falte release válido.
   Errores de entrada/ID/capacidad no deben devolver recomendaciones de muestra.
10. Verificar con pruebas significativas de motor, API e integración: splits,
    identidad/espacio, self-exclusion, filtros, consultas vacías/OOV, top_k, errores,
    scores/versiones y una interacción real desde navegador (escritorio/móvil).
    Medir tiempos de arranque/consulta y RAM; si hay búsqueda aproximada, comparar
    recall top-k contra la referencia exacta sin llamarlo relevancia humana.

## Corpus completo y separación experimental

Puede explorarse el catálogo completo de 3 155 772 letras como producto usando
vectores congelados de E5, sin reentrenar con validation/test. Separar explícitamente
ese recorrido de una evaluación retenida: los experimentos conservan candidatos
train y semillas de validation; no usar navegación/juicios de test para elegir
pesos, hiperparámetros o modelos. La API debe reflejar el alcance de catálogo y
versión en su respuesta, no cambiarlo silenciosamente según disponibilidad.

Para demostrar la intención «mismo tema o vocabulario», mostrar consultas reales
de afinidad temática y léxica, incluyendo fallos conocidos: E5 detectó que el
vecino de una letra sobre embarazo no conserva necesariamente ese tema. Revisar
contextos con IDs y registrar juicios asistidos como tales. No prometer garantía
de calidad ni publicar accuracy sin protocolo y juicios independientes.

## Criterio de entrega

Desde un comando documentado se abre la web y funciona este recorrido real:
buscar canción → elegir semilla → recomendar por letra → ver títulos/artistas,
explicaciones sustentadas y scores de resultados reales. Si se incluye texto
libre, funciona el recorrido paralelo con errores OOV claros. El catálogo usa
el corpus completo disponible, las representaciones son comunes/versionadas,
no se ejecuta entrenamiento por petición, y los recursos caben en el equipo.
Pruebas y comprobación de navegador ejecutadas; documentación y handoff actualizados.
No se declara implementado audio ni evaluación final. Mantener H12 pendiente.

## Prompt listo para copiar en una nueva sesión

```text
Continúa SONORA en B:\SONORA, Windows/PowerShell. Implementa y deja funcionando
la API de recomendación por letras y su conexión a la web existente. El objetivo
del usuario es recomendar canciones que hablen de lo mismo o tengan vocabulario
similar, aprovechando TODO el trabajo PLN ya ejecutado, antes de iniciar audio.

Lee primero CLAUDE.md y docs/handoff/API_TEXTO_WEB_2026-11-16.md COMPLETO: contiene
estado, rutas reales, contratos, plan técnico, límites y criterio de entrega.
Después consulta docs/REQUIREMENTS.md, docs/CONTRATO_API.md, docs/E5_RESULTADOS.md,
docs/E5_RECOMMENDATIONS.md y TODO-human.md. Respeta cambios de otras sesiones,
especialmente reports/articulo_nlp/; comprueba Git antes de editar.

E5 ya terminó: modelos SGNS propios y TF-IDF train-only; 3 155 772 letras tienen
vectores congelados. No reentrenes ni repitas corpus/spaCy/exportación. Reutiliza
sonora.recommendation.lyrics, los manifiestos y representaciones e5-surface-v2.
La búsqueda actual recorre Parquet por petición: prepara acceso reutilizable
apropiado para API, sin N×N ni varias copias completas por worker.

Web real en apps/web/public; conserva su diseño y sustituye canciones de muestra
por fetch a la API canónica /api/v1. Implementa búsqueda título/artista, selección
de semilla y recomendación textual real; añade texto libre como entrada adicional
si corresponde a la interpretación del objetivo, con la política E5 congelada.
Separa búsqueda de metadatos de búsqueda semántica. Usa corpus completo como
catálogo textual sin exigir audio; conserva splits para evaluación y no elijas
modelos/pesos con test. SGNS para afinidad semántica y TF-IDF para vocabulario;
LDA no debe entrar al ranking sin ablación. No inventes temas, canciones o audio.

Resuelve contratos/IDs sin inventar correspondencia a grabaciones FMA, modos no
disponibles, recursos/puertos, errores, filtros y versiones. Prueba motor/API y
recorrido real de navegador; registra latencia y límites. Actualiza documentación
y handoff. E3/E4/E5 mantienen revisión personal pendiente. No publiques, despliegues
ni hagas nuevos commits/push sin solicitud. Trabaja hasta lograr el recorrido real,
no sólo un scaffold o una propuesta.
```
