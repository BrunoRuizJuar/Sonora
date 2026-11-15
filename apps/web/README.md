# Frontend previsto

Next.js App Router, React y TypeScript. Esta carpeta reserva rutas y componentes;
todavía no contiene una aplicación Next.js inicializada ni un lockfile de npm.
El diseño se desarrolla en el otro chat y sus assets se importarán después.

- `src/app/`: rutas de descubrimiento, búsqueda, canción y evaluación.
- `src/components/`: controles reutilizables, layout y UI.
- `src/features/`: búsqueda, recomendaciones y evaluación.
- `src/lib/api/`: cliente de la API; ningún cliente de CouchDB/OpenSearch en el navegador.
- `public/assets/`: exports optimizados de marca, texturas y portadas de ejemplo.

Usar una versión LTS de Node compatible con la versión elegida de Next.js. Al inicializar,
fijar dependencias y conservar el lockfile. Las variables `NEXT_PUBLIC_*` son públicas;
no contienen credenciales. Los endpoints/estados del diseño están en `docs/CONTRATO_API.md`.
