# Entrega de SONORA para ChatGPT

El paquete reúne un Markdown principal, una imagen usada en el artículo, instrucciones y evidencia verificable. No es un artículo terminado ni un PDF ya compilado.

## Qué adjuntar

Opción recomendada: adjunta SONORA_PARA_CHATGPT.zip, solicita que se extraiga y pega el contenido de PROMPT_PARA_CHATGPT.md. El ZIP contiene este directorio completo.

Si prefieres adjuntar archivos por separado, los mínimos son:

1. SONORA_MANUSCRITO_Y_EVIDENCIAS.md: único documento de lectura principal, con manuscrito y controles separados.
2. figuras/e1_longitud_por_tag.png: única figura actualmente incorporada.
3. PROMPT_PARA_CHATGPT.md: instrucciones; también puedes pegarlas como mensaje.

Para permitir fact checks contra los notebooks, adjunta además SONORA_FUENTES_APOYO.zip, que contiene fuentes/ con snapshots E1–E5 y los archivos de soporte seleccionados. No es necesario adjuntarlo por separado si ya entregaste el ZIP principal. Si el entorno de destino no abre ZIP, adjunta individualmente los notebooks de fuentes/notebooks/evidencias/ y los JSON que necesite consultar.

## Qué contiene y qué falta

La PARTE I del Markdown reúne Introducción, Corpus y referencias. La PARTE II reúne estado, revisión crítica, cifras, citas por celda e inventario de figuras. Sólo la PARTE I se destina al cuerpo del PDF. No se han redactado aún el resto de los análisis, el resumen definitivo ni las conclusiones. Se conservaron sus pendientes para evitar que la conversión los oculte.

Las citas de notebook usan índices de celda desde cero. La figura procede de E1 celda 28; su ordinal desde uno, ID y ejecución se distinguen en el documento. Los resultados documentales, las revalidaciones propias y las revisiones humanas pendientes permanecen separados.

No se incluyeron el corpus completo, audios, secretos, modelos binarios ni imágenes candidatas que el artículo no utiliza. Los documentos y notebooks copiados conservan su contenido y sus hashes. Las rutas originales que aparezcan dentro de esos snapshots pertenecen al repositorio SONORA; no necesariamente están todas incluidas. Sólo los enlaces del Markdown principal se prepararon como entrada portable.

MANIFIESTO_PAQUETE.json registra los archivos, sus hashes y la hora de empaquetado. Este paquete es una fotografía de la entrega actual; los cambios posteriores del artículo necesitan volver a empaquetarse.
