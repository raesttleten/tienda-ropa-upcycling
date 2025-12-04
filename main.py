from fastapi import FastAPI, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import engine, get_db
from datetime import datetime
import models
import os
import shutil

# --- para auth ---
from passlib.context import CryptContext
from starlette.middleware.sessions import SessionMiddleware

# Crear las tablas en la base de datos
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Middleware de sesiones (cambiar SECRET por algo seguro en prod / Railway env var)
app.add_middleware(SessionMiddleware, secret_key="CAMBIA_POR_UNA_SECRETA")

# Crear carpetas si no existen
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/images", exist_ok=True)

# Configurar archivos estáticos y templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Contexto para hashear contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ================= utilidades =================
def format_cop(value):
    return "{:,.0f}".format(value).replace(",", ".")

templates.env.filters["format_cop"] = format_cop

def get_current_user(request: Request, db: Session = Depends(get_db)):
    session = request.session
    if not session or "user_id" not in session:
        return None
    user = db.query(models.User).filter(models.User.id == session["user_id"]).first()
    return user

# Crear admin por defecto si no existe (cambiar email/clave si quieres)
def ensure_default_admin(db: Session):
    admin_email = "admin@example.com"
    admin_password = "admin123"  # cámbiala en producción
    admin = db.query(models.User).filter(models.User.email == admin_email).first()
    if not admin:
        hashed = pwd_context.hash(admin_password)
        new_admin = models.User(email=admin_email, password=hashed, role="admin")
        db.add(new_admin)
        db.commit()

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

    user = get_current_user(request, db)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "productos_destacados": productos_destacados,
        "user": user
    })

@app.get("/categoria/{categoria}", response_class=HTMLResponse)
async def categoria(request: Request, categoria: str, db: Session = Depends(get_db)):
    """Página de categoría"""
    productos = db.query(models.Producto).filter(models.Producto.categoria == categoria).all()
    user = get_current_user(request, db)

    return templates.TemplateResponse("categoria.html", {
        "request": request,
        "productos": productos,
        "categoria": categoria,
        "user": user
    })

@app.get("/buscar", response_class=HTMLResponse)
async def buscar(request: Request, q: str, db: Session = Depends(get_db)):
    """Búsqueda de productos"""
    productos = db.query(models.Producto).filter(
        models.Producto.nombre.contains(q) |
        models.Producto.descripcion.contains(q) |
        models.Producto.categoria.contains(q)
    ).all()
    user = get_current_user(request, db)

    return templates.TemplateResponse("categoria.html", {
        "request": request,
        "productos": productos,
        "categoria": f"Resultados para '{q}'",
        "user": user
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

    user = get_current_user(request, db)
    return templates.TemplateResponse("detalle.html", {
        "request": request,
        "producto": producto,
        "productos_relacionados": productos_relacionados,
        "user": user
    })

# ==================== AUTH: Registro / Login / Logout ====================

@app.get("/registro", response_class=HTMLResponse)
async def registro_get(request: Request):
    return templates.TemplateResponse("registro.html", {"request": request})

@app.post("/registro")
async def registro_post(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    # validar existencia
    existe = db.query(models.User).filter(models.User.email == email).first()
    if existe:
        return templates.TemplateResponse("registro.html", {"request": request, "error": "El usuario ya existe"})
    hashed = pwd_context.hash(password)
    nuevo = models.User(email=email, password=hashed, role="user")
    db.add(nuevo)
    db.commit()
    # auto-login tras registro
    request.session["user_id"] = nuevo.id
    request.session["role"] = nuevo.role
    return RedirectResponse(url="/", status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login_post(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not pwd_context.verify(password, user.password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Credenciales inválidas"})
    # guardar sesión
    request.session["user_id"] = user.id
    request.session["role"] = user.role
    # redirigir según rol
    if user.role == "admin":
        return RedirectResponse(url="/admin", status_code=303)
    return RedirectResponse(url="/", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

# ==================== ADMIN (PROTEGIDO) ====================

@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request, db: Session = Depends(get_db)):
    """Panel de administrador (protegido)"""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="No tienes permisos para ver esta página")

    productos = db.query(models.Producto).all()
    total_productos = len(productos)
    total_stock = sum([p.stock for p in productos])
    valor_inventario = sum([p.precio * p.stock for p in productos])

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "productos": productos,
        "total_productos": total_productos,
        "total_stock": total_stock,
        "valor_inventario": valor_inventario,
        "user": user
    })

@app.get("/admin/editar/{producto_id}", response_class=HTMLResponse)
async def obtener_producto_editar(request: Request, producto_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role != "admin":
        return RedirectResponse(url="/login", status_code=303)

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
        "valor_inventario": valor_inventario,
        "user": user
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
        request: Request = None
):
    user = get_current_user(request, db)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

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
        request: Request = None
):
    user = get_current_user(request, db)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

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
async def eliminar_producto(producto_id: int, db: Session = Depends(get_db), request: Request = None):
    user = get_current_user(request, db)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if producto:
        db.delete(producto)
        db.commit()

    return RedirectResponse(url="/admin", status_code=303)

# ==================== RUTAS DE CUENTA ====================

@app.get("/mi-cuenta", response_class=HTMLResponse)
async def account(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("mi-cuenta.html", {"request": request, "user": user})

# Ejecutar servidor (útil para pruebas locales)
if __name__ == "__main__":
    import uvicorn
    # crear admin por defecto si no existe
    db = next(get_db())
    ensure_default_admin(db)
    uvicorn.run(app, host="0.0.0.0", port=8000)
