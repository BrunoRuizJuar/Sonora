# Contrato API propuesto

Prefijo `/api/v1`. Los endpoints de producto descritos aquí son diseño pendiente de implementación.
El scaffold sólo implementa las dos rutas de salud.

| Método | Ruta | Función |
|---|---|---|
| GET | `/health/live` | Proceso API activo |
| GET | `/health/ready` | Catálogo/modelos/dependencias listos; 503 mientras no se integren |
| GET | `/tracks/search?q=...&limit=20` | Búsqueda por título y artista, con cursor si se agrega paginación |
| GET | `/tracks/{track_id}` | Metadatos y capacidades de una canción |
| GET | `/catalog/stats` | Versiones activas y cobertura por modalidad |
| POST | `/recommendations` | Ranking de canciones |
| POST | `/evaluations` | Juicio de una sesión de evaluación |

## Solicitud de recomendación

```json
{
  "track_id": "example-internal-id",
  "mode": "mixed",
  "lyrics_weight": 0.7,
  "exploration": 0.2,
  "top_k": 10,
  "max_per_artist": 1,
  "exclude_known_covers": true,
  "seed": 42
}
```

`mode`: `lyrics`, `audio` o `mixed`. En Mixto el peso acústico es `1-lyrics_weight`.
En Letras/Música los pesos efectivos son 1/0 o 0/1 y se reflejan en la respuesta.
`top_k` entre 1 y 50; controles numéricos entre 0 y 1. La semilla es opcional para reproducibilidad.
Estos campos se validan en el esquema Python incluido, que todavía no está conectado a un endpoint.

## Respuesta de diseño

```json
{
  "query_track_id": "example-internal-id",
  "mode": "mixed",
  "catalog_version": "example-v1",
  "model_versions": {"text": "example-text-v1", "audio": "example-audio-v1"},
  "effective_weights": {"lyrics": 0.7, "audio": 0.3},
  "applied_filters": {"max_per_artist": 1, "exclude_known_covers": true},
  "total_returned": 0,
  "items": [],
  "warnings": []
}
```

Cada item incluirá track_id, título, artista, capacidades, scores por señal y razones disponibles.
Los ejemplos vacíos no representan resultados ejecutados. Si los filtros dejan menos de K,
se devuelve el número real y una explicación. No se inventan canciones ni se relajan filtros
sin reflejarlo al usuario.

Errores previstos: 404 canción inexistente, 409 modalidad no disponible o release incompatible,
422 parámetros inválidos y 503 dependencias/artefactos no preparados. Un fallo de Redis puede
omitir la caché y continuar; un fallo del índice necesario no puede producir resultados ficticios.

## Evaluación

Sesión seudónima, query_track_id, candidate_track_id, modo, versiones, parámetros, posición,
relevancia de 0 a 3 y comentario opcional. Se valida que canción y versión pertenecen al
experimento. El identificador de sesión no requiere una cuenta ni un perfil personal.
Las rutas administrativas y de carga masiva se reservan a CLI/operación interna.
