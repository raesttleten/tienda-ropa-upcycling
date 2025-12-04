# ...existing code...
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    correo = Column(String(150), unique=True, index=True, nullable=False)
    contrasena = Column(String(255), nullable=False)
    es_admin = Column(Boolean, default=False)

    pedidos = relationship("Pedido", back_populates="usuario", cascade="all, delete-orphan")
    carrito = relationship("Carrito", back_populates="usuario", cascade="all, delete-orphan")

class Producto(Base):
    __tablename__ = "productos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text, default="")
    precio = Column(Float, default=0.0)
    talla = Column(String(20), default="")
    categoria = Column(String(100), default="General")
    imagen_url = Column(String(500), default="")
    stock = Column(Integer, default=0)

    carrito_items = relationship("Carrito", back_populates="producto", cascade="all, delete-orphan")

class Carrito(Base):
    __tablename__ = "carrito"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Integer, default=1)

    usuario = relationship("Usuario", back_populates="carrito")
    producto = relationship("Producto", back_populates="carrito_items")

class Pedido(Base):
    __tablename__ = "pedidos"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    estado = Column(String(50), default="pendiente")
    fecha = Column(String(100))

    usuario = relationship("Usuario", back_populates="pedidos")
# ...existing code...

    def __repr__(self):
        return f"<Pedido(id={self.id}, usuario_id={self.usuario_id}, estado='{self.estado}', fecha='{self.fecha}')>"