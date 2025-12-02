from sqlalchemy import Column, Integer, String, Float, Text
from database import Base


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


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)