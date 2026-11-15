Trabaja como ingeniero principal de SONORA dentro del repositorio existente.
La raíz de Windows es B:\University\2027-1\SONORA y el remoto esperado es
https://github.com/BrunoRuizJuar/Sonora.git. Si estoy en WSL, descubre la ruta montada
equivalente; no asumas que B: equivale siempre a /mnt/b. Comprueba cwd y git antes de escribir.

Primero lee AGENTS.md y CLAUDE.md existentes, si los hay, y los archivos en
docs/handoff/SONORA_Contexto_Claude/ en este orden:
1. REQUISITOS_SONORA.md (versión 1.2: especificación vigente).
2. ESTADO_Y_DATOS.md.
3. ARQUITECTURA_ACTUAL.md.
4. SIGUIENTE_ETAPA.md.

Lee después el código y configuración relevantes. Los documentos anteriores del repositorio
pueden mencionar Next.js, MusicBrainz/AcousticBrainz como núcleo, FMA sin variante elegida
o PLN sólo sobre audio: esas decisiones están sustituidas por la versión 1.2.
Revisa diferencias antes de reconciliar docs/REQUIREMENTS.md y arquitectura; preserva cambios
locales válidos. Integra instrucciones duraderas en CLAUDE.md si conviene, sin borrar las existentes.

Objetivo: recomendador de canciones basado en contenido, de ítem a ítem, con Letras, Audio
y Mixto y un peso configurable. Dashboard A/B con reproductores, letras, similitudes por
embeddings, LDA y audio, tópicos y descriptores. Interfaz en español, corpus inicial inglés.
TF-IDF es baseline; embeddings propios y LDA son parte del trabajo. No hay historial real
para justificar filtrado colaborativo. No cambies el diseño web aprobado.

Decisiones obligatorias:
- PLN abarca TODO el corpus de letras válidas en inglés de los diez Parquet de Genius,
  tras limpieza/deduplicación documentada. No limitar a las 886 pistas con audio.
- Las muestras sirven para desarrollo, auditoría y figuras; no sustituyen métricas globales.
  POS, lemas y dependencias también deben procesarse por lotes sobre ese corpus limpio.
- FMA Medium es la selección de audio: clips de 30 segundos. Comprobar archivos locales.
- Mantener todas las coincidencias exactas de título Y artista normalizados: 886 pistas
  Medium, incluidas 99 con clave repetida; 850 filas Genius distintas. No descartarlas por repetición.
- Fuzzy separado para revisión. Conservar candidato no significa validar letra/audio.
- Corpus y catálogo de demo comparten IDs y grupos. Split objetivo 70 train / 20 test /
  10 validation, agrupando letras idénticas y versiones relacionadas antes del reparto.
- Ajustar IDF, vocabulario aprendido, embeddings, tópicos y escaladores sólo en train;
  elegir hiperparámetros con validation; test queda para evaluación final.
- Audio: Fourier/FFT y STFT documentadas, ritmo, energía, timbre y armonía. Resultados
  referidos al segmento medido, sin convertir similitud en porcentaje de gusto.
- Nunca inventar métricas, licencias, idiomas, audio disponible o resultados ejecutados.

TAREA ACTUAL: implementar la preparación reproducible del corpus completo y la vinculación
de la demo, según SIGUIENTE_ETAPA.md. No te detengas en un plan: inspecciona esquema real,
implementa CLI y pruebas relevantes, ejecuta un smoke test y deja comandos exactos para la
corrida completa. Ejecuta el corpus completo si el entorno y los recursos lo permiten;
en caso contrario informa claramente qué se ejecutó, qué falta y el comando para continuarlo.
No entrenes todavía modelos ni migres frontend o bases como parte de esta etapa.

Los datos deben procesarse por batches y guardarse incrementalmente en Parquet; no cargues
los diez archivos completos con pandas ni construyas matrices N×N. El trabajo debe poder
reanudarse y no debe reemplazar entradas originales. Guarda conteos y motivos de exclusión.
Antes de diseñar filtros, inspecciona columnas y contenido real: no supongas que hay language,
lyrics, year o un ID único. Si no hay idioma confiable, implementa detección documentada,
conservar incertidumbre y reportar el filtro; no uses presencia de caracteres ASCII como detector.
Preserva versos, estrofas, contracciones y negaciones en las vistas adecuadas; no colapses
todo el texto a una bolsa de palabras antes de las prácticas sintácticas.

Respeta el repo existente y cambios del usuario. No borres datos ni vuelvas a descargarlos
si ya existen. No publiques corpus, audio, claves o modelos grandes en Git. Puedes editar
código/documentos y ejecutar verificaciones locales de esta tarea; no hagas push ni despliegue
sin instrucción. Evita pedir confirmación por decisiones reversibles dentro del alcance.

Si usamos varios paneles del multiplexor, mantén una sola instancia que escriba sobre el repo.
Otros paneles pueden monitorizar logs/recursos o revisar resultados en modo lectura. Si se
decide desarrollar con varios agentes, asigna archivos separados o worktrees y un integrador;
no lances dos procesos a escribir la misma salida, lockfile o partición Parquet.

Al terminar muestra: archivos cambiados, esquema detectado, comandos Windows/WSL efectivos,
pruebas y ejecuciones realizadas, conteos reales, pendientes y el siguiente paso. Distingue
siempre resultados del dataset real frente a fixtures de prueba.
