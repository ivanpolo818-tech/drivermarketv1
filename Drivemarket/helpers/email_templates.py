# -*- coding: utf-8 -*-
from flask import url_for

def generar_html_email(tipo, data):
    """
    Genera un HTML premium para correos electrónicos.
    Tipos: 'success' (verde), 'alert' (rojo), 'warning' (naranja), 'info' (azul)
    Data: dict con titulo, subtitulo, mensaje, datos_clave (lista de dicts), boton_texto, boton_url
    """
    
    # Configuración de colores según el tipo
    colores = {
        'success': {'header': '#10b981', 'bg_icon': '#ecfdf5', 'text_icon': '#059669', 'btn': '#10b981', 'icon': '✅'},
        'alert': {'header': '#ef4444', 'bg_icon': '#fef2f2', 'text_icon': '#dc2626', 'btn': '#ef4444', 'icon': '🚨'},
        'warning': {'header': '#f59e0b', 'bg_icon': '#fffbeb', 'text_icon': '#d97706', 'btn': '#f59e0b', 'icon': '⚠️'},
        'info': {'header': '#6366f1', 'bg_icon': '#eef2ff', 'text_icon': '#4f46e5', 'btn': '#6366f1', 'icon': 'ℹ️'}
    }
    
    c = colores.get(tipo, colores['info'])
    
    titulo = data.get('titulo', 'Notificación de Drive Market')
    subtitulo = data.get('subtitulo', 'Portal de Administración')
    mensaje = data.get('mensaje', '')
    datos_clave = data.get('datos_clave', []) # [{'label': 'ID', 'value': '123'}]
    boton_texto = data.get('boton_texto')
    boton_url = data.get('boton_url', '#')
    
    # Generar bloques de datos clave
    bloques_datos = ""
    if datos_clave:
        for item in datos_clave:
            bloques_datos += f"""
            <div style="margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid #f1f5f9;">
                <span style="font-size: 12px; color: #64748b; text-transform: uppercase; font-weight: bold; letter-spacing: 0.5px;">{item['label']}</span><br>
                <span style="font-size: 15px; color: #1e293b; font-weight: 500;">{item['value']}</span>
            </div>
            """

    # Botón si existe
    html_boton = ""
    if boton_texto:
        html_boton = f"""
        <div style="text-align: center; margin-top: 35px;">
            <a href="{boton_url}" style="display: inline-block; background-color: {c['btn']}; color: #ffffff; padding: 14px 32px; text-decoration: none; border-radius: 10px; font-weight: 600; font-size: 15px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
                {boton_texto}
            </a>
        </div>
        """

    html_final = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{titulo}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; color: #334155;">
        <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 520px; margin: 20px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <!-- Header -->
            <tr>
                <td style="background: linear-gradient(135deg, #1e293b, #0f172a); padding: 25px 20px; text-align: center;">
                    <h1 style="color: #ffffff; margin: 0; font-size: 22px; font-weight: 800; letter-spacing: 1.5px;">DRIVE MARKET</h1>
                    <p style="color: #94a3b8; margin: 5px 0 0 0; font-size: 11px; text-transform: uppercase; font-weight: 600; letter-spacing: 1px;">{subtitulo}</p>
                </td>
            </tr>
            
            <!-- Body -->
            <tr>
                <td style="padding: 30px 25px;">
                    <!-- Icon Circle -->
                    <div style="text-align: center; margin-bottom: 20px;">
                        <div style="display: inline-block; width: 55px; height: 55px; background-color: {c['bg_icon']}; border-radius: 50%; text-align: center; line-height: 55px; font-size: 28px;">
                            {c['icon']}
                        </div>
                    </div>
                    
                    <h2 style="color: #0f172a; font-size: 20px; font-weight: 700; margin-bottom: 15px; text-align: center;">{titulo}</h2>
                    
                    <div style="font-size: 14px; color: #475569; line-height: 1.5; margin-bottom: 25px; text-align: center;">
                        {mensaje}
                    </div>
                    
                    <!-- Data Card -->
                    {f'<div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 15px; margin-top: 20px;">{bloques_datos}</div>' if bloques_datos else ''}
                    
                    {html_boton}
                </td>
            </tr>
            
            <!-- Footer -->
            <tr>
                <td style="background-color: #f1f5f9; padding: 20px; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="margin: 0; font-size: 11px; color: #64748b; line-height: 1.4;">
                        Mensaje automático de <strong>Drive Market</strong>.<br>
                        Actualización de cuenta o administración.
                    </p>
                    <div style="margin-top: 15px;">
                        <a href="#" style="color: #6366f1; text-decoration: none; font-size: 11px; font-weight: 600; margin: 0 8px;">Términos</a>
                        <a href="#" style="color: #6366f1; text-decoration: none; font-size: 11px; font-weight: 600; margin: 0 8px;">Privacidad</a>
                        <a href="#" style="color: #6366f1; text-decoration: none; font-size: 11px; font-weight: 600; margin: 0 8px;">Ayuda</a>
                    </div>
                    <p style="margin-top: 20px; font-size: 10px; color: #94a3b8; text-transform: uppercase; font-weight: bold; letter-spacing: 1px;">
                        &copy; 2026 Drive Market S.A.S.
                    </p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    return html_final

