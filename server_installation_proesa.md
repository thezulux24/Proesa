# Guía de Instalación y Despliegue en Servidor (PROESA)
**Suite Data Universal - Inteligencia de Mercado (Alcohol, Tabaco y Ultraprocesados)**

Este documento detalla los pasos para instalar, configurar y automatizar la extracción de datos en el servidor de producción.

## 1. Requisitos del Sistema
- **Sistema Operativo:** Windows Server 2016 (con Interfaz Gráfica).
- **Hardware Recomendado:** 100GB RAM, 16 Núcleos AMD Epyc (Cumplido).
- **Red Local:** El servidor operará de forma aislada. La base de datos es local (SQLite) y **no** requiere abrir ningún puerto hacia el exterior.

## 2. Instalación de Dependencias Base

### 2.1. Python
1. Descargar **Python 3.10+** para Windows (ejecutable de 64-bit).
2. Durante la instalación, asegurarse de marcar la casilla **"Add Python to PATH"**.
3. Verificar instalación en CMD o PowerShell:
   ```powershell
   python --version
   pip --version
   ```


## 3. Configuración del Proyecto

### 3.1. Clonar/Copiar el Repositorio
Ubicarse en `C:\projects\WB\Proesa\` (o donde se haya depositado el proyecto).

### 3.2. Instalar Librerías Python
Abrir PowerShell en la raíz del proyecto y ejecutar:
```powershell
pip install -r requirements.txt
```
*(Si no existe un `requirements.txt`, instalar las principales manualmente):*
```powershell
pip install requests beautifulsoup4 pandas python-dotenv resend scrapling customtkinter matplotlib seaborn
```

### 3.3. Configuración de Variables de Entorno (`.env`)
Crear un archivo `.env` en la raíz del proyecto (`C:\projects\WB\Proesa\.env`) con las credenciales necesarias (únicamente para envíos de correo):

```env
# Configuración de Resend (Alertas Diarias)
RESEND_API_KEY=tu_api_key_aqui
NOTIFY_EMAIL=tu_correo@proesa.org.co
```

## 4. Inicialización de la Base de Datos (SQLite)

Gracias al uso de **SQLite**, no es necesario instalar motores pesados. El sistema creará automáticamente el archivo `suite_data.db` y sus tablas en la primera ejecución.

1. Ejecutar el orquestador principal de manera manual por primera vez:
   ```powershell
   python main.py
   ```
2. La terminal mostrará: `Database tables initialized successfully.` y procederá a correr los scrapers (Éxito, Carulla, Jumbo, D1, Cañaveral, Olímpica, Makro).
3. En la raíz del proyecto verás que se ha creado el archivo `suite_data.db`. Todos los datos residirán de forma segura y portable en este archivo.

## 5. Automatización (Ejecución Diaria) / Automation (Daily Execution)

Para asegurar que la extracción corra todos los días sin intervención humana, usaremos **Windows Task Scheduler (Programador de Tareas)**.
*To ensure the extraction runs every day without human intervention, we will use **Windows Task Scheduler**.*

1. Abrir **Task Scheduler** en Windows Server 2016.
   *Open **Task Scheduler** on Windows Server 2016.*
2. En el panel derecho, hacer clic en **"Create Task..."** (Crear Tarea). **No** usar "Create Basic Task...".
   *In the right pane, click on **"Create Task..."**. **Do not** use "Create Basic Task...".*
3. **Pestaña General (General Tab):**
   - **Name (Nombre):** `Proesa Data Suite Automator`
   - **IMPORTANTE:** Marcar **"Run whether user is logged on or not"** (Ejecutar sin importar si el usuario inició sesión o no). Esto garantiza que corra aunque el servidor se reinicie y nadie inicie sesión.
     * **IMPORTANT:** Check **"Run whether user is logged on or not"**. This ensures it runs even if the server reboots and no one logs in.*
   - Marcar **"Run with highest privileges"** (Ejecutar con los privilegios más altos).
     * Check **"Run with highest privileges"**.*
4. **Pestaña Triggers (Desencadenadores):**
   - Hacer clic en **"New..."** (Nuevo...).
   - Seleccionar **"Daily"** (Diariamente) y configurar la hora a un horario de bajo tráfico, por ejemplo, **02:00 AM**.
     * Select **"Daily"** and set the time to a low-traffic hour, e.g., **02:00 AM**.*
   - Asegurarse de que la casilla **"Enabled"** (Habilitado) esté marcada y presionar OK.
     * Ensure the **"Enabled"** checkbox is checked and press OK.*
5. **Pestaña Actions (Acciones):**
   - Hacer clic en **"New..."** (Nuevo...).
   - **Action (Acción):** Seleccionar **"Start a program"** (Iniciar un programa).
   - **Program/script:** `C:\projects\WB\Proesa\run_scraper.bat` (Este archivo .bat primero hace un `git pull` para descargar los últimos cambios de GitHub y luego ejecuta el código).
     * **Program/script:** `C:\projects\WB\Proesa\run_scraper.bat` (This .bat file first does a `git pull` to download the latest changes from GitHub and then runs the code).*
   - **Start in (Empezar en):** `C:\projects\WB\Proesa\` (Opcional pero recomendado).
     * **Start in:** `C:\projects\WB\Proesa\` (Optional but recommended).*
6. **Guardar y probar (Save and test):** 
   - Hacer clic en **OK**.
   - Se solicitará la contraseña de administrador (Administrator password) para autorizar que la tarea corra sin inicio de sesión. Ingresarla.
     * You will be prompted for the administrator password to authorize the task to run without a logged-in user. Enter it.*
   - Para probar, hacer clic derecho sobre la tarea en la lista y seleccionar **"Run"** (Ejecutar).
     * To test, right-click the task in the list and select **"Run"**.*

---

### Solución de Problemas Frecuentes
- **Scraper devuelve 0 productos o falla con Timeout:** Las páginas web suelen tener latencia. El sistema tiene reintentos, pero si falla consistentemente, revisar si la URL principal ha cambiado en la tienda (ej. un rediseño de Makro o D1).
- **Memoria Llena:** Monitorear el uso de RAM. Al usar Scrapling/Requests de manera "HTTP Only", la memoria utilizada no debería exceder un par de gigabytes incluso al correr los 7 scrapers, garantizando estabilidad total en el Windows Server de 100GB.
- **Bloqueo en la Base de Datos:** Como la extracción se ejecuta de forma secuencial una vez al día, la base de datos SQLite no presentará bloqueos. Sin embargo, si tratas de ejecutar dos extracciones simultáneas o tienes la base abierta en modo escritura en otro software al mismo tiempo, podrías recibir un error de tipo `database is locked`. En ese caso, basta con asegurarse de que la automatización sea la única modificando el archivo `.db`.
