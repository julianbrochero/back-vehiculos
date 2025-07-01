from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configuración para SQLite (compatible con Render)
SQLALCHEMY_DATABASE_URL = "sqlite:///./vehiculos.db"  # Archivo en el mismo directorio
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"  # Alternativa para PostgreSQL

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()