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
        
        total_productos = sum(stats.values()) if stats else 0
        total_tiendas = len(stats) if stats else 0
        
        # Generar filas de la tabla de éxito
        filas_exito = ""
        if stats:
            for comercio, cantidad in stats.items():
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
            
        # Build HTML Master Template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <!-- Header -->
                <div style="background: #004481; color: #ffffff; padding: 25px 20px; text-align: center;">
                    <h1 style="margin: 0; font-size: 24px; font-weight: 300;">Datos Alcohol y Tabaco</h1>
                    <p style="margin: 10px 0 0 0; font-size: 14px; opacity: 0.9;">Reporte de ejecución web scraping</p>
                </div>
                
                <!-- Content -->
                <div style="padding: 30px;">
                    <div style="background: #e8f4f8; border-left: 4px solid #004481; padding: 15px; margin-bottom: 25px; border-radius: 4px;">
                        <h3 style="margin-top: 0; color: #004481;">Resumen del {today_str}</h3>
                        <p style="margin: 0;">El proceso de extracción automatizado ha finalizado. Se han recolectado un total de <strong>{total_productos} productos</strong> a través de <strong>{total_tiendas} catálogos comerciales</strong> exitosos.</p>
                    </div>
                    
                    <h3 style="color: #444; border-bottom: 2px solid #eee; padding-bottom: 10px;">Detalle de Extracción</h3>
                    <table style="width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 15px;">
                        <thead>
                            <tr>
                                <th style="padding: 12px 15px; text-align: left; background-color: #f8f9fa; border-bottom: 2px solid #e1e1e1; color: #555;">Supermercado / Fuente</th>
                                <th style="padding: 12px 15px; text-align: left; background-color: #f8f9fa; border-bottom: 2px solid #e1e1e1; color: #555;">Productos Recolectados</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filas_exito}
                        </tbody>
                    </table>
                    
                    {seccion_errores}
                </div>
                
                <!-- Footer -->
                <div style="background: #f1f1f1; text-align: center; padding: 20px; font-size: 12px; color: #777;">
                    <p style="margin: 0;">Este es un mensaje generado automáticamente por el Orquestador.</p>
                    <p style="margin: 5px 0 0 0;">© {datetime.date.today().year} PROESA</p>
                </div>
            </div>
        </body>
        </html>
        """
            
        params = {
            "from": f"Extracción Datos <{self.email_from}>",
            "to": self.emails_to,
            "subject": f"{'[ERROR] ' if errores else ''}Reporte de ejecución web scraping - {today_str}",
            "html": html_content
        }
        
        try:
            email = resend.Emails.send(params)
            print(f"Email report sent successfully! ID: {email.get('id', 'unknown')}")
        except Exception as e:
            print(f"Failed to send email report: {e}")

if __name__ == '__main__':
    # Test dummy execution
    notifier = Notifier()
    if notifier.is_configured():
        # notifier.enviar_reporte_ejecucion({'Prueba': 100}, {})
        pass
    else:
        print("Set RESEND_API_KEY and EMAIL_TO to test.")
