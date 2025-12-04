from fastapi import FastAPI, Request, Depends, Form, HTTPException, UploadFile, File, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import engine, get_db
from datetime import datetime
import models
import auth
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


# ==================== MIDDLEWARE PARA INYECTAR USUARIO EN TEMPLATES ====================
@app.middleware("http")
async def agregar_usuario_a_request(request: Request, call_next):
    """Middleware para inyectar usuario en todos los templates"""
    response = await call_next(request)
    return response


# ==================== API DE AUTENTICACIÓN ====================

@app.post("/api/auth/registro")
async def api_registro(
        nombre: str = Form(...),
        email: str = Form(...),
        password: str = Form(...),
        telefono: str = Form(None),
        db: Session = Depends(get_db)
):
    """Registro de nuevo usuario"""
    # Validar contraseña
    es_valida, mensaje = auth.validar_password(password)
    if not es_valida:
        raise HTTPException(status_code=400, detail=mensaje)

    # Verificar si el email ya existe
    usuario_existente = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    # Crear usuario
    password_hash = auth.hash_password(password)
    nuevo_usuario = models.Usuario(
        nombre=nombre,
        email=email,
        password_hash=password_hash,
        telefono=telefono,
        rol="user"
    )

    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    # Crear token
    token = auth.crear_token({"sub": str(nuevo_usuario.id), "rol": nuevo_usuario.rol})

    # Crear respuesta con cookie
    response = JSONResponse({
        "success": True,
        "mensaje": "Registro exitoso",
        "usuario": {
            "id": nuevo_usuario.id,
            "nombre": nuevo_usuario.nombre,
            "email": nuevo_usuario.email,
            "rol": nuevo_usuario.rol
        }
    })
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,  # 7 días
        samesite="lax"
    )

    return response


@app.post("/api/auth/login")
async def api_login(
        email: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db)
):
    """Inicio de sesión"""
    # Buscar usuario
    usuario = db.query(models.Usuario).filter(models.Usuario.email == email).first()

    if not usuario or not auth.verify_password(password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    # Crear token
    token = auth.crear_token({"sub": str(usuario.id), "rol": usuario.rol})

    # Crear respuesta con cookie
    response = JSONResponse({
        "success": True,
        "mensaje": "Inicio de sesión exitoso",
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "rol": usuario.rol
        }
    })
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,
        samesite="lax"
    )

    return response


@app.post("/api/auth/logout")
async def api_logout():
    """Cerrar sesión"""
    response = JSONResponse({"success": True, "mensaje": "Sesión cerrada"})
    response.delete_cookie("access_token")
    return response


@app.get("/api/auth/usuario-actual")
async def api_usuario_actual(
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.obtener_usuario_actual)
):
    """Obtener información del usuario actual"""
    if not usuario:
        return {"autenticado": False}

    return {
        "autenticado": True,
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "rol": usuario.rol,
            "telefono": usuario.telefono,
            "direccion": usuario.direccion,
            "ciudad": usuario.ciudad
        }
    }


# ==================== API DEL CARRITO ====================

@app.post("/api/carrito/agregar")
async def api_agregar_carrito(
        producto_id: int = Form(...),
        cantidad: int = Form(1),
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.obtener_usuario_requerido)
):
    """Agregar producto al carrito"""
    # Verificar producto
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Verificar stock
    if producto.stock < cantidad:
        raise HTTPException(status_code=400, detail=f"Stock insuficiente. Disponible: {producto.stock}")

    # Verificar si ya existe en el carrito
    item_existente = db.query(models.CarritoItem).filter(
        models.CarritoItem.usuario_id == usuario.id,
        models.CarritoItem.producto_id == producto_id
    ).first()

    if item_existente:
        # Actualizar cantidad
        nueva_cantidad = item_existente.cantidad + cantidad
        if producto.stock < nueva_cantidad:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente. Disponible: {producto.stock}")
        item_existente.cantidad = nueva_cantidad
    else:
        # Crear nuevo item
        nuevo_item = models.CarritoItem(
            usuario_id=usuario.id,
            producto_id=producto_id,
            cantidad=cantidad
        )
        db.add(nuevo_item)

    db.commit()

    # Contar items en carrito
    total_items = db.query(models.CarritoItem).filter(
        models.CarritoItem.usuario_id == usuario.id
    ).count()

    return {
        "success": True,
        "mensaje": "Producto agregado al carrito",
        "total_items": total_items
    }


@app.get("/api/carrito")
async def api_obtener_carrito(
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.obtener_usuario_requerido)
):
    """Obtener carrito del usuario"""
    items = db.query(models.CarritoItem).filter(
        models.CarritoItem.usuario_id == usuario.id
    ).all()

    carrito_data = []
    total = 0

    for item in items:
        producto = item.producto
        subtotal = producto.precio * item.cantidad
        total += subtotal

        carrito_data.append({
            "id": item.id,
            "producto": {
                "id": producto.id,
                "nombre": producto.nombre,
                "precio": producto.precio,
                "imagen_url": producto.imagen_url,
                "stock": producto.stock
            },
            "cantidad": item.cantidad,
            "subtotal": subtotal
        })

    return {
        "items": carrito_data,
        "total": total,
        "total_items": len(items)
    }


@app.put("/api/carrito/actualizar/{item_id}")
async def api_actualizar_carrito(
        item_id: int,
        cantidad: int = Form(...),
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.obtener_usuario_requerido)
):
    """Actualizar cantidad de un item del carrito"""
    item = db.query(models.CarritoItem).filter(
        models.CarritoItem.id == item_id,
        models.CarritoItem.usuario_id == usuario.id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")

    if cantidad <= 0:
        raise HTTPException(status_code=400, detail="La cantidad debe ser mayor a 0")

    # Verificar stock
    if item.producto.stock < cantidad:
        raise HTTPException(status_code=400, detail=f"Stock insuficiente. Disponible: {item.producto.stock}")

    item.cantidad = cantidad
    db.commit()

    return {"success": True, "mensaje": "Carrito actualizado"}


@app.delete("/api/carrito/eliminar/{item_id}")
async def api_eliminar_item_carrito(
        item_id: int,
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.obtener_usuario_requerido)
):
    """Eliminar item del carrito"""
    item = db.query(models.CarritoItem).filter(
        models.CarritoItem.id == item_id,
        models.CarritoItem.usuario_id == usuario.id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")

    db.delete(item)
    db.commit()

    return {"success": True, "mensaje": "Producto eliminado del carrito"}


@app.delete("/api/carrito/vaciar")
async def api_vaciar_carrito(
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.obtener_usuario_requerido)
):
    """Vaciar carrito completo"""
    db.query(models.CarritoItem).filter(
        models.CarritoItem.usuario_id == usuario.id
    ).delete()
    db.commit()

    return {"success": True, "mensaje": "Carrito vaciado"}


# ==================== API DE PEDIDOS ====================

@app.post("/api/pedidos/crear")
async def api_crear_pedido(
        direccion_envio: str = Form(...),
        ciudad: str = Form(...),
        telefono: str = Form(...),
        notas: str = Form(None),
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.obtener_usuario_requerido)
):
    """Crear pedido desde el carrito"""
    # Obtener items del carrito
    items_carrito = db.query(models.CarritoItem).filter(
        models.CarritoItem.usuario_id == usuario.id
    ).all()

    if not items_carrito:
        raise HTTPException(status_code=400, detail="El carrito está vacío")

    # Calcular total y verificar stock
    total = 0
    for item in items_carrito:
        if item.producto.stock < item.cantidad:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente para {item.producto.nombre}. Disponible: {item.producto.stock}"
            )
        total += item.producto.precio * item.cantidad

    # Crear pedido
    nuevo_pedido = models.Pedido(
        usuario_id=usuario.id,
        total=total,
        estado="pendiente",
        direccion_envio=direccion_envio,
        ciudad=ciudad,
        telefono=telefono,
        notas=notas
    )
    db.add(nuevo_pedido)
    db.flush()

    # Crear items del pedido
    for item in items_carrito:
        pedido_item = models.PedidoItem(
            pedido_id=nuevo_pedido.id,
            producto_id=item.producto_id,
            nombre_producto=item.producto.nombre,
            precio_unitario=item.producto.precio,
            cantidad=item.cantidad,
            subtotal=item.producto.precio * item.cantidad
        )
        db.add(pedido_item)

    # Crear registro de pago (simulado por ahora)
    pago = models.Pago(
        pedido_id=nuevo_pedido.id,
        metodo="simulado",
        estado="pendiente",
        monto=total
    )
    db.add(pago)

    db.commit()
    db.refresh(nuevo_pedido)

    return {
        "success": True,
        "mensaje": "Pedido creado exitosamente",
        "pedido_id": nuevo_pedido.id
    }


@app.post("/api/pedidos/{pedido_id}/pagar")
async def api_pagar_pedido(
        pedido_id: int,
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.obtener_usuario_requerido)
):
    """Simular pago de pedido"""
    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == pedido_id,
        models.Pedido.usuario_id == usuario.id
    ).first()

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    if pedido.estado != "pendiente":
        raise HTTPException(status_code=400, detail="El pedido ya fue procesado")

    # Actualizar estado del pedido
    pedido.estado = "pagado"

    # Actualizar pago
    if pedido.pago:
        pedido.pago.estado = "aprobado"
        pedido.pago.fecha_aprobacion = datetime.utcnow()

    # Reducir stock de productos
    for item in pedido.items:
        producto = item.producto
        producto.stock -= item.cantidad

    # Vaciar carrito
    db.query(models.CarritoItem).filter(
        models.CarritoItem.usuario_id == usuario.id
    ).delete()

    db.commit()

    return {
        "success": True,
        "mensaje": "Pago procesado exitosamente",
        "pedido_id": pedido.id
    }


@app.get("/api/pedidos")
async def api_obtener_pedidos(
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.obtener_usuario_requerido)
):
    """Obtener pedidos del usuario"""
    pedidos = db.query(models.Pedido).filter(
        models.Pedido.usuario_id == usuario.id
    ).order_by(models.Pedido.fecha_pedido.desc()).all()

    pedidos_data = []
    for pedido in pedidos:
        items_data = []
        for item in pedido.items:
            items_data.append({
                "nombre_producto": item.nombre_producto,
                "precio_unitario": item.precio_unitario,
                "cantidad": item.cantidad,
                "subtotal": item.subtotal
            })

        pedidos_data.append({
            "id": pedido.id,
            "total": pedido.total,
            "estado": pedido.estado,
            "fecha_pedido": pedido.fecha_pedido.strftime("%d/%m/%Y %H:%M"),
            "direccion_envio": pedido.direccion_envio,
            "ciudad": pedido.ciudad,
            "items": items_data
        })

    return {"pedidos": pedidos_data}


# ==================== API DASHBOARD (YA EXISTENTE) ====================

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


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Página de login"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/registro", response_class=HTMLResponse)
async def registro_page(request: Request):
    """Página de registro"""
    return templates.TemplateResponse("registro.html", {"request": request})


@app.get("/mi-cuenta", response_class=HTMLResponse)
async def mi_cuenta_page(
        request: Request,
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.obtener_usuario_requerido)
):
    """Página de cuenta del usuario"""
    # Obtener pedidos del usuario
    pedidos = db.query(models.Pedido).filter(
        models.Pedido.usuario_id == usuario.id
    ).order_by(models.Pedido.fecha_pedido.desc()).all()

    return templates.TemplateResponse("mi-cuenta.html", {
        "request": request,
        "usuario": usuario,
        "pedidos": pedidos
    })


@app.get("/carrito", response_class=HTMLResponse)
async def carrito_page(request: Request):
    """Página del carrito"""
    return templates.TemplateResponse("carrito.html", {"request": request})


@app.get("/checkout", response_class=HTMLResponse)
async def checkout_page(
        request: Request,
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.obtener_usuario_requerido)
):
    """Página de checkout"""
    # Verificar que haya items en el carrito
    items_carrito = db.query(models.CarritoItem).filter(
        models.CarritoItem.usuario_id == usuario.id
    ).all()

    if not items_carrito:
        return RedirectResponse(url="/carrito", status_code=303)

    return templates.TemplateResponse("checkout.html", {
        "request": request,
        "usuario": usuario
    })


@app.get("/pedido/{pedido_id}/confirmacion", response_class=HTMLResponse)
async def confirmacion_pedido_page(
        request: Request,
        pedido_id: int,
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.obtener_usuario_requerido)
):
    """Página de confirmación de pedido"""
    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == pedido_id,
        models.Pedido.usuario_id == usuario.id
    ).first()

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    return templates.TemplateResponse("pedido-confirmacion.html", {
        "request": request,
        "pedido": pedido
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


# ==================== ADMIN (PROTEGIDO) ====================

@app.get("/admin", response_class=HTMLResponse)
async def admin(
        request: Request,
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.verificar_admin)
):
    """Panel de administrador"""
    productos = db.query(models.Producto).all()
    total_productos = len(productos)
    total_stock = sum([p.stock for p in productos])
    valor_inventario = sum([p.precio * p.stock for p in productos])

    # Obtener todos los pedidos
    pedidos = db.query(models.Pedido).order_by(models.Pedido.fecha_pedido.desc()).all()

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "productos": productos,
        "total_productos": total_productos,
        "total_stock": total_stock,
        "valor_inventario": valor_inventario,
        "pedidos": pedidos,
        "usuario": usuario
    })


@app.post("/admin/agregar")
async def agregar_producto(
        nombre: str = Form(...),
        descripcion: str = Form(...),
        precio: float = Form(...),
        talla: str = Form(...),
        categoria: str = Form(...),
        imagen: UploadFile = File(...),
        stock: int = Form(...),
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.verificar_admin)
):
    """Agregar producto con imagen"""
    # Guardar imagen
    file_location = f"static/images/{imagen.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(imagen.file, buffer)

    imagen_url = f"/static/images/{imagen.filename}"

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
        usuario: models.Usuario = Depends(auth.verificar_admin)
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
async def eliminar_producto(
        producto_id: int,
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.verificar_admin)
):
    """Eliminar producto"""
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if producto:
        db.delete(producto)
        db.commit()

    return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/pedido/{pedido_id}/actualizar-estado")
async def actualizar_estado_pedido(
        pedido_id: int,
        estado: str = Form(...),
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.verificar_admin)
):
    """Actualizar estado de pedido"""
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if pedido:
        pedido.estado = estado
        pedido.fecha_actualizado = datetime.utcnow()
        db.commit()

    return RedirectResponse(url="/admin", status_code=303)


# Ejecutar servidor
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)