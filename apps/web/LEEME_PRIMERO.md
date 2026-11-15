# SONORA en tu laptop

Este paquete incluye la página completa y sus assets, el logo aprobado, un servidor local y accesos para Windows. Funciona sin instalar librerías con pip, Node, npm ni una base de datos. Necesitas Python 3.10 o posterior y un navegador actual.

## 1. Arrancar en Windows

1. Extrae **todo** el ZIP en una carpeta. Puedes poner `SONORA_Web` dentro de tu proyecto; no necesitas mover tus notebooks ni cambiar el repositorio.
2. Si ya tienes Python, compruébalo en PowerShell con `py -3 --version`. También sirve `python --version`.
3. Si no tienes Python, instálalo desde [Python para Windows](https://www.python.org/downloads/windows/), cierra y abre PowerShell y vuelve a comprobarlo.
4. Abre `INICIAR_LOCAL.cmd` con doble clic. Se abre SONORA en **http://localhost:8000/**.
5. Conserva abierta la ventana de la terminal. Para apagar el servidor, pulsa **Ctrl+C**.

No ejecutes el acceso desde dentro del ZIP: primero extráelo.

También puedes abrir PowerShell dentro de la carpeta `SONORA_Web` y ejecutar:

```powershell
py -3 serve.py --open
```

Si usas `python` en lugar de `py`:

```powershell
python serve.py --open
```

## 2. Abrirla desde tu celular u otra laptop en el mismo Wi-Fi

1. Detén el modo local con Ctrl+C.
2. Abre `COMPARTIR_WIFI.cmd`.
3. El servidor imprime una o más direcciones locales, por ejemplo `http://192.168.1.70:8000/`. Esa dirección es un ejemplo: utiliza la que aparece en **tu** terminal.
4. Conecta el celular u otro equipo al mismo Wi-Fi y abre esa dirección en su navegador. En el celular no uses `localhost`, porque se referiría al celular.
5. Si Windows solicita acceso para Python, permite el acceso en **redes privadas** para esta prueba. Si tu firewall lo bloquea, revisa Seguridad de Windows → Firewall y protección de red → Permitir una aplicación a través del firewall.

Comando equivalente:

```powershell
py -3 serve.py --wifi --open
```

Si no aparece tu dirección local, abre otra terminal, ejecuta `ipconfig` y busca **Dirección IPv4** en el adaptador Wi-Fi. Las redes de invitados y algunas redes de universidad bloquean las conexiones entre dispositivos.

La laptop debe permanecer encendida, sin suspensión y con el servidor abierto. El servidor no tiene inicio de sesión: otros dispositivos que puedan acceder a esa dirección podrán ver la página. Solo se publica la carpeta `public`, no la carpeta de tu proyecto ni tus notebooks.

## 3. Compartir un enlace por Internet durante una demostración

El sitio que ya está en la nube funciona sin tu laptop y conserva su acceso privado actual. Para una demostración desde tu laptop a personas fuera de tu Wi-Fi puedes usar un túnel temporal.

1. Arranca SONORA en modo local: `INICIAR_LOCAL.cmd`.
2. Descarga `cloudflared` desde [Cloudflare: descargas oficiales](https://developers.cloudflare.com/tunnel/downloads/). Es un programa adicional y solo se necesita para este paso opcional.
3. Si descargaste el ejecutable de Windows, renómbralo como `cloudflared.exe` y abre PowerShell en esa carpeta. En una **segunda** terminal ejecuta:

```powershell
.\cloudflared.exe tunnel --url http://localhost:8000
```

4. Comparte el enlace HTTPS `trycloudflare.com` que aparece en esa terminal.
5. Mantén abiertas las dos terminales. El enlace deja de funcionar cuando detienes el túnel; normalmente cambia al volver a iniciarlo.

El enlace permite que cualquiera que lo tenga vea la interfaz. Un túnel rápido es para pruebas; este servidor de Python también es para desarrollo y demostraciones, no para un servicio público permanente. Para una publicación estable conviene usar hosting y un backend preparado para producción cuando conectemos el modelo.

## 4. Qué funciona ahora

| Función | Estado |
| --- | --- |
| Pantalla de inicio y las tres direcciones visuales | Funcional |
| Logo aprobado, favicon, imágenes, fuentes e iconos locales | Incluidos |
| Interfaz en escritorio y móvil | Funcional |
| Búsqueda por título y artista | Cinco canciones de muestra |
| Letras / Música / Mixto y ponderaciones | Interacción visual; el peso cambia el énfasis de las explicaciones de ejemplo |
| Cambiar la canción de partida | Funcional sobre la muestra |
| Filtro de idioma | Funcional sobre la muestra |
| Guardar canciones | En el navegador de cada dispositivo, mediante localStorage |
| Limitar artistas y excluir covers | Controles listos; la muestra ya contiene artistas y composiciones distintos |
| Explorar más | Demostración visual que cambia el orden de la muestra |
| Explicaciones de recomendación | Ejemplos editoriales, no resultados de un modelo |
| Reproducción de audio, cuentas y sincronización | Pendientes |
| Catálogo real y modelos de letras y música | Pendientes de conectar |

Las canciones de muestra son Hasta la Raíz, Brillas, Eres, San Lucas y Bloom. Las portadas son ilustraciones originales de ejemplo, no portadas oficiales.

## 5. Qué archivo editar

| Archivo o carpeta | Contenido |
| --- | --- |
| `public/index.html` | Estructura, textos, formularios y easter egg del cactus «¡AJÚA!» |
| `public/styles.css` | Colores, tipografías, componentes y adaptación móvil |
| `public/app.js` | Canciones de muestra, búsqueda, guardados y demás interacciones |
| `public/mobile.html` | Marco de revisión para móvil |
| `public/assets/brand/cactus-sonora.svg` | Logo aprobado: vector editable y transparente |
| `public/assets/brand/cactus-sonora-transparente.png` | Logo transparente de 900 × 1120 px |
| `public/assets/brand/wordmark-sonora.svg` | Símbolo y nombre en SVG; el texto sigue editable |
| `public/assets/fonts` | Fuentes y licencias, sin descargas externas |
| `public/assets/covers` | Portadas de ejemplo |
| `public/assets/illustrations` | Fondos e ilustraciones |
| `serve.py` | Servidor local que solo sirve `public` |
| `docs/CONECTAR_RECOMENDADOR.md` | Contrato propuesto para conectar el modelo real |

Para cambiar el diseño inicial, modifica el valor de respaldo `'ocaso'` en `themeFromUrl()` dentro de `public/app.js`. También puedes abrir `/?direccion=archivo` o `/?direccion=cobre`.

Después de editar, recarga el navegador. Si parece conservar una versión anterior, usa **Ctrl+F5**. Los archivos que publiques en `public` son visibles para los visitantes; el servidor no necesita credenciales ni claves de API.

## 6. Problemas habituales

| Problema | Solución |
| --- | --- |
| La ventana se cierra o dice que falta Python | Ejecuta `py -3 --version` y revisa el paso 1. Si falla, instala Python o prueba `python`. |
| `No se pudo abrir el puerto 8000` | Usa `py -3 serve.py --port 8080 --open`. En Wi-Fi añade `--wifi`. Abre la dirección con el nuevo puerto. |
| Faltan imágenes o estilos | Extrae todo el ZIP y conserva el árbol de carpetas. Abre la URL del servidor. |
| El celular no conecta | Usa la IPv4 de la laptop, mismo Wi-Fi, servidor en modo Wi-Fi y excepción de Python en la red privada. |
| Hay varias direcciones IPv4 | Usa la del adaptador Wi-Fi conectado; las otras pueden corresponder a VPN, Ethernet o máquinas virtuales. |
| Se pierde el acceso cuando cierro la laptop | Desactiva temporalmente la suspensión durante la demo y conserva abiertas las terminales. |
| Mis guardados no aparecen en otro dispositivo | Se almacenan en cada navegador. No hay cuentas ni sincronización todavía. |
| Una canción no aparece | La búsqueda actual solo tiene las cinco canciones de muestra. |

## 7. macOS y Linux

En una terminal dentro de `SONORA_Web`:

```bash
python3 serve.py --open
# Para compartir en la misma red:
python3 serve.py --wifi --open
```

## 8. Fuentes de las instrucciones

- [Python: servidor HTTP y limitación a desarrollo](https://docs.python.org/3/library/http.server.html).
- [Microsoft: firewall y protección de red](https://support.microsoft.com/es-es/windows/security/windows-security/firewall-and-network-protection-in-the-windows-security-app).
- [Cloudflare: descargas](https://developers.cloudflare.com/tunnel/downloads/).
- [Cloudflare: túneles rápidos](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).

Comprobado en este entorno: sintaxis de JavaScript, assets SVG, servidor HTTP, carga de archivos y aislamiento de la carpeta pública. Los accesos `.cmd` se incluyen para Windows, pero no se han ejecutado en tu laptop desde aquí.
