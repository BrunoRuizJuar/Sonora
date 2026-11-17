# Prompt para pegar en ChatGPT

Convierte el borrador de SONORA adjunto a un proyecto LaTeX y un PDF académico en español. Usa SONORA_MANUSCRITO_Y_EVIDENCIAS.md como entrada principal y consulta fuentes/ para cotejar las afirmaciones cuando sea necesario. Lee primero la distinción entre PARTE I (manuscrito) y PARTE II (controles editoriales).

El manuscrito es PARCIAL. Maqueta sólo las secciones existentes y conserva las marcas [PENDIENTE]. No inventes resultados, antecedentes, autoría, afiliación, fechas institucionales, resumen ni conclusiones. No presentes el PDF como artículo final. No uses los controles editoriales para rellenar secciones no redactadas ni conviertas una propuesta en ejecución. Si falta un elemento de plantilla, utiliza un diseño académico neutro de una columna, papel A4 y márgenes de 2,5 cm.

Mantén todas las cifras, denominadores, particiones, unidades, alcances y límites. Conserva especialmente: los 180 tokens reconciliados en 56 letras; separación de grupos registrada; demo 886/850/849 como resultado histórico y ausencia de sus archivos en las rutas comprobadas; contextos E5 de una muestra de 2000 validation frente a ajuste/exportación completos. No conviertas similitud en gusto, precisión lingüística o calidad demostrada del recomendador.

Usa un único sistema bibliográfico numérico y conserva la correspondencia [1]–[18]. Puedes usar thebibliography o referencias.bib, con metadatos sólo de las referencias suministradas. No inventes autores ni DOI. Las fuentes internas deben identificarse como artefactos del proyecto, distintas de publicaciones metodológicas. Conserva las citas E1–E5, notebook y celda, inline o mediante notas al pie; la celda comienza en cero, no es el contador In[n]. Las rutas locales se muestran como localizadores o se enlazan dentro del material adjunto; no son URLs públicas.

Incluye únicamente las imágenes que aparecen en la PARTE I: figuras/e1_longitud_por_tag.png. Mantén su pie autosuficiente, universo, ejes, observación y límites, junto al origen E1/celda 28. No generes figuras artificiales ni incorpores las candidatas del inventario sin una solicitud posterior. Usa imágenes con proporción conservada, leyendas legibles y referencia desde el texto. No recrees la curva a partir de una descripción.

Explica o conserva las explicaciones de conceptos y fórmulas; mantén redacción formal y cohesionada. Mejora sólo maquetación y correcciones tipográficas inequívocas. Para cambios de contenido, proporciona una lista separada de propuestas y no los apliques silenciosamente. No repitas en el cuerpo todas las tablas de auditoría de la PARTE II.

Prepara main.tex, los archivos auxiliares que realmente uses, la carpeta figuras/ y, si puedes compilar, SONORA_borrador.pdf. Usa LuaLaTeX o XeLaTeX y fuentes disponibles, pues hay español, Unicode y caracteres como İ; renderiza puntos de código/rutas en un formato que no pierda símbolos. Escapa correctamente _, %, &, #, llaves y barras en LaTeX. Las tablas deben caber en el ancho de página sin fuente ilegible. Usa \path o \nolinkurl para rutas y \includegraphics para imágenes. Indica el comando de compilación real.

Si tu entorno permite ejecutar herramientas, compila, revisa errores, referencias sin resolver, imágenes ausentes y desbordamientos, y entrega el PDF real junto con las fuentes en un ZIP. Si no puedes compilar, entrega las fuentes y las instrucciones, indicando claramente que el PDF no fue generado. No simules una compilación ni un enlace de descarga.

La entrega debe contener: proyecto LaTeX descargable, PDF si realmente se compiló, instrucciones mínimas y una lista breve de pendientes científicos conservados. No declarar cerrado el artículo.
