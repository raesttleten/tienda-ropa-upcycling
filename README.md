# ThriftStoreCol

## Descripción
ThriftStoreCol es una plataforma de comercio electrónico de moda vintage y sostenible. Permite explorar productos por categoría, agregar al carrito, realizar un checkout simulado y gestionar productos desde un panel administrativo. Incluye dashboard con métricas de sostenibilidad.

## Tecnologías
- Backend: FastAPI, SQLAlchemy (Async)
- Base de datos: SQLite (local) o PostgreSQL (producción)
- Frontend: HTML, CSS, JS, Jinja2 Templates
- Gráficos: ApexCharts

## Instalación y ejecución
1. Clonar el repositorio:
bash
git clone <URL_DEL_REPOSITORIO>
cd <NOMBRE_DEL_PROYECTO>
Crear y activar entorno virtual:

bash
Copiar código
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
Instalar dependencias:

bash
Copiar código
pip install -r requirements.txt
Configurar base de datos:

SQLite: se crea automáticamente.

PostgreSQL: modificar DATABASE_URL en database.py.

Iniciar la aplicación:

bash
Copiar código
uvicorn main:app --reload
Abrir en navegador:

cpp
Copiar código
http://127.0.0.1:8000/
https://tienda-ropa-upcycling-production-3f81.up.railway.app

Imagenes:
https://co.pinterest.com/raesttleten/closetsale/
