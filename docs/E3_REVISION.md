## 6. Revisión de resultados y revisión pendiente del autor

**Fecha: 2026-11-16. Estado: revisión técnica y lingüística asistida realizada;
pendiente revisión personal del autor. E3 no se declara cerrada.**

Esta lectura utiliza el resumen ejecutado `reports/nlp/lyrics_full_v1/e3_summary.json`
y las tablas completas del notebook. Las observaciones lingüísticas son juicios de revisión,
no etiquetas gold. Se conservan las predicciones originales y no se modifica la anotación.

### Hallazgos sustentados por las tablas

1. En los 1 033 733 693 tokens, PRON representa 17,975 %, VERB 15,396 % y
   NOUN 14,218 %. Excluyendo PUNCT/SYM/SPACE (954 321 127 tokens), son
   19,471 %, 16,677 % y 15,401 %. El peso de pronombres es compatible con
   voces e interlocutores frecuentes en letras; POS por sí solo no prueba diálogo,
   persona gramatical concreta ni emoción. Los estribillos escritos cuentan varias veces.
2. La mayor separación por tag es PRON: `rb` 22,614 % frente a `country`
   18,594 % (**4,020 puntos porcentuales**). NOUN alcanza 16,432 % en `rap`
   frente a 12,761 % en `rb` (3,672 pp). PROPN llega a 6,046 % en `rap`
   y 3,055 % en `rock` (2,991 pp). Estas diferencias describen etiquetas de la fuente;
   los errores de PROPN observados impiden leerlo como un censo fiable de entidades.
3. La normalización por tokens no elimina el desequilibrio documental: `pop` tiene
   1 336 051 letras y `country` 85 258. `rap`, con 959 763 letras, aporta
   475 239 909 tokens, más que los 342 698 294 de `pop`. Por eso el perfil global
   está afectado por longitud/repetición y no representa una media de cinco tags.
4. Entre 1970 y 2020, PRON dentro de `pop` pasa de 18,651 % a 21,433 %;
   en `rb`, de 20,304 % a 22,723 %; en `country`, de 18,578 % a 18,641 %.
   El cambio no es uniforme entre tags. NOUN en `pop` pasa de 15,114 % a 13,151 %,
   mientras `country` pasa de 14,923 % a 15,084 %. Son comparaciones descriptivas,
   no cambios de los mismos artistas ni pruebas de evolución causal del lenguaje.
   Los extremos son décadas de `year`; 2020 sólo incluye años válidos hasta 2022.
   La celda `rap` de 1970 tiene 129 247 tokens sin puntuación frente a 129 586 892
   en 2020: exige especial cautela. Los tamaños documentales mostrados por década
   son globales, no tamaños documentales de cada cruce tag–década.
5. Cambian de forma a lema, ignorando mayúsculas, 177 278 975 tokens (18,576 %).
   Los tipos bajan de 1 503 152 a 1 450 635 (3,494 %). Entre los cambios frecuentes
   están `me`→`I` (13 916 368), `n't`→`not` (13 851 892) y `'m`→`be`
   (10 292 562). La reducción incluye normalización de pronombres y clíticos,
   no sólo flexión de sustantivos o verbos. No cuantifica exactitud ni garantiza
   que todos los lemas sean adecuados para la representación semántica de E5.

Todos los porcentajes comparativos por tag/década anteriores excluyen PUNCT/SYM/SPACE.
Los valores se redondean a tres decimales; pp significa puntos porcentuales.

### Revisión individual de los nueve criterios dirigidos

Los ejemplos están en `e3_summary.json`, con archivo, `lyrics_id`, `line_i`,
`sent_i`, `tok_i` y anotación. Los índices empiezan en cero. Se inspeccionaron las
primeras partes de diez shards (5 000 letras), pero los primeros ejemplos de los
nueve criterios proceden del shard 0 y de sólo **tres letras distintas**. Siete ejemplos
comparten una letra; esto es una limitación adicional de la selección por primer hallazgo.
Encontrar nueve criterios no equivale a tener nueve documentos independientes.

| Criterio | Localizador: letra / oración / token | Lectura cualitativa y límite |
|---|---|---|
| Slang `gonna` | `lyr_94b5237c6f7464b6c4b5` / 0 / 5 | `gon` VERB→`go` y `na` PART→`to` son compatibles con la construcción prospectiva del contexto. `na` aquí no es una sílaba de estribillo; la etiqueta VERB es la salida UPOS del modelo, no una garantía de análisis funcional completo. |
| Posesivo/auxiliar | misma letra / 3 / 41 | `'s` PART→`'s` es inadecuado en este uso: la lectura contextual es auxiliar/cópula `is`, con lema `be`; `wrong` aparece como NOUN donde la lectura predicativa favorece ADJ. No extrapolar el error a todas las apariciones de `'s`. |
| Nombre propio | misma letra / 3 / 53 | `Slim` y el token siguiente `Shady` forman un nombre; PROPN resulta plausible. No confundir este caso con los vocablos mal clasificados como PROPN. |
| Negación contraída | misma letra / 4 / 80 | `n't` PART→`not`, junto a `do` AUX, conserva la negación y ofrece una normalización apropiada para este uso. No se elimina como stopword en la vista sintáctica. |
| G-dropping | misma letra / 9 / 133 | `beginnin'` VERB→`begin`, con bandera de normalización activa, es adecuado en el contexto progresivo. El acierto puntual no demuestra una mejora global frente a no normalizar: no hay ablación. |
| Interjección | misma letra / 42 / 526 | `Well` INTJ→`well` es una lectura plausible como marcador discursivo. No implica que cada aparición de `well` sea una interjección o una vocalización musical. |
| Vocablo como PROPN | `lyr_0c2a202b3c00dfad766c` / 33 / 365 | `Yeah` como intervención entre paréntesis favorece INTJ; PROPN parece error de dominio. `thang` también aparece como PROPN, aunque su lectura contextual es nominal común. No corregir por diccionario todas sus apariciones sin contexto. |
| Lema de `ridin'` | `lyr_95301e309a7ad7dd1298` / 23 / 265 | VERB es plausible; `rid` es un lema inadecuado para el desplazamiento en vehículo descrito: se esperaría `ride`. La normalización gráfica está activa, pero no resuelve la desambiguación léxica del lematizador. |
| Fragmento sin verbo | `lyr_94b5237c6f7464b6c4b5` / 43 / 535 | El segmento nominal sin VERB/AUX continúa el verso anterior, cuyo final contiene `blueprint` y `'s`. La ausencia de verbo en este segmento no demuestra que el pasaje completo carezca de predicación; ilustra el efecto de forzar fronteras por verso. |

**Implicación para SONORA:** conservar forma, lema y POS separados permite analizar errores
sin reescribir el corpus. Filtrar por PROPN o colapsar palabras exclusivamente por lema
puede introducir pérdidas como las observadas; E5 deberá justificar su política de texto.
Esta auditoría dirigida no permite estimar tasas de error o precisión del modelo.

### Figuras y cobertura de requisitos

Las tres figuras se inspeccionaron visualmente. El gráfico global conserva la tabla
completa para categorías pequeñas; se añadieron porcentajes encima de las barras.
El mapa de calor muestra los valores y elimina la cuadrícula que atravesaba las celdas.
El gráfico temporal distingue trazos y coloca la leyenda fuera de los datos.
La comparación temporal sigue siendo descriptiva y las décadas pequeñas permanecen
visibles en tablas aunque no se dibujen con menos de 1 000 letras.

| Requisito | Evidencia disponible | Estado de revisión |
|---|---|---|
| E3-01 POS y lemas | Modelo/versiones, anotación completa, tabla de cambios y ejemplos con procedencia | Revisión asistida realizada; confirmación personal pendiente |
| E3-02 distribución gramatical | Conteos completos y dos denominadores explícitos, gráfico global | Reconciliación técnica realizada; lectura personal pendiente |
| E3-03 comparación de secciones | Cinco tags, décadas, tamaños, porcentajes y contraste temporal dentro de tag | Hallazgos documentados con límites; revisión personal pendiente |
| E3-04 interpretación y errores | Nueve criterios revisados individualmente; contracciones, slang, nombres y fragmentación | Juicios cualitativos propuestos; revisión personal pendiente; sin gold ni accuracy |

### Lo que tú debes revisar antes de cerrar E3

- [ ] Leer los cinco hallazgos y comprobar que puedes explicar sus denominadores,
  la diferencia entre porcentaje y puntos porcentuales y el efecto de letras largas.
- [ ] Abrir los nueve ejemplos en la sección 4 del notebook y contrastar las propuestas
  de esta tabla con sus contextos. Confirmar o corregir especialmente `'s`, `Yeah` y `ridin'`.
- [ ] Revisar los dos versos consecutivos del ejemplo sin verbo: decidir si la explicación
  de la frontera forzada refleja correctamente el pasaje, sin presentar el fragmento aislado
  como prueba de una oración agramatical.
- [ ] Revisar las tres figuras al tamaño de lectura/exportación que usarás y confirmar
  etiquetas, porcentajes, leyenda y legibilidad. No leer diferencias por color como significancia.
- [ ] Confirmar que la selección de ejemplos (tres letras, principalmente una) basta para
  tu discusión cualitativa. Si deseas mayor variedad, añadir ejemplos dirigidos identificados;
  no presentarlos como muestra representativa ni como evaluación de precisión.
- [ ] Revisar la tabla E3-01…04 y dejar por escrito tu conformidad o las correcciones
  solicitadas. **Hasta entonces mantener E3 como pendiente de revisión del autor.**

La revisión personal es un pendiente explícito del trabajo solicitado. No se ha realizado
en tu nombre ni se presume aprobación por haber regenerado el notebook.
