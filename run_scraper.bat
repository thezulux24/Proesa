@echo off
cd /d "D:\webscraping\Proesa"

echo [1/3] Obteniendo ultimos cambios de GitHub...
git pull

echo [2/3] Verificando e instalando dependencias de Python...
pip install --disable-pip-version-check -r requirements.txt

echo [3/3] Iniciando Suite Data Universal - Tarea Programada Diaria
python main.py

echo Tarea finalizada.