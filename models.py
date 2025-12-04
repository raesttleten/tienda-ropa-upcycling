from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


# ==================== USUARIO ====================
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    telefono = Column(String, nullable=True)
    direccion = Column(Text, nullable=True)
    ciudad = Column(String, nullable=True)
    rol = Column(String, default="user")  # "user" o "admin"
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    activo = Column(Boolean, default=True)

    # Relaciones
    carrito_items = relationship("CarritoItem", back_populates="usuario", cascade="all, delete-orphan")
    pedidos = relationship("Pedido", back_populates="usuario", cascade="all, delete-orphan")


# ==================== PRODUCTO ====================
class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    descripcion = Column(Text)
    precio = Column(Float)
    talla = Column(String)
    categoria = Column(String)
    imagen_url = Column(String)
    stock = Column(Integer, default=1)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    # Relaciones
    carrito_items = relationship("CarritoItem", back_populates="producto")
    pedido_items = relationship("PedidoItem", back_populates="producto")


# ==================== CARRITO ====================
class CarritoItem(Base):
    __tablename__ = "carrito_items"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    producto_id = Column(Integer, ForeignKey("productos.id"))
    cantidad = Column(Integer, default=1)
    fecha_agregado = Column(DateTime, default=datetime.utcnow)

    # Relaciones
    usuario = relationship("Usuario", back_populates="carrito_items")
    producto = relationship("Producto", back_populates="carrito_items")


# ==================== PEDIDO ====================
class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    total = Column(Float)
    estado = Column(String, default="pendiente")  # pendiente, pagado, enviado, entregado, cancelado
    direccion_envio = Column(Text)
    ciudad = Column(String)
    telefono = Column(String)
    notas = Column(Text, nullable=True)
    fecha_pedido = Column(DateTime, default=datetime.utcnow)
    fecha_actualizado = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    usuario = relationship("Usuario", back_populates="pedidos")
    items = relationship("PedidoItem", back_populates="pedido", cascade="all, delete-orphan")
    pago = relationship("Pago", back_populates="pedido", uselist=False, cascade="all, delete-orphan")


# ==================== ITEMS DE PEDIDO ====================
class PedidoItem(Base):
    __tablename__ = "pedido_items"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"))
    producto_id = Column(Integer, ForeignKey("productos.id"))
    nombre_producto = Column(String)  # Guardado para histórico
    precio_unitario = Column(Float)  # Guardado para histórico
    cantidad = Column(Integer)
    subtotal = Column(Float)

    # Relaciones
    pedido = relationship("Pedido", back_populates="items")
    producto = relationship("Producto", back_populates="pedido_items")


# ==================== PAGO ====================
class Pago(Base):
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"))
    metodo = Column(String, default="simulado")  # simulado, stripe, paypal
    estado = Column(String, default="pendiente")  # pendiente, aprobado, rechazado
    external_reference = Column(String, nullable=True)
    monto = Column(Float)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_aprobacion = Column(DateTime, nullable=True)

    # Relaciones
    pedido = relationship("Pedido", back_populates="pago")