# Requisitos Funcionales y No Funcionales - Drivemarket (Documento Oficial)

Este documento representa la especificación técnica final de la plataforma Drivemarket, consolidando todas las funciones activas y los estándares de calidad establecidos.

---

## 1. Requisitos Funcionales (RF)

### 1.1. Seguridad, Usuarios y Gobernanza
*   **RF-01 [Autenticación Multiclase]**: Gestión segura de sesiones para Compradores, Vendedores y personal administrativo (`superadmin`, `admin`, `moderador`, `editor`) usando `flask-login`.
*   **RF-02 [KYC Vendedor (Identidad)]**: Proceso de validación empresarial que exige Cédula/NIT, teléfono, correo comercial y fotos frontales/traseras de documentos legales para aprobación manual.
*   **RF-03 [Auditoría Administrativa]**: Registro de eventos críticos realizados por administradores (bloqueos, ediciones, aprobaciones) para trazabilidad.

### 1.2. Gestión de Inventario y Publicación
*   **RF-04 [Publicación Avanzada]**: Inserción de vehículos con 12+ variables técnicas (Marca, Modelo, Año, Placa, Ciudad, etc.) y generación de **Slugs SEO únicos**.
*   **RF-05 [Protección Multimedia (Watermark)]**: Aplicación automática de marcas de agua profesionales (Logo Naranja/Negro) a todas las fotos subidas para evitar robo de contenido.
*   **RF-06 [Métricas de Rendimiento]**: Contador de vistas únicas por vehículo y seguimiento de la tasa de completitud del anuncio para incentivar al vendedor.

### 1.3. Monetización y Herramientas Elite
*   **RF-07 [Inteligencia de Mercado]**: Algoritmo que calcula el "Promedio de Mercado" (+/- 2 años del modelo consultado) para informar si un precio es competitivo.
*   **RF-08 [Planes Destacados (Pago Manual)]**: Sistema de solicitud de avisos premium mediante la subida de un **Comprobante de Pago** (Imagen/PDF) para verificación administrativa.
*   **RF-09 [Tracking de Conversión (WhatsApp)]**: Registro de cada clic en el botón de WhatsApp, capturando IP y User-Agent para analíticas de ventas reales en el dashboard.

### 1.4. Interacción y Experiencia del Usuario
*   **RF-10 [Comparator IA]**: Herramienta de comparación lado a lado con un motor de IA que analiza las opciones y recomienda la mejor compra técnica.
*   **RF-11 [Centro de Notificaciones Glassmorphism]**: Alertas en tiempo real con barras de progreso dinámicas, paginación y gestión individual (leído/no leído/borrado).
*   **RF-12 [Alertas de Precio]**: Monitoreo proactivo que notifica al usuario cuando un vehículo guardado en sus favoritos baja de precio.
*   **RF-13 [Mensajería de Doble Borrado]**: Chat interno donde vendedor y comprador pueden eliminar su copia de la conversación de forma independiente.

### 1.5. Soporte e Inteligencia Artificial
*   **RF-14 [Chatbot Híbrido FAQ/IA]**: Widget flotante que resuelve dudas usando una DB de FAQs local o escala a la API de OpenAI para consultas complejas.
*   **RF-15 [Chatbot de Tienda]**: IA especializada por vendedor que conoce el catálogo específico de esa tienda y actúa como asesor comercial automático 24/7.

---

## 2. Requisitos No Funcionales (RNF)

### 2.1. Estética y Calidad de Interfaz (UI/UX)
*   **RNF-01 [Premium SaaS Aesthetics]**: Uso estricto de Glassmorphism, efectos de backdrop-blur, sombras suaves y componentes tipo **Bento Grid** en dashboards.
*   **RNF-02 [Emoji-Free Policy]**: Comunicación 100% profesional. Prohibido el uso de emojis en todo el flujo de transacciones, mensajes oficiales y paneles administrativos.
*   **RNF-03 [SaaS Tone (Usted)]**: El sistema debe dirigirse al usuario de manera formal ("Usted"), manteniendo una autoridad de marca Premium.

### 2.2. Arquitectura y Rendimiento
*   **RNF-04 [Modularidad por Blueprints]**: Separación lógica total (admin, vendedor, mensajes, soporte) para escalabilidad y mantenimiento atómico.
*   **RNF-05 [Resiliencia de Servicios]**: Manejo de errores en APIs externas (OpenAI, SMTP) mediante bloques try-catch que registran fallos sin interrumpir la experiencia el usuario.
*   **RNF-06 [SEO & Performance]**: URLs amigables (Slugs) e índices SQL en campos de búsqueda crítica para garantizar respuestas de carga rápidas.

### 2.3. Seguridad Técnica
*   **RNF-07 [Seguridad File System]**: Validación estricta con `secure_filename`, inyección de UUIDs y limitación de extensiones para prevenir ataques RCE.
*   **RNF-08 [Privacidad KYC]**: Acceso restringido a documentos de identidad; solo el rol Admin puede visualizar archivos cargados por seguridad de datos personales.

