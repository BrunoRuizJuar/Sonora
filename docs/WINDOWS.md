# Preparación en Windows

Destino: `B:\University\2027-1\SONORA`.
Repositorio: `https://github.com/BrunoRuizJuar/Sonora.git`.
La letra B: pertenece a tu equipo; esta entrega prepara archivos y un script para ese destino.

## Crear carpetas y asociar Git

Descarga `Initialize-SONORA.ps1`, abre PowerShell en su carpeta y ejecuta:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Initialize-SONORA.ps1
Set-Location 'B:\University\2027-1\SONORA'
git remote -v
git status
```

La opción de ejecución se aplica sólo a ese proceso. El script requiere Git instalado,
valida la unidad y el remoto antes de escribir plantillas. En una carpeta nueva o vacía
clona el repositorio. En una carpeta con trabajo conserva los archivos y el repositorio
existente; si aún no hay Git, lo inicializa y configura `origin` sin mezclar historiales.
Crea archivos que falten y puede ejecutarse otra vez. No descarga datasets, cambia la
rama de un repositorio existente, mezcla ramas, crea commits ni realiza push.

Si la carpeta es nueva y prefieres copiar el historial remoto, también puedes clonar primero
con `git clone https://github.com/BrunoRuizJuar/Sonora.git 'B:\University\2027-1\SONORA'`
y después ejecutar el script. No se debe clonar sobre una carpeta que ya contiene trabajo.
El script no reescribe el historial para reconciliar un repositorio local y uno remoto distintos.

## Importar trabajo existente

Copiar los corpus originales bajo `data/raw/legacy/` y los notebooks bajo `notebooks/legacy/`.
No mover los originales antes de comprobar checksums y que los procesos puedan leer las copias.
Los logos y originales del otro chat van en `design/brand/`; los exports para la web en
`apps/web/public/assets/brand/`.

## API mínima

```powershell
Set-Location 'B:\University\2027-1\SONORA'
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
$env:SONORA_HOME = (Get-Location).Path
.\.venv\Scripts\python.exe -m uvicorn sonora_api.main:app --host 127.0.0.1 --port 8000 --reload
```

Abrir `http://127.0.0.1:8000/docs`. La API puede arrancar sin Docker para comprobar el scaffold.
El frontend aún requiere inicialización de Next.js e incorporación del diseño elegido.

## Infraestructura

Desde la raíz:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
docker compose config --quiet
docker compose up -d couchdb opensearch
```

Completar `COUCHDB_PASSWORD` antes de arrancar. Para la cola, añadir Redis con
`docker compose --profile jobs up -d redis`. Las bases operativas y los índices se crean
durante M1; iniciar contenedores no completa esa fase.

Los volúmenes persistentes de las bases son administrados por Docker Desktop/WSL2;
no necesariamente están físicamente en B:. Los corpus, modelos, configuración y código sí
se organizan bajo la carpeta del proyecto. Si se exige que también los volúmenes vivan en B:,
hay que configurar por separado la ubicación de datos de Docker Desktop y medir rendimiento.

La documentación de OpenSearch pide al menos 4 GB asignados a Docker Desktop. Para el stack
combinado debe medirse el consumo y ajustar memoria y tamaño del catálogo. Con WSL2 puede
ser necesario establecer `vm.max_map_count=262144` en el entorno de Docker. Consultar la
[guía oficial](https://docs.opensearch.org/latest/install-and-configure/install-opensearch/docker/)
según la versión instalada, antes de cambiar parámetros del host.

El compose enlaza servicios a localhost y desactiva seguridad de OpenSearch para desarrollo.
La publicación por enlace utiliza otra configuración con HTTPS, autenticación interna y
servicios de datos privados. No se expone este compose directamente a Internet.

## Control de versiones

Versionar código, configuración de ejemplo, documentación, notebooks revisados y assets
ligeros. Los corpus, audio, modelos grandes, logs, cachés, `.env`, `.venv` y `node_modules`
están excluidos mediante `.gitignore`. Conservar manifiestos/checksums en `manifests/`.
Antes de publicar, revisar `git status` y los archivos incluidos. El scaffold no sube datos.
