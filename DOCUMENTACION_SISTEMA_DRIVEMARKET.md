# Documentación Técnica Pro: Drivemarket Platform
**Versión**: 1.0.0 | **Fecha**: Abril 2026 | **Estándar**: Premium SaaS

---

## 1. Introducción
Drivemarket es una plataforma de marketplace automotriz de alto rendimiento diseñada para profesionalizar la compra y venta de vehículos. El sistema utiliza una estética de vanguardia (Glassmorphism), inteligencia artificial híbrida y una arquitectura modular escalable.

---

## 2. Arquitectura del Sistema

### 2.1. Core Tecnológico
- **Lenguaje**: Python 3.x
- **Framework**: Flask
- **Base de Datos**: PostgreSQL
- **ORM/Capa de Datos**: SQLAlchemy (Modelado) + Psycopg2 (Consultas de rendimiento)
- **Autenticación**: Flask-Login + OAuth 2.0 (Google)
- **Frontend**: Jinja2 + Vanilla CSS (Aesthetic Premium) + Chart.js

### 2.2. Estructura Modular (Blueprints)
El proyecto se divide en módulos atómicos para facilitar el mantenimiento:
- **`admin_bp` (`admin_routes.py`)**: Gestión de usuarios, moderación de vehículos, auditoría de logs y aprobación de pagos.
- **`vendedor_bp` (`vendedores.py`)**: Centro de comando para concesionarios y vendedores particulares.
- **`users_bp` (`users_bp.py`)**: Gestión de perfil, seguridad y preferencias.
- **`mensajes_bp` (`mensajes_bp.py`)**: Sistema de chat seguro con doble borrado.
- **`soporte_bp` (`soporte_routes.py`)**: Inteligencia Artificial y FAQs dinámicas.
- **`comparador_bp` (`comparador_routes.py`)**: Motor de comparación técnica de vehículos.
- **`notificaciones_bp` (`notificaciones_routes.py`)**: Centro de alertas con Glassmorphism.

---

## 3. Modelo de Datos (Esquema Crítico)

### 3.1. Usuarios y Roles
- **`usuarios`**: Entidad central. Roles: `comprador`, `vendedor`, `editor`, `moderador`, `admin`, `superadmin`.
- **`perfil_vendedor`**: Extensión de usuario para KYC empresarial (NIT, documentos legales, estado de verificación).

### 3.2. Inventario
- **`vehiculos`**: Almacena detalles técnicos (Marca, Modelo, Año, Precio, etc.), estado de publicación y métricas de visualización.
- **`imagenes_vehiculos`**: Gestión multimedia con soporte para marcas de agua automáticas.

### 3.3. Interacción
- **`conversaciones`** & **`mensajes`**: Hilos de comunicación encriptados lógicamente entre actores.
- **`notificaciones`**: Alertas automáticas (Baja de precio, mensaje nuevo, sistema).
- **`logs_admin`**: Trazabilidad completa de operaciones administrativas.

---

## 4. Funcionalidades de Élite

### 4.1. Inteligencia Artificial (IA)
Drivemarket utiliza un motor híbrido:
1. **Local FAQ**: Respuestas instantáneas basadas en una base de datos de preguntas frecuentes.
2. **OpenAI Integration**: Para consultas complejas sobre mecánica, comparativas o sugerencias de precios.

### 4.2. Sistema de Marcas de Agua (Watermark)
Al subir imágenes, el servidor procesa automáticamente cada archivo para incrustar el logo de Drivemarket en el centro, utilizando transparencias escalonadas para proteger la propiedad intelectual sin afectar la visibilidad del producto.

### 4.3. Dashboards de Alto Impacto
- **Bento Grid Layout**: Organización de métricas clara y moderna.
- **Real-time Analytics**: Seguimiento de clics de WhatsApp y vistas por IP única.
- **Market Insights**: Comparativa automática de precios frente a la media del mercado.

---

## 5. Gobernanza y Seguridad
- **Políticas de Tono**: Uso exclusivo del tratamiento "Usted" en todas las comunicaciones automáticas.
- **Emoji-Free**: Eliminación total de emojis en interfaces críticas para garantizar seriedad comercial.
- **Protección KYC**: Documentos de identidad sensibles solo son accesibles por roles de nivel superior.

---

## 6. Configuración de Entorno
Claves necesarias en el archivo `.env`:
- `DATABASE_URL`: Conexión de PostgreSQL.
- `APP_SECRET_KEY`: Seguridad de sesiones.
- `MAIL_PASSWORD`: Puerto SMTP para notificaciones.
- `OPENAI_API_KEY`: Motor de IA.

---

## 7. Estructura de Directorios
```text
/
├── app.py                # Punto de entrada y rutas globales
├── db_config.py          # Proxy de conexión resiliente
├── models.py             # Definición de tablas (SQLAlchemy)
├── helpers/              # Utilidades (SEO, Imágenes, Email)
├── static/
│   ├── css/              # Design System (HSL, Variables)
│   ├── js/               # Lógica de Dashboards y Gráficos
│   └── uploads/          # Almacenamiento seguro de medios
└── templates/            # Vistas Jinja2 organizadas por módulo
```

