from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

# ============================================
# USUARIOS
# ============================================

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)  # hashed
    es_admin = Column(Boolean, default=False)

    # Relaciones
    carrito = relationship("CarritoItem", back_populates="usuario", cascade="all, delete")
    pedidos = relationship("Pedido", back_populates="usuario")


# ============================================
# PRODUCTOS (Tus productos actuales)
# ============================================

class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True, nullable=False)
    descripcion = Column(Text, nullable=False)
    precio = Column(Float, nullable=False)
    talla = Column(String, nullable=False)
    categoria = Column(String, nullable=False)
    imagen_url = Column(String, nullable=False)
    stock = Column(Integer, default=1)

    # Relaciones
    carrito_items = relationship("CarritoItem", back_populates="producto")
    items_pedido = relationship("PedidoItem", back_populates="producto")


# ============================================
# CARRITO
# ============================================

class CarritoItem(Base):
    __tablename__ = "carrito_items"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    producto_id = Column(Integer, ForeignKey("productos.id"))
    cantidad = Column(Integer, default=1)

    usuario = relationship("Usuario", back_populates="carrito")
    producto = relationship("Producto", back_populates="carrito_items")


# ============================================
# PEDIDOS
# ============================================

class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    fecha = Column(DateTime, default=datetime.utcnow)
    total = Column(Float, nullable=False)

    usuario = relationship("Usuario", back_populates="pedidos")
    items = relationship("PedidoItem", back_populates="pedido", cascade="all, delete")


class PedidoItem(Base):
    __tablename__ = "pedido_items"

    id = Column(Integer, primary_key=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"))
    producto_id = Column(Integer, ForeignKey("productos.id"))
    cantidad = Column(Integer, default=1)
    precio_unitario = Column(Float, nullable=False)

    pedido = relationship("Pedido", back_populates="items")
    producto = relationship("Producto", back_populates="items_pedido")
