# ThriftStoreCol ദ്ദി◝ ⩊ ◜.ᐟ⋆𐙚₊˚⊹♡

## Descripción
ThriftStoreCol es una plataforma de comercio electrónico de moda vintage y sostenible. Permite explorar productos por categoría, agregar al carrito, realizar un checkout simulado y gestionar productos desde un panel administrativo. Incluye dashboard con métricas de sostenibilidad.

## Tecnologías
- Backend: FastAPI, SQLAlchemy (Async)
- Base de datos: SQLite (local) o PostgreSQL (producción)
- Frontend: HTML, CSS, JS, Jinja2 Templates
- Gráficos: ApexCharts

## Estructura del proyecto

/app
│── main.py               # Archivo principal de FastAPI
│── database.py           # Configuración de la base de datos
│── models.py             # Modelos ORM
│── /templates            # Plantillas HTML
│── /static               # Archivos estáticos: CSS, JS, imágenes

## Instalación y Ejecución
1.	Clonar el repositorio:
  git clone <URL_DEL_REPOSITORIO>
cd <NOMBRE_REPOSITORIO>

2.	Crear entorno virtual e instalar dependencias:

python -m venv venv
venv\Scripts\activate      # Windows
# o
source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt

3.	Configurar la base de datos:

	•	SQLite: se crea automáticamente al iniciar la app.
	•	PostgreSQL: actualizar la URL de conexión en database.py.

4.	Ejecutar la aplicación:
python main.py

Abrir en el navegador: http://127.0.0.1:8000


Recursos Adicionales⋆˚꩜｡
	•	Copiar código: http://127.0.0.1:8000/https://tienda-ropa-upcycling-production-3f81.up.railway.app￼
	•	Imágenes e inspiración: Pinterest Closet Sale￼

Funcionalidades(˶˃ ᵕ ˂˶)
	•	Visualización de productos destacados y filtrado por categoría
	•	Carrito de compras y simulación de checkout
	•	Dashboard con métricas de sostenibilidad
	•	Gestión de productos y métricas para administradores
	•	Registro, inicio de sesión y control de usuarios


  

