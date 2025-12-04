# ThriftStoreCol - Moda Vintage Sostenible

## Descripción
ThriftStoreCol es una aplicación web de e-commerce enfocada en moda vintage y sostenible, desarrollada con **FastAPI**, **SQLAlchemy** y **Jinja2**. La plataforma permite:

- Visualizar productos destacados y por categoría.
- Realizar búsquedas de productos.
- Gestionar un carrito de compras.
- Registrar y autenticar usuarios.
- Administrar productos desde un panel de administrador.
- Consultar métricas de sostenibilidad y consumo mediante un dashboard interactivo.

## Tecnologías
- **Backend:** Python 3.11, FastAPI, SQLAlchemy (async), Passlib para hashing de contraseñas.
- **Base de datos:** SQLite (local) o PostgreSQL (deploy en Railway/Heroku).
- **Frontend:** Jinja2 Templates, HTML5, CSS3, JavaScript, ApexCharts para gráficos.
- **Dependencias adicionales:** `bcrypt`, `uvicorn`, `psycopg2-binary` (para PostgreSQL en Windows).

## Instalación Local

1. **Clonar el repositorio**

git clone <URL_DEL_REPOSITORIO>
cd <NOMBRE_DEL_REPOSITORIO>
Crear entorno virtual

bash
Copiar código
python -m venv venv
Activar entorno virtual

Windows:

bash
Copiar código
venv\Scripts\activate
Linux / MacOS:

bash
Copiar código
source venv/bin/activate
Instalar dependencias

bash
Copiar código
pip install -r requirements.txt
Configurar base de datos

Para SQLite (local):

La app crea automáticamente database.db al inicializar.

Para PostgreSQL (deploy):

Instalar psycopg2-binary:

bash
Copiar código
pip install psycopg2-binary
Cambiar la URL de conexión en database.py:

python
Copiar código
DATABASE_URL = "postgresql+asyncpg://usuario:contraseña@host:puerto/nombre_db"
Inicializar modelos y base de datos

La app se encargará de crear las tablas al iniciar.

Solo asegúrate de que init_models() se ejecute antes de correr la app.

Ejecutar la aplicación

bash
Copiar código
uvicorn main:app --reload
Accede en tu navegador a http://127.0.0.1:8000/.

Uso
Inicio: Muestra productos destacados, galería y dashboard de métricas.

Categorías: Filtra productos por tipo (Camisas, Pantalones, Faldas, etc.).

Producto: Visualiza detalles de cada producto y productos relacionados.

Carrito: Agrega productos, consulta total y realiza checkout simulado.

Administración: Usuarios con rol de admin pueden agregar productos y ver métricas generales.

Autenticación: Registro, login y logout con manejo de cookies.




La aplicación requiere que el navegador soporte cookies para autenticación y carrito.

La base de datos local puede usarse para pruebas; para producción se recomienda PostgreSQL.

Licencia
Este proyecto está bajo licencia MIT.
