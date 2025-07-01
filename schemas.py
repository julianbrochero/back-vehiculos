from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    nombre: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    rol: str
    
    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class VehiculoBase(BaseModel):
    marca: str
    modelo: str
    año: int
    matricula: str
    capacidad: int
    categoria_id: int

class Vehiculo(VehiculoBase):
    id: int
    
    class Config:
        orm_mode = True

class CategoriaBase(BaseModel):
    nombre: str
    descripcion: str

class Categoria(CategoriaBase):
    id: int
    
    class Config:
        orm_mode = True

class ReservaBase(BaseModel):
    vehiculo_id: int
    fecha_reserva: datetime
    fecha_devolucion: datetime

class Reserva(ReservaBase):
    id: int
    usuario_id: int
    
    class Config:
        orm_mode = True