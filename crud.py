from sqlalchemy.orm import Session
from models import User, Vehiculo, Categoria, Reserva
from schemas import UserCreate, VehiculoBase, CategoriaBase, ReservaBase
from auth import get_password_hash

# Operaciones de usuario
def create_user(db: Session, user: UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = User(
        nombre=user.nombre,
        email=user.email,
        hashed_password=hashed_password,
        rol="Cliente"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

# Operaciones de vehículos
def create_vehiculo(db: Session, vehiculo: VehiculoBase):
    db_vehiculo = Vehiculo(**vehiculo.dict())
    db.add(db_vehiculo)
    db.commit()
    db.refresh(db_vehiculo)
    return db_vehiculo

def get_vehiculo(db: Session, vehiculo_id: int):
    return db.query(Vehiculo).filter(Vehiculo.id == vehiculo_id).first()

def get_vehiculos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Vehiculo).offset(skip).limit(limit).all()

def get_vehiculos_disponibles(db: Session, fecha_inicio: datetime, fecha_fin: datetime):
    # Vehículos que no tienen reservas en el rango de fechas
    subquery = db.query(Reserva.vehiculo_id).filter(
        Reserva.fecha_reserva <= fecha_fin,
        Reserva.fecha_devolucion >= fecha_inicio
    ).subquery()
    
    return db.query(Vehiculo).filter(~Vehiculo.id.in_(subquery)).all()

# Operaciones de categorías
def create_categoria(db: Session, categoria: CategoriaBase):
    db_categoria = Categoria(**categoria.dict())
    db.add(db_categoria)
    db.commit()
    db.refresh(db_categoria)
    return db_categoria

def get_categoria(db: Session, categoria_id: int):
    return db.query(Categoria).filter(Categoria.id == categoria_id).first()

def get_categorias(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Categoria).offset(skip).limit(limit).all()

# Operaciones de reservas
def create_reserva(db: Session, reserva: ReservaBase, usuario_id: int):
    # Verificar disponibilidad del vehículo
    vehiculo_disponible = db.query(Vehiculo).filter(
        Vehiculo.id == reserva.vehiculo_id,
        ~Vehiculo.reservas.any(
            (Reserva.fecha_reserva <= reserva.fecha_devolucion) &
            (Reserva.fecha_devolucion >= reserva.fecha_reserva)
        )
    ).first()
    
    if not vehiculo_disponible:
        raise ValueError("El vehículo no está disponible en las fechas seleccionadas")
    
    db_reserva = Reserva(**reserva.dict(), usuario_id=usuario_id)
    db.add(db_reserva)
    db.commit()
    db.refresh(db_reserva)
    return db_reserva

def get_reservas_usuario(db: Session, usuario_id: int):
    return db.query(Reserva).filter(Reserva.usuario_id == usuario_id).all()

def get_reservas_activas_usuario(db: Session, usuario_id: int):
    ahora = datetime.now()
    return db.query(Reserva).filter(
        Reserva.usuario_id == usuario_id,
        Reserva.fecha_reserva <= ahora,
        Reserva.fecha_devolucion >= ahora
    ).all()