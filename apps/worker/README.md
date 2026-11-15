# Worker previsto

Procesos RQ sobre Redis para extracción, generación de representaciones e indexación.
Comparten el paquete `sonora` con la API. Los trabajos se ejecutarán en Linux/WSL2 o contenedor;
el primer pipeline puede ejecutarse por CLI. Los resultados persistentes y su estado final
se registran fuera de Redis. No hay worker implementado en esta entrega.
