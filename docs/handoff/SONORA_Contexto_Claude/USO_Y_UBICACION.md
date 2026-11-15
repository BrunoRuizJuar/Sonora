# Cómo incorporar este contexto

## ZIP de revisión que ya recibiste

Guarda `SONORA_Revision_Matching.zip` en:
`B:\University\2027-1\SONORA\data\interim\matching\`.
Extráelo ahí: aparecerá `SONORA_Revision_Matching\` con cinco archivos.
Es un resultado de cruce/revisión; no son los audios ni los Parquet Genius y no va en `data/raw`.
El JSON `medium_prioritarios.json` debe indicar count=886 y distinct_genius_rows=850.

## Este nuevo ZIP de contexto

Guarda `SONORA_Contexto_Claude.zip` donde descargas archivos y extráelo en:
`B:\University\2027-1\SONORA\docs\handoff\`.
Ya contiene una carpeta raíz `SONORA_Contexto_Claude`, así que la ruta final será:
`docs\handoff\SONORA_Contexto_Claude\PROMPT_INICIO.md`.
No copies manualmente todos los archivos a la raíz ni reemplaces un CLAUDE.md/AGENTS.md existente.

También se incluye una copia exacta del ZIP de revisión dentro de `matching/`, por si quieres
usarla en lugar de descargar otra vez el ZIP anterior.

Desde PowerShell, después de descargar el nuevo ZIP:

```powershell
Set-Location 'B:\University\2027-1\SONORA'
New-Item -ItemType Directory -Force '.\docs\handoff', '.\data\interim\matching' | Out-Null

# Ajusta sólo esta ruta a donde hayas descargado el nuevo archivo.
$contextZip = Join-Path $env:USERPROFILE 'Downloads\SONORA_Contexto_Claude.zip'
Expand-Archive -LiteralPath $contextZip -DestinationPath '.\docs\handoff' -Force

$reviewZip = '.\docs\handoff\SONORA_Contexto_Claude\matching\SONORA_Revision_Matching.zip'
Copy-Item -LiteralPath $reviewZip -Destination '.\data\interim\matching\SONORA_Revision_Matching.zip' -Force
Expand-Archive -LiteralPath '.\data\interim\matching\SONORA_Revision_Matching.zip' `
    -DestinationPath '.\data\interim\matching' -Force

Get-Content '.\docs\handoff\SONORA_Contexto_Claude\PROMPT_INICIO.md' -Raw
```

Estos dos ZIP generados para el contexto usan deflate estándar, distinto del archivo FMA que
antes falló por método de compresión. El comando -Force sólo reemplaza archivos de este paquete
de contexto y la revisión con los mismos nombres; conserva por separado cualquier edición propia.

## Claude y el multiplexor

Abre Claude dentro de la raíz SONORA usando tu instalación habitual y pega PROMPT_INICIO.md.
El paquete no instala ni configura Claude ni el multiplexor llamado “herdr”; no asume que esté
instalado ni inventa sus flags. Si corre dentro de WSL, primero confirma desde su shell la ruta
montada real del proyecto y abre allí el repo, sin crear una segunda copia accidental.

Organización inicial sugerida de paneles:

| Panel | Trabajo |
|---|---|
| 1 | Claude: único escritor de código en el repo |
| 2 | Ejecutar pipeline y consultar logs |
| 3 | Monitorizar RAM/disco/GPU y revisar outputs en lectura |

No correr dos instancias del mismo pipeline sobre el mismo directorio de salida. No lanzar
dos agentes a modificar el mismo árbol sin asignación de archivos o worktrees. El multiplexor
organiza terminales; el corpus no necesita duplicarse por panel.

## Qué documentos leerá

REQUISITOS_SONORA.md v1.2 es la especificación completa actualizada. Claude debe compararla
con docs/REQUIREMENTS.md y reconciliarla antes de implementar, respetando cambios locales.
ARQUITECTURA_ACTUAL.md resuelve decisiones que pueden haber quedado viejas en documentos
anteriores. SIGUIENTE_ETAPA.md define el trabajo inmediato y sus criterios de aceptación.

No se incluyen corpus, audios, modelos ni credenciales. Tampoco significa que estos documentos
ya estén en GitHub: Claude deberá verificar el checkout y el remoto reales.
