## 6. Revisión lingüística y cierre de E4

**Fecha: 2026-11-16. Estado: cierre técnico y documental completado; revisión asistida
realizada. La lectura y validación personal del autor siguen pendientes y no se presumen.**

Los pendientes humanos se centralizan en [`TODO-human.md`](../TODO-human.md), H03–H06.

### Hallazgos contrastados con los datos

- Las 3 155 772 letras contienen **144 457 653 segmentos anotados** y
  **809 010 838 arcos incluidos**. Longitud media: 6,5976 tokens sin puntuación;
  profundidad media: 2,4413 saltos; distancia media por arco: 1,9360 posiciones.
  La media de distancias por segmento con arcos es 1,7739: usarla como si ponderara
  arcos produciría otro estimando. La longitud incluye clíticos, números y símbolos.
- Hay **11 030 574 segmentos sin arcos**, **1 186 993 sin tokens no puntuación**
  y **40 981 827 con raíz no VERB/AUX**. Son categorías diferentes y pueden solaparse.
  Ninguna equivale automáticamente a una oración mal analizada; una raíz nominal puede
  ser compatible con una expresión breve, y una frontera por verso puede partir una oración.
- `rap` presenta longitud media 7,1527 y distancia 2,0060; `rock`, 6,1006 y 1,8390.
  Sin embargo, `country` alcanza profundidad 2,6342 frente a 2,5742 de `rap`.
  Las métricas no ordenan los tags de una única manera ni definen complejidad artística.
- Parte de las diferencias depende de longitud. En la banda 5–9 tokens, la profundidad
  de `rap` es 2,7465 y la de `country` 2,6884: el orden cambia respecto de la media
  global de esos tags. La distancia en esa banda es 1,8348 y 1,8178, respectivamente.
  Las bandas reducen un factor de confusión, pero no controlan exactamente la longitud
  ni artista, estilo o calidad del parser.
- Entre 1970 y 2020, la longitud global pasa de 6,4244 a 6,5953, mientras en `pop`
  baja de 6,3542 a 6,1301 y en `country` de 7,7381 a 7,0323. La mezcla del dataset
  puede producir una evolución agregada distinta de la observada dentro de los tags.
  No se atribuye el contraste a un cambio causal del lenguaje. `rap` de 1970 sólo
  tiene 216 letras, frente a 306 458 de la década 2020, y exige particular cautela.

Los hallazgos anteriores se obtienen de `e4_summary.json`. Los diez shards se procesaron
en un solo proceso, por lotes, con checkpoints por shard. El tiempo de agregación se
registra en su campo `seconds`; no incluye auditoría dirigida ni generación del notebook.
Los datos originales y la anotación spaCy permanecen intactos.

### Lectura de los cuatro árboles (E4-01/02/04)

Cada árbol incluye tabla de tokens, cabeza, etiqueta, POS, lema, archivo y posiciones
originales. Sus profundidades, números de arcos y distancias se recalcularon desde los
tokens y coinciden con las partes de oraciones originales (tolerancia float32 de 1e-6).
La revisión lingüística propone lecturas; no modifica las predicciones ni constituye gold.

| Criterio y localizador | Lectura y limitación |
|---|---|
| Transitiva · `country` · `lyr_79bf500aa6f551ad02e4`, sent_i 0, line_i 0 | Raíz `leave`; `We`→`leave` (`nsubj`) y `lights`→`leave` (`dobj`) son relaciones plausibles; `could` aporta auxiliar/modalidad. Sujeto/objeto son funciones sintácticas, no etiquetas universales de agente/paciente. El final temporal recibe un análisis dudoso: `til` como PROPN y compuesto de `January`; requiere revisión contextual. La validez estructural no elimina ese problema. |
| Subordinada · `pop` · `lyr_2315a48e066ced8009d6`, sent_i 1, line_i 1 | `bar` depende de `is` como `nsubj`; `I` depende de `go` como `nsubj`; `go` se une a `is` con `advcl`. La secuencia con `where` introduce contenido locativo y funciona en la predicación copulativa: llamar a todo ello un adjunto adverbial sin discusión sería simplificar. La selección se basa en la etiqueta `advcl` del parser, no en una clasificación humana ya confirmada. |
| Coordinación · `rap` · `lyr_94b5237c6f7464b6c4b5`, sent_i 17, line_i 17 | `livin'` y `killin'` están etiquetados NOUN y la lectura favorece coordinación nominal. Sin embargo, `killin'` se adjunta mediante `conj` a `Made`, no a `livin'`; `and` también se une al verbo. Hay un probable error de alcance de coordinación. `off` marcado `prt` bajo un nombre merece revisión. El sujeto omitido no se inventa como token. |
| Fragmento sin VERB/AUX · `rb` · `lyr_9b869033ae33f65fdae4`, sent_i 56, line_i 61 | El parser produce raíz nominal `konjo`, con `Yene` como `compound` y `ewedihalehu` como `appos`. Las formas y versos vecinos no permiten una interpretación inglesa segura. Se conserva el caso y se señala para auditoría de idioma/contexto; no se asigna un idioma ni se valida la sintaxis sin evidencia. Una letra predominantemente inglesa puede contener un pasaje en otra lengua. “Sin VERB/AUX predicho” no demuestra fragmentación gramatical correcta. |

Los cuatro árboles son de **cuatro letras y cuatro tags**, pero todos proceden de la
primera parte del shard 0 porque el criterio conserva el primer hallazgo. No son
representativos de cada tag. La auditoría de grafos sí cubrió las primeras partes de
los diez shards: **5 000 letras, 244 951 segmentos**, sin anomalías en las comprobaciones
de raíz, etiqueta ROOT, cabezas presentes y ciclos. Ese resultado sólo concierne a esa
selección y a esas propiedades estructurales, **no a precisión lingüística** ni al estado
de todos los árboles del corpus.

El ejemplo de E3 sin verbo y su continuación entre versos refuerza el límite de segmentación.
No se presenta la profundidad de segmentos forzados como profundidad de oraciones completas.
No se ejecutó un parser de constituyentes ni se presenta un chunker como tal.

### Cobertura y reproducibilidad

| Requisito | Evidencia | Estado |
|---|---|---|
| E4-01 árboles y parser | Cuatro árboles con criterios, procedencia e índices; versiones y convenciones documentadas | Implementado y ejecutado; lectura personal pendiente |
| E4-02 relaciones | Tablas cabeza–dependiente, etiquetas y comentario individual, con separación sintaxis/semántica | Revisión asistida realizada; confirmar juicios |
| E4-03 complejidad | Longitud, profundidad y dos ponderaciones de distancia, distribuciones, denominadores y exclusiones sobre todo el corpus | Reconciliado y ejecutado |
| E4-04 comparación y límites | Tags, décadas, bandas de longitud, contraste temporal dentro de tag; fragmentos y parses dudosos discutidos | Ejecutado; revisión personal pendiente |

Desde `B:\SONORA`, con la `.venv` activa:

```powershell
python pipelines/nlp/e4_syntax.py
python notebooks/evidencias/build_e4.py
```

El pipeline lee `spacy_sm_v1/sentences/`, `doc_stats/` y partes seleccionadas de
`tokens/`; no ejecuta spaCy. Los checkpoints quedan en
`data/processed/nlp/lyrics_full_v1/syntax/e4-syntax-v2/` y sólo se reutilizan si coinciden configuración,
código y firmas de entradas. Se usa lock de un único escritor; no borrar salidas para
forzar una reanudación incompatible. Los resultados publicables están en
`reports/nlp/lyrics_full_v1/e4_{summary,examples}.json` y `reports/figures/E4/`.
Los checkpoints de la primera ejecución permanecen conservados en `syntax/`; v2 usa
su propia carpeta tras el ajuste de representación de arcos y no sobrescribe esos archivos.

### Lo que tú debes revisar para completar tu validación de E4

- [ ] Leer las convenciones y comprobar que distingues segmentos anotados de oraciones
  completas, longitud sin puntuación de tokens regex y media por arco de media por segmento.
- [ ] Revisar los cuatro árboles con sus tablas y confirmar o corregir los juicios de
  la revisión: especialmente adjunción de coordinación, etiqueta `advcl` y el final temporal.
- [ ] Revisar el contexto e idioma del ejemplo nominal opaco; no aceptar sus etiquetas
  inglesas como análisis lingüístico validado sin esa revisión. No se propone descartarlo
  silenciosamente ni cambiar el corpus a partir de este único caso.
- [ ] Comprobar las figuras y los tamaños por tag/década. Confirmar que el texto no afirma
  causalidad, significancia o superioridad sintáctica de un género.
- [ ] Confirmar la tabla E4-01…04 o anotar correcciones; mantener E4 pendiente de tu lectura
  hasta entonces. E3 conserva por separado su pendiente de revisión personal.
