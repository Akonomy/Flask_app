from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import initializeaza_db
from .routers import produse, sarcini, utilizatori


@asynccontextmanager
async def durata_de_viata(app: FastAPI):
    initializeaza_db()
    yield


app = FastAPI(
    title="Lab 02 + Lab 03 — Inventar & Gestionar de sarcini",
    version="2.0.0",
    lifespan=durata_de_viata,
)

# Lab 02 — inventar produse (in-memory, fără auth)
app.include_router(produse.router)

# Lab 03 — autentificare + sarcini (SQLite + JWT)
app.include_router(utilizatori.router)
app.include_router(sarcini.router)
