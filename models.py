from sqlalchemy import Column, Integer, String, Float, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

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

    def __repr__(self):
        return f"<Producto(id={self.id}, nombre='{self.nombre}', categoria='{self.categoria}')>"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    correo = Column(String, unique=True, index=True, nullable=False)
    contrasena = Column(String, nullable=False)  # hash
    es_admin = Column(Boolean, default=False)

    carrito = relationship("Carrito", back_populates="usuario", cascade="all, delete-orphan")
    pedidos = relationship("Pedido", back_populates="usuario", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Usuario(id={self.id}, nombre='{self.nombre}', correo='{self.correo}', admin={self.es_admin})>"


class Carrito(Base):
    __tablename__ = "carrito"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id", ondelete="CASCADE"), nullable=False)
    cantidad = Column(Integer, default=1)

    usuario = relationship("Usuario", back_populates="carrito")
    producto = relationship("Producto")

    def __repr__(self):
        return f"<Carrito(id={self.id}, usuario_id={self.usuario_id}, producto_id={self.producto_id}, cantidad={self.cantidad})>"


class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    estado = Column(String, default="pendiente")  # pendiente, confirmado, cancelado
    fecha = Column(String, nullable=False)

    usuario = relationship("Usuario", back_populates="pedidos")

    def __repr__(self):
        return f"<Pedido(id={self.id}, usuario_id={self.usuario_id}, estado='{self.estado}', fecha='{self.fecha}')>"