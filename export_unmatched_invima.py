import sqlite3
import pandas as pd

def export_unmatched_invima(output_excel="productos_pendientes_invima.xlsx"):
    conn = sqlite3.connect("suite_data.db")
    
    query = """
        SELECT 
            mp.codigo_universal AS [Codigo Universal],
            m.producto_id AS [ID Producto Exito],
            mp.nombre_estandar AS [Nombre Comercial],
            mp.marca_estandar AS [Marca],
            mp.tipo_producto_estandar AS [Tipo Producto],
            mp.subcategoria_estandar AS [Subcategoria / Categoria],
            mp.volumen_estandar AS [Medida / Volumen],
            mp.grados_alcohol_estandar AS [Grados Alcohol],
            h.precio_final AS [Precio Actual ($)],
            h.url_producto AS [URL Producto],
            '' AS [REGISTRO_SANITARIO_INVIMA_MANUAL (Diligenciar)],
            '' AS [NOTAS_OBSERVACIONES]
        FROM maestro_productos mp
        LEFT JOIN mapeo_productos m ON mp.codigo_universal = m.codigo_universal
        LEFT JOIN productos_historico h ON m.comercio = h.comercio AND m.producto_id = h.producto_id
        WHERE (mp.registro_sanitario_invima = 'SIN_REGISTRO_ENCONTRADO' 
            OR mp.registro_sanitario_invima IS NULL 
            OR mp.registro_sanitario_invima = '')
          AND mp.tipo_producto_estandar = 'Alcohol'
          AND mp.deleted = 0
        GROUP BY mp.codigo_universal
        ORDER BY mp.marca_estandar, mp.nombre_estandar
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Exportar a Excel con formato
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Pendientes_INVIMA")
        
        # Ajustar ancho de columnas automáticamente
        worksheet = writer.sheets["Pendientes_INVIMA"]
        for col in worksheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = col[0].column_letter
            worksheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 60)
            
    print(f"OK: Excel generado exitosamente en '{output_excel}' con {len(df)} productos pendientes.")
    return output_excel, len(df)

if __name__ == "__main__":
    export_unmatched_invima()
