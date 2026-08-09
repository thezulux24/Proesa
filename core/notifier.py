import os
import datetime
import resend
from dotenv import load_dotenv

class Notifier:
    def __init__(self):
        load_dotenv()
        resend.api_key = os.getenv('RESEND_API_KEY', '')
        self.email_from = os.getenv('EMAIL_FROM', 'onboarding@resend.dev')
        
        # Parse emails (can be comma separated)
        emails_str = os.getenv('EMAIL_TO', '')
        self.emails_to = [e.strip() for e in emails_str.split(',') if e.strip()]
        
        # Boolean to toggle notifications
        self.enabled = os.getenv('ENABLE_NOTIFICATIONS', 'True').lower() in ('true', '1', 'yes')
        
    def is_configured(self):
        return bool(resend.api_key and self.emails_to and self.enabled)

    def enviar_reporte_ejecucion(self, stats, errores):
        """
        Envia un correo con el resumen de ejecucion de los scrapers con formato HTML profesional.
        stats: dict con formato {'Exito': 450, 'Carulla': 320}
        errores: dict con formato {'D1': 'Timeout error...'}
        """
        if not self.is_configured():
            print("Notifier not configured. Skipping email alert.")
            return
            
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        
        # Sumar únicamente valores numéricos de tiendas para el total recolectado
        total_productos = sum(v for v in stats.values() if isinstance(v, (int, float))) if stats else 0
        
        # Tiendas físicas/digitales procesadas (excluyendo estadísticas de IA si están en formato texto)
        tiendas_procesadas = [k for k, v in stats.items() if isinstance(v, (int, float))]
        total_tiendas = len(tiendas_procesadas)
        
        # Generar filas de la tabla de éxito y sección de IA
        filas_exito = ""
        seccion_ai_mdm = ""

        if stats:
            for comercio, cantidad in stats.items():
                if comercio == "MDM_AI_Matcher":

                    seccion_ai_mdm += f'''
                    <div style="background: #eef2ff; border-left: 4px solid #4f46e5; padding: 15px; margin-top: 20px; border-radius: 4px;">
                        <h4 style="margin-top: 0; color: #3730a3; margin-bottom: 5px;">🤖 Automatización e Inteligencia de Mercado MDM</h4>
                        <p style="margin: 0; font-size: 13px; color: #4338ca;"><strong>Resultado IA:</strong> {cantidad}</p>
                    </div>
                    '''
                elif comercio == "INVIMA_AI_Matcher":
                    seccion_ai_mdm += f'''
                    <div style="background: #f0fdf4; border-left: 4px solid #16a34a; padding: 15px; margin-top: 15px; border-radius: 4px;">
                        <h4 style="margin-top: 0; color: #166534; margin-bottom: 5px;">📜 Asignación de Registros Sanitarios INVIMA (IA)</h4>
                        <p style="margin: 0; font-size: 13px; color: #15803d;"><strong>Resultado INVIMA:</strong> {cantidad}</p>
                    </div>
                    '''

                elif isinstance(cantidad, (int, float)):
                    filas_exito += f'''
                    <tr>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e1e1e1;"><strong>{comercio}</strong></td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e1e1e1; color: #28a745; font-weight: bold;">{cantidad:,}</td>
                    </tr>
                    '''
                else:
                    filas_exito += f'''
                    <tr>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e1e1e1;"><strong>{comercio}</strong></td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e1e1e1; color: #28a745; font-weight: bold;">{cantidad}</td>
                    </tr>
                    '''
        else:
            filas_exito = '<tr><td colspan="2" style="padding: 12px 15px; text-align: center;">No hubo extracciones exitosas hoy.</td></tr>'


        # Generar sección de errores
        seccion_errores = ""
        if errores:
            lista_errores = "".join([f'<div style="margin-bottom: 10px;"><strong>{comercio}:</strong> <span style="color: #d8000c;">{err}</span></div>' for comercio, err in errores.items()])
            seccion_errores = f'''
            <div style="background: #fdf3f4; border-left: 4px solid #dc3545; padding: 15px; margin-top: 25px; border-radius: 4px;">
                <h3 style="margin-top: 0; color: #dc3545;">Alertas de Extracción ({len(errores)} tiendas fallaron)</h3>
                {lista_errores}
                <p style="font-size: 12px; color: #666; margin-bottom: 0; margin-top: 15px;">Por favor, revise los logs del servidor para más detalles técnicos sobre estos fallos.</p>
            </div>
            '''

        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333333; background-color: #f4f6f9; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ background-color: #1a202c; color: #ffffff; padding: 25px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 20px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }}
                .header p {{ margin: 5px 0 0 0; font-size: 13px; color: #cbd5e0; }}
                .content {{ padding: 30px; }}
                .summary-card {{ background: #ebf8ff; border-left: 4px solid #3182ce; padding: 15px; margin-bottom: 25px; border-radius: 4px; }}
                .summary-card table {{ width: 100%; border-collapse: collapse; }}
                .summary-card td {{ padding: 5px 0; font-size: 14px; }}
                .data-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                .data-table th {{ background-color: #f7fafc; padding: 12px 15px; text-align: left; font-size: 12px; text-transform: uppercase; color: #4a5568; border-bottom: 2px solid #e2e8f0; }}
                .footer {{ background-color: #edf2f7; padding: 20px; text-align: center; font-size: 12px; color: #718096; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>PROESA - Alcohol y tabaco scraping</h1>
                    <p>Reporte de Extracción Diaria de Precios - {today_str}</p>
                </div>
                <div class="content">
                    <div class="summary-card">
                        <table>
                            <tr>
                                <td><strong>Estado General:</strong></td>
                                <td style="text-align: right; color: {'#28a745' if not errores else '#d9534f'}; font-weight: bold;">
                                    {'EJECUCIÓN EXITOSA' if not errores else 'FINALIZADO CON ALERTAS'}
                                </td>
                            </tr>
                            <tr>
                                <td><strong>Total Productos Recolectados:</strong></td>
                                <td style="text-align: right; font-weight: bold;">{total_productos:,}</td>
                            </tr>
                            <tr>
                                <td><strong>Comercios Procesados:</strong></td>
                                <td style="text-align: right;">{total_tiendas}</td>
                            </tr>
                        </table>
                    </div>

                    <h3 style="color: #2d3748; margin-bottom: 10px;">Resumen por Comercio</h3>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Comercio</th>
                                <th>Registros Insertados</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filas_exito}
                        </tbody>
                    </table>

                    {seccion_ai_mdm}

                    {seccion_errores}

                </div>
                <div class="footer">
                    <p>Este es un reporte automático generado por la Suite Data de Inteligencia de Mercado (PROESA / Banco Mundial).</p>
                    <p>© {datetime.date.today().year} PROESA - Centro de Estudios en Protección Social y Economía de la Salud.</p>
                </div>
            </div>
        </body>
        </html>
        '''

        try:
            r = resend.Emails.send({
                "from": self.email_from,
                "to": self.emails_to,
                "subject": f"Reporte de Extracción PROESA Data Suite [{today_str}]",
                "html": html_content
            })
            print(f"Correo de notificación enviado exitosamente. ID: {r.get('id', 'OK')}")
        except Exception as e:
            print(f"Error al enviar notificación por correo vía Resend: {e}")

if __name__ == "__main__":
    notifier = Notifier()
    if notifier.is_configured():
        print("Notifier is properly configured.")
    else:
        print("Notifier is not configured or disabled.")
