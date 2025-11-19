from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./database.db"

# For SQLite, check_same_thread must be False when used with FastAPI / multi-threaded environments
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that provides a SQLAlchemy session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_preorder_column():
    """Ensure the 'preorder' column exists on 'orders' table (SQLite).
    Adds NOT NULL column with DEFAULT 0 and creates an index if missing.
    Safe to call multiple times.
    """
    with engine.begin() as conn:
        result = conn.execute(text("PRAGMA table_info('orders')"))
        columns = {row[1] for row in result}  # row[1] is the column name
        if "preorder" not in columns:
            conn.execute(text("ALTER TABLE orders ADD COLUMN preorder BOOLEAN NOT NULL DEFAULT 0"))
            # Backfill safeguard for any NULLs (defensive; shouldn't be needed)
            conn.execute(text("UPDATE orders SET preorder = 0 WHERE preorder IS NULL"))
        # Create index if it doesn't exist
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_orders_preorder ON orders (preorder)"))
