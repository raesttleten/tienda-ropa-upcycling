import asyncio
import os
from datetime import datetime
from fastapi import FastAPI, Request, Depends, Form, Response, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.hash import bcrypt

import models
from database import get_db, init_models

# -------------------- INICIALIZAR BASE DE DATOS --------------------
asyncio.run(init_models())

# -------------------- CONFIGURACIÓN FASTAPI --------------------
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/images", exist_ok=True)

# -------------------- FILTROS --------------------
def format_cop(value):
    return "{:,.0f}".format(value).replace(",", ".")

templates.env.filters["format_cop"] = format_cop

# -------------------- DEPENDENCIAS --------------------
async def admin_required(request: Request, db: AsyncSession = Depends(get_db)):
    usuario_id = request.cookies.get("usuario_id")
    if not usuario_id:
        raise HTTPException(status_code=401, detail="No autenticado")
    result = await db.execute(select(models.Usuario).filter(models.Usuario.id == int(usuario_id)))
    usuario = result.scalars().first()
    if not usuario or not usuario.es_admin:
        raise HTTPException(status_code=403, detail="No autorizado")
    return usuario

# -------------------- DASHBOARD --------------------
@app.get("/api/dashboard/impacto-ambiental")
async def get_impacto_ambiental():
    return {
        "labels": ["Agua Ahorrada", "CO2 Reducido", "Residuos Evitados", "Energía Ahorrada"],
        "values": [85, 70, 90, 65],
        "units": ["%", "%", "%", "%"]
    }

@app.get("/api/dashboard/prendas-por-categoria")
async def get_prendas_por_categoria(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Producto.categoria))
    categorias = result.scalars().all()
    conteo = {}
    for categoria in categorias:
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
async def get_metricas_generales(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Producto))
    productos = result.scalars().all()
    total_productos = len(productos)
    prendas_unicas = sum(1 for p in productos if p.stock == 1)
    return {
        "total_prendas": total_productos,
        "piezas_unicas": prendas_unicas,
        "kg_co2_ahorrado": total_productos * 15,
        "litros_agua_ahorrados": total_productos * 2700
    }

# -------------------- VISTAS HTML --------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Producto).limit(4))
    productos_destacados = result.scalars().all()

    if len(productos_destacados) < 4:
        faltantes = 4 - len(productos_destacados)
        ids_existentes = [p.id for p in productos_destacados]
        result = await db.execute(
            select(models.Producto).filter(~models.Producto.id.in_(ids_existentes)).order_by(models.Producto.id.desc()).limit(faltantes)
        )
        productos_destacados.extend(result.scalars().all())

    return templates.TemplateResponse("index.html", {
        "request": request,
        "productos_destacados": productos_destacados
    })

@app.get("/categoria/{categoria}", response_class=HTMLResponse)
async def categoria(request: Request, categoria: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Producto).filter(models.Producto.categoria == categoria))
    productos = result.scalars().all()
    return templates.TemplateResponse("categoria.html", {
        "request": request,
        "productos": productos,
        "categoria": categoria
    })

@app.get("/buscar", response_class=HTMLResponse)
async def buscar(request: Request, q: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Producto).filter(
            models.Producto.nombre.contains(q) |
            models.Producto.descripcion.contains(q) |
            models.Producto.categoria.contains(q)
        )
    )
    productos = result.scalars().all()
    return templates.TemplateResponse("categoria.html", {
        "request": request,
        "productos": productos,
        "categoria": f"Resultados para '{q}'"
    })

@app.get("/producto/{producto_id}", response_class=HTMLResponse)
async def detalle_producto(request: Request, producto_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Producto).filter(models.Producto.id == producto_id))
    producto = result.scalars().first()
    if not producto:
        return RedirectResponse(url="/", status_code=303)

    result = await db.execute(select(models.Producto).filter(
        models.Producto.categoria == producto.categoria,
        models.Producto.id != producto_id
    ).limit(4))
    productos_relacionados = result.scalars().all()

    return templates.TemplateResponse("detalle.html", {
        "request": request,
        "producto": producto,
        "productos_relacionados": productos_relacionados
    })

# -------------------- ADMIN --------------------
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, db: AsyncSession = Depends(get_db), admin: models.Usuario = Depends(admin_required)):
    result = await db.execute(select(models.Producto))
    productos = result.scalars().all()
    total_productos = len(productos)
    total_stock = sum(p.stock for p in productos)
    valor_inventario = sum(p.precio * p.stock for p in productos)
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
    db: AsyncSession = Depends(get_db),
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
    await db.commit()
    return RedirectResponse(url="/admin", status_code=303)

# -------------------- AUTENTICACIÓN --------------------
@app.post("/registro")
async def registro(nombre: str = Form(...), email: str = Form(...), contraseña: str = Form(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Usuario).filter(models.Usuario.correo == email))
    if result.scalars().first():
        return JSONResponse({"error": "Email ya registrado"}, status_code=400)
    hashed = bcrypt.hash(contraseña)
    usuario = models.Usuario(nombre=nombre, correo=email, contrasena=hashed)
    db.add(usuario)
    await db.commit()
    return RedirectResponse(url="/login", status_code=303)

@app.post("/login")
async def login(response: Response, email: str = Form(...), contraseña: str = Form(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Usuario).filter(models.Usuario.correo == email))
    usuario = result.scalars().first()
    if not usuario or not bcrypt.verify(contraseña, usuario.contrasena):
        return JSONResponse({"error": "Usuario o contraseña incorrecta"}, status_code=401)
    response.set_cookie(key="usuario_id", value=str(usuario.id))
    return RedirectResponse(url="/", status_code=303)

@app.get("/logout")
async def logout(response: Response):
    response.delete_cookie("usuario_id")
    return RedirectResponse(url="/", status_code=303)

# -------------------- CARRITO --------------------
@app.get("/api/carrito")
async def obtener_carrito(request: Request, db: AsyncSession = Depends(get_db)):
    usuario_id = request.cookies.get("usuario_id")
    if not usuario_id:
        return {"total_items": 0, "items": []}
    result = await db.execute(select(models.Carrito).filter(models.Carrito.usuario_id == int(usuario_id)))
    carrito_items = result.scalars().all()
    total_items = sum(c.cantidad for c in carrito_items)
    items = [{"producto": c.producto.nombre, "cantidad": c.cantidad, "precio": c.producto.precio} for c in carrito_items]
    return {"total_items": total_items, "items": items}

@app.post("/api/carrito/agregar")
async def agregar_carrito(request: Request, producto_id: int = Form(...), cantidad: int = Form(1), db: AsyncSession = Depends(get_db)):
    usuario_id = request.cookies.get("usuario_id")
    if not usuario_id:
        return JSONResponse({"error": "No autenticado"}, status_code=401)
    usuario_id = int(usuario_id)

    result = await db.execute(select(models.Carrito).filter_by(usuario_id=usuario_id, producto_id=producto_id))
    item = result.scalars().first()
    if item:
        item.cantidad += cantidad
    else:
        item = models.Carrito(usuario_id=usuario_id, producto_id=producto_id, cantidad=cantidad)
        db.add(item)
    await db.commit()

    result = await db.execute(select(models.Carrito).filter(models.Carrito.usuario_id == usuario_id))
    total_items = sum(c.cantidad for c in result.scalars().all())
    return {"total_items": total_items}

@app.get("/checkout", response_class=HTMLResponse)
async def checkout(request: Request, db: AsyncSession = Depends(get_db)):
    usuario_id = request.cookies.get("usuario_id")
    if not usuario_id:
        return RedirectResponse(url="/login")
    usuario_id = int(usuario_id)

    result = await db.execute(select(models.Carrito).filter(models.Carrito.usuario_id == usuario_id))
    carrito_items = result.scalars().all()
    total = sum(c.cantidad * c.producto.precio for c in carrito_items)

    # Crear pedido simulado
    pedido = models.Pedido(usuario_id=usuario_id, estado="confirmado", fecha=str(datetime.now()))
    db.add(pedido)

    # Limpiar carrito
    for c in carrito_items:
        await db.delete(c)
    await db.commit()

    return templates.TemplateResponse("pedido_confirmacion.html", {"request": request, "total": total})
