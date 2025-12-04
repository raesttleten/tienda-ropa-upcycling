from sqlalchemy import Column, Integer, String, Float, Text
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