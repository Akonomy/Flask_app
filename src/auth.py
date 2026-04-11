import sqlite3
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from .database import get_db

SECRET_KEY = "cheie-secreta-foarte-lunga-schimbati-obligatoriu-in-productie"
ALGORITHM = "HS256"
EXPIRARE_TOKEN_MINUTE = 30

oauth2_schema = OAuth2PasswordBearer(tokenUrl="autentificare")


def hasheaza_parola(parola: str) -> str:
    return bcrypt.hashpw(parola.encode(), bcrypt.gensalt()).decode()


def verifica_parola(parola: str, hash_parola: str) -> bool:
    return bcrypt.checkpw(parola.encode(), hash_parola.encode())


def creeaza_token(date: dict) -> str:
    date_copie = date.copy()
    date_copie["exp"] = datetime.now(timezone.utc) + timedelta(minutes=EXPIRARE_TOKEN_MINUTE)
    return jwt.encode(date_copie, SECRET_KEY, algorithm=ALGORITHM)


def get_utilizator_curent(
    token: str = Depends(oauth2_schema),
    db: sqlite3.Connection = Depends(get_db),
):
    """Extrage și validează token-ul JWT; returnează utilizatorul autentificat."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Token invalid.")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirat. Autentificați-vă din nou.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalid.")

    utilizator = db.execute(
        "SELECT * FROM utilizatori WHERE email = ?", (email,)
    ).fetchone()
    if not utilizator:
        raise HTTPException(status_code=401, detail="Utilizatorul nu există.")
    return utilizator
