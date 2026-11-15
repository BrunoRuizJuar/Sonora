# Infraestructura

El compose de la raíz prepara servicios locales. No implementa despliegue público.
M1 debe crear las bases operativas y cargar los mappings del release activo.
Los servicios internos sólo deben ser accesibles por backend y procesos offline.
`infra/opensearch/` reserva configuraciones versionadas; los vectores necesitan una dimensión
definida por el modelo real antes de crear cada índice.
