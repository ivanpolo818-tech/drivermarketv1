# 📁 Estructura de carpetas organizada

La documentación ha sido reorganizada por carpetas para mejor navegación.

## 🗂️ Nueva estructura

```
docs/
├── index.md                          # Página principal
├── stylesheets/
│   └── extra.css                    # Estilos personalizados
│
├── inicio/                           # 🚀 PARA EMPEZAR
│   ├── index.md                     # Índice de inicio
│   ├── bienvenida.md                # Introducción
│   └── primeros-pasos.md            # Ejecutar en 3 pasos
│
├── documentacion/                    # 📚 REFERENCIA TÉCNICA
│   ├── index.md                     # Índice de documentación
│   ├── manual-tecnico.md            # Manual completo (3,500+ líneas)
│   ├── diagramas.md                 # 10 diagramas Mermaid
│   ├── referencia-rapida.md         # Quick reference
│   └── indice.md                    # Índice maestro
│
└── referencia/                       # 📋 INFORMACIÓN GENERAL
    ├── index.md                     # Índice de referencias
    ├── resumen.md                   # Resumen completo
    ├── estado.md                    # Estado del proyecto
    ├── checklist.md                 # Verificación
    └── instalacion.md               # Troubleshooting
```

## 🎯 Navegación por sección

### 🚀 INICIO (`docs/inicio/`)
**Para empezar rápido**
- `index.md` - Elige por dónde empezar
- `bienvenida.md` - Introducción general
- `primeros-pasos.md` - Ejecuta en 3 pasos

**Tiempo estimado:** 5-10 minutos

---

### 📚 DOCUMENTACIÓN (`docs/documentacion/`)
**Para referencia técnica completa**
- `index.md` - Índice de documentación
- `manual-tecnico.md` - Guía técnica completa
- `diagramas.md` - Arquitectura visual
- `referencia-rapida.md` - Cheatsheet
- `indice.md` - Navegación maestro

**Tiempo estimado:** 30+ minutos (lectura completa)

---

### 📋 REFERENCIAS (`docs/referencia/`)
**Para información general y troubleshooting**
- `index.md` - Índice de referencias
- `resumen.md` - Descripción detallada
- `estado.md` - Status actual
- `checklist.md` - Verificación
- `instalacion.md` - Setup y solución de problemas

**Tiempo estimado:** 15-20 minutos

---

## 📍 Acceso rápido desde docs/index.md

La página principal `docs/index.md` te proporciona:
- ✅ Tabla de contenidos
- ✅ Links a cada sección
- ✅ Guía por rol (Junior, Senior, DevOps)
- ✅ Búsqueda integrada
- ✅ 3 opciones para empezar

---

## 🚀 Cómo navegar

### Opción 1: Comienza en index.md
```
http://localhost:8000
↓
Elige por dónde empezar
```

### Opción 2: Ve directamente a una sección
```
http://localhost:8000/inicio/
→ Comienza rápido

http://localhost:8000/documentacion/
→ Referencia técnica

http://localhost:8000/referencia/
→ Información general
```

### Opción 3: Usa la búsqueda
```
Presiona Ctrl+K (o Cmd+K)
Busca lo que necesitas
```

---

## 📊 Contenido por sección

| Sección | Archivos | Líneas | Contenido |
|---------|----------|--------|-----------|
| **Inicio** | 3 | ~500 | Introducción, primeros pasos |
| **Documentación** | 5 | ~4,000 | Manual técnico, diagramas, ejemplos |
| **Referencia** | 5 | ~1,000 | Resumen, estado, troubleshooting |
| **Total** | 13+ | ~5,500 | Documentación completa |

---

## 🔗 Links de acceso rápido

### Desde la raíz del proyecto

Si quieres links a la documentación, usa:
- `docs/inicio/` - Para nuevos desarrolladores
- `docs/documentacion/` - Para referencia técnica
- `docs/referencia/` - Para información general

### Desde archivos markdown

Usa paths relativos:
```markdown
[Ir a inicio](../inicio/)
[Ver manual](../documentacion/manual-tecnico.md)
[Consultar](../referencia/resumen.md)
```

### Links externos

Cuando despliegues:
```
https://tu-sitio.com/
https://tu-sitio.com/inicio/
https://tu-sitio.com/documentacion/
https://tu-sitio.com/referencia/
```

---

## 💡 Tips de navegación

### Busca rápido
Presiona `Ctrl+K` (o `Cmd+K` en Mac) para abrir la búsqueda

### Navega con sidebar
Usa el sidebar izquierdo para moverse entre secciones

### Modo oscuro
Usa el toggle en la esquina superior derecha

### Exporta a PDF
Haz click en el ícono de PDF en cualquier página

### Usa breadcrumbs
Sigue el path en la parte superior para navegar

---

## 📱 Responsive

La documentación es **totalmente responsive**:
- ✅ Desktop (ancho completo)
- ✅ Tablet (layout adaptado)
- ✅ Mobile (menú colapsable)

---

## ✅ Verifica la estructura

Ejecuta:
```bash
python verify_documentation.py
```

Debería mostrar ✓ en todos los archivos y carpetas.

---

## 🎯 Próximos pasos

1. **Ejecuta el sitio** → `python setup_docs.py serve`
2. **Abre en navegador** → http://localhost:8000
3. **Navega las secciones** → Explora cada carpeta
4. **Usa la búsqueda** → Encuentra lo que necesitas
5. **Consulta según necesidad** → Referencia rápida

---

**¡La documentación está completamente organizada y lista para usar!** 🎉

