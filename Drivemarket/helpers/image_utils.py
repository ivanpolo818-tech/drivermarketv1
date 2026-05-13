import os
from PIL import Image, ImageDraw, ImageFont

def apply_watermark(image_path, text="DRIVE MARKET"):
    """
    Aplica una marca de agua de texto profesional a la imagen proporcionada.
    """
    if not os.path.exists(image_path):
        print(f"Error: No se encuentra la imagen en {image_path}")
        return False

    try:
        # Abrir la imagen original
        base = Image.open(image_path).convert("RGBA")
        width, height = base.size

        # Crear una capa para el watermark
        txt_layer = Image.new("RGBA", base.size, (255, 255, 255, 0))
        
        # Intentar cargar una fuente elegante, si no, usar la por defecto
        try:
            # En Windows, Arial es común. Ajustamos tamaño según la resolución de la foto
            font_size = int(width * 0.04) # 4% del ancho
            # Rutas comunes de fuentes en Windows
            font_paths = [
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "Roboto-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            ]
            font = None
            for path in font_paths:
                if os.path.exists(path):
                    font = ImageFont.truetype(path, font_size)
                    break
            if not font:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()

        draw = ImageDraw.Draw(txt_layer)

        # Configuración del texto (Separado por colores)
        text1 = "DRIVE"
        text2 = "MARKET"
        
        # Obtener dimensiones de ambas partes
        try:
            # DRIVE
            l1, t1, r1, b1 = draw.textbbox((0, 0), text1, font=font)
            w1 = r1 - l1
            h1 = b1 - t1
            # MARKET
            l2, t2, r2, b2 = draw.textbbox((0, 0), text2, font=font)
            w2 = r2 - l2
            # Total
            text_width = w1 + w2
            text_height = max(h1, b2 - t2)
        except AttributeError:
            # Fallback para versiones antiguas de Pillow
            w1, h1 = draw.textsize(text1, font=font)
            w2, h2 = draw.textsize(text2, font=font)
            text_width = w1 + w2
            text_height = max(h1, h2)

        # Posicionamiento: Margen 4%
        margin_x = int(width * 0.04)
        margin_y = int(height * 0.04)
        x = width - text_width - margin_x
        y = height - text_height - margin_y

        # COLORES PREMIUM
        # Sombra sutil para legibilidad (Gris oscuro transparente)
        shadow_color = (0, 0, 0, 60)
        color_drive = (255, 255, 255, 230)  # Blanco Premium con opacidad
        color_market = (255, 112, 67, 240) # Naranja oficial (#FF7043)
        
        # 1. Dibujar sombra (desplazada 2px)
        shadow_offset = max(1, int(width * 0.002))
        draw.text((x + shadow_offset, y + shadow_offset), text1, font=font, fill=shadow_color)
        draw.text((x + w1 + shadow_offset, y + shadow_offset), text2, font=font, fill=shadow_color)

        # 2. Dibujar Parte 1: DRIVE (Blanco para contraste profesional)
        draw.text((x, y), text1, font=font, fill=color_drive)
        
        # 3. Dibujar Parte 2: MARKET (Naranja institucional)
        draw.text((x + w1, y), text2, font=font, fill=color_market)

        # Combinar capas
        out = Image.alpha_composite(base, txt_layer)
        
        # Guardar en formato original preservando calidad
        if image_path.lower().endswith(('.jpg', '.jpeg')):
            out = out.convert("RGB")
            out.save(image_path, "JPEG", quality=95, optimize=True)
        else:
            out.save(image_path, optimize=True)
            
        return True

    except Exception as e:
        print(f"Error al aplicar marca de agua: {e}")
        return False

