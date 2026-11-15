# Conectar SONORA al recomendador real

La versión entregada es una interfaz estática con datos de muestra. `serve.py` entrega sus archivos y un diagnóstico en `/__sonora_health`; no ejecuta modelos ni implementa las rutas `/api` de esta propuesta.

## Trabajo que falta

1. Construir el catálogo con identificadores estables: título, artista, idioma, composición original y relación entre covers.
2. Preparar los vectores y resultados de similitud de letras y música según los modelos del proyecto.
3. Exponer esos resultados mediante un backend. Mantener claves y archivos del modelo fuera de `public`.
4. Sustituir el arreglo `songs` de `public/app.js` y la selección de muestra de `render()` por llamadas a la API. Las ponderaciones reales deben afectar el ranking, no solo la explicación.
5. Añadir los estados de carga, error y catálogo vacío para las peticiones a la API.

## Contrato sugerido; aún no implementado

`GET /api/search?q=Brillas%20Leon%20Larregui`

Respuesta propuesta:

```json
{
  "songs": [
    {"id": "song_001", "title": "Brillas", "artist": "León Larregui", "language": "es", "cover_url": "/assets/covers/brillas.svg"}
  ]
}
```

`POST /api/recommend`

Solicitud propuesta:

```json
{
  "song_id": "song_001",
  "mode": "mixed",
  "weights": {"lyrics": 0.6, "music": 0.4},
  "exploration": 0.5,
  "max_per_artist": 1,
  "exclude_covers": true,
  "language": "all",
  "limit": 12
}
```

`mode` puede ser `lyrics`, `music` o `mixed`; los pesos mixtos deben sumar 1. `language` puede ser `es`, `en` o `all`. El control actual guarda el porcentaje de música; el de letras se obtiene como 100 menos ese valor. El backend debe validar los parámetros.

Respuesta propuesta:

```json
{
  "seed_id": "song_001",
  "recommendations": [
    {
      "id": "song_002",
      "title": "Canción del catálogo",
      "artist": "Artista del catálogo",
      "language": "es",
      "cover_url": "/assets/covers/eres.svg",
      "reason": "Explicación respaldada por los resultados del modelo."
    }
  ]
}
```

Los nombres genéricos de esa respuesta son un esquema de integración, no resultados reales. Servir la interfaz y la API desde el mismo origen simplifica las peticiones. Si se usan orígenes distintos, habrá que configurar las URL y CORS del backend.

Los guardados actuales son locales. Una base de datos y cuentas solo hacen falta si después se desea sincronizar bibliotecas, registrar evaluaciones o almacenar usuarios.
