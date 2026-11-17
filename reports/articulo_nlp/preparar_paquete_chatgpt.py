"""Empaqueta borrador y fuentes para conversión externa a LaTeX/PDF.
Sólo escribe en reports/articulo_nlp/. No cambia archivos originales ni convierte
el borrador parcial en un artículo terminado.
"""
from pathlib import Path
import json,re,shutil,hashlib,zipfile
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'reports/articulo_nlp'
DEST=BASE/'paquete_chatgpt'
DEST.mkdir(parents=True,exist_ok=True)
def write(name,txt):
    p=DEST/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(txt.strip()+'\n',encoding='utf-8')
def read(name):return (BASE/name).read_text(encoding='utf-8')
copied={}
def include(p):
    p=p.resolve()
    assert p.is_relative_to(ROOT.resolve()),p
    if p.is_relative_to((BASE/'figuras').resolve()):dest=Path('figuras')/p.name
    elif p.is_relative_to(BASE.resolve()):dest=Path('fuentes/articulo')/p.name
    else:dest=Path('fuentes')/p.relative_to(ROOT)
    if p not in copied:
        assert p.is_file()
        assert p.suffix in {'.md','.json','.ipynb','.py','.yaml','.png'}
        assert p.stat().st_size<20_000_000,'No incluir artefactos grandes'
        target=DEST/dest;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,target)
        copied[p]=dest.as_posix()
    return copied[p]

def portable(name):
    source=BASE/name;txt=source.read_text(encoding='utf-8')
    def link(match):
        label,target=match.groups()
        if target.startswith(('https:','http:','#')):return match.group(0)
        p=(source.parent/target.split('#')[0]).resolve()
        if not p.is_file():return f'{label} (`{target}`; archivo externo al paquete)'
        return f'[{label}]({include(p)})'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)',link,txt)

body=portable('ARTICULO_COMPLETO.md')
appendices=[('00_ESTADO_ARTICULO.md','A. Alcance y pendientes'),('00_FACT_CHECKS.md','B. Veredictos por hallazgo'),('00_REGISTRO_RESULTADOS.md','C. Registro de cifras y denominadores'),('00_CITAS_NOTEBOOKS.md','D. Notebooks, índices de celda e identificadores'),('00_INVENTARIO_FIGURAS.md','E. Procedencia de imágenes')]
master=['# SONORA — Manuscrito y evidencias para conversión a LaTeX/PDF',
'''## Cómo utilizar este documento

Este es el archivo de entrada principal. Contiene TODO el texto del artículo redactado hasta esta entrega, seguido de controles para verificarlo. El manuscrito sigue siendo parcial: se han redactado Introducción, Corpus y referencias; no se han redactado las secciones 03 y 05–12 ni el resumen definitivo. No rellenar esas secciones con información supuesta. Autoría, afiliación y plantilla institucional no confirmadas.

La PARTE I es el contenido que debe convertirse al cuerpo del PDF. La PARTE II contiene material editorial de apoyo: no incorporarlo íntegramente al cuerpo del artículo. Puede usarse para notas de trazabilidad o un anexo técnico claramente separado, si resulta necesario. No convertir actas de revisión entre sesiones en referencias científicas.

Las citas bibliográficas conservan [1]–[18]. Los localizadores E1–E5 y «celda» pertenecen a esa evidencia; la celda empieza en cero e incluye Markdown. No confundirla con In[n]. Mantener nombre del notebook y celda en las citas o en notas al pie. La figura incluida procede del PNG externo generado por E1, celda 28 (ordinal 29, ID 6e450d0a), copiado sin modificación. No afirmar que fue extraída del output incrustado.

Se adjuntan snapshots de los cinco notebooks y archivos de apoyo en fuentes/. Los textos originales completos, MP3 y modelos binarios no forman parte de este paquete. Los enlaces relativos de este documento apuntan a archivos incluidos. En el PDF, las rutas de fuentes locales deben tratarse como localizadores documentales, no como enlaces públicos que el lector pueda abrir sin los adjuntos.

## PARTE I — MANUSCRITO DISPONIBLE
''',body,'---\n\n## FIN DE LA PARTE I\n\n## PARTE II — EVIDENCIA Y CONTROLES EDITORIALES\n\nLos siguientes documentos apoyan la conversión; no son secciones nuevas del artículo.']
for name,title in appendices:
    master.extend(['\n---\n\n### '+title,portable(name)])
write('SONORA_MANUSCRITO_Y_EVIDENCIAS.md','\n\n'.join(master))

# Asegurar snapshots de los cinco notebooks y evidencia reproducible resumida.
for p in sorted((ROOT/'notebooks/evidencias').glob('E[1-5]_*.ipynb')):include(p)
for name in ['resultados_verificados.json','revalidacion_independiente.json','revision_cruzada_sonora.json','verificacion_segunda_entrega.json','fuentes_segunda_entrega.json','revalidar_hallazgos.py']:
    include(BASE/name)

write('PROMPT_PARA_CHATGPT.md','''# Prompt para pegar en ChatGPT

Convierte el borrador de SONORA adjunto a un proyecto LaTeX y un PDF académico en español. Usa SONORA_MANUSCRITO_Y_EVIDENCIAS.md como entrada principal y consulta fuentes/ para cotejar las afirmaciones cuando sea necesario. Lee primero la distinción entre PARTE I (manuscrito) y PARTE II (controles editoriales).

El manuscrito es PARCIAL. Maqueta sólo las secciones existentes y conserva las marcas [PENDIENTE]. No inventes resultados, antecedentes, autoría, afiliación, fechas institucionales, resumen ni conclusiones. No presentes el PDF como artículo final. No uses los controles editoriales para rellenar secciones no redactadas ni conviertas una propuesta en ejecución. Si falta un elemento de plantilla, utiliza un diseño académico neutro de una columna, papel A4 y márgenes de 2,5 cm.

Mantén todas las cifras, denominadores, particiones, unidades, alcances y límites. Conserva especialmente: los 180 tokens reconciliados en 56 letras; separación de grupos registrada; demo 886/850/849 como resultado histórico y ausencia de sus archivos en las rutas comprobadas; contextos E5 de una muestra de 2000 validation frente a ajuste/exportación completos. No conviertas similitud en gusto, precisión lingüística o calidad demostrada del recomendador.

Usa un único sistema bibliográfico numérico y conserva la correspondencia [1]–[18]. Puedes usar thebibliography o referencias.bib, con metadatos sólo de las referencias suministradas. No inventes autores ni DOI. Las fuentes internas deben identificarse como artefactos del proyecto, distintas de publicaciones metodológicas. Conserva las citas E1–E5, notebook y celda, inline o mediante notas al pie; la celda comienza en cero, no es el contador In[n]. Las rutas locales se muestran como localizadores o se enlazan dentro del material adjunto; no son URLs públicas.

Incluye únicamente las imágenes que aparecen en la PARTE I: figuras/e1_longitud_por_tag.png. Mantén su pie autosuficiente, universo, ejes, observación y límites, junto al origen E1/celda 28. No generes figuras artificiales ni incorpores las candidatas del inventario sin una solicitud posterior. Usa imágenes con proporción conservada, leyendas legibles y referencia desde el texto. No recrees la curva a partir de una descripción.

Explica o conserva las explicaciones de conceptos y fórmulas; mantén redacción formal y cohesionada. Mejora sólo maquetación y correcciones tipográficas inequívocas. Para cambios de contenido, proporciona una lista separada de propuestas y no los apliques silenciosamente. No repitas en el cuerpo todas las tablas de auditoría de la PARTE II.

Prepara main.tex, los archivos auxiliares que realmente uses, la carpeta figuras/ y, si puedes compilar, SONORA_borrador.pdf. Usa LuaLaTeX o XeLaTeX y fuentes disponibles, pues hay español, Unicode y caracteres como İ; renderiza puntos de código/rutas en un formato que no pierda símbolos. Escapa correctamente _, %, &, #, llaves y barras en LaTeX. Las tablas deben caber en el ancho de página sin fuente ilegible. Usa \u005cpath o \u005cnolinkurl para rutas y \u005cincludegraphics para imágenes. Indica el comando de compilación real.

Si tu entorno permite ejecutar herramientas, compila, revisa errores, referencias sin resolver, imágenes ausentes y desbordamientos, y entrega el PDF real junto con las fuentes en un ZIP. Si no puedes compilar, entrega las fuentes y las instrucciones, indicando claramente que el PDF no fue generado. No simules una compilación ni un enlace de descarga.

La entrega debe contener: proyecto LaTeX descargable, PDF si realmente se compiló, instrucciones mínimas y una lista breve de pendientes científicos conservados. No declarar cerrado el artículo.
''')

write('LEEME.md','''# Entrega de SONORA para ChatGPT

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
''')

allfiles=sorted(p for p in DEST.rglob('*') if p.is_file() and p.name!='MANIFIESTO_PAQUETE.json')
manifest={'generated_utc':datetime.now(timezone.utc).isoformat(),'status':'borrador parcial; no LaTeX/PDF generado','main':'SONORA_MANUSCRITO_Y_EVIDENCIAS.md','source_root':str(ROOT),'files':[{'path':p.relative_to(DEST).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in allfiles]}
write('MANIFIESTO_PAQUETE.json',json.dumps(manifest,ensure_ascii=False,indent=2))

# Verificar enlaces del documento principal y copia de figura, sin revisar pipelines.
main=(DEST/manifest['main']).read_text(encoding='utf-8')
missing=[]
for target in re.findall(r'\]\(([^)]+)\)',main):
    if target.startswith(('http:','https:','#')):continue
    if not (DEST/target.split('#')[0]).is_file():missing.append(target)
assert not missing,missing
assert (DEST/'figuras/e1_longitud_por_tag.png').read_bytes()==(BASE/'figuras/e1_longitud_por_tag.png').read_bytes()
assert sum(1 for p in (DEST/'fuentes/notebooks/evidencias').glob('*.ipynb'))==5
for name,selection in [('SONORA_PARA_CHATGPT.zip',list(DEST.rglob('*'))),('SONORA_FUENTES_APOYO.zip',list((DEST/'fuentes').rglob('*')))]:
    path=BASE/name
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(selection):
            if p.is_file():z.write(p,p.relative_to(DEST).as_posix())
    with zipfile.ZipFile(path) as z:assert z.testzip() is None
    print(name,path.stat().st_size,'bytes')
print('Packaged files:',len(manifest['files'])+1,'main bytes:',(DEST/manifest['main']).stat().st_size,'broken main links:',missing)
