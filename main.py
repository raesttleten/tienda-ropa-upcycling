from fastapi import FastAPI, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import engine, get_db
import models
import shutil
import os

# Crear las tablas en la base de datos
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Crear carpeta para uploads si no existe
os.makedirs("static/uploads", exist_ok=True)

# Configurar archivos estáticos y templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ==================== RUTAS ====================

# Página principal - Catálogo de productos
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db), busqueda: str = None):
    if busqueda:
        productos = db.query(models.Producto).filter(
            models.Producto.nombre.contains(busqueda) |
            models.Producto.categoria.contains(busqueda)
        ).all()
    else:
        productos = db.query(models.Producto).all()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "productos": productos,
        "busqueda": busqueda
    })


# Filtrar por categoría
@app.get("/categoria/{categoria}", response_class=HTMLResponse)
async def filtrar_categoria(request: Request, categoria: str, db: Session = Depends(get_db)):
    productos = db.query(models.Producto).filter(models.Producto.categoria == categoria).all()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "productos": productos,
        "categoria_actual": categoria
    })


# Dashboard administrativo
@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request, db: Session = Depends(get_db)):
    productos = db.query(models.Producto).all()
    total_productos = len(productos)
    total_stock = sum([p.stock for p in productos])
    valor_inventario = sum([p.precio * p.stock for p in productos])

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "productos": productos,
        "total_productos": total_productos,
        "total_stock": total_stock,
        "valor_inventario": valor_inventario
    })


# Agregar producto (POST)
@app.post("/admin/agregar")
async def agregar_producto(
        nombre: str = Form(...),
        descripcion: str = Form(...),
        precio: float = Form(...),
        talla: str = Form(...),
        categoria: str = Form(...),
        imagen_url: str = Form(...),
        stock: int = Form(...),
        db: Session = Depends(get_db)
):
    nuevo_producto = models.Producto(
        nombre=nombre,
        descripcion=descripcion,
        precio=precio,
        talla=talla,
        categoria=categoria,
        imagen_url=imagen_url,
        stock=stock
    )
    db.add(nuevo_producto)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


# Editar producto
@app.post("/admin/editar/{producto_id}")
async def editar_producto(
        producto_id: int,
        nombre: str = Form(...),
        descripcion: str = Form(...),
        precio: float = Form(...),
        talla: str = Form(...),
        categoria: str = Form(...),
        imagen_url: str = Form(...),
        stock: int = Form(...),
        db: Session = Depends(get_db)
):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if producto:
        producto.nombre = nombre
        producto.descripcion = descripcion
        producto.precio = precio
        producto.talla = talla
        producto.categoria = categoria
        producto.imagen_url = imagen_url
        producto.stock = stock
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)


# Eliminar producto
@app.get("/admin/eliminar/{producto_id}")
async def eliminar_producto(producto_id: int, db: Session = Depends(get_db)):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if producto:
        db.delete(producto)
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)


# Página de detalle del producto
@app.get("/producto/{producto_id}", response_class=HTMLResponse)
async def detalle_producto(request: Request, producto_id: int, db: Session = Depends(get_db)):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    productos_relacionados = db.query(models.Producto).filter(
        models.Producto.categoria == producto.categoria,
        models.Producto.id != producto_id
    ).limit(4).all()

    return templates.TemplateResponse("detalle.html", {
        "request": request,
        "producto": producto,
        "productos_relacionados": productos_relacionados
    })


# Página del carrito
@app.get("/carrito", response_class=HTMLResponse)
async def carrito(request: Request):
    return templates.TemplateResponse("carrito.html", {
        "request": request
    })


# Página de favoritos
@app.get("/favoritos", response_class=HTMLResponse)
async def favoritos(request: Request):
    return templates.TemplateResponse("favoritos.html", {
        "request": request
    })


# Ejecutar el servidor
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)