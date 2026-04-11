import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_utilizator_curent
from ..database import get_db
from ..models import SarcinaActualizare, SarcinaCreare

router = APIRouter(prefix="/sarcini", tags=["sarcini"])


@router.get("")
def obtine_sarcini(
    doar_nefinalizate: bool = False,
    db: sqlite3.Connection = Depends(get_db),
    utilizator_curent=Depends(get_utilizator_curent),
):
    if doar_nefinalizate:
        sarcini = db.execute(
            "SELECT * FROM sarcini WHERE utilizator_id = ? AND finalizata = 0",
            (utilizator_curent["id"],),
        ).fetchall()
    else:
        sarcini = db.execute(
            "SELECT * FROM sarcini WHERE utilizator_id = ?", (utilizator_curent["id"],)
        ).fetchall()
    return [dict(s) for s in sarcini]


@router.get("/{sarcina_id}")
def obtine_sarcina(
    sarcina_id: int,
    db: sqlite3.Connection = Depends(get_db),
    utilizator_curent=Depends(get_utilizator_curent),
):
    sarcina = db.execute(
        "SELECT * FROM sarcini WHERE id = ? AND utilizator_id = ?",
        (sarcina_id, utilizator_curent["id"]),
    ).fetchone()
    if not sarcina:
        raise HTTPException(status_code=404, detail="Sarcina nu a fost găsită.")
    return dict(sarcina)


@router.post("", status_code=201)
def creeaza_sarcina(
    sarcina: SarcinaCreare,
    db: sqlite3.Connection = Depends(get_db),
    utilizator_curent=Depends(get_utilizator_curent),
):
    cursor = db.execute(
        "INSERT INTO sarcini (titlu, descriere, utilizator_id) VALUES (?, ?, ?)",
        (sarcina.titlu, sarcina.descriere, utilizator_curent["id"]),
    )
    db.commit()
    sarcina_noua = db.execute(
        "SELECT * FROM sarcini WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return dict(sarcina_noua)


@router.patch("/{sarcina_id}/finaliza")
def finalizeaza_sarcina(
    sarcina_id: int,
    db: sqlite3.Connection = Depends(get_db),
    utilizator_curent=Depends(get_utilizator_curent),
):
    sarcina = db.execute(
        "SELECT * FROM sarcini WHERE id = ? AND utilizator_id = ?",
        (sarcina_id, utilizator_curent["id"]),
    ).fetchone()
    if not sarcina:
        raise HTTPException(status_code=404, detail="Sarcina nu a fost găsită.")

    db.execute("UPDATE sarcini SET finalizata = 1 WHERE id = ?", (sarcina_id,))
    db.commit()
    return dict(db.execute("SELECT * FROM sarcini WHERE id = ?", (sarcina_id,)).fetchone())


@router.put("/{sarcina_id}")
def actualizeaza_sarcina(
    sarcina_id: int,
    date: SarcinaActualizare,
    db: sqlite3.Connection = Depends(get_db),
    utilizator_curent=Depends(get_utilizator_curent),
):
    sarcina = db.execute(
        "SELECT * FROM sarcini WHERE id = ? AND utilizator_id = ?",
        (sarcina_id, utilizator_curent["id"]),
    ).fetchone()
    if not sarcina:
        raise HTTPException(status_code=404, detail="Sarcina nu a fost găsită.")

    sarcina_dict = dict(sarcina)
    titlu_nou = date.titlu if date.titlu is not None else sarcina_dict["titlu"]
    descriere_noua = date.descriere if date.descriere is not None else sarcina_dict["descriere"]
    finalizata_noua = int(date.finalizata) if date.finalizata is not None else sarcina_dict["finalizata"]

    db.execute(
        "UPDATE sarcini SET titlu = ?, descriere = ?, finalizata = ? WHERE id = ?",
        (titlu_nou, descriere_noua, finalizata_noua, sarcina_id),
    )
    db.commit()
    return dict(db.execute("SELECT * FROM sarcini WHERE id = ?", (sarcina_id,)).fetchone())


@router.delete("/{sarcina_id}")
def sterge_sarcina(
    sarcina_id: int,
    db: sqlite3.Connection = Depends(get_db),
    utilizator_curent=Depends(get_utilizator_curent),
):
    sarcina = db.execute(
        "SELECT * FROM sarcini WHERE id = ? AND utilizator_id = ?",
        (sarcina_id, utilizator_curent["id"]),
    ).fetchone()
    if not sarcina:
        raise HTTPException(status_code=404, detail="Sarcina nu a fost găsită.")

    db.execute("DELETE FROM sarcini WHERE id = ?", (sarcina_id,))
    db.commit()
    return {"mesaj": f"Sarcina cu ID-ul {sarcina_id} a fost ștearsă."}
