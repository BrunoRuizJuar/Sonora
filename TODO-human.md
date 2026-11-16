# Pendientes de revisión humana — SONORA

Actualizado: 2026-11-16. Raíz actual: `B:\SONORA`.

E1 y E2 cerradas. E3 revisada de forma asistida; falta tu lectura personal.
**E4 tiene implementación, ejecución y cierre técnico/documental completos**;
su revisión personal sigue pendiente. No se marcan estas casillas en tu nombre.
Los pendientes de lectura no requieren repetir el corpus ni la anotación spaCy
y no impiden preparar E5. Si encuentras un problema sistemático, primero se prueba
una corrección pequeña y se registra qué resultados quedarían afectados.

## Ahora: E3 y E4

- [ ] **H01 — Leer y confirmar la interpretación de E3.**
  Abrir [E3_REVISION.md](docs/E3_REVISION.md) y
  [el notebook E3](notebooks/evidencias/E3_morfosintaxis.ipynb), especialmente secciones 4 y 6.
  Revisar los nueve criterios; confirmar o corregir las lecturas de `'s`, `Yeah`
  y `ridin'`, y la continuación entre versos del ejemplo sin verbo.
  Registrar conformidad o correcciones en este archivo, con fecha.
- [ ] **H02 — Confirmar que puedes explicar los resultados de E3.**
  Revisar denominadores, porcentaje frente a puntos porcentuales, peso de letras largas
  y repeticiones. Las métricas abarcan 3 155 772 letras; los nueve ejemplos son de tres
  letras distintas y no sirven para estimar precisión. Decidir si deseas ejemplos de
  más canciones para la exposición. Esa ampliación sería cualitativa, no una nueva corrida.
- [ ] **H03 — Leer y confirmar la interpretación de E4.**
  Abrir [E4_REVISION.md](docs/E4_REVISION.md) y
  [el notebook E4](notebooks/evidencias/E4_sintaxis_dependencias.ipynb).
  Revisar los cuatro árboles y sus tablas: adjunción de coordinación, etiqueta `advcl`
  y análisis del final temporal. Distinguir función sintáctica de papel semántico.
  Registrar conformidad o correcciones, con fecha.
- [ ] **H04 — Revisar el pasaje de idioma/contexto incierto de E4.**
  Letra `lyr_9b869033ae33f65fdae4`, `sent_i=56`, `line_i=61`.
  Su procedencia está en `reports/nlp/lyrics_full_v1/e4_examples.json` y el notebook.
  Consultar la letra y contexto originales; identificar el idioma sólo si tienes evidencia.
  No asumir que los POS de un modelo inglés sean correctos para ese pasaje ni que toda
  la letra deba excluirse. Anotar lo verificado y lo que siga incierto.
- [ ] **H05 — Revisar figuras y alcance de E4 antes de presentar.**
  Confirmar que puedes explicar segmento por verso frente a oración completa,
  profundidad con raíz cero y distancia media por arco frente a media por segmento.
  Revisar legibilidad al tamaño de exportación y tablas por tag/década/longitud.
  Las métricas cubren el corpus completo; la auditoría estructural dirigida cubre
  5 000 letras y no es precisión del parser. Los cuatro árboles proceden del shard 0.
- [ ] **H06 — Confirmar las matrices de requisitos E3-01…04 y E4-01…04.**
  Están al final de sus documentos de revisión. Dejar una nota de revisión personal
  terminada o una lista concreta de correcciones. El cierre técnico de E4 ya está
  documentado; esto completa tu revisión de contenido, no reemplaza las evidencias.

## Antes del cierre académico

- [ ] **H12 — Revisar el contenido de E5 cuando estén sus resultados reales.**
  Consultar `docs/handoff/E5_2026-11-16.md` para distinguir ejecución de implementación.
  Cuando existan vecinos, contextos y tópicos reales: confirmar o corregir sus
  interpretaciones, registrar fallos y valorar si las etiquetas temáticas son defendibles.
  Distinguir el modelo estático de sus contextos por década/tag y la muestra de figuras
  del corpus completo. No usar PCA, coherencia o perplexity como juicios de recomendación.
  La revisión humana no sustituye ejecutar y comprobar las etapas técnicas pendientes.

- [ ] **H07 — Aclarar el requisito de 150–300 páginas con el profesor.**
  Registrar el criterio aceptado para este corpus digital o la aclaración recibida.
  El tamaño en documentos/tokens y el split 70/20/10 no sustituyen esa condición.
- [ ] **H08 — Completar la auditoría humana de idioma del corpus.**
  La muestra está en `data/processed/lyrics/lyrics_full_v1/language_audit_sample.parquet`:
  200 aceptados, 200 inciertos y 100 no ingleses. Revisar con criterios explícitos
  y registrar decisiones y dudas. La tasa de aciertos del detector sigue sin medirse.
  Esta revisión no exige volver a detectar el idioma de todas las letras.

## Cuando retomemos audio y evaluación del recomendador

- [ ] **H09 — Revisar vínculos FMA–Genius y condiciones de reproducción.**
  Verificar correspondencia de letra/grabación, audio y licencia por pista con evidencia.
  Las 886 coincidencias exactas retenidas no equivalen a 886 pistas autorizadas para
  reproducción; `catalog_eligible` no debe activarse sólo por existir el MP3.
  Los candidatos fuzzy siguen separados hasta su revisión.
- [ ] **H10 — Confirmar participantes y protocolo de evaluación humana.**
  Antes de recoger juicios finales: confirmar disponibilidad de evaluadores, semillas,
  carga, instrucciones y escala; separar validación de test. Valorar letras y sonido
  por separado cuando corresponda y conservar no juzgados y desacuerdos.
  No recoger test para elegir modelos ni sustituir juicios con scores del recomendador.

## Opcional: si queremos medir precisión lingüística

- [ ] **H11 — Decidir si crear una referencia humana de POS/dependencias.**
  Sólo si se quiere estimar precisión: definir muestreo, esquema de etiquetas,
  anotadores y resolución de desacuerdos antes de medir. Los ejemplos dirigidos actuales
  muestran problemas posibles, pero no su prevalencia. No es motivo por sí solo para
  repetir toda la anotación.

## Notas de revisión del autor

Añadir fecha, ID del pendiente, resultado y correcciones solicitadas. Dejar vacías
las casillas que todavía no hayas revisado; no confundir ejecución con aprobación humana.

| Fecha | Pendiente | Resultado / corrección |
|---|---|---|
| — | — | Pendiente de tu revisión |

## Seguimiento técnico que puede hacer el agente

- Continuar E5 según `docs/handoff/E5_2026-11-16.md`: caché completa y vocabulario/IDF
  ya ajustados con train; verificar recuperación, entrenamiento propio, tópicos,
  exportación y análisis reales. Validation selecciona; test sigue reservado.
- Gensim 4.4.0 ya compilado y verificado, con Build Tools y Cython 3.3.1;
  procedimiento/hashes en el handoff. Python/spaCy/modelo conservan sus versiones.
- Mantener el ZIP y los datos locales fuera de Git; no repetir ingesta, anotación o
  corridas completas sin un problema identificado y una corrección justificada.
