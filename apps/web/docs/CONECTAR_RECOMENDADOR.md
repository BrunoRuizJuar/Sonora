# Conectar SONORA al recomendador real

La web usa `/api/v1` en el mismo origen. Ejecutar desde la raíz:

```powershell
.\scripts\Start-SONORA-Web.ps1
```

Abrir http://127.0.0.1:8010/. La API sirve únicamente `public/` y sus rutas.
`serve.py` continúa como servidor estático; no utilizarlo para el flujo integrado.

Contrato, construcción del release, identidad, ejemplos, pruebas y límites:
[API_TEXTO_WEB.md](../../../docs/API_TEXTO_WEB.md).

`public/app.js` consulta título/artista, selecciona semilla y solicita ranking real.
También ofrece texto libre en inglés y estrategias SGNS/TF-IDF separadas.
Música, Mixto y covers no están disponibles; no se simulan canciones ni audio.
