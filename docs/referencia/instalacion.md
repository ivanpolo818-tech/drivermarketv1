# Instalación del Sitio de Documentación

## Requisitos

- Python 3.8+
- pip (gestor de paquetes)

## Instalación

### 1. Instalar Dependencias

```bash
# Navega al directorio del proyecto
cd c:\Users\ASUS\OneDrive\Documentos\Proyect

# Crea un entorno virtual
python -m venv .venv-docs

# Activa el entorno
# En Windows:
.venv-docs\Scripts\activate
# En Linux/Mac:
source .venv-docs/bin/activate

# Instala las dependencias
pip install -r requirements-docs.txt
```

### 2. Generar el Sitio

```bash
# Generar sitio estático
mkdocs build

# El sitio se generará en: site/
```

### 3. Servir Localmente

```bash
# Ejecutar servidor de desarrollo
mkdocs serve

# Acceder a: http://localhost:8000
# Hot reload automático al editar archivos
```

## Generar PDF

### Opción 1: Usando mkdocs-pdf-export

El plugin `mkdocs-pdf-export` genera PDFs automáticamente.

```bash
# El PDF se genera en: site/pdf/
mkdocs build

# Los archivos PDF estarán listos
```

### Opción 2: Usando Pandoc (Alternativa)

```bash
# Instalar Pandoc
# Windows: choco install pandoc
# Mac: brew install pandoc
# Linux: apt-get install pandoc

# Generar PDF a partir de Markdown
pandoc docs/index.md -o Drivemarket-Docs.pdf \
  --pdf-engine=xelatex \
  --template=eisvogel \
  -V colorlinks
```

### Opción 3: Usar Navegador (PDF desde HTML)

```bash
# 1. Generar sitio
mkdocs build

# 2. Abrir en navegador
# file:///ruta/al/proyecto/site/index.html

# 3. Ctrl+P → Guardar como PDF
```

## Estructura de Directorios

```
Drivemarket/
├── docs/                      # Archivos fuente
│   ├── index.md              # Página principal
│   ├── guia-inicio/          # Getting started
│   ├── manual-tecnico/       # Manual
│   ├── diagramas/            # Diagrams
│   ├── guia-rapida/          # Quick reference
│   ├── referencia/           # API Reference
│   ├── assets/               # Imágenes
│   ├── stylesheets/          # CSS personalizado
│   └── javascripts/          # JS personalizado
│
├── mkdocs.yml                # Configuración
├── requirements-docs.txt     # Dependencias
├── site/                     # Sitio generado (NO editar)
└── [otros archivos...]
```

## Desplegar Sitio

### GitHub Pages (Recomendado)

```bash
# 1. Asegúrate de estar en rama main
git checkout main

# 2. Deploy a GitHub Pages
mkdocs gh-deploy

# El sitio estará en: https://username.github.io/drivemarket/
```

### Netlify

```bash
# Crea cuenta en netlify.com
# Conecta tu repositorio GitHub
# Configura:
# - Build command: mkdocs build
# - Publish directory: site

# El sitio se deployará automáticamente
```

### Servidor Propio

```bash
# 1. Generar sitio
mkdocs build

# 2. Subir carpeta 'site/' a servidor web
# 3. Servir con nginx/apache

# Ejemplo nginx:
server {
    listen 80;
    server_name docs.drivemarket.com;
    root /var/www/drivemarket-docs/site;
    index index.html;
}
```

## Mantenimiento

### Actualizar la Documentación

```bash
# Edita archivos en docs/
nano docs/manual-tecnico/01-estructura.md

# El servidor de desarrollo recarga automáticamente
# mkdocs serve

# Cuando esté listo, haz commit
git add docs/
git commit -m "docs: actualizar sección estructura"
git push origin main
```

### Agregar Nueva Página

1. Crea archivo en `docs/`:
```bash
touch docs/nueva-seccion/nueva-pagina.md
```

2. Edita `mkdocs.yml` y agrega a `nav`:
```yaml
nav:
  - Nueva Sección:
    - Nueva Página: nueva-seccion/nueva-pagina.md
```

3. Genera el sitio:
```bash
mkdocs build
```

## Troubleshooting

### "No such file or directory: mkdocs"

```bash
# Verifica que el entorno virtual esté activado
# Reinstala las dependencias
pip install -r requirements-docs.txt
```

### El sitio no se actualiza

```bash
# Limpia la caché
rm -rf site/

# Reconstruye
mkdocs build
```

### Error en PDF generation

```bash
# Asegúrate de tener el plugin instalado
pip install mkdocs-pdf-export

# O usa la alternativa con Pandoc
pip install pandoc
```

## Ver el Sitio

Después de ejecutar `mkdocs serve`, el sitio estará disponible en:

**Local Development:** http://localhost:8000  
**GitHub Pages:** https://username.github.io/drivemarket  
**Netlify:** https://drivemarket-docs.netlify.app  

## Configuración Avanzada

Edita `mkdocs.yml` para personalizar:

- **Tema:** `theme.name` (material, readthedocs, etc.)
- **Colores:** `theme.palette`
- **Logo:** `theme.logo`
- **Favicon:** `theme.favicon`
- **Analytics:** `extra.analytics`

## Soporte

- 📚 [Documentación MkDocs](https://www.mkdocs.org/)
- 📚 [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- 💬 Slack: #documentation
- 📧 Email: tech@drivemarket.com

