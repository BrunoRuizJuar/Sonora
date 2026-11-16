# Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Todas las pruebas usan datos **sintéticos** generados en `tests/conftest.py` (shards Parquet
pequeños con row groups de 13 filas, una selección demo de 5 pistas y detectores de idioma
falsos), salvo `test_real_detectors_on_tiny_synthetic_texts`, que carga lingua y py3langid reales
sobre dos frases inventadas. Ningún resultado de estas pruebas describe el corpus Genius real.

Cubren: vistas de texto (original intacto, contracciones, negaciones, Unicode, estrofas,
marcadores), reglas de idioma, normalización idéntica al cruce FMA–Genius, localizadores globales
independientes del batch, reanudación tras interrupción sin duplicados ni partes `.tmp`,
rechazo de configuración distinta al reanudar, reconciliación de totales, duplicados con una
canónica, grupos sin fuga entre particiones, demo con varias grabaciones por letra y localizador
erróneo, alcance parcial nunca marcado como completo y lock de un único escritor.

Pendiente para etapas siguientes: invariantes de vectores, capacidades por modo, filtros,
pesos, versiones y recuperación frente a referencia exacta.

E4 añade pruebas sintéticas de ponderación de distancias por arco frente a segmento,
distancia no definida sin arcos, conservación de índices con huecos y detección de ciclos,
cabezas ausentes y múltiples raíces (`tests/unit/test_syntax.py`). No miden precisión del parser.
