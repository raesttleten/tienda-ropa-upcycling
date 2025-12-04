import os
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, Form, Response, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.hash import bcrypt

import models
from database import get_db, init_models

# -------------------- CONFIGURACIÓN DE LOGGING --------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# -------------------- LIFESPAN EVENTS --------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Iniciando aplicación...")
    try:
        # Crear directorios necesarios
        os.makedirs("static/uploads", exist_ok=True)
        os.makedirs("static/images", exist_ok=True)
        logger.info("✓ Directorios creados")

        # Inicializar base de datos
        await init_models()
        logger.info("✓ Base de datos inicializada correctamente")
    except Exception as e:
        logger.error(f"✗ Error al inicializar aplicación: {e}")
        raise

    yield

    # Shutdown
    logger.info("👋 Cerrando aplicación...")


# -------------------- CONFIGURACIÓN FASTAPI --------------------
app = FastAPI(lifespan=lifespan, title="EcoWear App")
templates = Jinja2Templates(directory="templates")

# Montar archivos estáticos
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("✓ Archivos estáticos montados")


# -------------------- FILTROS --------------------
def format_cop(value):
    try:
        return "{:,.0f}".format(float(value)).replace(",", ".")
    except (ValueError, TypeError):
        return "0"


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


# -------------------- HEALTH CHECK --------------------
@app.get("/health")
async def health_check():
    """Endpoint para verificar que la app está funcionando"""
    return {
        "status": "ok",
        "message": "Aplicación funcionando correctamente",
        "version": "1.0.0"
    }


@app.get("/api/test-db")
async def test_db(db: AsyncSession = Depends(get_db)):
    """Endpoint para probar conexión a base de datos"""
    try:
        result = await db.execute(select(models.Producto).limit(1))
        producto = result.scalars().first()

        # Contar productos
        result_count = await db.execute(select(models.Producto))
        productos_count = len(result_count.scalars().all())

        return {
            "status": "ok",
            "message": "Conexión a DB exitosa",
            "productos_en_db": productos_count
        }
    except Exception as e:
        logger.error(f"Error en test de DB: {e}")
        raise HTTPException(status_code=500, detail=f"Error de DB: {str(e)}")


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
    try:
        result = await db.execute(select(models.Producto.categoria))
        categorias = result.scalars().all()
        conteo = {}
        for categoria in categorias:
            conteo[categoria] = conteo.get(categoria, 0) + 1
        return {
            "labels": list(conteo.keys()) if conteo else ["Sin datos"],
            "values": list(conteo.values()) if conteo else [0]
        }
    except Exception as e:
        logger.error(f"Error en prendas por categoría: {e}")
        return {"labels": ["Sin datos"], "values": [0]}


@app.get("/api/dashboard/consumo-mensual")
async def get_consumo_mensual():
    return {
        "labels": ["Ene", "Feb", "Mar", "Abr", "May", "Jun"],
        "values": [12, 19, 15, 25, 22, 30]
    }


@app.get("/api/dashboard/metricas-generales")
async def get_metricas_generales(db: AsyncSession = Depends(get_db)):
    try:
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
    except Exception as e:
        logger.error(f"Error en métricas generales: {e}")
        return {
            "total_prendas": 0,
            "piezas_unicas": 0,
            "kg_co2_ahorrado": 0,
            "litros_agua_ahorrados": 0
        }


# -------------------- VISTAS HTML --------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(models.Producto).limit(4))
        productos_destacados = result.scalars().all()

        if len(productos_destacados) < 4:
            faltantes = 4 - len(productos_destacados)
            ids_existentes = [p.id for p in productos_destacados]
            if ids_existentes:
                result = await db.execute(
                    select(models.Producto).filter(~models.Producto.id.in_(ids_existentes)).order_by(
                        models.Producto.id.desc()).limit(faltantes)
                )
                productos_destacados.extend(result.scalars().all())

        return templates.TemplateResponse("index.html", {
            "request": request,
            "productos_destacados": productos_destacados
        })
    except Exception as e:
        logger.error(f"Error en home: {e}")
        return templates.TemplateResponse("index.html", {
            "request": request,
            "productos_destacados": []
        })


@app.get("/categoria/{categoria}", response_class=HTMLResponse)
async def categoria(request: Request, categoria: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(models.Producto).filter(models.Producto.categoria == categoria))
        productos = result.scalars().all()
        return templates.TemplateResponse("categoria.html", {
            "request": request,
            "productos": productos,
            "categoria": categoria
        })
    except Exception as e:
        logger.error(f"Error en categoría {categoria}: {e}")
        return templates.TemplateResponse("categoria.html", {
            "request": request,
            "productos": [],
            "categoria": categoria
        })


@app.get("/buscar", response_class=HTMLResponse)
async def buscar(request: Request, q: str, db: AsyncSession = Depends(get_db)):
    try:
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
    except Exception as e:
        logger.error(f"Error en búsqueda '{q}': {e}")
        return templates.TemplateResponse("categoria.html", {
            "request": request,
            "productos": [],
            "categoria": f"Resultados para '{q}'"
        })


@app.get("/producto/{producto_id}", response_class=HTMLResponse)
async def detalle_producto(request: Request, producto_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(models.Producto).filter(models.Producto.id == producto_id))
        producto = result.scalars().first()
        if not producto:
            logger.warning(f"Producto {producto_id} no encontrado")
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
    except Exception as e:
        logger.error(f"Error en detalle producto {producto_id}: {e}")
        return RedirectResponse(url="/", status_code=303)


# -------------------- ADMIN --------------------
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, db: AsyncSession = Depends(get_db),
                      admin: models.Usuario = Depends(admin_required)):
    try:
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
    except Exception as e:
        logger.error(f"Error en panel admin: {e}")
        raise HTTPException(status_code=500, detail="Error al cargar panel de administración")


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
    try:
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
        logger.info(f"✓ Producto '{nombre}' agregado exitosamente")
        return RedirectResponse(url="/admin", status_code=303)
    except Exception as e:
        logger.error(f"✗ Error al agregar producto: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al agregar producto")


# -------------------- AUTENTICACIÓN --------------------
@app.post("/registro")
async def registro(nombre: str = Form(...), email: str = Form(...), contraseña: str = Form(...),
                   db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(models.Usuario).filter(models.Usuario.correo == email))
        if result.scalars().first():
            logger.warning(f"Intento de registro con email duplicado: {email}")
            return JSONResponse({"error": "Email ya registrado"}, status_code=400)

        hashed = bcrypt.hash(contraseña)
        usuario = models.Usuario(nombre=nombre, correo=email, contrasena=hashed)
        db.add(usuario)
        await db.commit()
        logger.info(f"✓ Usuario '{nombre}' registrado exitosamente")
        return RedirectResponse(url="/login", status_code=303)
    except Exception as e:
        logger.error(f"✗ Error en registro: {e}")
        await db.rollback()
        return JSONResponse({"error": "Error al registrar usuario"}, status_code=500)


@app.post("/login")
async def login(response: Response, email: str = Form(...), contraseña: str = Form(...),
                db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(models.Usuario).filter(models.Usuario.correo == email))
        usuario = result.scalars().first()
        if not usuario or not bcrypt.verify(contraseña, usuario.contrasena):
            logger.warning(f"Intento de login fallido para: {email}")
            return JSONResponse({"error": "Usuario o contraseña incorrecta"}, status_code=401)

        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="usuario_id", value=str(usuario.id), httponly=True)
        logger.info(f"✓ Usuario '{usuario.nombre}' inició sesión")
        return response
    except Exception as e:
        logger.error(f"✗ Error en login: {e}")
        return JSONResponse({"error": "Error al iniciar sesión"}, status_code=500)


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("usuario_id")
    logger.info("Usuario cerró sesión")
    return response


# -------------------- CARRITO --------------------
@app.get("/api/carrito")
async def obtener_carrito(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        usuario_id = request.cookies.get("usuario_id")
        if not usuario_id:
            return {"total_items": 0, "items": []}

        result = await db.execute(select(models.Carrito).filter(models.Carrito.usuario_id == int(usuario_id)))
        carrito_items = result.scalars().all()
        total_items = sum(c.cantidad for c in carrito_items)
        items = [{"producto": c.producto.nombre, "cantidad": c.cantidad, "precio": c.producto.precio} for c in
                 carrito_items]
        return {"total_items": total_items, "items": items}
    except Exception as e:
        logger.error(f"Error al obtener carrito: {e}")
        return {"total_items": 0, "items": []}


@app.post("/api/carrito/agregar")
async def agregar_carrito(request: Request, producto_id: int = Form(...), cantidad: int = Form(1),
                          db: AsyncSession = Depends(get_db)):
    try:
        usuario_id = request.cookies.get("usuario_id")
        if not usuario_id:
            return JSONResponse({"error": "No autenticado"}, status_code=401)
        usuario_id = int(usuario_id)

        result = await db.execute(select(models.Carrito).filter_by(usuario_id=usuario_id, producto_id=producto_id))
        item = result.scalars().first()
        if item:
            item.cantidad += cantidad
            logger.info(f"Actualizado carrito: producto {producto_id}, nueva cantidad: {item.cantidad}")
        else:
            item = models.Carrito(usuario_id=usuario_id, producto_id=producto_id, cantidad=cantidad)
            db.add(item)
            logger.info(f"Agregado al carrito: producto {producto_id}")
        await db.commit()

        result = await db.execute(select(models.Carrito).filter(models.Carrito.usuario_id == usuario_id))
        total_items = sum(c.cantidad for c in result.scalars().all())
        return {"total_items": total_items}
    except Exception as e:
        logger.error(f"Error al agregar al carrito: {e}")
        await db.rollback()
        return JSONResponse({"error": "Error al agregar al carrito"}, status_code=500)


@app.get("/checkout", response_class=HTMLResponse)
async def checkout(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        usuario_id = request.cookies.get("usuario_id")
        if not usuario_id:
            logger.warning("Intento de checkout sin autenticación")
            return RedirectResponse(url="/login")
        usuario_id = int(usuario_id)

        result = await db.execute(select(models.Carrito).filter(models.Carrito.usuario_id == usuario_id))
        carrito_items = result.scalars().all()

        if not carrito_items:
            logger.warning(f"Usuario {usuario_id} intentó checkout con carrito vacío")
            return RedirectResponse(url="/", status_code=303)

        total = sum(c.cantidad * c.producto.precio for c in carrito_items)

        # Crear pedido
        pedido = models.Pedido(usuario_id=usuario_id, estado="confirmado", fecha=str(datetime.now()))
        db.add(pedido)

        # Limpiar carrito
        for c in carrito_items:
            await db.delete(c)
        await db.commit()

        logger.info(f"✓ Pedido confirmado para usuario {usuario_id}, total: ${total}")
        return templates.TemplateResponse("pedido_confirmacion.html", {"request": request, "total": total})
    except Exception as e:
        logger.error(f"✗ Error en checkout: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al procesar el pedido")


# -------------------- EJECUCIÓN --------------------
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🚀 Iniciando servidor en puerto {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)