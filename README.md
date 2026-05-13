# 🚗 Drivemarket - Plataforma de Marketplace Automotriz Premium

> Una plataforma SaaS de vanguardia para la compra y venta de vehículos con inteligencia artificial, análisis de mercado y herramientas profesionales para vendedores.

![Versión](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.x-brightgreen)
![Flask](https://img.shields.io/badge/flask-2.3.3-lightblue)
![PostgreSQL](https://img.shields.io/badge/postgresql-12+-336791)

---

## 📋 Tabla de Contenidos

- [Descripción General](#descripción-general)
- [Características Principales](#características-principales)
- [Tecnologías](#tecnologías)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Funcionalidades por Módulo](#funcionalidades-por-módulo)
- [Roles y Permisos](#roles-y-permisos)
- [API y Rutas](#api-y-rutas)
- [Base de Datos](#base-de-datos)
- [Uso y Ejemplos](#uso-y-ejemplos)
- [Contribuir](#contribuir)
- [Licencia](#licencia)

---

## 🎯 Descripción General

**Drivemarket** es una plataforma completa de marketplace automotriz desarrollada con arquitectura modular, diseño premium con Glassmorphism y funcionalidades avanzadas como:

- 🤖 **Inteligencia Artificial Híbrida** (FAQs + OpenAI)
- 📊 **Análisis de Mercado en Tiempo Real**
- 🔐 **Sistema de Verificación KYC** para vendedores
- 💬 **Messaging Seguro** con doble borrado
- 📱 **Dashboards Interactivos** estilo Bento Grid
- 🎨 **Diseño Premium** con Glassmorphism
- 📈 **Tracking de Conversiones** y Analytics

---

## ✨ Características Principales

### 1. **Gestión de Usuarios y Autenticación**
- Registro e inicio de sesión seguro
- OAuth 2.0 con Google
- Sistema de roles multinivel (Comprador, Vendedor, Admin, Moderador, Editor, Superadmin)
- Perfil de usuario personalizable
- Gestión de contraseñas segura con hash

### 2. **Plataforma de Vendedores**
- Dashboard personalizado con métricas
- Gestión de inventario de vehículos
- Verificación KYC (Identidad + Documentos legales)
- Planes destacados y promociones
- Control de publicaciones (Borrador, Publicado, Pausado)

### 3. **Catálogo de Vehículos**
- Publicación avanzada con 12+ variables técnicas
- Generación automática de URLs SEO-friendly
- Protección multimedia con Watermark automático
- Galería de imágenes mejorada
- Métricas de rendimiento (Vistas, Clics, Tasas)

### 4. **Inteligencia Artificial**
- **Chatbot Híbrido**: FAQs locales + OpenAI para consultas complejas
- **Comparador IA**: Análisis técnico y recomendaciones
- **Asistente de Mercado**: Cálculo de precios competitivos
- **Chatbot por Tienda**: IA especializada por vendedor

### 5. **Sistema de Mensajería**
- Chat interno entre compradores y vendedores
- Mensajes encriptados lógicamente
- Doble borrado independiente
- Notificaciones en tiempo real
- Historial persistente

### 6. **Centro de Notificaciones**
- Alertas de precio
- Nuevos mensajes
- Eventos del sistema
- Diseño Glassmorphism
- Paginación y gestión de lectura

### 7. **Panel Administrativo**
- Gestión de usuarios
- Moderación de vehículos
- Validación de planes destacados
- Auditoría de logs
- Reportes y estadísticas

### 8. **Herramientas de Comparación**
- Comparador lado a lado
- Análisis técnico automático
- Motor de recomendaciones
- Integración con IA

---

## 🛠️ Tecnologías

| Capa | Tecnología | Versión |
|------|-----------|---------|
| **Backend** | Python | 3.x |
| **Framework Web** | Flask | 2.3.3 |
| **Base de Datos** | PostgreSQL | 12+ |
| **ORM** | SQLAlchemy | 3.0.5 |
| **Autenticación** | Flask-Login + OAuth2 | - |
| **Email** | Flask-Mail | - |
| **API Externa** | OpenAI | 0.28.0 |
| **Frontend** | Jinja2 + HTML/CSS | - |
| **Gráficos** | Chart.js | - |
| **Procesamiento de Imágenes** | Pillow | - |
| **PDF** | fpdf2 | - |

---

## 📦 Requisitos

- **Python** 3.8 o superior
- **PostgreSQL** 12 o superior
- **pip** (gestor de paquetes de Python)
- **Git**
- **Variables de entorno** configuradas (.env)

### Dependencias Python

```
flask==2.3.3
flask-cors==4.0.0
flask-login==0.6.2
flask-sqlalchemy==3.0.5
openai==0.28.0
python-dotenv==1.0.0
requests==2.31.0
fpdf2
authlib
flask-mail
psycopg2-binary
pillow
```

---

## 🚀 Instalación

### 1. Clonar el Repositorio

```bash
git clone <url-del-repositorio>
cd Proyect
```

### 2. Crear Virtual Environment

**En Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**En Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```env
# Base de Datos
DATABASE_URL=postgresql+psycopg2://usuario:contraseña@localhost:5432/drivemarket

# Seguridad
APP_SECRET_KEY=tu_clave_secreta_super_segura_aqui

# Email/SMTP
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=tu_correo@gmail.com
MAIL_PASSWORD=tu_contraseña_aplicacion

# Google OAuth
GOOGLE_CLIENT_ID=tu_google_client_id
GOOGLE_CLIENT_SECRET=tu_google_client_secret

# OpenAI
OPENAI_API_KEY=tu_api_key_openai

# Configuración
FLASK_ENV=development
FLASK_DEBUG=True
```

### 5. Crear Base de Datos

```bash
# Con PostgreSQL
createdb drivemarket

# Luego, desde Python en la aplicación:
python
>>> from app import app, db
>>> with app.app_context():
>>>     db.create_all()
>>> exit()
```

---

## ⚙️ Configuración

### Estructura de Directorios

```
Drivemarket/
├── app.py                           # Punto de entrada principal
├── db_config.py                     # Configuración de conexión DB
├── models.py                        # Definición de modelos SQLAlchemy
├── requirements.txt                 # Dependencias Python
│
├── helpers/                         # Módulos de utilidades
│   ├── asistente_ia.py            # Lógica de IA y chatbot
│   ├── email_templates.py         # Plantillas de email HTML
│   ├── image_utils.py             # Procesamiento de imágenes y watermark
│   ├── notificaciones.py          # Sistema de notificaciones
│   ├── seo_utils.py               # Generación de slugs y SEO
│   └── vendedor_utils.py          # Utilidades para vendedores
│
├── static/
│   ├── css/                        # Hojas de estilos
│   │   ├── base.css
│   │   ├── admin_usuarios.css
│   │   ├── vendedor_dashboard.css
│   │   ├── chatbot.css
│   │   └── [otros archivos CSS]
│   ├── js/                         # Scripts JavaScript
│   │   ├── vendedor_dashboard.js
│   │   ├── chatbot.js
│   │   ├── carrusel.js
│   │   └── [otros scripts]
│   ├── img/                        # Imágenes estáticas
│   │   ├── logos/
│   │   └── publicidades/
│   └── uploads/                    # Almacenamiento de archivos subidos
│       ├── vehiculos/
│       ├── usuarios/
│       ├── documentos/
│       └── comprobantes/
│
├── templates/                       # Plantillas Jinja2
│   ├── base.html                  # Plantilla base
│   ├── admin/                      # Vistas administrativas
│   ├── users/                      # Vistas de usuario
│   ├── vendedor/                   # Vistas de vendedor
│   ├── soporte/                    # Vistas de soporte
│   ├── notificaciones/             # Vistas de notificaciones
│   └── [otros templates]
│
├── admin_routes.py                  # Rutas administrativas
├── users_bp.py                      # Rutas de usuario
├── vendedores.py                    # Rutas y lógica de vendedor
├── mensajes_bp.py                   # Sistema de mensajería
├── notificaciones_routes.py         # Rutas de notificaciones
├── soporte_routes.py                # Rutas de soporte e IA
├── comparador_routes.py             # Rutas del comparador
│
└── DOCUMENTACION_SISTEMA_DRIVEMARKET.md  # Documentación técnica
```

---

## 📂 Estructura del Proyecto

### Arquitectura Modular (Blueprints)

Drivemarket utiliza **Blueprints de Flask** para una arquitectura modular y escalable:

#### **1. Admin (`admin_routes.py`)**
Gestión completa del sistema:
- Crear/editar/eliminar usuarios
- Moderación de vehículos
- Validación de planes destacados
- Auditoría de logs
- Gestión de roles
- Panel de reportes

#### **2. Usuarios (`users_bp.py`)**
Gestión de cuenta del comprador:
- Registro e inicio de sesión
- Perfil de usuario
- Cambio de contraseña
- Preferencias
- Historial de búsquedas

#### **3. Vendedores (`vendedores.py`)**
Dashboard y herramientas de vendedor:
- Centro de control del inventario
- Publicación de vehículos
- Verificación KYC
- Solicitud de planes destacados
- Análisis de vendedor
- Seguimiento de conversiones

#### **4. Mensajes (`mensajes_bp.py`)**
Sistema de chat interno:
- Creación de conversaciones
- Envío de mensajes
- Doble borrado
- Historial de chat
- Notificaciones de nuevos mensajes

#### **5. Notificaciones (`notificaciones_routes.py`)**
Centro de alertas:
- Notificaciones de precio
- Alertas de mensaje nuevo
- Alertas del sistema
- Gestión de lectura
- Paginación

#### **6. Soporte e IA (`soporte_routes.py`)**
Inteligencia artificial y atención al cliente:
- Chatbot híbrido (FAQ + OpenAI)
- Gestión de FAQs
- Panel de soporte
- Integración con OpenAI
- Respuestas automáticas

#### **7. Comparador (`comparador_routes.py`)**
Herramienta de comparación:
- Comparación lado a lado
- Análisis técnico IA
- Recomendaciones
- Métricas de comparación

---

## 🔐 Roles y Permisos

### Roles del Sistema

| Rol | Descripción | Permisos |
|-----|-------------|----------|
| **Comprador** | Usuario regular que busca vehículos | Ver catálogo, Mensajes, Notificaciones, Comparar |
| **Vendedor** | Concesionario o vendedor particular | Publicar vehículos, Dashboard, Planes destacados |
| **Editor** | Moderador de contenido | Editar vehículos, Cambiar información |
| **Moderador** | Validador de vendedores | Aprobar KYC, Validar documentos |
| **Admin** | Administrador de plataforma | Gestión de usuarios, Roles, Logs, Reportes |
| **Superadmin** | Acceso total | Todas las operaciones, Configuración del sistema |

---

## 🗄️ Base de Datos

### Tablas Principales

#### **usuarios**
- Almacena información de todos los usuarios
- Roles: comprador, vendedor, admin, etc.
- Autenticación y sesiones

#### **perfil_vendedor**
- Extensión de usuario para vendedores
- Información KYC (Cédula, documentos)
- Datos bancarios
- Estado de verificación

#### **vehiculos**
- Catálogo principal de vehículos
- Detalles técnicos (Marca, Modelo, Año, Precio)
- Estado de publicación
- Métricas de rendimiento

#### **imagenes_vehiculos**
- Galería de fotos por vehículo
- Rutas de imágenes con watermark
- Orden de visualización

#### **conversaciones** & **mensajes**
- Chat entre compradores y vendedores
- Mensajes encriptados
- Doble borrado

#### **notificaciones**
- Alertas de precio
- Nuevos mensajes
- Eventos del sistema
- Estado de lectura

#### **faqs**
- Base de datos de preguntas frecuentes
- Categorías
- Respuestas dinámicas
- Creadas por administradores

#### **conversaciones_chatbot**
- Historial de conversaciones con IA
- Feedback de utilidad
- Tipo de respuesta (FAQ, IA, etc.)

#### **logs_admin**
- Trazabilidad de operaciones administrativas
- Quién hizo qué y cuándo
- Auditoría completa

---

## 🚀 Cómo Ejecutar

### Desarrollo Local

```bash
# Activar virtual environment
# (En Windows)
venv\Scripts\activate
# (En Linux/Mac)
source venv/bin/activate

# Ejecutar la aplicación
python app.py
```

La aplicación estará disponible en: **http://localhost:5000**

### Con Gunicorn (Producción)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

## 📊 Funcionalidades por Módulo

### 🎯 Módulo de Vendedores

**Dashboard Principal:**
- Resumen de vehículos (Publicados, Borradores, Pausados)
- Estadísticas de vista por vehículo
- Últimas conversaciones
- Opciones de planes destacados
- Acceso rápido a KYC

**Inventario:**
- Tabla de vehículos con filtros
- Edición rápida
- Cambio de estado
- Borrado seguro
- Publicación masiva

**Publicación de Vehículo:**
- 12+ campos técnicos
- Carga de imágenes con preview
- Watermark automático
- SEO slug automático
- Estados de completitud

**Planes Destacados:**
- Solicitud de promoción
- Subida de comprobante de pago
- Validación administrativa
- Historial de solicitudes

**KYC (Verificación):**
- Formulario de identidad
- Carga de documentos frontales/traseros
- Estado de verificación
- Información comercial

### 💬 Módulo de Mensajería

- Chat en tiempo real
- Historial completo
- Notificaciones
- Doble borrado independiente
- Búsqueda de conversaciones

### 🤖 Módulo de Soporte e IA

- **Chatbot Flotante**: Widget en todas las páginas
- **FAQs Dinámicas**: Gestión desde admin
- **OpenAI Integration**: Para preguntas complejas
- **Comparador IA**: Análisis de vehículos
- **Tono Professional**: Uso exclusivo de "Usted"

### 📈 Panel Administrativo

- Gestión de usuarios
- Moderación de vehículos
- Logs de auditoría
- Reportes por período
- Estadísticas del sistema

---

## 🔗 API y Rutas Principales

### Autenticación
```
GET/POST  /login                    # Inicio de sesión
GET/POST  /register                 # Registro
GET       /auth/google              # OAuth Google
GET       /logout                   # Cerrar sesión
```

### Vendedor
```
GET/POST  /vendedor/dashboard       # Dashboard principal
GET/POST  /vendedor/inventario      # Gestión de inventario
GET/POST  /vendedor/publicar        # Publicar vehículo
GET/POST  /vendedor/kyc             # Verificación KYC
GET/POST  /vendedor/planes          # Planes destacados
GET       /vendedor/vender-premium  # Opciones premium
```

### Usuario
```
GET/POST  /perfil                   # Perfil de usuario
GET/POST  /cuenta/ajustes           # Ajustes de cuenta
GET       /favoritos                # Vehículos guardados
GET       /historial                # Historial de búsqueda
```

### Catálogo
```
GET       /catalogo                 # Listado de vehículos
GET       /vehiculo/<slug>          # Detalle de vehículo
GET/POST  /comparador               # Herramienta de comparación
```

### Mensajes
```
GET/POST  /mensajes                 # Centro de mensajes
GET/POST  /mensajes/nuevo           # Nueva conversación
GET/POST  /mensajes/<id>            # Conversación específica
```

### Notificaciones
```
GET       /notificaciones           # Centro de notificaciones
GET/POST  /notificaciones/<id>      # Marcar como leído
DELETE    /notificaciones/<id>      # Eliminar notificación
```

### Soporte
```
GET/POST  /soporte                  # Centro de soporte
POST      /api/chatbot              # IA chatbot
GET/POST  /soporte/faq              # Base de FAQs
```

### Admin
```
GET/POST  /admin/dashboard          # Dashboard admin
GET/POST  /admin/usuarios           # Gestión de usuarios
GET/POST  /admin/vehículos          # Moderación
GET/POST  /admin/logs               # Auditoría
GET/POST  /admin/planes             # Validación de planes
GET/POST  /admin/reportes           # Reportes
```

---

## 💾 Modelos de Datos

### Ejemplo: Tabla de Usuarios
```python
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), default='comprador')
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)
```

### Ejemplo: Tabla de Vehículos
```python
class Vehiculo(db.Model):
    __tablename__ = 'vehiculos'
    id = db.Column(db.Integer, primary_key=True)
    marca = db.Column(db.String(50), nullable=False)
    modelo = db.Column(db.String(100), nullable=False)
    año = db.Column(db.Integer, nullable=False)
    precio = db.Column(db.Float, nullable=False)
    ciudad = db.Column(db.String(50))
    slug = db.Column(db.String(200), unique=True)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    vistas = db.Column(db.Integer, default=0)
    estado = db.Column(db.String(20), default='borrador')  # borrador, publicado, pausado
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
```

---

## 🎨 Características de Diseño

### Glassmorphism Premium
- Fondos semi-transparentes con blur
- Sombras suaves
- Gradientes sutiles
- Animaciones fluidas

### Componentes UI
- **Bento Grid**: Dashboards organizados
- **Cards Glassmorphic**: Componentes principales
- **Charts modernos**: Con Chart.js
- **Tablas interactivas**: Con filtros y búsqueda

### Paleta de Colores
- Naranja principal (#FF6B35)
- Negros profesionales (#1A1A1A)
- Blancos premium (#FFFFFF, #F5F5F5)
- Grises neutrales (#E8E8E8, #CCCCCC)

---

## 🛡️ Seguridad

### Prácticas Implementadas

1. **Autenticación**
   - Hash seguro de contraseñas (Werkzeug)
   - Sessions con Flask-Login
   - OAuth 2.0 con Google

2. **Validación de Archivos**
   - `secure_filename()` para nombres
   - Inyección de UUIDs
   - Validación de extensiones
   - Límite de tamaño

3. **Privacidad**
   - Acceso restringido a documentos KYC
   - Encriptación lógica de mensajes
   - Roles con permisos específicos

4. **Auditoría**
   - Logs completos de operaciones admin
   - Seguimiento de cambios
   - Trazabilidad de eventos

---

## 📝 Uso y Ejemplos

### Publicar un Vehículo (Vendedor)

1. Acceder a `/vendedor/inventario`
2. Clic en "Publicar Nuevo Vehículo"
3. Llenar formulario:
   - Marca, Modelo, Año
   - Precio y Kilometraje
   - Ciudad y Descripción
   - Cargar imágenes (se aplica watermark automático)
4. Guardar como borrador o publicar
5. URL slug se genera automáticamente

### Buscar y Comparar Vehículos (Comprador)

1. Acceder a `/catalogo`
2. Usar filtros de búsqueda
3. Ver detalles en `/vehiculo/<slug>`
4. Generar comparación en `/comparador`
5. IA proporciona recomendación

### Usar el Chatbot IA

1. Widget flotante en todas las páginas
2. Escribir pregunta
3. Sistema intenta responder con FAQ
4. Si no encuentra, usa OpenAI
5. Feedback sobre utilidad de respuesta

---

## 📚 Documentación Adicional

- [Documentación Técnica](Drivemarket/DOCUMENTACION_SISTEMA_DRIVEMARKET.md)
- [Requisitos Oficiales](Drivemarket/REQUISITOS_OFICIALES_DRIVEMARKET.md)
- [Esquema SQL original](todoen1unos.sql)
- [Esquema SQL actualizado](todoen1unos_pg.sql)

---

## 🤝 Contribuir

1. Fork el repositorio
2. Crear rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

### Estándares

- Python: PEP 8
- Commits: messages en inglés descriptivos
- Documentación: Actualizar cuando sea necesario

---

## 🐛 Problemas Comunes

### Error: `ModuleNotFoundError: No module named 'flask'`
```bash
pip install -r requirements.txt
```

### Error: `connection refused` en PostgreSQL
Verificar que PostgreSQL esté corriendo:
```bash
# Windows
pg_ctl -D "C:\Program Files\PostgreSQL\14\data" start

# Linux
sudo systemctl start postgresql
```

### Error: `No such table: usuarios`
Ejecutar migraciones:
```python
from app import app, db
with app.app_context():
    db.create_all()
```

### Error: CORS bloqueado
Verificar que `flask-cors` esté configurado en `app.py`

---

## 📞 Soporte

Para dudas o problemas:
- Email: soporte@drivemarket.com
- Documento de soporte: `/soporte`
- Chatbot IA: Disponible 24/7

---

## 📄 Licencia

Este proyecto es privado y propietario de Drivemarket. Todos los derechos reservados © 2026.

---

## 🎯 Roadmap Futuro

- [ ] App móvil (React Native)
- [ ] Notificaciones push
- [ ] Búsqueda por voz
- [ ] Integración con sistemas de pago
- [ ] ML para recomendaciones
- [ ] Marketplace secundario

---

**Última actualización:** Abril 2026  
**Desarrollado por:** Samuel A.  
**Estado:** ✅ En Desarrollo Activo
# drivermarketV1
# drivermarketv1

