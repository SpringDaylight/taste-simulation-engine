import os
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import get_database_url


class Base(DeclarativeBase):
    pass


def get_engine():
    """
    Create SQLAlchemy engine with RDS connection
    
    Returns:
        Engine: SQLAlchemy engine instance
    """
    database_url = get_database_url()
    
    url = make_url(database_url)
    is_postgres = url.get_backend_name().startswith("postgresql")

    # Engine configuration
    engine_config = {
        "echo": os.getenv("SQL_ECHO", "false").lower() == "true",
    }

    if is_postgres:
        engine_config.update(
            {
                "pool_pre_ping": True,  # Verify connections before using
                "pool_size": 10,
                "max_overflow": 20,
                "pool_recycle": 3600,  # Recycle connections after 1 hour
                "connect_args": {
                    "connect_timeout": 10  # 10 second timeout
                },
            }
        )
    
    # Add SSL configuration for RDS (optional)
    ssl_cert_path = os.getenv("SSL_CERT_PATH", "/certs/global-bundle.pem")
    env = os.getenv("ENV", "local").lower()
    default_ssl_mode = "disable" if env == "local" else "prefer"
    ssl_mode = os.getenv("SSL_MODE", default_ssl_mode)  # prefer, require, verify-full, disable
    
    if is_postgres and ssl_mode != "disable":
        if os.path.exists(ssl_cert_path) and ssl_mode == "verify-full":
            engine_config["connect_args"]["sslmode"] = "verify-full"
            engine_config["connect_args"]["sslrootcert"] = ssl_cert_path
        else:
            # Use require mode if cert not found but SSL is desired
            engine_config["connect_args"]["sslmode"] = "require"
    
    return create_engine(database_url, **engine_config)


# Create engine instance
engine = get_engine()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency for FastAPI to get database session
    
    Yields:
        Session: SQLAlchemy session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
