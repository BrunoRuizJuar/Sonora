# Continuación en computadora con 25 GB de RAM

## Estado real

E1 y E2 cerradas. E3 implementada y ejecutada en 48 s: notebook
`notebooks/evidencias/E3_morfosintaxis.ipynb`, generador `build_e3.py`, módulo
`sonora.nlp.morphology`, tres figuras y `reports/nlp/lyrics_full_v1/e3_summary.json`.
No se repitió la anotación: se reutilizaron los agregados completos de E2.

E3 reconcilia 1 033 733 693 tokens y 3 155 772 letras. Sin UPOS PUNCT/SYM/SPACE:
954 321 127 tokens; 177 278 975 cambian de forma a lema ignorando mayúsculas (18,5764 %).
Tipos superficiales: 1 503 152; lemas: 1 450 635; reducción descriptiva 3,4938 %.
Esto no mide precisión. Los nueve criterios de ejemplos dirigidos fueron encontrados.

Incluye POS global, porcentajes con denominadores explícitos, tamaños por tag/década,
comparaciones normalizadas, contraste temporal dentro de tag, lemas por POS y ejemplos
trazables tomados del primer archivo de cada shard. La muestra sólo ilustra ejemplos.

**E3 está ejecutada, pero falta revisar cualitativamente cada ejemplo y escribir hallazgos
específicos a partir de las tablas; el texto actual explica mecanismos y limitaciones.
No marcar E3 cerrada todavía.** Revisar también legibilidad de figuras y cobertura E3-01…04.

Pruebas nuevas: 2 aprobadas. Suite completa dentro del sandbox: 28 aprobadas y 12 errores
de preparación por permisos sobre temporales pytest, no fallos de aserción. Se solicitó
repetición con permisos; la herramienta fue interrumpida y su resultado no quedó recogido.
Repetir la suite en la nueva máquina. Última suite completa previa a E3: 38 aprobadas.

## Clonar y preparar

```powershell
git clone https://github.com/BrunoRuizJuar/Sonora.git
cd Sonora
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install -e '.[corpus,nlp,data]'
.venv\Scripts\python.exe -m pip install spacy==3.8.18 matplotlib nbformat nbclient ipykernel
.venv\Scripts\python.exe -m spacy download en_core_web_sm-3.8.0
.venv\Scripts\python.exe -m ipykernel install --user --name sonora --display-name 'SONORA (.venv)'
```

Usar el modelo 3.8.0 para reproducir la anotación; si el comando de descarga no lo resuelve,
instalar el wheel oficial de esa versión. No sustituirlo silenciosamente por otro modelo.
No copiar `.venv`: recrearla en destino. La nueva raíz puede ser distinta a B:; trabajar
desde ella y actualizar referencias de entorno. El código usa rutas relativas al proyecto.

## Datos que Git NO transporta

Copiar conservando estructura desde la máquina original (sin sobrescribir entradas distintas):

- `data/processed/lyrics/lyrics_full_v1/`: corpus canónico y correspondencias.
- `data/processed/splits/lyrics_full_v1/`: particiones por grupo.
- `data/processed/nlp/lyrics_full_v1/`: anotación spaCy (~11 GB), doc_stats, léxico,
  agregados frequency y n-gramas. **Necesario para continuar E3/E4 sin recalcular.**
- `data/raw/` e `data/interim/` para reproducibilidad completa de la ingesta, y audio cuando
  se retome esa fase. Nunca modificar raw.
- Modelos KenLM en WSL: `/home/theas/sonora_lm/lyrics_full_v1/` y, si se quiere reutilizar
  el ejecutable compilado, `~/opt/kenlm`. Son externos al clon; sólo copiar el binario no
  prepara WSL ni sus dependencias. Los resultados medidos permanecen en manifiestos/notebook.

Verificar tamaños/checksums de las copias y mantener los manifiestos del repositorio.
No ejecutar `--force` ni borrar salidas para resolver una copia incompleta.

## Retomar

1. Leer `CLAUDE.md`, este documento, `ESTADO_2026-11-14.md` y REQUIREMENTS §5.3.
2. Verificar rutas, RAM disponible y archivos transferidos. Con 25 GB seguir con un solo
   trabajo pesado a la vez; no aumentar workers sin medir memoria.
3. Ejecutar `.venv\Scripts\python.exe -m pytest -q` y revisar el notebook E3 existente.
4. Si hace falta regenerar: `.venv\Scripts\python.exe notebooks\evidencias\build_e3.py`.
5. Terminar revisión e interpretación E3 y actualizar documentos; luego E4, E5/modelos,
   finalmente audio. Ajustar sólo train; elegir con validation; evaluación final en test.

No hay agentes delegados ni trabajos pesados pendientes autorizados para la nueva máquina.
