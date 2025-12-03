from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import engine, get_db
import models
import os

# Crear las tablas en la base de datos
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Crear carpeta para uploads si no existe
os.makedirs("static/uploads", exist_ok=True)

# Configurar archivos estáticos y templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Filtro personalizado para formatear precios en COP
def format_cop(value):
    return "{:,.0f}".format(value).replace(",", ".")


templates.env.filters["format_cop"] = format_cop


# ==================== API DASHBOARD ====================

@app.get("/api/dashboard/impacto-ambiental")
async def get_impacto_ambiental():
    """Datos de impacto ambiental del upcycling"""
    return {
        "labels": ["Agua Ahorrada", "CO2 Reducido", "Residuos Evitados", "Energía Ahorrada"],
        "values": [85, 70, 90, 65],
        "units": ["%", "%", "%", "%"]
    }


@app.get("/api/dashboard/prendas-por-categoria")
async def get_prendas_por_categoria(db: Session = Depends(get_db)):
    """Distribución de prendas por categoría"""
    categorias = db.query(models.Producto.categoria, models.Producto.id).all()

    # Contar productos por categoría
    conteo = {}
    for categoria, _ in categorias:
        conteo[categoria] = conteo.get(categoria, 0) + 1

    return {
        "labels": list(conteo.keys()) if conteo else ["Sin datos"],
        "values": list(conteo.values()) if conteo else [0]
    }


@app.get("/api/dashboard/consumo-mensual")
async def get_consumo_mensual():
    """Consumo sostenible mensual (simulado)"""
    return {
        "labels": ["Ene", "Feb", "Mar", "Abr", "May", "Jun"],
        "values": [12, 19, 15, 25, 22, 30]
    }


@app.get("/api/dashboard/metricas-generales")
async def get_metricas_generales(db: Session = Depends(get_db)):
    """Métricas generales de la tienda"""
    productos = db.query(models.Producto).all()
    total_productos = len(productos)
    prendas_unicas = sum(1 for p in productos if p.stock == 1)

    return {
        "total_prendas": total_productos,
        "piezas_unicas": prendas_unicas,
        "kg_co2_ahorrado": total_productos * 15,  # 15kg por prenda
        "litros_agua_ahorrados": total_productos * 2700  # 2700L por prenda
    }


# ==================== RUTAS PRINCIPALES ====================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    """Página principal con 4 productos destacados"""
    # 4 productos destacados (piezas únicas o más recientes)
    productos_destacados = db.query(models.Producto).filter(models.Producto.stock == 1).limit(4).all()

    # Si no hay suficientes piezas únicas, completar con los más recientes
    if len(productos_destacados) < 4:
        faltantes = 4 - len(productos_destacados)
        ids_existentes = [p.id for p in productos_destacados]
        adicionales = db.query(models.Producto).filter(~models.Producto.id.in_(ids_existentes)).order_by(
            models.Producto.id.desc()).limit(faltantes).all()
        productos_destacados.extend(adicionales)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "productos_destacados": productos_destacados
    })


@app.get("/categoria/{categoria}", response_class=HTMLResponse)
async def categoria(request: Request, categoria: str, db: Session = Depends(get_db)):
    """Página de categoría específica"""
    productos = db.query(models.Producto).filter(models.Producto.categoria == categoria).all()

    return templates.TemplateResponse("categoria.html", {
        "request": request,
        "productos": productos,
        "categoria": categoria
    })


@app.get("/buscar", response_class=HTMLResponse)
async def buscar(request: Request, q: str, db: Session = Depends(get_db)):
    """Búsqueda de productos"""
    productos = db.query(models.Producto).filter(
        models.Producto.nombre.contains(q) |
        models.Producto.categoria.contains(q)
    ).all()

    return templates.TemplateResponse("categoria.html", {
        "request": request,
        "productos": productos,
        "categoria": f"Resultados para '{q}'"
    })


@app.get("/producto/{producto_id}", response_class=HTMLResponse)
async def detalle_producto(request: Request, producto_id: int, db: Session = Depends(get_db)):
    """Página de detalle del producto"""
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


@app.get("/carrito", response_class=HTMLResponse)
async def carrito(request: Request):
    """Página del carrito"""
    return templates.TemplateResponse("carrito.html", {"request": request})


@app.get("/favoritos", response_class=HTMLResponse)
async def favoritos(request: Request):
    """Página de favoritos"""
    return templates.TemplateResponse("favoritos.html", {"request": request})


# ==================== ADMIN ====================

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


@app.get("/admin/editar/{producto_id}", response_class=HTMLResponse)
async def obtener_producto_editar(request: Request, producto_id: int, db: Session = Depends(get_db)):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    productos = db.query(models.Producto).all()
    total_productos = len(productos)
    total_stock = sum([p.stock for p in productos])
    valor_inventario = sum([p.precio * p.stock for p in productos])

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "productos": productos,
        "producto_editar": producto,
        "total_productos": total_productos,
        "total_stock": total_stock,
        "valor_inventario": valor_inventario
    })


@app.post("/admin/actualizar/{producto_id}")
async def actualizar_producto(
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


@app.get("/admin/eliminar/{producto_id}")
async def eliminar_producto(producto_id: int, db: Session = Depends(get_db)):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if producto:
        db.delete(producto)
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)


# Ejecutar el servidor
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)