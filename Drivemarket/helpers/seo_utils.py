import re
import unicodedata

def generate_slug(marca, modelo, anio, ciudad=None):
    """
    Genera un slug SEO-friendly: marca-modelo-anio-ciudad
    Ejemplo: Mazda CX-5 2018 Bogotá -> mazda-cx-5-2018-bogota
    """
    text = f"{marca} {modelo} {anio}"
    if ciudad:
        text += f" {ciudad}"
    
    # Normalizar (eliminar acentos)
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    
    # Minúsculas y eliminar caracteres no alfa-numéricos
    text = re.sub(r'[^\w\s-]', '', text).lower().strip()
    
    # Reemplazar espacios y guiones bajos por un solo guion
    text = re.sub(r'[\s_]+', '-', text)
    
    # Eliminar guiones duplicados
    text = re.sub(r'-+', '-', text)
    
    return text

