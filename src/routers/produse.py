from fastapi import APIRouter, HTTPException

from ..models import Produs

router = APIRouter(prefix="/produse", tags=["produse (lab 02)"])

inventar: list[Produs] = []


@router.get("")
def obtine_toate_produsele():
    return inventar


@router.get("/{produs_id}")
def obtine_produs(produs_id: int):
    for produs in inventar:
        if produs.id == produs_id:
            return produs
    raise HTTPException(status_code=404, detail=f"Produsul cu ID-ul {produs_id} nu a fost găsit.")


@router.post("", status_code=201)
def adauga_produs(produs: Produs):
    for p in inventar:
        if p.id == produs.id:
            raise HTTPException(status_code=400, detail=f"Produsul cu ID-ul {produs.id} există deja.")
    inventar.append(produs)
    return produs


@router.put("/{produs_id}")
def actualizeaza_produs(produs_id: int, produs_nou: Produs):
    for index, produs in enumerate(inventar):
        if produs.id == produs_id:
            inventar[index] = produs_nou
            return inventar[index]
    raise HTTPException(status_code=404, detail=f"Produsul cu ID-ul {produs_id} nu a fost găsit.")


@router.delete("/{produs_id}")
def sterge_produs(produs_id: int):
    for index, produs in enumerate(inventar):
        if produs.id == produs_id:
            sters = inventar.pop(index)
            return sters
    raise HTTPException(status_code=404, detail=f"Produsul cu ID-ul {produs_id} nu a fost găsit.")
