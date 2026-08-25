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

    def enviar_reporte_ejecucion(self, stats, errores, descartados=None):
        """
        Envia un correo con el resumen de ejecucion de los scrapers y consolidacion IA con formato HTML profesional y sin emojis.
        stats: dict con formato {'Exito': 450, 'Carulla': 320, 'MDM_AI_Matcher': '...'}
        errores: dict con formato {'D1': 'Timeout error...'}
        descartados: list de dicts con formato [{'comercio': 'Rappi', 'nombre': '...', 'categoria': '...'}]
        """
        if not self.is_configured():
            print("Notifier no configurado o deshabilitado. Omitiendo envio de correo.")
            return
            
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        
        # Sumar únicamente valores numéricos de tiendas para el total recolectado
        total_productos = sum(v for v in stats.values() if isinstance(v, (int, float))) if stats else 0
        tiendas_procesadas = [k for k, v in stats.items() if isinstance(v, (int, float))]
        total_tiendas = len(tiendas_procesadas)
        
        # Generar filas de la tabla de éxito y secciones de IA
        filas_exito = ""
        seccion_ai_mdm = ""

        if stats:
            for comercio, cantidad in stats.items():
                if comercio == "MDM_AI_Matcher":
                    seccion_ai_mdm += f'''
                    <div style="background: #eef2ff; border-left: 4px solid #4f46e5; padding: 15px; margin-top: 20px; border-radius: 4px;">
                        <h4 style="margin-top: 0; color: #3730a3; margin-bottom: 5px; font-size: 14px; text-transform: uppercase;">Automatizacion e Inteligencia de Mercado MDM</h4>
                        <p style="margin: 0; font-size: 13px; color: #4338ca;"><strong>Resultado MDM AI:</strong> {cantidad}</p>
                    </div>
                    '''
                elif comercio == "MDM_Deduplication":
                    seccion_ai_mdm += f'''
                    <div style="background: #fdf4ff; border-left: 4px solid #c026d3; padding: 15px; margin-top: 15px; border-radius: 4px;">
                        <h4 style="margin-top: 0; color: #86198f; margin-bottom: 5px; font-size: 14px; text-transform: uppercase;">Deduplicacion y Fusion de Catalogo Maestro</h4>
                        <p style="margin: 0; font-size: 13px; color: #a21caf;"><strong>Resultado Deduplicacion:</strong> {cantidad}</p>
                    </div>
                    '''
                elif comercio == "INVIMA_AI_Matcher":
                    seccion_ai_mdm += f'''
                    <div style="background: #f0fdf4; border-left: 4px solid #16a34a; padding: 15px; margin-top: 15px; border-radius: 4px;">
                        <h4 style="margin-top: 0; color: #166534; margin-bottom: 5px; font-size: 14px; text-transform: uppercase;">Asignacion de Registros Sanitarios INVIMA (IA)</h4>
                        <p style="margin: 0; font-size: 13px; color: #15803d;"><strong>Resultado INVIMA:</strong> {cantidad}</p>
                    </div>
                    '''
                elif isinstance(cantidad, (int, float)):
                    filas_exito += f'''
                    <tr>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e2e8f0;"><strong>{comercio}</strong></td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e2e8f0; color: #16a34a; font-weight: bold;">{cantidad:,}</td>
                    </tr>
                    '''
                else:
                    filas_exito += f'''
                    <tr>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e2e8f0;"><strong>{comercio}</strong></td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e2e8f0; color: #16a34a; font-weight: bold;">{cantidad}</td>
                    </tr>
                    '''
        else:
            filas_exito = '<tr><td colspan="2" style="padding: 12px 15px; text-align: center; color: #64748b;">No hubo extracciones exitosas registradas en esta sesion.</td></tr>'

        # Generar sección de falsos positivos descartados
        seccion_descartados = ""
        if descartados is None:
            try:
                from core.database import get_recent_discarded_products
                descartados = get_recent_discarded_products(limit=25)
            except Exception:
                descartados = []

        if descartados:
            filas_desc = ""
            for item in descartados[:20]:
                com = item.get('comercio', 'N/A')
                nom = item.get('nombre', 'N/A')
                cat = item.get('categoria', item.get('descripcion', 'Falso positivo'))
                filas_desc += f'''
                <tr>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #fed7aa; font-size: 12px;"><strong>{com}</strong></td>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #fed7aa; font-size: 12px; color: #9a3412;">{nom}</td>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #fed7aa; font-size: 11px; color: #7c2d12;">{cat}</td>
                </tr>
                '''
            
            seccion_descartados = f'''
            <div style="background: #fff7ed; border-left: 4px solid #ea580c; padding: 15px; margin-top: 25px; border-radius: 4px;">
                <h4 style="margin-top: 0; color: #9a3412; font-size: 14px; text-transform: uppercase; margin-bottom: 8px;">
                    Listado de Productos Descartados (Falsos Positivos Depurados)
                </h4>
                <p style="font-size: 12px; color: #c2410c; margin-top: 0; margin-bottom: 12px;">
                    Los siguientes articulos no pertenecen a las categorias de Alcohol o Tabaco y fueron excluidos automaticamente mediante Soft Delete (deleted = 1):
                </p>
                <table style="width: 100%; border-collapse: collapse; background: #ffffff; border-radius: 4px; overflow: hidden;">
                    <thead>
                        <tr style="background: #ffedd5;">
                            <th style="padding: 8px 12px; text-align: left; font-size: 11px; text-transform: uppercase; color: #9a3412; border-bottom: 1px solid #fed7aa;">Comercio</th>
                            <th style="padding: 8px 12px; text-align: left; font-size: 11px; text-transform: uppercase; color: #9a3412; border-bottom: 1px solid #fed7aa;">Producto</th>
                            <th style="padding: 8px 12px; text-align: left; font-size: 11px; text-transform: uppercase; color: #9a3412; border-bottom: 1px solid #fed7aa;">Motivo / Categoria</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filas_desc}
                    </tbody>
                </table>
            </div>
            '''

        # Generar sección de errores
        seccion_errores = ""
        if errores:
            lista_errores = "".join([f'<div style="margin-bottom: 10px; font-size: 13px;"><strong>{comercio}:</strong> <span style="color: #dc2626;">{err}</span></div>' for comercio, err in errores.items()])
            seccion_errores = f'''
            <div style="background: #fef2f2; border-left: 4px solid #dc2626; padding: 15px; margin-top: 25px; border-radius: 4px;">
                <h4 style="margin-top: 0; color: #991b1b; font-size: 14px; text-transform: uppercase; margin-bottom: 10px;">Alertas de Extraccion ({len(errores)} comercios o modulos con incidencia)</h4>
                {lista_errores}
                <p style="font-size: 12px; color: #7f1d1d; margin-bottom: 0; margin-top: 15px;">Por favor, revise los registros del servidor para diagnosticar estas alertas.</p>
            </div>
            '''

        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #1e293b; background-color: #f1f5f9; margin: 0; padding: 20px; }}
                .container {{ max-width: 650px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; }}
                .header {{ background-color: #0f172a; color: #ffffff; padding: 25px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 18px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }}
                .header p {{ margin: 5px 0 0 0; font-size: 13px; color: #94a3b8; }}
                .content {{ padding: 25px; }}
                .summary-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-left: 4px solid #2563eb; padding: 15px; margin-bottom: 20px; border-radius: 4px; }}
                .summary-card table {{ width: 100%; border-collapse: collapse; }}
                .summary-card td {{ padding: 6px 0; font-size: 13px; }}
                .data-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; border: 1px solid #e2e8f0; border-radius: 4px; overflow: hidden; }}
                .data-table th {{ background-color: #f8fafc; padding: 10px 15px; text-align: left; font-size: 11px; text-transform: uppercase; color: #475569; border-bottom: 2px solid #e2e8f0; }}
                .footer {{ background-color: #f8fafc; padding: 20px; text-align: center; font-size: 11px; color: #64748b; border-top: 1px solid #e2e8f0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>PROESA - Suite Data Alcohol y Tabaco</h1>
                    <p>Reporte de Extraccion y Consolidacion Diaria - {today_str}</p>
                </div>
                <div class="content">
                    <div class="summary-card">
                        <table>
                            <tr>
                                <td><strong>Estado General:</strong></td>
                                <td style="text-align: right; color: {'#16a34a' if not errores else '#dc2626'}; font-weight: bold;">
                                    {'EJECUCION EXITOSA' if not errores else 'FINALIZADO CON ALERTAS'}
                                </td>
                            </tr>
                            <tr>
                                <td><strong>Total Productos Recolectados:</strong></td>
                                <td style="text-align: right; font-weight: bold; color: #0f172a;">{total_productos:,}</td>
                            </tr>
                            <tr>
                                <td><strong>Comercios Procesados:</strong></td>
                                <td style="text-align: right;">{total_tiendas}</td>
                            </tr>
                        </table>
                    </div>

                    <h3 style="color: #0f172a; margin-bottom: 10px; font-size: 15px; text-transform: uppercase;">Resumen por Comercio</h3>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Comercio</th>
                                <th>Registros Insertados / Actualizados</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filas_exito}
                        </tbody>
                    </table>

                    {seccion_ai_mdm}

                    {seccion_descartados}

                    {seccion_errores}

                </div>
                <div class="footer">
                    <p style="margin: 0 0 5px 0;">Este es un reporte automatico generado por la Suite Data de Inteligencia de Mercado (PROESA / Banco Mundial).</p>
                    <p style="margin: 0;">(C) {datetime.date.today().year} PROESA - Centro de Estudios en Proteccion Social y Economia de la Salud.</p>
                </div>
            </div>
        </body>
        </html>
        '''

        try:
            r = resend.Emails.send({
                "from": self.email_from,
                "to": self.emails_to,
                "subject": f"PROESA Data Suite - Reporte Diario de Extraccion [{today_str}]",
                "html": html_content
            })
            print(f"Correo de notificacion enviado exitosamente. ID: {r.get('id', 'OK')}")
        except Exception as e:
            print(f"Error al enviar notificacion por correo via Resend: {e}")

if __name__ == "__main__":
    notifier = Notifier()
    if notifier.is_configured():
        print("Notifier esta configurado correctamente.")
    else:
        print("Notifier no esta configurado o esta deshabilitado.")
