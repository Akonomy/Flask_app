from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5173",   # Vite dev server
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROUTES_HTML = """<!DOCTYPE html>
<html lang="ro">
<head><meta charset="UTF-8"><title>Rute disponibile</title></head>
<body>
<h2>Rute disponibile</h2>
<table border="1" cellpadding="6" cellspacing="0">
  <tr><th>Lab</th><th>Metodă</th><th>Rută</th><th>Funcționalitate</th></tr>
  <tr><td>—</td><td>GET</td><td><a href="/docs">/docs</a></td><td>Swagger UI — testare interactivă a tuturor endpoint-urilor</td></tr>
  <tr><td>—</td><td>GET</td><td><a href="/redoc">/redoc</a></td><td>ReDoc — documentație alternativă a API-ului</td></tr>
  <tr><td colspan="4"><strong>Lab 02 — Inventar produse (fără autentificare, in-memory)</strong></td></tr>
  <tr><td>Lab 02</td><td>GET</td><td><a href="/produse">/produse</a></td><td>Lista tuturor produselor</td></tr>
  <tr><td>Lab 02</td><td>GET</td><td>/produse/{id}</td><td>Detalii produs după ID</td></tr>
  <tr><td>Lab 02</td><td>POST</td><td>/produse</td><td>Adăugare produs (JSON: id, nume, pret, stoc)</td></tr>
  <tr><td>Lab 02</td><td>PUT</td><td>/produse/{id}</td><td>Înlocuire completă produs (JSON: id, nume, pret, stoc)</td></tr>
  <tr><td>Lab 02</td><td>DELETE</td><td>/produse/{id}</td><td>Ștergere produs</td></tr>
  <tr><td colspan="4"><strong>Lab 03 — Autentificare utilizatori (SQLite + JWT)</strong></td></tr>
  <tr><td>Lab 03</td><td>POST</td><td>/inregistrare</td><td>Înregistrare utilizator nou (JSON: email, parola)</td></tr>
  <tr><td>Lab 03</td><td>POST</td><td>/autentificare</td><td>Autentificare și obținere token JWT (form: username, password)</td></tr>
  <tr><td colspan="4"><strong>Lab 03 — Sarcini (necesită JWT)</strong></td></tr>
  <tr><td>Lab 03</td><td>GET</td><td>/sarcini</td><td>Lista sarcinilor utilizatorului curent</td></tr>
  <tr><td>Lab 03</td><td>GET</td><td>/sarcini/{id}</td><td>Detalii sarcină după ID</td></tr>
  <tr><td>Lab 03</td><td>POST</td><td>/sarcini</td><td>Creare sarcină nouă (JSON: titlu, descriere)</td></tr>
  <tr><td>Lab 03</td><td>PUT</td><td>/sarcini/{id}</td><td>Actualizare sarcină (JSON: titlu, descriere, finalizata — toate opționale)</td></tr>
  <tr><td>Lab 03</td><td>DELETE</td><td>/sarcini/{id}</td><td>Ștergere sarcină</td></tr>
  <tr><td colspan="4"><strong>Lab 03 (extensie) — Filtrare și finalizare</strong></td></tr>
  <tr><td>Lab 03</td><td>GET</td><td>/sarcini?doar_nefinalizate=true</td><td>Lista sarcinilor nefinalizate ale utilizatorului curent</td></tr>
  <tr><td>Lab 03</td><td>PATCH</td><td>/sarcini/{id}/finaliza</td><td>Marchează sarcina ca finalizată</td></tr>
  <tr><td colspan="4"><strong>Lab 04 — Interfețe web</strong></td></tr>
  <tr><td>Lab 04</td><td>GET</td><td><a href="/playground">/playground</a></td><td>API Playground — testare vizuală cu formulare, exemple și răspunsuri colorate</td></tr>
  <tr><td>Lab 04</td><td>GET</td><td>/index.html</td><td>Aplicație SPA gestionar de sarcini (deschideți cu Live Server din VS Code)</td></tr>
</table>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index():
    return ROUTES_HTML


@app.get("/playground", response_class=HTMLResponse, include_in_schema=False)
def playground():
    return Path("playground.html").read_text(encoding="utf-8")


# Lab 02 — inventar produse (in-memory, fără auth)
app.include_router(produse.router)

# Lab 03 — autentificare + sarcini (SQLite + JWT)
app.include_router(utilizatori.router)
app.include_router(sarcini.router)
