# ÑM Performance — Entrega de integración para TESTING

Incluye registro, aprobación de usuarios, asignación de roles y control restrictivo por defecto para Nadador y Delegado. El Nadador puede entrar a /mi-panel y su propia ficha; no puede acceder a fichas de terceros cambiando la URL. El Entrenador no accede a administración. Los roles heredados editor/viewer se migran a entrenador/delegado.

## Limitaciones importantes
- **NO apto para producción ni para abrir el registro público**: faltan pruebas end-to-end con Neon, pruebas de autorización de todas las rutas, CSRF en formularios históricos, rate limiting y auditoría de privacidad de rankings/exportaciones.
- Los rankings generales para Nadador están temporalmente bloqueados hasta sanear sus consultas; es una medida de protección, no una funcionalidad completada.
- El acceso de Delegado es de consulta y limitado hasta auditar las rutas de gestión.
- El esquema se modifica automáticamente al iniciar: usar exclusivamente rama Neon testing.
- No incluye `archivo.env`, bases de datos locales ni archivos secretos.

## Instalación solo en testing
1. Conservar copia del repositorio actual y respaldo de Neon.
2. Subir el contenido a GitHub rama `testing` (no `main`).
3. Verificar Render `nm-performance-testing`: branch testing y DATABASE_URL apunta a Neon nm-performance-testing.
4. Desplegar; revisar logs y probar con cuentas ficticias, nunca con datos reales de terceros.
5. No promover a producción hasta completar pruebas y controles pendientes.
