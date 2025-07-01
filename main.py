from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session
import models
import schemas
import crud
from database import SessionLocal, engine
import os

# Crear las tablas en la base de datos
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configuración para servir archivos estáticos y templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Configuración CORS (para desarrollo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de autenticación
SECRET_KEY = os.getenv("SECRET_KEY", "tu_clave_secreta_aleatoria_aqui")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dependencia para obtener la sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Funciones de autenticación
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str):
    return pwd_context.hash(password)

def authenticate_user(db: Session, email: str, password: str):
    user = crud.get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = crud.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: schemas.User = Depends(get_current_user)):
    return current_user

async def get_admin_user(current_user: schemas.User = Depends(get_current_user)):
    if current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="Se requieren privilegios de administrador")
    return current_user

# Rutas de autenticación
@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email ya registrado")
    return crud.create_user(db=db, user=user)

@app.get("/users/me/", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(get_current_active_user)):
    return current_user

# Rutas para vehículos
@app.get("/vehiculos/", response_model=list[schemas.Vehiculo])
def read_vehiculos(
    skip: int = 0, 
    limit: int = 100,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Obtiene todos los vehículos, con opción de filtrar por búsqueda o categoría"""
    return crud.get_vehiculos(db, skip=skip, limit=limit, search=search, category_id=category_id)

@app.post("/vehiculos/", response_model=schemas.Vehiculo)
def create_vehiculo(
    vehiculo: schemas.VehiculoBase, 
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_admin_user)
):
    """Crea un nuevo vehículo (solo administradores)"""
    return crud.create_vehiculo(db=db, vehiculo=vehiculo)

@app.get("/vehiculos/{vehiculo_id}", response_model=schemas.Vehiculo)
def read_vehiculo(vehiculo_id: int, db: Session = Depends(get_db)):
    """Obtiene un vehículo por su ID"""
    db_vehiculo = crud.get_vehiculo(db, vehiculo_id=vehiculo_id)
    if db_vehiculo is None:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return db_vehiculo

@app.put("/vehiculos/{vehiculo_id}", response_model=schemas.Vehiculo)
def update_vehiculo(
    vehiculo_id: int, 
    vehiculo: schemas.VehiculoBase,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_admin_user)
):
    """Actualiza un vehículo (solo administradores)"""
    db_vehiculo = crud.get_vehiculo(db, vehiculo_id=vehiculo_id)
    if db_vehiculo is None:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return crud.update_vehiculo(db=db, vehiculo_id=vehiculo_id, vehiculo=vehiculo)

@app.delete("/vehiculos/{vehiculo_id}")
def delete_vehiculo(
    vehiculo_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_admin_user)
):
    """Elimina un vehículo (solo administradores)"""
    db_vehiculo = crud.get_vehiculo(db, vehiculo_id=vehiculo_id)
    if db_vehiculo is None:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    crud.delete_vehiculo(db=db, vehiculo_id=vehiculo_id)
    return {"message": "Vehículo eliminado correctamente"}

@app.get("/vehiculos/disponibles/", response_model=list[schemas.Vehiculo])
def read_vehiculos_disponibles(
    fecha_inicio: datetime,
    fecha_fin: datetime,
    db: Session = Depends(get_db)
):
    """Obtiene vehículos disponibles en un rango de fechas"""
    return crud.get_vehiculos_disponibles(db, fecha_inicio, fecha_fin)

# Rutas para categorías
@app.get("/categorias/", response_model=list[schemas.Categoria])
def read_categorias(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Obtiene todas las categorías"""
    return crud.get_categorias(db, skip=skip, limit=limit)

@app.post("/categorias/", response_model=schemas.Categoria)
def create_categoria(
    categoria: schemas.CategoriaBase, 
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_admin_user)
):
    """Crea una nueva categoría (solo administradores)"""
    return crud.create_categoria(db=db, categoria=categoria)

@app.get("/categorias/{categoria_id}", response_model=schemas.Categoria)
def read_categoria(categoria_id: int, db: Session = Depends(get_db)):
    """Obtiene una categoría por su ID"""
    db_categoria = crud.get_categoria(db, categoria_id=categoria_id)
    if db_categoria is None:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return db_categoria

@app.put("/categorias/{categoria_id}", response_model=schemas.Categoria)
def update_categoria(
    categoria_id: int, 
    categoria: schemas.CategoriaBase,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_admin_user)
):
    """Actualiza una categoría (solo administradores)"""
    db_categoria = crud.get_categoria(db, categoria_id=categoria_id)
    if db_categoria is None:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return crud.update_categoria(db=db, categoria_id=categoria_id, categoria=categoria)

@app.delete("/categorias/{categoria_id}")
def delete_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_admin_user)
):
    """Elimina una categoría (solo administradores)"""
    db_categoria = crud.get_categoria(db, categoria_id=categoria_id)
    if db_categoria is None:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    crud.delete_categoria(db=db, categoria_id=categoria_id)
    return {"message": "Categoría eliminada correctamente"}

# Rutas para reservas
@app.post("/reservas/", response_model=schemas.Reserva)
def create_reserva(
    reserva: schemas.ReservaBase,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_active_user)
):
    """Crea una nueva reserva para el usuario actual"""
    try:
        return crud.create_reserva(db=db, reserva=reserva, usuario_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/reservas/", response_model=list[schemas.Reserva])
def read_reservas(
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_admin_user)
):
    """Obtiene todas las reservas (solo administradores)"""
    return crud.get_reservas(db, skip=skip, limit=limit)

@app.get("/reservas/me/", response_model=list[schemas.Reserva])
def read_reservas_usuario(
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_active_user)
):
    """Obtiene las reservas del usuario actual"""
    return crud.get_reservas_usuario(db, usuario_id=current_user.id, skip=skip, limit=limit)

@app.get("/reservas/me/activas/", response_model=list[schemas.Reserva])
def read_reservas_activas_usuario(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_active_user)
):
    """Obtiene las reservas activas del usuario actual"""
    return crud.get_reservas_activas_usuario(db, usuario_id=current_user.id)

@app.get("/reservas/{reserva_id}", response_model=schemas.Reserva)
def read_reserva(
    reserva_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_active_user)
):
    """Obtiene una reserva específica (solo si pertenece al usuario o es admin)"""
    db_reserva = crud.get_reserva(db, reserva_id=reserva_id)
    if db_reserva is None:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    if db_reserva.usuario_id != current_user.id and current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No tienes permiso para ver esta reserva")
    return db_reserva

@app.delete("/reservas/{reserva_id}")
def delete_reserva(
    reserva_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_active_user)
):
    """Cancela una reserva (solo si pertenece al usuario o es admin)"""
    db_reserva = crud.get_reserva(db, reserva_id=reserva_id)
    if db_reserva is None:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    if db_reserva.usuario_id != current_user.id and current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No tienes permiso para cancelar esta reserva")
    
    # Verificar que la reserva no haya comenzado
    if datetime.now() > db_reserva.fecha_reserva:
        raise HTTPException(status_code=400, detail="No se puede cancelar una reserva que ya ha comenzado")
    
    crud.delete_reserva(db=db, reserva_id=reserva_id)
    return {"message": "Reserva cancelada correctamente"}

# Rutas para el dashboard
@app.get("/dashboard/estadisticas/")
def get_estadisticas(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_admin_user)
):
    """Obtiene estadísticas para el dashboard (solo administradores)"""
    total_vehiculos = db.query(models.Vehiculo).count()
    total_reservas_activas = db.query(models.Reserva).filter(
        models.Reserva.fecha_reserva <= datetime.now(),
        models.Reserva.fecha_devolucion >= datetime.now()
    ).count()
    
    # Categoría con más reservas
    categoria_mas_reservas = db.query(
        models.Categoria.nombre,
        db.func.count(models.Reserva.id).label("total_reservas")
    ).join(models.Vehiculo, models.Vehiculo.categoria_id == models.Categoria.id)\
     .join(models.Reserva, models.Reserva.vehiculo_id == models.Vehiculo.id)\
     .group_by(models.Categoria.id)\
     .order_by(db.func.count(models.Reserva.id).desc())\
     .first()
    
    # Vehículo con más reservas
    vehiculo_mas_reservas = db.query(
        models.Vehiculo.marca,
        models.Vehiculo.modelo,
        db.func.count(models.Reserva.id).label("total_reservas")
    ).join(models.Reserva, models.Reserva.vehiculo_id == models.Vehiculo.id)\
     .group_by(models.Vehiculo.id)\
     .order_by(db.func.count(models.Reserva.id).desc())\
     .first()
    
    return {
        "total_vehiculos": total_vehiculos,
        "total_reservas_activas": total_reservas_activas,
        "categoria_mas_reservas": categoria_mas_reservas[0] if categoria_mas_reservas else None,
        "vehiculo_mas_reservas": f"{vehiculo_mas_reservas[0]} {vehiculo_mas_reservas[1]}" if vehiculo_mas_reservas else None,
        "total_usuarios": db.query(models.User).count(),
        "reservas_ultimo_mes": db.query(models.Reserva).filter(
            models.Reserva.fecha_reserva >= datetime.now() - timedelta(days=30)
        ).count()
    }

# Rutas para el frontend (opcional)
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def read_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def read_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Configuración para producción
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)