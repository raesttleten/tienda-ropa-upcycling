import os
import asyncio
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

# -------------------- INICIALIZACIÓN DE MODELOS --------------------
# Se usa create_task para no bloquear el event loop de Uvicorn
async def startup():
    await init_models()

# -------------------- CONFIGURACIÓN FASTAPI --------------------
app = FastAPI(on_startup=[startup])
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

# -------------------- MÁS ENDPOINTS --------------------
# Aquí van todos tus endpoints de categoria, buscar, producto, admin,
# registro, login, logout, carrito, checkout
# Manteniendo tu lógica actual intacta

# -------------------- EJECUCIÓN --------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))  # Railway usa PORT env
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
