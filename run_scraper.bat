@echo off
cd /d C:\projects\WB\Proesa
echo Obteniendo ultimos cambios de GitHub...
git pull
echo Iniciando Suite Data Universal - Tarea Programada Diaria
python main.py
echo Tarea finalizada.
