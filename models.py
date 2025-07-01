from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(200))
    rol = Column(String(20), default="Cliente")
    
    reservas = relationship("Reserva", back_populates="usuario")

class Vehiculo(Base):
    __tablename__ = "vehiculos"
    
    id = Column(Integer, primary_key=True, index=True)
    marca = Column(String(50), nullable=False)
    modelo = Column(String(50), nullable=False)
    año = Column(Integer)
    matricula = Column(String(20), unique=True)
    capacidad = Column(Integer)
    categoria_id = Column(Integer, ForeignKey("categorias.id"))
    
    categoria = relationship("Categoria", back_populates="vehiculos")
    reservas = relationship("Reserva", back_populates="vehiculo")

class Categoria(Base):
    __tablename__ = "categorias"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True)
    descripcion = Column(String(200))
    
    vehiculos = relationship("Vehiculo", back_populates="categoria")

class Reserva(Base):
    __tablename__ = "reservas"
    
    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"))
    usuario_id = Column(Integer, ForeignKey("users.id"))
    fecha_reserva = Column(DateTime)
    fecha_devolucion = Column(DateTime)
    
    vehiculo = relationship("Vehiculo", back_populates="reservas")
    usuario = relationship("User", back_populates="reservas")