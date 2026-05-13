#!/usr/bin/env python3
"""
Script de verificación de documentación
Verifica que todos los archivos de documentación estén en su lugar
"""

import os
import sys
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def check_file_exists(filepath, description):
    """Verifica si un archivo existe"""
    exists = Path(filepath).exists()
    status = f"{Colors.GREEN}✓{Colors.END}" if exists else f"{Colors.RED}✗{Colors.END}"
    print(f"{status} {description:50} {'OK' if exists else 'MISSING'}")
    return exists

def check_directory_exists(dirpath, description):
    """Verifica si una carpeta existe"""
    exists = Path(dirpath).is_dir()
    status = f"{Colors.GREEN}✓{Colors.END}" if exists else f"{Colors.RED}✗{Colors.END}"
    print(f"{status} {description:50} {'OK' if exists else 'MISSING'}")
    return exists

def main():
    print(f"\n{Colors.BOLD}{Colors.BLUE}📊 VERIFICACIÓN DE DOCUMENTACIÓN DRIVEMARKET{Colors.END}\n")
    
    base_path = Path(__file__).parent
    os.chdir(base_path)
    
    all_good = True
    
    # Archivos principales
    print(f"{Colors.BOLD}📄 Archivos Markdown de Documentación:{Colors.END}")
    files_to_check = [
        ("LEETE.md", "Readme principal"),
        ("GUIA_RAPIDA_EJECUCION.md", "Guía rápida (3 pasos)"),
        ("MANUAL_TECNICO_COMPLETO.md", "Manual técnico completo"),
        ("DIAGRAMAS_TECNICOS.md", "Diagramas Mermaid"),
        ("GUIA_RAPIDA_REFERENCIA.md", "Quick reference"),
        ("INDICE_MAESTRO.md", "Índice maestro"),
        ("RESUMEN_DOCUMENTACION_FINAL.md", "Resumen final"),
        ("COMO_COMPLETAR_SITIO.md", "Checklist de completado"),
        ("SUMARIO_VISUAL.md", "Sumario visual"),
        ("INSTALAR_SITIO_DOCUMENTACION.md", "Instrucciones de instalación"),
    ]
    
    for filename, description in files_to_check:
        if not check_file_exists(filename, description):
            all_good = False
    
    # Archivos de configuración
    print(f"\n{Colors.BOLD}⚙️  Archivos de Configuración:{Colors.END}")
    config_files = [
        ("mkdocs.yml", "Configuración de MkDocs"),
        ("requirements-docs.txt", "Dependencias de documentación"),
        ("setup_docs.py", "Script de automatización"),
    ]
    
    for filename, description in config_files:
        if not check_file_exists(filename, description):
            all_good = False
    
    # Carpetas de documentación
    print(f"\n{Colors.BOLD}📁 Carpetas de Documentación:{Colors.END}")
    directories = [
        ("docs", "Carpeta raíz de documentación"),
        ("docs/stylesheets", "Estilos CSS"),
        ("docs/guia-inicio", "Guía de inicio"),
        ("docs/manual-tecnico", "Manual técnico"),
        ("docs/diagramas", "Diagramas"),
        ("docs/guias-desarrollo", "Guías de desarrollo"),
        ("docs/referencias", "Referencias"),
    ]
    
    for dirname, description in directories:
        if not check_directory_exists(dirname, description):
            all_good = False
    
    # Archivos principales de docs
    print(f"\n{Colors.BOLD}📖 Archivos en docs/:{Colors.END}")
    docs_files = [
        ("docs/index.md", "Página principal del sitio"),
        ("docs/stylesheets/extra.css", "Estilos personalizados"),
        ("docs/guia-inicio/bienvenida.md", "Bienvenida"),
        ("docs/guia-inicio/primeros-pasos.md", "Primeros pasos"),
    ]
    
    for filename, description in docs_files:
        if not check_file_exists(filename, description):
            all_good = False
    
    # Resultados
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    
    if all_good:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ ¡DOCUMENTACIÓN COMPLETA Y LISTA!{Colors.END}")
        print(f"\n{Colors.BLUE}Próximos pasos:{Colors.END}")
        print(f"  1. {Colors.YELLOW}python setup_docs.py install{Colors.END}")
        print(f"  2. {Colors.YELLOW}python setup_docs.py serve{Colors.END}")
        print(f"  3. Abre http://localhost:8000 en tu navegador")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ FALTAN ARCHIVOS{Colors.END}")
        print(f"\n{Colors.YELLOW}Verifica que los archivos marcados con ✗ estén presentes{Colors.END}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

