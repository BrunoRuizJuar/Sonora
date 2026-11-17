# Probar recomendaciones con los embeddings propios

Actualización 2026-11-16: exportación completa y auditada; 3 155 772 embeddings
disponibles. Consulta real ejecutada para `lyr_edc300ca1b86e86572b2` contra los
2 208 832 candidatos train. Resultado local: `runtime/e5_recommendation_trial.json`.
Cinco consultas adicionales y comparación con TF-IDF documentadas en
[E5_RESULTADOS.md](E5_RESULTADOS.md). Suite sintética vigente: 48 passed;
el ensayo real no mide calidad de recomendación.

Se entrenaron dos Word2Vec/SGNS de 128 dimensiones, ventanas 5 y 10 y tres
épocas completas sobre 2 208 832 letras de train. Validación eligió ventana 5.
La selección intrínseca no demuestra calidad de recomendación.

No es necesario entrenar con validation/test para obtener sus vectores. La
exportación transforma todas las letras con el mismo modelo congelado: combina
palabras distintas con pesos TF-IDF sublineales y normaliza L2. OOV se omite;
una letra sin vector utilizable queda explícitamente no disponible. La cobertura
real se confirma en `representations/complete.json` al finalizar la exportación.

Desde la raíz, una vez terminada la exportación:

```powershell
.venv\Scripts\python.exe pipelines/nlp/recommend_e5.py lyr_edc300ca1b86e86572b2 --k 10
```

Devuelve vecinos exactos por coseno, candidatos sólo de train por defecto, con
ID, título, artista, split, score y versión del espacio. Excluye la propia letra
y candidatos sin embedding. Recorre lotes, sin construir una matriz N×N.
La búsqueda exacta es una primera interfaz experimental; todavía no tiene un
índice para consultas interactivas de baja latencia.

Para explorar candidatos de los tres splits, sin usarlo como evaluación ni selección:

```powershell
.venv\Scripts\python.exe pipelines/nlp/recommend_e5.py lyr_edc300ca1b86e86572b2 --all-splits
```

La interfaz exige una exportación completa y comprueba su espacio y conteos por
split. No modifica los artefactos E5 ni interfiere con el coordinador activo.
Sus pruebas sintéticas comprueban aislamiento de candidatos, exclusión de la
consulta, coseno, vectores no disponibles e incompatibilidad de espacio.

Esta es la primera integración en `sonora.recommendation`, para letras canónicas.
No implementa todavía filtros por artista/covers, mezcla con audio ni conexión a
la interfaz web. No certifica correspondencia de grabación ni reproducción legal:
el paso a track_id requiere el catálogo verificado. LDA no participa en el score;
su incorporación requiere una ablación con juicios de validación. Los pesos
provisionales de `config/ranking.yaml` no se aplican en esta prueba.

Tras comprobar resultados reales se pueden comparar TF-IDF y SGNS con las mismas
semillas de validación, y después conectar las letras del catálogo de audio al
espacio común. Entrenar una variante con todos los splits sería un experimento
separado que invalidaría su uso como evaluación retenida para esa variante;
no se necesita para representar todas las letras y no se ha ejecutado aquí.
