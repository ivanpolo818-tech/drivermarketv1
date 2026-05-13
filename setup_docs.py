#!/usr/bin/env python3
"""
Script de Automatización - Sitio de Documentación Drivemarket

Funcionalidades:
1. Instalar dependencias de MkDocs
2. Generar sitio estático HTML
3. Generar PDFs
4. Servir localmente para desarrollo
5. Deploy a GitHub Pages

Uso:
    python setup_docs.py install     # Instalar dependencias
    python setup_docs.py build       # Generar sitio
    python setup_docs.py serve       # Servidor local
    python setup_docs.py pdf         # Generar PDFs
    python setup_docs.py deploy      # Deploy a GitHub Pages
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

# Colores para terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def run_command(cmd, description=""):
    """Ejecuta un comando y retorna True/False"""
    try:
        if description:
            print_info(description)
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Error: {e}")
        if e.stderr:
            print(e.stderr)
        return False

def install_dependencies():
    """Instala las dependencias de MkDocs"""
    print_header("Instalando Dependencias de Documentación")
    
    # Verificar Python
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print_error(f"Python 3.8+ requerido (tienes {python_version.major}.{python_version.minor})")
        return False
    
    print_success(f"Python {python_version.major}.{python_version.minor} detectado")
    
    # Crear/usar entorno virtual
    venv_path = Path(".venv-docs")
    if not venv_path.exists():
        print_info("Creando entorno virtual...")
        if not run_command(f"{sys.executable} -m venv .venv-docs", ""):
            return False
        print_success("Entorno virtual creado")
    else:
        print_success("Entorno virtual ya existe")
    
    # Instalar dependencias
    print_info("Instalando dependencias...")
    if platform.system() == "Windows":
        pip_cmd = ".venv-docs\\Scripts\\pip"
    else:
        pip_cmd = ".venv-docs/bin/pip"
    
    if not run_command(f"{pip_cmd} install --upgrade pip", ""):
        return False
    
    if not run_command(f"{pip_cmd} install -r requirements-docs.txt", "Instalando MkDocs y plugins..."):
        return False
    
    print_success("Todas las dependencias instaladas correctamente")
    
    # Información de próximos pasos
    print_info("Próximos pasos:")
    if platform.system() == "Windows":
        print(f"  1. Activar entorno: .venv-docs\\Scripts\\activate")
    else:
        print(f"  1. Activar entorno: source .venv-docs/bin/activate")
    print(f"  2. Servir sitio: python setup_docs.py serve")
    
    return True

def build_site():
    """Genera el sitio estático HTML"""
    print_header("Generando Sitio Estático")
    
    if not run_command("mkdocs build", "Compilando sitio..."):
        print_error("Error al compilar sitio")
        return False
    
    print_success("Sitio compilado en directorio 'site/'")
    print_info("Archivo principal: site/index.html")
    
    return True

def serve_site():
    """Sirve el sitio localmente para desarrollo"""
    print_header("Iniciando Servidor Local")
    
    print_info("Servidor iniciado en: http://localhost:8000")
    print_info("Presiona CTRL+C para detener")
    print_warning("El sitio se recargará automáticamente cuando edites archivos\n")
    
    if not run_command("mkdocs serve", ""):
        return False
    
    return True

def generate_pdfs():
    """Genera PDFs de la documentación"""
    print_header("Generando PDFs")
    
    # Primero construir sitio
    if not build_site():
        return False
    
    print_info("Generando PDF desde sitio compilado...")
    
    # Verificar si existe Pandoc para mejor generación de PDF
    try:
        subprocess.run("pandoc --version", shell=True, capture_output=True, check=True)
        print_success("Pandoc detectado")
        
        # Generar PDF con Pandoc
        if run_command(
            'pandoc docs/index.md -o site/pdf/drivemarket-docs.pdf --pdf-engine=xelatex -V geometry:margin=1in',
            "Generando PDF con Pandoc..."
        ):
            print_success("PDF generado: site/pdf/drivemarket-docs.pdf")
    except:
        print_warning("Pandoc no instalado, usando alternativa con mkdocs-pdf-export")
        print_info("Para mejor calidad, instala Pandoc:")
        if platform.system() == "Windows":
            print("  choco install pandoc")
        elif platform.system() == "Darwin":
            print("  brew install pandoc")
        else:
            print("  apt-get install pandoc")
    
    print_success("PDFs generados en: site/pdf/")
    
    return True

def deploy_github_pages():
    """Deploy a GitHub Pages"""
    print_header("Deploying a GitHub Pages")
    
    # Verificar que estemos en rama main
    try:
        branch = subprocess.run(
            "git rev-parse --abbrev-ref HEAD",
            shell=True,
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        
        if branch != "main":
            print_warning(f"Actualmente en rama '{branch}', GitHub Pages generalmente usa 'main'")
    except:
        print_error("No es un repositorio git")
        return False
    
    print_info("Haciendo deploy a GitHub Pages...")
    if not run_command("mkdocs gh-deploy", ""):
        print_error("Error en deploy")
        print_info("Asegúrate de haber configurado GitHub Pages en settings")
        return False
    
    print_success("Sitio deployado a GitHub Pages")
    print_info("URL: https://username.github.io/drivemarket/")
    
    return True

def show_help():
    """Muestra la ayuda"""
    print(f"""
{Colors.BOLD}Drivemarket - Script de Documentación{Colors.ENDC}

{Colors.BOLD}Uso:{Colors.ENDC}
  python setup_docs.py [comando]

{Colors.BOLD}Comandos:{Colors.ENDC}
  install     Instalar dependencias de MkDocs
  build       Generar sitio estático HTML
  serve       Servir sitio localmente (http://localhost:8000)
  pdf         Generar archivos PDF
  deploy      Hacer deploy a GitHub Pages
  clean       Limpiar archivos generados
  help        Mostrar esta ayuda

{Colors.BOLD}Ejemplos:{Colors.ENDC}
  python setup_docs.py install      # Primera vez
  python setup_docs.py serve        # Desarrollo local
  python setup_docs.py build        # Producción
  python setup_docs.py pdf          # Generar PDFs
  python setup_docs.py deploy       # GitHub Pages

{Colors.BOLD}Flujo típico:{Colors.ENDC}
  1. python setup_docs.py install
  2. python setup_docs.py serve
  3. Edita archivos en docs/
  4. python setup_docs.py build
  5. python setup_docs.py pdf
  6. python setup_docs.py deploy
    """)

def clean_files():
    """Limpia archivos generados"""
    print_header("Limpiando Archivos Generados")
    
    if Path("site").exists():
        shutil.rmtree("site")
        print_success("Directorio 'site/' eliminado")
    
    if Path(".site_cache").exists():
        shutil.rmtree(".site_cache")
        print_success("Caché eliminado")
    
    print_success("Limpieza completada")

def main():
    if len(sys.argv) < 2:
        show_help()
        return
    
    comando = sys.argv[1].lower()
    
    if comando == "install":
        install_dependencies()
    elif comando == "build":
        build_site()
    elif comando == "serve":
        serve_site()
    elif comando == "pdf":
        generate_pdfs()
    elif comando == "deploy":
        deploy_github_pages()
    elif comando == "clean":
        clean_files()
    elif comando == "help" or comando == "-h" or comando == "--help":
        show_help()
    else:
        print_error(f"Comando desconocido: '{comando}'")
        print_info("Usa 'python setup_docs.py help' para ver todos los comandos")

if __name__ == "__main__":
    main()

