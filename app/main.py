from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .routers import menu, orders, reports

# Create all tables on startup (simple approach for this small app)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Fun Fair Order Management Server")

# CORS (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for uploaded images
app.mount("/media", StaticFiles(directory="media"), name="media")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Include routers
app.include_router(menu.router, prefix="", tags=["menu"])
app.include_router(orders.router, prefix="", tags=["orders"])
app.include_router(reports.router, prefix="", tags=["reports"])
