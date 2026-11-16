# SONORA — instrucciones duraderas para agentes

- Especificación vigente: `docs/REQUIREMENTS.md` (v1.2). Contexto de traspaso:
  `docs/handoff/SONORA_Contexto_Claude/`. Documentos de `docs/` con la nota "anterior a v1.2"
  ceden ante ella.
- Raíz Windows actual `B:\SONORA` (equipo de continuación); remoto `https://github.com/BrunoRuizJuar/Sonora.git`.
  En WSL, descubrir la ruta montada real; no asumir `/mnt/b`. No hacer push ni desplegar sin pedirlo.
- Python: usar el venv existente `.venv` (Python 3.14). Pruebas: `.venv\Scripts\python.exe -m pytest -q`.
- Recomendador de contenido ítem a ítem (Letras, Audio, Mixto con alpha = peso de letras).
  No llamarlo filtrado colaborativo. Interfaz en español; corpus inicial en inglés.
- PLN sobre TODO el corpus limpio de letras en inglés de los diez Parquet Genius
  (`docs/CORPUS_LETRAS.md`), no sólo sobre las 886 pistas FMA Medium. Las muestras son para
  desarrollo/figuras y deben declararse como tales.
- Ajustar IDF, vocabularios, embeddings, tópicos y escaladores sólo con `train`; elegir
  hiperparámetros con `validation`; `test` sólo para evaluación final. Splits por grupo en
  `data/processed/splits/<run_id>/lyrics_splits.parquet`; la demo hereda el split de su letra.
- Datos: nunca modificar `data/raw/`; procesar por lotes con escrituras atómicas y reanudables;
  no cargar los diez Parquet completos en memoria ni construir matrices N×N.
  No versionar corpus, audio, modelos ni claves (`.gitignore` ya lo cubre).
- No inventar métricas, licencias, idiomas, audio disponible ni resultados: distinguir siempre
  datos reales de fixtures sintéticos de prueba y subconjuntos de smoke test.
- No cambiar el diseño web aprobado (sepia rojizo, terracota, viejo oeste; Smokum/Rubik
  Distressed/Ovo; banners día [06:00,18:00)).
- Un solo proceso escribe en una misma `--run-id` (lock en `runtime/locks/`).
- Estado y siguiente paso más reciente: `docs/handoff/ESTADO_2026-11-14.md` (añadido 2026-11-14).
  Prioridad del usuario: PLN completo (E1–E5) antes del audio; un solo trabajo pesado a la vez.

- Continuación más reciente: `docs/handoff/MIGRACION_2026-11-16.md`; E3 ejecutada, revisión final pendiente; nuevo equipo 25 GB RAM.
- E3: revisión asistida y lista para revisión del autor en `docs/E3_REVISION.md`, también
  incorporada al notebook por `build_e3.py`. No cerrar E3 hasta la revisión personal del usuario.
- E4 implementada usando anotaciones existentes; continuación en
  `docs/handoff/E4_2026-11-16.md`, revisión del autor en `docs/E4_REVISION.md`.
  El usuario autorizó E4 conservando E3 pendiente de su revisión personal.
- E4: cierre técnico/documental completado. Pendientes de revisión humana del proyecto
  centralizados en `TODO-human.md`; no marcar casillas ni aprobar contenido en nombre del usuario.
