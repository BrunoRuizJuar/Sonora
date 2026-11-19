# SONORA

## INSTRUCCIONES PARA LUIS MAZA

Desde la raíz de tu clon de SONORA, en PowerShell y con Python 3.10 o posterior:

```powershell
git switch main
git pull --ff-only origin main
py -3 apps/web/serve.py --open
```

1. Abre **Anotar letras** en el menú de SONORA. También puedes entrar directamente en [localhost:8000/anotacion.html](http://localhost:8000/anotacion.html).
2. Carga [anotacion.json](data/evaluation/emotion-pilot/anotacion.json) desde tu clon. Es el mismo piloto de 200 letras, con 224 pares en el orden original.
3. Empieza por el primer par y completa **al menos las primeras 26 comparaciones** (las 20 de *Cell-by-date* y las primeras 6 de *Frank*). Si tienes tiempo, sigue con más pares en orden.
4. Califica **relevancia temática** y **afinidad emocional** por separado, de 0 a 5 en pasos de media estrella. Usa 0 cuando el parecido sea nulo y deja el campo vacío si vas a revisarlo después. Si haces una pausa, vuelve a cargar el mismo archivo en el mismo navegador para recuperar tu avance.
5. Pulsa **Exportar valoraciones** y envíale a Bruno el archivo `valoraciones-sonora.json` que descargue el navegador.

Si usas macOS o Linux, ejecuta `python3 apps/web/serve.py --open` en lugar de `py -3`. [Guía del piloto y criterios de anotación](docs/PILOTO_EMOCIONAL.md).

Prototipo de recomendación musical entre canciones por **letras, audio o una combinación de ambos**. Ya se integró el recomendador por letras con la web. Para mostrarlo con el corpus real se necesita el paquete de datos de servicio. La demo ligera incluye cinco canciones de muestra. El procesamiento de audio y la evaluación final siguen pendientes.

## Qué se hizo en cada evidencia de PLN

| Evidencia | Estado | Trabajo realizado y siguiente paso |
| --- | --- | --- |
| [E1 · Construcción y exploración del corpus](notebooks/evidencias/E1_construccion_exploracion.ipynb) | Cerrada | Se limpiaron y deduplicaron las letras en inglés hasta obtener **3 155 772 letras canónicas**. Se crearon particiones por grupos (70 % entrenamiento, 20 % prueba y 10 % validación) y se exploraron tamaños, cobertura y estadísticas del corpus. |
| [E2 · Estadística léxica y modelos de lenguaje](notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb) | Cerrada | Se analizaron frecuencias, palabras funcionales, muletillas, n-gramas, ley de Zipf, palabras de una sola aparición y repetición de estribillos. Se compararon modelos KenLM de órdenes 2, 3 y 4. El orden 4 obtuvo la menor perplejidad en validación (82,34). |
| [E3 · Morfosintaxis](notebooks/evidencias/E3_morfosintaxis.ipynb) | Ejecutada, en revisión | Se analizaron categorías gramaticales (POS) y lemas con spaCy sobre el corpus completo. El notebook incluye proporciones, comparaciones por etiqueta de género y década, y ejemplos trazables. Hay revisión asistida y queda la revisión personal del autor. |
| [E4 · Dependencias sintácticas](notebooks/evidencias/E4_sintaxis_dependencias.ipynb) | Ejecutada, revisión personal pendiente | Se construyeron árboles de dependencias y se compararon relaciones sintácticas y métricas de complejidad por género y década. Se documentaron ejemplos y limitaciones del parser. |
| [E5 · Representación y análisis semántico](notebooks/evidencias/E5_semantica.ipynb) | Entrenada y verificada, revisión personal pendiente | Se ajustaron TF-IDF, Word2Vec/SGNS y LDA con entrenamiento. En validación se eligieron Word2Vec de 128 dimensiones con ventana 5 y LDA de 20 tópicos. Se verificaron embeddings y tópicos para **3 155 772 letras** y se analizaron vecinos, contextos y una proyección PCA. [Resultados](docs/E5_RESULTADOS.md) |

## Comandos importantes

Los ejemplos usan PowerShell en Windows. Ejecuta cada bloque desde la raíz del repositorio, salvo el comando de clonación.

### 1. Iniciar la webapp en la laptop

Necesitas Python 3.10 o posterior. El servidor de la demo funciona con la biblioteca estándar de Python y los archivos incluidos en Git.

```powershell
py -3 apps/web/serve.py --open
```

Abre [localhost:8000](http://localhost:8000/) si el navegador no se abre automáticamente. También puedes hacer doble clic en `apps/web/INICIAR_LOCAL.cmd`. Usa **Ctrl+C** para detener el servidor. Si el puerto está ocupado, agrega `--port 8080` al comando. [Guía de la webapp](apps/web/LEEME_PRIMERO.md)

**Web con el recomendador por letras.** Prepara el entorno y el paquete `artifacts/releases/lyrics-serving-v1/` según la guía de la API. Luego ejecuta:

```powershell
.\scripts\Start-SONORA-Web.ps1
```

Abre [127.0.0.1:8010](http://127.0.0.1:8010/). [Preparación y arranque de la API textual](docs/API_TEXTO_WEB.md)

### 2. Configurar Git y colaborar en GitHub

Con Git instalado y acceso al repositorio, configura tu nombre y correo para los commits y clona el proyecto. Sustituye los valores de ejemplo por los tuyos. Si ya tienes el clon, abre esa carpeta y usa `git remote -v` para verificar `origin`.

```powershell
git config --global user.name "Tu Nombre"
git config --global user.email "tu-correo-verificado-en-github@example.com"
git clone https://github.com/BrunoRuizJuar/Sonora.git
cd Sonora
```

Para trabajar en un cambio, sincroniza `main` y crea una rama. Después de editar, revisa el estado y añade los archivos que quieras incluir. Este ejemplo publica un cambio al README. En GitHub, abre un pull request de tu rama hacia `main`.

```powershell
git switch main
git pull --ff-only origin main
git switch -c docs/actualizar-guia
git status --short
git add README.md
git commit -m "Actualizar guía de SONORA"
git push -u origin docs/actualizar-guia
```

Git contiene código, notebooks ejecutados y reportes. Los datos grandes, el audio, los modelos y las credenciales se manejan fuera del repositorio.

### 3. Flujo general del trabajo

1. **Preparar el corpus.** Ingerir los archivos de origen, limpiar y deduplicar las letras en inglés y generar las particiones por grupos. Conservar los originales en `data/raw/`. [Corpus y particiones](docs/CORPUS_LETRAS.md)
2. **Generar la evidencia de PLN.** Reutilizar la anotación, los conteos y los agregados del corpus completo. Los notebooks ejecutados se pueden consultar directamente en GitHub. Para reproducirlos, preparar el entorno de la migración y copiar los datos procesados. En la laptop basta el clon para revisar el trabajo y abrir la demo. Usar el equipo con más memoria para las corridas del corpus completo, con un solo proceso pesado a la vez. [Entorno y transferencia de datos](docs/handoff/MIGRACION_2026-11-16.md)
3. **Revisar y validar PLN.** E1 y E2 están cerradas. Queda la revisión personal de E3–E5. Se usó `train` para ajustar vocabularios y modelos y `validation` para elegir configuraciones. `test` queda reservado para la evaluación final. [Revisión pendiente](TODO-human.md)
4. **Integrar y evaluar el recomendador.** La API y la web ya se conectaron por letras. Quedan los descriptores de audio FMA, la integración de las señales y la evaluación final. [Arquitectura](docs/ARQUITECTURA_SONORA.md) · [API textual](docs/API_TEXTO_WEB.md)

Para correr las pruebas en el entorno de PLN o regenerar evidencias con sus datos ya preparados:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe notebooks/evidencias/build_e1.py
.\.venv\Scripts\python.exe notebooks/evidencias/build_e2.py
.\.venv\Scripts\python.exe notebooks/evidencias/build_e3.py
.\.venv\Scripts\python.exe notebooks/evidencias/build_e4.py
.\.venv\Scripts\python.exe notebooks/evidencias/build_e5.py
```

## Más documentación

- [Especificación vigente](docs/REQUIREMENTS.md)
- [Datos y fuentes](docs/DATOS_Y_FUENTES.md)
- [Entorno de desarrollo en Windows y arranque de la API](docs/WINDOWS.md)
- [Plan de implementación](docs/PLAN_IMPLEMENTACION.md)
- [Estructura del repositorio](docs/ESTRUCTURA.md)
