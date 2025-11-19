from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import Base, engine, ensure_preorder_column
from .routers import menu, orders, reports

# Lightweight migration then create tables on startup
ensure_preorder_column()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Fun Fair Order Management Server")

origins = [
    "http://localhost:8100",
    "http://127.0.0.1:8100",
    "https://4xrop09rx746lp-8100.proxy.runpod.net"
]
# CORS (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
