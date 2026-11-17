# API textual y web local — 2026-11-16

Implementación funcional sobre las **3 155 772 letras** de E5. No requiere audio,
reentrenamiento, nueva exportación, Redis ni OpenSearch. Conserva la web aprobada.

Desde `B:\SONORA`:

```powershell
. .\scripts\Enter-SONORA.ps1
# Sólo para construir/reconstruir el release de servicio desde E5:
.venv\Scripts\python.exe scripts/build_text_release.py
# Arranque cotidiano, API + assets públicos, un worker:
.\scripts\Start-SONORA-Web.ps1
```

Abrir <http://127.0.0.1:8010/>; vista móvil <http://127.0.0.1:8010/mobile.html>.
Documentación interactiva: <http://127.0.0.1:8010/docs>.
El servidor nunca publica la raíz del repositorio. El antiguo `apps/web/serve.py`
sólo sirve assets; para recomendaciones se utiliza este nuevo arranque conjunto.

## Recorridos

Buscar título/artista → seleccionar letra → diez resultados reales. Se puede
elegir SGNS (afinidad del embedding) o TF-IDF (vocabulario compartido), guardar
resultados en el navegador y abrir su detalle. Ejemplo real: buscar
**Evil dudes demo**, ID `lyr_edc300ca1b86e86572b2`. En el experimento con candidatos
train su primer vecino SGNS es **Jealous Girl — Tages**, coseno ≈ 0,941382.
El catálogo exploratorio completo puede ofrecer vecinos distintos.

En cada resultado, **Comparar letras** abre la sección «Letras frente a frente»:
canción de partida a la izquierda y canción seleccionada a la derecha, con título,
artista y letra original conservando versos y estrofas. También se abre desde
**Ver letras lado a lado** en el detalle. En móvil los dos paneles se apilan;
cada letra tiene desplazamiento independiente. Si se parte de texto libre,
el panel izquierdo muestra exactamente la consulta introducida. Cambiar la
semilla limpia la comparación anterior. No se reconstruyen letras desde tokens.

La instalación del acceso a originales se realiza una sola vez:

```powershell
.venv\Scripts\python.exe scripts/build_lyric_index.py
```

`artifacts/releases/lyrics-original-v1/lyrics.sqlite` indexa ID → archivo, grupo
de filas y posición del corpus canónico. Verifica hashes de los originales contra
los inputs congelados de E5 al construir; no cambia modelos ni release vectorial.
Cada petición lee sólo el grupo necesario y comprueba identidad, tamaño y fecha
del original. `SONORA_LYRIC_INDEX` permite elegir otra ubicación del índice.
Si falta el índice, las recomendaciones siguen disponibles y se informa del
error al pedir letras. Reiniciar la API después de instalarlo.

El campo adicional consulta texto en inglés, por ejemplo
`Leaving home and missing my family`. No es el buscador de títulos.
Se conserva NFC, apóstrofo normalizado, regex E5, TF sublineal, IDF train-only,
pooling de términos distintos y L2. OOV parcial se omite y se cuenta en
`query.coverage`; texto vacío, totalmente OOV o norma cero genera error.
No existe traducción ni garantía de equivalencia temática.

## Contrato canónico `/api/v1`

| Método/ruta | Comportamiento |
|---|---|
| GET `/health/live` | Proceso vivo. |
| GET `/health/ready` | 503 sin release íntegro/compatible; 200 si abre. |
| GET `/catalog/stats` | Tamaño, espacio, versión, dimensiones y capacidades. |
| GET `/tracks/search?q=...&limit=20` | Prefijos de palabras en título/artista, AND, máximo 50. |
| GET `/tracks/{track_id}` | Metadatos, split y capacidades. |
| GET `/tracks/{track_id}/lyrics` | Letra original: `text`, `view`, identidad, metadatos y `space_id`. 404 ID desconocido, 503 sin índice, 409 original inaccesible/incompatible. |
| POST `/recommendations` | Exactamente una entrada `track_id` o `text`. |

```json
{
  "track_id": "lyr_edc300ca1b86e86572b2",
  "mode": "lyrics",
  "strategy": "sgns",
  "top_k": 10,
  "candidate_splits": ["train", "validation", "test"],
  "max_per_artist": 1,
  "exclude_known_covers": false
}
```

Alternativa: sustituir `track_id` por `"text": "Leaving home and missing my family"`.
`text`: 1–10 000 caracteres, no blanco. `strategy`: `sgns` o `tfidf`, sin fusión,
LDA ni pesos provisionales. `top_k`: 1–50; `max_per_artist`: null o 1–50.
Sin filtro de artista por defecto en API; la web solicita máximo uno.
Campos desconocidos se rechazan. Audio/Mixto o exclusión de covers solicitados:
409; ID inexistente: 404; entrada inválida/OOV: 422; release ausente: 503.
No hay endpoints de evaluación ni audio implementados.

Respuesta: `query`, `mode`, `strategy`, `metric`, `space_id`, `release_id`,
`catalog_version`, `candidate_splits`, `scope`, `items`, `total_returned`,
`elapsed_seconds`, `warnings`. Cada ítem incluye `id`, `track_id`, `lyrics_id`,
título/artista, metadatos originales, split, capacidades, `score` coseno y
`shared_terms` (hasta ocho términos ordenados por producto TF-IDF).
Los cosenos no son probabilidades ni scores calibrados entre estrategias.
Si no hay vecinos léxicos positivos se devuelve una lista vacía.

**Identidad:** `id = track_id = lyrics_id` es un alias público estable de la letra
canónica en este catálogo textual, no de una grabación FMA. Se conservan los IDs
y metadatos exportados; no se crean vínculos de grabación, portadas o licencias.
Las variantes continúan como ítems del corpus si E5 las conserva; la procedencia
completa sigue en los artefactos canónicos de E1/E5. No hay detección de covers.
No se limita el catálogo a las 886 coincidencias de audio.

## Almacenamiento y coste

`artifacts/releases/lyrics-serving-v1/` queda fuera de Git. Cada shard contiene
SQLite con FTS5 y metadatos, matriz float32 y CSR TF-IDF mapeables. Los vectores
de palabras congelados se incluyen en el release; la API no abre pickles/modelos.
La construcción usa un lock exclusivo, lotes de 2048, directorio temporal y rename
por shard; se reanuda por shards completos, reiniciando sólo el incompleto.
El manifiesto final se publica al terminar y contiene firmas SHA-256, dimensiones,
conteos y espacio. No ejecutar dos escritores; si un apagado deja el lock,
comprobar primero que el PID guardado no sigue construyendo antes de retirarlo.
Para cambiar de fuente/espacio utilizar otro `--target`; no reutilizar un release
activo durante la construcción. `SONORA_TEXT_RELEASE` permite elegir otra ruta.

Arranque: se validan identidad de manifiestos, espacio común, conteos, tamaños y
hashes del vocabulario y vectores de palabras. Los hashes de todos los archivos
grandes se auditan fuera de las peticiones con `verify_text_release.py --hashes`.
La API conserva conexiones y mapas; recorre los vectores numéricos por bloques,
pero sólo obtiene metadatos de candidatos que pueden entrar al top-k. Ranking
exacto, desempate por ID descendente, exclusión de semilla y no disponibles,
filtros de split y límite por artista; no se construye N×N ni se releen Parquet.
Un lock de servicio serializa consultas para acotar memoria. Un worker.

El catálogo completo usa vectores congelados de los tres splits para exploración.
La comprobación de referencia utiliza semilla validation y candidatos train;
no se eligen modelos/pesos mediante test ni se mide relevancia humana.

## Verificación reproducible

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts/verify_text_release.py --hashes --reference
# Con el servidor en ejecución y Playwright + Edge instalados:
.venv\Scripts\python.exe scripts/verify_text_web.py
```

Resultados locales en `runtime/text_catalog_benchmark.json` y
`runtime/text_web_browser.json`, capturas `runtime/text_web_1440.png` y
`runtime/text_web_390.png`. La auditoría mide latencia/RSS y coincidencia con la
referencia; no accuracy ni relevancia. La suite incluye fixtures sintéticos
identificados y la comprobación real va por separado.

Música, Mixto, exploración/diversidad adicional y covers siguen no disponibles.
E3/E4/H12 y evaluación humana continúan pendientes; esta entrega no cierra todo
el producto multimodal ni la revisión académica.
