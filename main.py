from fastapi import FastAPI, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import engine, get_db
from datetime import datetime
import models
import os
import shutil

# Crear las tablas en la base de datos
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Crear carpetas si no existen
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/images", exist_ok=True)

# Configurar archivos estáticos y templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Filtro personalizado para formatear precios
def format_cop(value):
    return "{:,.0f}".format(value).replace(",", ".")


templates.env.filters["format_cop"] = format_cop


# ==================== API DASHBOARD ====================

@app.get("/api/dashboard/impacto-ambiental")
async def get_impacto_ambiental():
    return {
        "labels": ["Agua Ahorrada", "CO2 Reducido", "Residuos Evitados", "Energía Ahorrada"],
        "values": [85, 70, 90, 65],
        "units": ["%", "%", "%", "%"]
    }


@app.get("/api/dashboard/prendas-por-categoria")
async def get_prendas_por_categoria(db: Session = Depends(get_db)):
    categorias = db.query(models.Producto.categoria, models.Producto.id).all()
    conteo = {}
    for categoria, _ in categorias:
        conteo[categoria] = conteo.get(categoria, 0) + 1

    return {
        "labels": list(conteo.keys()) if conteo else ["Sin datos"],
        "values": list(conteo.values()) if conteo else [0]
    }


@app.get("/api/dashboard/consumo-mensual")
async def get_consumo_mensual():
    return {
        "labels": ["Ene", "Feb", "Mar", "Abr", "May", "Jun"],
        "values": [12, 19, 15, 25, 22, 30]
    }


@app.get("/api/dashboard/metricas-generales")
async def get_metricas_generales(db: Session = Depends(get_db)):
    productos = db.query(models.Producto).all()
    total_productos = len(productos)
    prendas_unicas = sum(1 for p in productos if p.stock == 1)

    return {
        "total_prendas": total_productos,
        "piezas_unicas": prendas_unicas,
        "kg_co2_ahorrado": total_productos * 15,
        "litros_agua_ahorrados": total_productos * 2700
    }


# ==================== RUTAS DE VISTAS (HTML) ====================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    """Página principal"""
    productos_destacados = db.query(models.Producto).filter(models.Producto.stock == 1).limit(4).all()

    if len(productos_destacados) < 4:
        faltantes = 4 - len(productos_destacados)
        ids_existentes = [p.id for p in productos_destacados]
        adicionales = db.query(models.Producto).filter(
            ~models.Producto.id.in_(ids_existentes)
        ).order_by(models.Producto.id.desc()).limit(faltantes).all()
        productos_destacados.extend(adicionales)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "productos_destacados": productos_destacados
    })


@app.get("/categoria/{categoria}", response_class=HTMLResponse)
async def categoria(request: Request, categoria: str, db: Session = Depends(get_db)):
    """Página de categoría"""
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
        models.Producto.descripcion.contains(q) |
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

    if not producto:
        return RedirectResponse(url="/", status_code=303)

    productos_relacionados = db.query(models.Producto).filter(
        models.Producto.categoria == producto.categoria,
        models.Producto.id != producto_id
    ).limit(4).all()

    return templates.TemplateResponse("detalle.html", {
        "request": request,
        "producto": producto,
        "productos_relacionados": productos_relacionados
    })


# ==================== ADMIN (SIN LOGIN) ====================

@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request, db: Session = Depends(get_db)):
    """Panel de administrador"""
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
    """Agregar producto"""
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
    """Actualizar producto"""
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
    """Eliminar producto"""
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if producto:
        db.delete(producto)
        db.commit()

    return RedirectResponse(url="/admin", status_code=303)


# Ejecutar servidor
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

# ==================== AUTENTICACIÓN ====================

from fastapi import Response
from passlib.hash import bcrypt

@app.post("/registro")
def registro(nombre: str = Form(...), email: str = Form(...), contraseña: str = Form(...), db: Session = Depends(get_db)):
    hashed = bcrypt.hash(contraseña)
    usuario = models.Usuario(nombre=nombre, email=email, contraseña=hashed)
    db.add(usuario)
    db.commit()
    return RedirectResponse(url="/login", status_code=303)

@app.post("/login")
def login(response: Response, email: str = Form(...), contraseña: str = Form(...), db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if not usuario or not bcrypt.verify(contraseña, usuario.contraseña):
        return Response({"error": "Usuario o contraseña incorrecta"}, status_code=401)
    response.set_cookie(key="usuario_id", value=str(usuario.id))
    return RedirectResponse(url="/", status_code=303)

@app.get("/logout")
def logout(response: Response):
    response.delete_cookie("usuario_id")
    return RedirectResponse(url="/", status_code=303)

@app.get("/api/auth/usuario-actual")
def usuario_actual(request: Request, db: Session = Depends(get_db)):
    usuario_id = request.cookies.get("usuario_id")
    if not usuario_id:
        return {"autenticado": False}
    usuario = db.query(models.Usuario).filter(models.Usuario.id == int(usuario_id)).first()
    if not usuario:
        return {"autenticado": False}
    return {"autenticado": True, "nombre": usuario.nombre, "es_admin": usuario.es_admin}

from fastapi.responses import JSONResponse, RedirectResponse
from fastapi import Response, Form
from passlib.hash import bcrypt
from datetime import datetime

# ===== Registro =====
@app.post("/registro")
def registro(nombre: str = Form(...), email: str = Form(...), contraseña: str = Form(...), db: Session = Depends(get_db)):
    if db.query(models.Usuario).filter(models.Usuario.email == email).first():
        return JSONResponse({"error": "Email ya registrado"}, status_code=400)
    hashed = bcrypt.hash(contraseña)
    usuario = models.Usuario(nombre=nombre, email=email, contraseña=hashed)
    db.add(usuario)
    db.commit()
    return RedirectResponse(url="/login", status_code=303)

# ===== Login =====
@app.post("/login")
def login(response: Response, email: str = Form(...), contraseña: str = Form(...), db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if not usuario or not bcrypt.verify(contraseña, usuario.contraseña):
        return JSONResponse({"error": "Usuario o contraseña incorrecta"}, status_code=401)
    response.set_cookie(key="usuario_id", value=str(usuario.id))
    return RedirectResponse(url="/", status_code=303)

# ===== Logout =====
@app.get("/logout")
def logout(response: Response):
    response.delete_cookie("usuario_id")
    return RedirectResponse(url="/", status_code=303)

# ===== Usuario Actual =====
@app.get("/api/auth/usuario-actual")
def usuario_actual(request: Request, db: Session = Depends(get_db)):
    usuario_id = request.cookies.get("usuario_id")
    if not usuario_id:
        return {"autenticado": False}
    usuario = db.query(models.Usuario).filter(models.Usuario.id == int(usuario_id)).first()
    if not usuario:
        return {"autenticado": False}
    return {"autenticado": True, "nombre": usuario.nombre, "es_admin": usuario.es_admin}

# ===== Ver carrito =====
@app.get("/api/carrito")
def obtener_carrito(request: Request, db: Session = Depends(get_db)):
    usuario_id = request.cookies.get("usuario_id")
    if not usuario_id:
        return {"total_items": 0, "items": []}

    carrito_items = db.query(models.Carrito).filter(models.Carrito.usuario_id == int(usuario_id)).all()
    total_items = sum([c.cantidad for c in carrito_items])
    items = [{"producto": c.producto.nombre, "cantidad": c.cantidad, "precio": c.producto.precio} for c in carrito_items]
    return {"total_items": total_items, "items": items}

# ===== Agregar al carrito =====
@app.post("/api/carrito/agregar")
def agregar_carrito(request: Request, producto_id: int = Form(...), cantidad: int = Form(1), db: Session = Depends(get_db)):
    usuario_id = request.cookies.get("usuario_id")
    if not usuario_id:
        return JSONResponse({"error": "No autenticado"}, status_code=401)
    usuario_id = int(usuario_id)

    item = db.query(models.Carrito).filter_by(usuario_id=usuario_id, producto_id=producto_id).first()
    if item:
        item.cantidad += cantidad
    else:
        item = models.Carrito(usuario_id=usuario_id, producto_id=producto_id, cantidad=cantidad)
        db.add(item)
    db.commit()

    total_items = sum([c.cantidad for c in db.query(models.Carrito).filter(models.Carrito.usuario_id == usuario_id).all()])
    return {"total_items": total_items}

@app.get("/checkout", response_class=HTMLResponse)
def checkout(request: Request, db: Session = Depends(get_db)):
    usuario_id = request.cookies.get("usuario_id")
    if not usuario_id:
        return RedirectResponse(url="/login")
    usuario_id = int(usuario_id)

    carrito_items = db.query(models.Carrito).filter(models.Carrito.usuario_id == usuario_id).all()
    total = sum([c.cantidad * c.producto.precio for c in carrito_items])

    # Crear pedido simulado
    pedido = models.Pedido(usuario_id=usuario_id, estado="confirmado", fecha=str(datetime.now()))
    db.add(pedido)
    db.commit()

    # Limpiar carrito
    for c in carrito_items:
        db.delete(c)
    db.commit()

    return templates.TemplateResponse("pedido_confirmacion.html", {"request": request, "total": total})


from fastapi import HTTPException


def admin_required(request: Request, db: Session = Depends(get_db)):
    usuario_id = request.cookies.get("usuario_id")
    if not usuario_id:
        raise HTTPException(status_code=401, detail="No autenticado")

    usuario = db.query(models.Usuario).filter(models.Usuario.id == int(usuario_id)).first()
    if not usuario or not usuario.es_admin:
        raise HTTPException(status_code=403, detail="No autorizado")

    return usuario

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, db: Session = Depends(get_db), admin: models.Usuario = Depends(admin_required)):
    """Panel de administrador"""
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


@app.get("/admin/editar/{producto_id}", response_class=HTMLResponse)
async def obtener_producto_editar(request: Request, producto_id: int, db: Session = Depends(get_db), admin: models.Usuario = Depends(admin_required)):
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


@app.post("/admin/agregar")
async def agregar_producto(
        nombre: str = Form(...),
        descripcion: str = Form(...),
        precio: float = Form(...),
        talla: str = Form(...),
        categoria: str = Form(...),
        imagen_url: str = Form(...),
        stock: int = Form(...),
        db: Session = Depends(get_db),
        admin: models.Usuario = Depends(admin_required)
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
        db: Session = Depends(get_db),
        admin: models.Usuario = Depends(admin_required)
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
async def eliminar_producto(producto_id: int, db: Session = Depends(get_db), admin: models.Usuario = Depends(admin_required)):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if producto:
        db.delete(producto)
        db.commit()

    return RedirectResponse(url="/admin", status_code=303)

from database import engine
import models

# Esto crea todas las tablas que no existan aún
models.Base.metadata.create_all(bind=engine)

