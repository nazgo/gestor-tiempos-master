# ÑM Performance — etapa 1: registro y aprobación (solo testing)

Esta entrega implementa el formulario de registro y la cola de solicitudes, y permite asignar uno de cuatro roles al aprobar. NO implementa todavía la autorización completa de rutas ni el panel personal del nadador. NO desplegar en producción.

1. Subir únicamente a la rama `testing` de GitHub; no a `main`.
2. Mantener DATABASE_URL apuntando exclusivamente a `nm-performance-testing` y SECRET_KEY distinta de producción.
3. El inicio aplica migración aditiva a `usuarios`. Verificar antes que la rama Neon testing sea independiente.
4. Abrir `/registro`, registrar una solicitud de prueba y comprobar que no puede iniciar sesión mientras está pendiente.
5. Iniciar sesión como administrador preexistente; abrir `/admin/solicitudes`, comprobar identidad, asignar rol y ficha.
6. El RUT de la ficha debe coincidir con el registrado; si no coincide, no aprobar hasta corregirlo.
7. Verificar que una solicitud rechazada no pueda iniciar sesión.

LIMITACIONES CONOCIDAS: Las rutas deportivas antiguas todavía no tienen permisos por rol; cualquier usuario activo puede conservar acceso a pantallas no autorizadas. No usar cuentas de nadador reales hasta completar etapa 2. Los formularios antiguos aún requieren migración CSRF. Las rutas administrativas antiguas de alta/cambio de roles necesitan endurecimiento. El registro público requiere rate limiting y verificación adicional antes de exposición pública. No se han realizado pruebas de integración contra PostgreSQL de Neon.
