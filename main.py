from flask import Flask, render_template, request, redirect, url_for, jsonify
from sqlalchemy.orm import Session
from database import engine, get_db
from datetime import datetime
import models
import os
import shutil

app = Flask(__name__)

# Crear las tablas en la base de datos
models.Base.metadata.create_all(bind=engine)

# Crear carpetas si no existen
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/images", exist_ok=True)


# Filtro personalizado para formatear precios
@app.template_filter('format_cop')
def format_cop(value):
    return "{:,.0f}".format(value).replace(",", ".")


# ==================== API DASHBOARD ====================

@app.route("/api/dashboard/impacto-ambiental", methods=["GET"])
def get_impacto_ambiental():
    return jsonify({
        "labels": ["Agua Ahorrada", "CO2 Reducido", "Residuos Evitados", "Energía Ahorrada"],
        "values": [85, 70, 90, 65],
        "units": ["%", "%", "%", "%"]
    })


@app.route("/api/dashboard/prendas-por-categoria", methods=["GET"])
def get_prendas_por_categoria():
    db = next(get_db())
    categorias = db.query(models.Producto.categoria, models.Producto.id).all()
    conteo = {}
    for categoria, _ in categorias:
        conteo[categoria] = conteo.get(categoria, 0) + 1

    return jsonify({
        "labels": list(conteo.keys()) if conteo else ["Sin datos"],
        "values": list(conteo.values()) if conteo else [0]
    })


@app.route("/api/dashboard/consumo-mensual", methods=["GET"])
def get_consumo_mensual():
    return jsonify({
        "labels": ["Ene", "Feb", "Mar", "Abr", "May", "Jun"],
        "values": [12, 19, 15, 25, 22, 30]
    })


@app.route("/api/dashboard/metricas-generales", methods=["GET"])
def get_metricas_generales():
    db = next(get_db())
    productos = db.query(models.Producto).all()
    total_productos = len(productos)
    prendas_unicas = sum(1 for p in productos if p.stock == 1)

    return jsonify({
        "total_prendas": total_productos,
        "piezas_unicas": prendas_unicas,
        "kg_co2_ahorrado": total_productos * 15,
        "litros_agua_ahorrados": total_productos * 2700
    })


# ==================== RUTAS DE VISTAS (HTML) ====================

@app.route("/")
def home():
    """Página principal"""
    db = next(get_db())
    productos_destacados = db.query(models.Producto).filter(models.Producto.stock == 1).limit(4).all()

    if len(productos_destacados) < 4:
        faltantes = 4 - len(productos_destacados)
        ids_existentes = [p.id for p in productos_destacados]
        adicionales = db.query(models.Producto).filter(
            ~models.Producto.id.in_(ids_existentes)
        ).order_by(models.Producto.id.desc()).limit(faltantes).all()
        productos_destacados.extend(adicionales)

    return render_template("index.html", productos_destacados=productos_destacados)


@app.route("/categoria/<categoria>")
def categoria(categoria):
    """Página de categoría"""
    db = next(get_db())
    productos = db.query(models.Producto).filter(models.Producto.categoria == categoria).all()

    return render_template("categoria.html", productos=productos, categoria=categoria)


@app.route("/buscar")
def buscar():
    """Búsqueda de productos"""
    q = request.args.get('q', '')
    db = next(get_db())
    productos = db.query(models.Producto).filter(
        models.Producto.nombre.contains(q) |
        models.Producto.descripcion.contains(q) |
        models.Producto.categoria.contains(q)
    ).all()

    return render_template("categoria.html", productos=productos, categoria=f"Resultados para '{q}'")


@app.route("/producto/<int:producto_id>")
def detalle_producto(producto_id):
    """Página de detalle del producto"""
    db = next(get_db())
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()

    if not producto:
        return redirect(url_for('home'))

    productos_relacionados = db.query(models.Producto).filter(
        models.Producto.categoria == producto.categoria,
        models.Producto.id != producto_id
    ).limit(4).all()

    return render_template("detalle.html", producto=producto, productos_relacionados=productos_relacionados)


# ==================== ADMIN (SIN LOGIN) ====================

@app.route("/admin")
def admin():
    """Panel de administrador"""
    db = next(get_db())
    productos = db.query(models.Producto).all()
    total_productos = len(productos)
    total_stock = sum([p.stock for p in productos])
    valor_inventario = sum([p.precio * p.stock for p in productos])

    return render_template("admin.html",
                           productos=productos,
                           total_productos=total_productos,
                           total_stock=total_stock,
                           valor_inventario=valor_inventario
                           )


@app.route("/admin/editar/<int:producto_id>")
def obtener_producto_editar(producto_id):
    db = next(get_db())
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    productos = db.query(models.Producto).all()
    total_productos = len(productos)
    total_stock = sum([p.stock for p in productos])
    valor_inventario = sum([p.precio * p.stock for p in productos])

    return render_template("admin.html",
                           productos=productos,
                           producto_editar=producto,
                           total_productos=total_productos,
                           total_stock=total_stock,
                           valor_inventario=valor_inventario
                           )


@app.route("/admin/agregar", methods=["POST"])
def agregar_producto():
    """Agregar producto"""
    nombre = request.form.get("nombre")
    descripcion = request.form.get("descripcion")
    precio = float(request.form.get("precio"))
    talla = request.form.get("talla")
    categoria = request.form.get("categoria")
    imagen_url = request.form.get("imagen_url")
    stock = int(request.form.get("stock"))

    db = next(get_db())
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

    return redirect(url_for('admin'))


@app.route("/admin/actualizar/<int:producto_id>", methods=["POST"])
def actualizar_producto(producto_id):
    """Actualizar producto"""
    nombre = request.form.get("nombre")
    descripcion = request.form.get("descripcion")
    precio = float(request.form.get("precio"))
    talla = request.form.get("talla")
    categoria = request.form.get("categoria")
    imagen_url = request.form.get("imagen_url")
    stock = int(request.form.get("stock"))

    db = next(get_db())
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

    return redirect(url_for('admin'))


@app.route("/admin/eliminar/<int:producto_id>")
def eliminar_producto(producto_id):
    """Eliminar producto"""
    db = next(get_db())
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if producto:
        db.delete(producto)
        db.commit()

    return redirect(url_for('admin'))


# Ejecutar servidor
if __name__ == '__main__':
    app.run(debug=True)