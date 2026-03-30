from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Lab 02 — Inventar produse (in-memory)
# ---------------------------------------------------------------------------

class Produs(BaseModel):
    id: int
    nume: str
    pret: float
    stoc: int = 0


# ---------------------------------------------------------------------------
# Lab 03 — Autentificare + Sarcini (SQLite + JWT)
# ---------------------------------------------------------------------------

class UtilizatorInregistrare(BaseModel):
    email: str = Field(min_length=5, max_length=100)
    parola: str = Field(min_length=8, max_length=100)

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Adresa de email nu este validă.")
        return v.lower()


class SarcinaCreare(BaseModel):
    titlu: str = Field(min_length=1, max_length=200)
    descriere: Optional[str] = Field(default=None, max_length=1000)


class SarcinaActualizare(BaseModel):
    titlu: Optional[str] = Field(default=None, min_length=1, max_length=200)
    descriere: Optional[str] = Field(default=None, max_length=1000)
    finalizata: Optional[bool] = None
