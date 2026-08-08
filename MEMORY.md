# Memoria del Proyecto (Base de Conocimiento)

Este archivo sirve como memoria persistente para el agente de IA. Aquí se documentan las decisiones críticas de diseño, la infraestructura, la base de datos y cómo interactúan las distintas partes de la Suite Data Universal para PROESA / Banco Mundial.

## 1. Infraestructura de Servidor
- **Hardware/OS:** Windows Server 2016 con Interfaz Gráfica, 100GB RAM, 16 núcleos AMD Epyc.
- **Ejecución Automatizada:** Los scrapers se ejecutan de manera diaria y sin interrupciones.
- **Notificaciones:** Se utiliza **Resend** para el envío de alertas y reportes diarios por correo (indicando éxito o detalles de fallo de cada scraper).

## 2. Esquema de Base de Datos (SQLite Local)
Por requerimiento de simplicidad extrema, nula concurrencia de escritura, y retrocompatibilidad con la Interfaz Gráfica original, se decidió mantener la base de datos en **SQLite** (`suite_data.db`) tras un intento de migrar a PostgreSQL.
Para mantener la UI funcionando sin reescribir todo `suite_app.py`, `database.py` actúa como una "vista" de traducción en memoria, renombrando dinámicamente columnas como `comercio -> fuente` y `descuento_porcentaje -> descuento` al entregar los DataFrames.
**Tabla principal (`productos`)**:
- `id` (PK)
- `fecha_extraccion` (Ej: 2026-06-23)
- `fuente` (Ej: Éxito, Jumbo, Rappi, Alkosto, D1, Carulla)
- `internal_id`
- `nombre`, `marca`, `referencia`, `categoria`
- `tipo_producto` (Puede ser "Alcohol", "Tabaco", "Ultraprocesado" o "NULL")
- `grados_alcohol`, `medida`
- `precio_original`, `precio_final`, `descuento`, `precio_unidad`, `disponibilidad`
- `url_producto`, `descripcion`
- `raw_data` (JSON con metadatos adicionales)
- `deleted` (Int 0 o 1. "Soft Deletes" para Falsos Positivos detectados por Gemini).

## 3. Decisiones de Interfaz de Usuario (`suite_app.py`)
- Desarrollada con `CustomTkinter`, `Matplotlib` y `Seaborn`.
- Diseñada para correr directamente en el Windows Server 2016.
- **Pestaña Análisis:** Resumen, distribución de descuentos, marcas más vendidas, heatmap de correlación, etc. Filtros dinámicos.
- **Pestaña Comparativas:** Búsqueda cruzada de guerra de precios y evolución temporal de inflación de productos.
- **Pestaña Limpieza IA:** Usa el modelo `gemini-2.5-flash-lite` para limpiar falsos positivos enviando chunks de 50 (con espera de 10s ante error HTTP 503).

## 4. Scrapers y Transferencia de Conocimiento
- **Extracción Actual:** Éxito (`scraper_exito/`).
- **Nuevos Scrapers (Carulla, Jumbo, Rappi, Alkosto, D1):** Adaptarse al esquema de Postgres. Si hay antibot (ej. Cloudflare), utilizar `scrapling-official`. **IMPORTANTE:** Todos los scrapers sin excepción deben operar de forma **HTTP ONLY** empleando Scrapling para no requerir la carga pesada de navegadores Headless y optimizar recursos.
- **Transferencia a PROESA:** Todo el código debe estar altamente documentado (inline y guías operativas) para que el equipo técnico pueda apropiarse de la metodología, solucionar errores frecuentes y entender la extracción automatizada.

## 5. Notas de Contexto Recientes (Bitácora)
- *2026-06-30:* Se actualizaron los requerimientos para migrar a PostgreSQL local, correr en el servidor Windows con 100GB RAM, implementar el monitoreo con alertas diarias por correo vía Resend, e incluir productos ultraprocesados.
- **D1 (Migración a VTEX API)**: `scraper_d1/scraper.py`
  - D1 actualizó su arquitectura de Next.js (FastStore RSC) a VTEX tradicional.
  - La extracción ahora se hace consumiendo la API Catalog de VTEX (`/api/catalog_system/pub/products/search`).
  - Se utiliza `scrapling-official` en modo HTTP ONLY (`FetcherSession`) para realizar las peticiones simulando un navegador Chrome, eludiendo antibots.
  - VTEX presenta un comportamiento "engañoso" en sus conteos de categoría del frontend: el número que visualmente arrojan los filtros de categoría de la página incluye artículos con `Precio = 0` (Agotados / Inactivos en backend). El scraper filtra y descarta activamente estos productos mediante la condición `if price_final == 0: continue`, previniendo que contaminen los análisis estadísticos de PROESA.
  - Para obtener todos los productos correctamente ante fallas de jerarquía de VTEX, se itera específicamente por las subcategorías finales (ej. `["7/66/", "7/67/", "7/68/", "7/69/"]` para Vinos, Licores, Cervezas y Cigarrillos) en lugar de la raíz `C:7`.
- **Cañaveral**: `scraper_canaveral/scraper.py`
  - Se corrigió la extracción de `URL_Producto`. Anteriormente asignaba `category_url` (`/ca/licores/03`); ahora extrae el `slug` del chunk de Next.js (`"slug": "..."`) para construir la URL exacta del producto (`https://www.domicilioscanaveral.com/p/{slug}-{sku}`). Se actualizó el scraper y se migraron las 6,094 lecturas de Cañaveral en la base de datos a sus enlaces individuales directos.
  - Utiliza la misma arquitectura Next.js / FastStore (RSC) que D1.
  - La extracción se hace limpiamente buscando las cadenas JSON dentro de `__next_f.push` del código fuente, lo que nos permite usar requests puro sin bloquearnos por antibots.
- **Olímpica**: `scraper_olimpica/scraper.py`
  - Los cigarrillos/vaporizadores tienen una ruta totalmente independiente (`/supermercado/cigarrillos-y-vaporizadores`). Se debe iterar explícitamente ambas rutas para extraer el catálogo completo (que asciende a más de 2200 productos).
- **Makro (Next.js FastStore Complejo)**: `scraper_makro/scraper.py`
# Memoria del Proyecto (Base de Conocimiento)

Este archivo sirve como memoria persistente para el agente de IA. Aquí se documentan las decisiones críticas de diseño, la infraestructura, la base de datos y cómo interactúan las distintas partes de la Suite Data Universal para PROESA / Banco Mundial.

## 1. Infraestructura de Servidor
- **Hardware/OS:** Windows Server 2016 con Interfaz Gráfica, 100GB RAM, 16 núcleos AMD Epyc.
- **Ejecución Automatizada:** Los scrapers se ejecutan de manera diaria y sin interrupciones.
- **Notificaciones:** Se utiliza **Resend** para el envío de alertas y reportes diarios por correo (indicando éxito o detalles de fallo de cada scraper).

## 2. Esquema de Base de Datos (SQLite Local)
Por requerimiento de simplicidad extrema, nula concurrencia de escritura, y retrocompatibilidad con la Interfaz Gráfica original, se decidió mantener la base de datos en **SQLite** (`suite_data.db`) tras un intento de migrar a PostgreSQL.
Para mantener la UI funcionando sin reescribir todo `suite_app.py`, `database.py` actúa como una "vista" de traducción en memoria, renombrando dinámicamente columnas como `comercio -> fuente` y `descuento_porcentaje -> descuento` al entregar los DataFrames.
**Tabla principal (`productos`)**:
- `id` (PK)
- `fecha_extraccion` (Ej: 2026-06-23)
- `fuente` (Ej: Éxito, Jumbo, Rappi, Alkosto, D1, Carulla)
- `internal_id`
- `nombre`, `marca`, `referencia`, `categoria`
- `tipo_producto` (Puede ser "Alcohol", "Tabaco", "Ultraprocesado" o "NULL")
- `grados_alcohol`, `medida`
- `precio_original`, `precio_final`, `descuento`, `precio_unidad`, `disponibilidad`
- `url_producto`, `descripcion`
- `raw_data` (JSON con metadatos adicionales)
- `deleted` (Int 0 o 1. "Soft Deletes" para Falsos Positivos detectados por Gemini).

## 3. Decisiones de Interfaz de Usuario (`suite_app.py`)
- Desarrollada con `CustomTkinter`, `Matplotlib` y `Seaborn`.
- Diseñada para correr directamente en el Windows Server 2016.
- **Pestaña Análisis:** Resumen, distribución de descuentos, marcas más vendidas, heatmap de correlación, etc. Filtros dinámicos.
- **Pestaña Comparativas:** Búsqueda cruzada de guerra de precios y evolución temporal de inflación de productos.
- **Pestaña Limpieza IA:** Usa el modelo `gemini-2.5-flash-lite` para limpiar falsos positivos enviando chunks de 50 (con espera de 10s ante error HTTP 503).

## 4. Scrapers y Transferencia de Conocimiento
- **Extracción Actual:** Éxito (`scraper_exito/`).
- **Nuevos Scrapers (Carulla, Jumbo, Rappi, Alkosto, D1):** Adaptarse al esquema de Postgres. Si hay antibot (ej. Cloudflare), utilizar `scrapling-official`. **IMPORTANTE:** Todos los scrapers sin excepción deben operar de forma **HTTP ONLY** empleando Scrapling para no requerir la carga pesada de navegadores Headless y optimizar recursos.
- **Transferencia a PROESA:** Todo el código debe estar altamente documentado (inline y guías operativas) para que el equipo técnico pueda apropiarse de la metodología, solucionar errores frecuentes y entender la extracción automatizada.

## 5. Notas de Contexto Recientes (Bitácora)
- *2026-06-30:* Se actualizaron los requerimientos para migrar a PostgreSQL local, correr en el servidor Windows con 100GB RAM, implementar el monitoreo con alertas diarias por correo vía Resend, e incluir productos ultraprocesados.
- **D1 (Migración a VTEX API)**: `scraper_d1/scraper.py`
  - D1 actualizó su arquitectura de Next.js (FastStore RSC) a VTEX tradicional.
  - La extracción ahora se hace consumiendo la API Catalog de VTEX (`/api/catalog_system/pub/products/search`).
  - Se utiliza `scrapling-official` en modo HTTP ONLY (`FetcherSession`) para realizar las peticiones simulando un navegador Chrome, eludiendo antibots.
  - VTEX presenta un comportamiento "engañoso" en sus conteos de categoría del frontend: el número que visualmente arrojan los filtros de categoría de la página incluye artículos con `Precio = 0` (Agotados / Inactivos en backend). El scraper filtra y descarta activamente estos productos mediante la condición `if price_final == 0: continue`, previniendo que contaminen los análisis estadísticos de PROESA.
  - Para obtener todos los productos correctamente ante fallas de jerarquía de VTEX, se itera específicamente por las subcategorías finales (ej. `["7/66/", "7/67/", "7/68/", "7/69/"]` para Vinos, Licores, Cervezas y Cigarrillos) en lugar de la raíz `C:7`.
- **Cañaveral**: `scraper_canaveral/scraper.py`
  - Utiliza la misma arquitectura Next.js / FastStore (RSC) que D1.
  - La extracción se hace limpiamente buscando las cadenas JSON dentro de `__next_f.push` del código fuente, lo que nos permite usar requests puro sin bloquearnos por antibots.
- **Olímpica**: `scraper_olimpica/scraper.py`
  - Los cigarrillos/vaporizadores tienen una ruta totalmente independiente (`/supermercado/cigarrillos-y-vaporizadores`). Se debe iterar explícitamente ambas rutas para extraer el catálogo completo (que asciende a más de 2200 productos).
- **Makro (Next.js FastStore Complejo)**: `scraper_makro/scraper.py`
  - Se utiliza extracción Regex iterando el chunk `__next_f.push`.
  - La categoría viene oculta en referencias de estado JSON (RSC). Se programó un *unpacking* recursivo (`categoriesData` -> `$fd` -> `["$fe", "$ff"]`) para extraer el árbol de jerarquía (ej. `Bebidas > Cervezas, Vinos y Licores > Whisky`).
  - **Diferencia Crítica de Paginación:** FastStore en Makro no usa `page=` sino `currentPage=` en la URL, y además **la paginación está basada en el índice 1** (no en 0). Esto se documenta para futuros desarrollos en ecosistemas similares.
- **Robustez del Orquestador y Alertas**:
  - `main.py` fue modificado para detectar "Fallos Silenciosos". Si un scraper termina sin errores de excepción pero devuelve 0 productos extraídos (Ej. Cloudflare bloquea la data pero devuelve un HTTP 200 con el HTML del captcha), el orquestador lo reclasifica como un Error Crítico y lo envía en la alerta.
  - El sistema de correos con **Resend** fue migrado a usar un Dominio Verificado (`bzuluaga.site`) enviando correos formales (sin emojis, con HTML estructurado) a múltiples destinatarios configurados dinámicamente en el `.env`.
- **Rediseño Completo de la Suite Data (`suite_app.py` & `database.py`)**:
  - **UI Limpia y Filtros en TODO:** Eliminación de emojis, panel de filtros multidimensionales en **todas las pestañas** (*Comercio, Tipo [Alcohol/Tabaco], Subcategoría MDM, Estado INVIMA, Rango Fechas Modal, Rango Precios $ Min/Max, Checkbox Solo Ofertas y Buscador Libre*).
  - **Gestión INVIMA MDM (`GestionINVIMAFrame` & `AssignInvimaModal`):** Nueva pestaña y modal interactivo para consultar, validar en vivo y asignar/editar registros sanitarios INVIMA o marcar "No Aplica (-1)".
  - **Catálogo Nacional INVIMA (`CatalogoINVIMAFrame`):** Visor paginado de los 10,972+ registros sanitarios certificados. Se sincronizó completamente la información de `PP24-7001-INVIMA.xlsx`, alcanzando **100% con Clasificación (10,972)**, **98.6% con Grados de Alcohol (10,821)** y **80.7% con Marca (8,859)**.
  - **Grados de Alcohol:** Ingesta completada desde `PP24-7001-INVIMA.xlsx`, poblando grados de alcohol, marcas y clasificaciones en `invima_certificados`.
  - **Filtro de Precios Disponibles (> $0):** El módulo de Análisis (`AnalysisFrame`) utiliza `productos_normalizados` excluyendo precios iguales a 0 (no disponibles en tienda) para cálculos estadísticos limpios.
  - **Módulo de Extracción:** Opciones desplegables para ejecutar scrapers individuales (*Éxito, Carulla, Jumbo, Olímpica, D1, Makro, Cañaveral*) o ejecuciones globales.
  - **Exportación Multiformato:** Todos los visores y tablas de la suite permiten exportar en formato **JSON** (`.json`), **Excel** (`.xlsx`) y **CSV** (`.csv`).

- **Reestructuración MDM e Integración INVIMA (`Anexo-2024.xlsx` y `PP24-7001-INVIMA.xlsx`)**:
  - Se reestructuró la tabla `maestro_productos` en SQLite agregando las columnas `registro_sanitario_invima`, `codigo_unico_invima` y `nombre_invima`.
  - Se creó `import_invima.py` y `import_new_invima.py` logrando acumular **10,972 registros sanitarios oficiales del INVIMA** (4,024 del Anexo 2024 PVPLVA + 6,948 nuevos del catálogo nacional unificado `PP24-7001-INVIMA.xlsx`).
  - Se creó `seed_mdm_exito.py` para reiniciar y sembrar los productos únicos de **Éxito** como la base inicial de la tabla maestra (112 clasificados como `N/A - TABACO`).
  - Se creó `match_invima_deepseek.py` con la API de **DeepSeek AI** (`deepseek-v4-flash`) e `import_manual_invima.py` para importación manual parcial desde Excel (trantando `-1` como Falso Positivo con `deleted = 1`).
  - Se creó `match_multi_store_deepseek.py` para cruzar los productos sin mapear de **Cañaveral, Carulla, Jumbo, Olímpica, Makro, D1** contra los 1,936 productos maestros existentes con tolerancia CERO a falsos positivos (temperatura `0.0`, matching estricto de variante, empaque y volumen), alcanzando **2,695 productos unificados en MDM** y **23,475 lecturas de precios históricos normalizadas** en `productos_normalizados`.

- **Refactorización Arquitectónica Completa (Paquetes `ui/` y `core/`)**:
  - **Paquete Frontend `ui/`**:
    - **`ui/styles.py`**: Configuración dinámica de estilos para `ttk.Treeview` y conmutación de temas (Light/Dark).
    - **`ui/components/modals.py`**: Componentes y diálogos reutilizables (`export_dataframe_dialog`, `DateRangeModal`, `AssignInvimaModal`).
    - **`ui/views/`**: Módulos individuales para cada vista (`extraction_view.py`, `raw_viewer_view.py`, `normalized_viewer_view.py`, `analysis_view.py`, `standardization_view.py`).
    - **`ui/app.py`**: Clase principal `DataSuiteApp` con menú lateral y navegación.
  - **Paquete Backend `core/`**:
    - **`core/database.py`**: Servicio principal de base de datos SQLite y capa de traducción.
    - **`core/notifier.py`**: Servicio de alertas y notificaciones HTML vía Resend.
  - Scripts en raíz (`suite_app.py`, `database.py`, `notifier.py`) reducidos a wrappers limpios de punto de entrada y compatibilidad.
  - **Asistente de Vinculación y Filtros en Mapeo MDM (`UnifiedStandardizationFrame` & `CandidateMatchingModal`)**:
  - **Filtro Precios $0 (`Ocultar Precios $0`):** Opción agregada en el panel de control del Paso 1 para filtrar productos sin mapear cuyo último precio extraído sea $0 o nulo.
  - **Modal Interactivo `CandidateMatchingModal` (`ui/components/modals.py`):**
    - Modal espacioso (`1020x680px`) con tarjetas descriptivas y badge del **último precio extraído del producto crudo**.
    - **Matching Inteligente por Texto:** Algoritmo combinado (SequenceMatcher + Jaccard token overlap + bonus por marca) que calcula similitud % y muestra el **Top 15 candidatos maestro** ordenados descendentemente.
  - **Migración y Portabilidad del MDM (`export_mdm.py` & `import_mdm.py`)**:
  - **`export_mdm.py`:** Genera un respaldo JSON portátil (`data/mdm_export.json`) que empaqueta las tablas `maestro_productos`, `mapeo_productos` y las banderas de depuración (`deleted = 1`).
  - **`import_mdm.py`:** Lee `data/mdm_export.json`, restaura los registros en `suite_data.db` en cualquier PC mediante `INSERT OR REPLACE` y ejecuta automáticamente `database.run_normalization_etl()` para reconstruir `productos_normalizados`.

    - **Barra de Búsqueda en Vivo:** Permite filtrar y buscar en tiempo real entre todo el universo de `maestro_productos` sin cerrar el modal.
    - **Modo Interactivo:** Botón toggle `Matching Auto (Top 15)` que abre automáticamente el asistente al hacer clic en cualquier producto crudo de la tabla.




