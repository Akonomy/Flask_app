import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from ..auth import creeaza_token, hasheaza_parola, verifica_parola
from ..database import get_db
from ..models import UtilizatorInregistrare

router = APIRouter(tags=["autentificare"])


@router.post("/inregistrare", status_code=201)
def inregistrare(utilizator: UtilizatorInregistrare, db: sqlite3.Connection = Depends(get_db)):
    existent = db.execute(
        "SELECT id FROM utilizatori WHERE email = ?", (utilizator.email,)
    ).fetchone()
    if existent:
        raise HTTPException(status_code=400, detail="Adresa de email este deja înregistrată.")

    db.execute(
        "INSERT INTO utilizatori (email, parola_hash) VALUES (?, ?)",
        (utilizator.email, hasheaza_parola(utilizator.parola)),
    )
    db.commit()
    return {"mesaj": f"Utilizatorul {utilizator.email} a fost înregistrat cu succes."}


@router.post("/autentificare")
def autentificare(
    formular: OAuth2PasswordRequestForm = Depends(),
    db: sqlite3.Connection = Depends(get_db),
):
    utilizator = db.execute(
        "SELECT * FROM utilizatori WHERE email = ?", (formular.username,)
    ).fetchone()
    if not utilizator or not verifica_parola(formular.password, utilizator["parola_hash"]):
        raise HTTPException(status_code=401, detail="Email sau parolă incorectă.")

    token = creeaza_token({"sub": utilizator["email"]})
    return {"access_token": token, "token_type": "bearer"}
