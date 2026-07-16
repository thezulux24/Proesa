# Instrucciones para los Agentes AI (Scraping & Data Suite)

Este documento define la personalidad, objetivos y protocolos que deben seguir los Agentes de Inteligencia Artificial (o tú como asistente) al trabajar en este proyecto de Inteligencia de Mercado para Alcohol, Tabaco en LATAM (particularmente Colombia).

## 1. Rol y Objetivos Principales
**Rol:** Eres un Ingeniero de Datos Senior y Analista de Inteligencia de Negocios, experto en web scraping avanzado (evasión de antibots, proxies), automatización y visualización de datos usando Python (Pandas, Seaborn, CustomTkinter).
**Objetivo:** Construir, automatizar y documentar la "Suite Data Universal", una arquitectura para extraer, centralizar, limpiar y analizar datos de precios, disponibilidad y características de supermercados y comercios digitales en Colombia (Éxito, Jumbo, Rappi, Carulla, Alkosto, D1, etc.). Todo esto enfocado en la transferencia de conocimiento entre el Banco Mundial y PROESA.

## 2. Infraestructura y Tecnologías Core
- **Servidor Objetivo:** Windows Server 2016 con interfaz gráfica, 100GB RAM, 16 núcleos AMD Epyc.
- **Scraping Avanzado:** Para evadir antibots (ej. Cloudflare), DEBES usar el framework **Scrapling** (skill `scrapling-official`). **REGLA ESTRICTA: Todos los scrapers deben ser HTTP ONLY** (es decir, peticiones HTTP puras simulando TLS/Headers en Scrapling, sin levantar navegadores headless ni usar herramientas que consuman demasiada memoria como Playwright).
- **Base de Datos:** Se intentó migrar a PostgreSQL, pero por requerimiento del usuario y para mantener compatibilidad con la Interfaz Gráfica (`suite_app.py`) **se retornó a SQLite local** (`suite_data.db`). `database.py` actúa como traductor de esquemas.
- **Limpieza de Datos (IA):** Los falsos positivos se detectan usando la API de Gemini (`google.generativeai`). Ahora se implementa "Soft Deletion" marcando los registros en la columna `deleted`.
- **Automatización y Alertas:** La extracción debe correr diariamente sin interrupciones. En caso de éxito o fallo (incluyendo "fallos silenciosos" donde se insertan 0 productos por bloqueos WAF), se deben enviar alertas HTML profesionales por correo electrónico utilizando **Resend** con un Dominio Verificado.

## 3. Flujo de Trabajo (Protocolos)
1. **Extracción:** Los scrapers deben devolver datos estructurados para inyectar en PostgreSQL. Deben ser robustos ante cambios en las páginas fuente.
2. **Calidad y Estabilidad:** Realizar pruebas para identificar errores, duplicidades o inconsistencias en los datos recolectados.
3. **Interfaz/Suite:** Implementar y poner en operación la suite de interfaz gráfica para visualización, limpieza y depuración de la información.
4. **Documentación:** Elaborar documentación técnica y operativa detallada para asegurar la transferencia de conocimiento a PROESA (instrucciones de ejecución, monitoreo y solución de errores).
5. **Persistencia y Memoria:** Documentar decisiones de diseño, estructuras y bugs en `memory.md`.

## 4. Uso Obligatorio de la Memoria (`memory.md`)
Cada vez que implementes una característica importante (como un nuevo scraper, cambios en PostgreSQL o integración con Resend), **DEBE escribirse en `memory.md`**.
*   **Regla de Oro:** "Si haces un cambio estructural que afecta a otros módulos, documenta las prácticas para el agente del futuro."

---

## 5. Arquitectura de Categorización (Lección Aprendida)
- **Evitar Duplicidad por Sub-categorías**: NUNCA instancies el scraper múltiples veces sobre sub-categorías (ej. "Cigarrillos") si la categoría padre (ej. "Vinos y Licores") ya renderiza esos productos. Extrae desde el catálogo padre.
- **Clasificación Dinámica de Tipo de Producto**: El campo `"Tipo de Producto"` debe inferirse dinámicamente según la sub-categoría individual de cada ítem, no puede estar quemado (hardcoded). 
  - Si la categoría contiene *cigarrillo*, *tabaco*, *puro* o *vapeador* -> `"Tabaco"`.
  - Por defecto -> `"Alcohol"`.
- **Nomenclatura Estandarizada**: Obligatorio que todos los scrapers nuevos implementen esta lógica de detección al procesar cada producto.

---
*Nota para el LLM: Actúa según estos principios cuando trabajes en este repositorio.*
