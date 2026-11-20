# Piloto emocional de SONORA

## Calificaciones en el recomendador

En el portal de SONORA, busca y selecciona una canción para abrir el reproductor. Cuando se prepare la siguiente pista, puedes calificar el par en sentimiento, temática y vibras musicales, de 0 a 5 en pasos de 0.5. Puedes guardar una parte y completar las demás después. El mismo navegador puede recuperar y actualizar su calificación para ese par. El recomendador textual conserva su formulario de comparación.

Las valoraciones de la web se guardan en la tabla `recommendation_ratings` de `runtime/feedback/ratings.sqlite3`. Para usar otra ubicación, configura `SONORA_RATINGS_DB` en el servidor. La tabla conserva los IDs de las pistas o de las letras según el catálogo, el identificador del catálogo, el identificador del navegador, la estrategia, la posición, las tres escalas (`emotion`, `theme`, `music_vibe`) y la fecha de actualización. En el reproductor, la posición 0 indica que el par no figura en las 20 primeras recomendaciones. Cada navegador conserva una valoración por par y catálogo. Extrae la tabla para futuros ajustes por lotes.

## Anotación

1. Abre `apps/web/public/anotacion.html` o visita `/anotacion.html` en el servidor local de SONORA. Carga el [archivo de anotación del piloto](../data/evaluation/emotion-pilot/anotacion.json).
2. Lee las dos letras y califica cada par de 0 a 5 con incrementos de media estrella. Deja la escala sin respuesta si todavía no puedes juzgarla. Puedes registrar ambigüedades en las notas.
3. Exporta las valoraciones cuando termines. Puedes trabajar por tandas en el mismo navegador.

| Escala | 0 | 2.5 | 5 |
| --- | --- | --- | --- |
| Relevancia temática | Temas distintos | Comparten un tema secundario o general | Comparten el tema central |
| Afinidad emocional | Tonos muy distintos | Mezcla de coincidencias y diferencias | Tonos emocionales muy parecidos |

Califica según la letra. Una canción puede compartir el tema central y recibir una calificación emocional baja. Ten en cuenta el contexto de las palabras, las negaciones y los cambios de tono dentro de la letra.

## Reproducción y evaluación

El piloto usa 200 letras del split de prueba del catálogo inglés de E5. Doce funcionan como consultas. Se comparan los diez primeros resultados de SGNS con los obtenidos al añadir pesos emocionales de 0.1, 0.2 y 0.3 sobre los mismos candidatos. La interfaz muestra la unión de esos resultados en orden aleatorio por consulta.

La muestra preparada contiene 224 pares que, en conjunto, muestran 111 letras distintas. Puedes revisar una consulta por tanda, con entre 14 y 22 comparaciones por consulta.

Tras anotar los pares completos, el evaluador elige el peso con mayor nDCG@10 emocional entre los que conservan el nDCG@10 temático en cuatro consultas de validación. Reporta SGNS y el peso elegido sobre ocho consultas reservadas. El ideal de nDCG se calcula sobre los candidatos anotados para cada consulta.

Desde la raíz del repositorio:

```powershell
.venv/Scripts/python.exe scripts/emotion_pilot.py prepare --lexicon runtime/tmp/NRC-Emotion-Lexicon.zip --output runtime/emotion-pilot
.venv/Scripts/python.exe scripts/emotion_pilot.py evaluate --design data/evaluation/emotion-pilot/diseno.json --ratings C:/ruta/valoraciones-sonora.json
```

El comando de preparación requiere un directorio de salida nuevo y los índices locales del recomendador y de letras originales. La señal usa NRC Word–Emotion Association Lexicon v0.92 de Saif M. Mohammad y Peter Turney, National Research Council Canada. [Fuente y descarga oficial](https://saifmohammad.com/WebPages/NRC-Emotion-Lexicon.htm).
