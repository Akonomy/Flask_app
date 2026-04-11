# Gestionar de sarcini — Lab 02 + Lab 03 + Lab 04

**Repository:** [https://github.com/Akonomy/Flask_app](https://github.com/Akonomy/Flask_app)

API REST construit cu FastAPI + SQLite, cu interfață web SPA. Acoperă trei laboratoare:
- **Lab 02** — CRUD produse, in-memory, fără autentificare
- **Lab 03** — Înregistrare/autentificare JWT, CRUD sarcini cu SQLite
- **Lab 04** — Interfață web SPA (HTML + Bootstrap + fetch)

---

## Cuprins

1. [Pornirea aplicației](#1-pornirea-aplicației)
2. [Structura proiectului](#2-structura-proiectului)
3. [Lab 02 — Produse](#3-lab-02--produse)
4. [Lab 03 — Autentificare și sarcini](#4-lab-03--autentificare-și-sarcini)
5. [Lab 04 — Interfața web](#5-lab-04--interfața-web)
6. [Referință rapidă endpoint-uri](#6-referință-rapidă-endpoint-uri)

---

## 1. Pornirea aplicației

### Cerințe

- Linux (orice distribuție)
- Python 3.10 sau mai nou
- Git

### Pași

**1. Clonează repository-ul**

```bash
git clone https://github.com/Akonomy/Flask_app
cd Flask_app
```

**2. Dă permisiuni de execuție scriptului**

```bash
chmod +x start.sh
```

**3. Rulează scriptul**

```bash
./start.sh
```

Scriptul face automat, în ordine:
1. Detectează `python3` instalat pe sistem
2. Creează un mediu virtual în folderul `.venv` (doar la primul rulaj)
3. Activează mediul virtual
4. Actualizează `pip` și instalează toate pachetele din `requirements.txt`
5. Pornește serverul `uvicorn` pe portul `8090`, cu `--reload` (repornire automată la modificări)

La pornire corectă vei vedea în terminal:

```
[+] Folosesc: Python 3.x.x
[+] Mediul virtual există deja — îl refolosesc.
[+] Instalez dependențele din requirements.txt...
[+] Pornesc serverul pe http://localhost:8090

  API:      http://localhost:8090
  Docs:     http://localhost:8090/docs
  Frontend: deschide index.html cu Live Server din VS Code

[!] Apasă Ctrl+C pentru a opri serverul.

INFO:     Uvicorn running on http://0.0.0.0:8090
```

**4. Verifică că serverul funcționează**

Deschide în browser: [http://localhost:8090](http://localhost:8090)

Trebuie să apară un tabel cu toate rutele disponibile.

**5. Oprirea serverului**

```bash
Ctrl+C
```

> **Notă:** La al doilea rulaj `./start.sh` sare peste crearea venv-ului și merge direct la instalarea dependențelor + pornirea serverului.

---

## 2. Structura proiectului

```
Flask_app/
├── src/
│   ├── main.py              # Aplicația FastAPI, CORS, ruta /
│   ├── auth.py              # JWT, bcrypt, get_utilizator_curent
│   ├── database.py          # SQLite, creare tabele, get_db
│   ├── models.py            # Modele Pydantic (validare date)
│   └── routers/
│       ├── produse.py       # Lab 02 — CRUD produse in-memory
│       ├── utilizatori.py   # Lab 03 — înregistrare, autentificare
│       └── sarcini.py       # Lab 03 — CRUD sarcini
├── index.html               # Lab 04 — interfață web SPA
├── requirements.txt         # Dependențe Python
├── start.sh                 # Script de pornire
├── .gitignore               # Exclude venv, __pycache__, .db
└── README.md
```

Baza de date `sarcini.db` se creează automat în folderul `Flask_app/` la primul start. Nu este inclusă în git.

---

## 3. Lab 02 — Produse

### Despre

CRUD complet pentru o listă de produse stocată **în memorie** (nu în baza de date). Datele se pierd la repornirea serverului. Nu necesită autentificare.

Toate cererile se pot testa din **Swagger UI**: [http://localhost:8090/docs](http://localhost:8090/docs)

---

### 3.1 Adăugare produs — `POST /produse`

**Swagger UI:**
1. Mergi la [http://localhost:8090/docs](http://localhost:8090/docs)
2. Click pe `POST /produse` → `Try it out`
3. În câmpul `Request body` înlocuiește conținutul cu:
```json
{
  "id": 1,
  "nume": "Laptop",
  "pret": 3500.00,
  "stoc": 10
}
```
4. Click `Execute`
5. Răspuns așteptat — `201 Created`:
```json
{
  "id": 1,
  "nume": "Laptop",
  "pret": 3500.0,
  "stoc": 10
}
```

Adaugă încă un produs pentru teste ulterioare:
```json
{
  "id": 2,
  "nume": "Mouse",
  "pret": 75.50,
  "stoc": 50
}
```

---

### 3.2 Lista tuturor produselor — `GET /produse`

**Swagger UI:**
1. Click pe `GET /produse` → `Try it out` → `Execute`
2. Răspuns așteptat — `200 OK`:
```json
[
  { "id": 1, "nume": "Laptop", "pret": 3500.0, "stoc": 10 },
  { "id": 2, "nume": "Mouse", "pret": 75.5, "stoc": 50 }
]
```

**Browser direct:** [http://localhost:8090/produse](http://localhost:8090/produse)

---

### 3.3 Detalii produs după ID — `GET /produse/{id}`

**Swagger UI:**
1. Click pe `GET /produse/{produs_id}` → `Try it out`
2. În câmpul `produs_id` scrie `1`
3. Click `Execute`
4. Răspuns așteptat — `200 OK`:
```json
{ "id": 1, "nume": "Laptop", "pret": 3500.0, "stoc": 10 }
```

**Caz de eroare:** Introdu `id = 999` → răspuns `404 Not Found`:
```json
{ "detail": "Produsul cu ID-ul 999 nu a fost găsit." }
```

---

### 3.4 Actualizare produs — `PUT /produse/{id}`

**Swagger UI:**
1. Click pe `PUT /produse/{produs_id}` → `Try it out`
2. `produs_id` = `1`
3. Body:
```json
{
  "id": 1,
  "nume": "Laptop Pro",
  "pret": 4200.00,
  "stoc": 5
}
```
4. Răspuns așteptat — `200 OK` cu datele actualizate.

---

### 3.5 Ștergere produs — `DELETE /produse/{id}`

**Swagger UI:**
1. Click pe `DELETE /produse/{produs_id}` → `Try it out`
2. `produs_id` = `2`
3. Răspuns așteptat — `200 OK` cu produsul șters.
4. Verifică cu `GET /produse` — Mouse-ul nu mai apare.

**Caz de eroare:** Încearcă să ștergi din nou `id = 2` → `404 Not Found`.

---

### 3.6 Eroare — ID duplicat la adăugare

Încearcă să adaugi un produs cu `id = 1` (deja există):
```json
{ "id": 1, "nume": "Alt produs", "pret": 100, "stoc": 1 }
```
Răspuns așteptat — `400 Bad Request`:
```json
{ "detail": "Produsul cu ID-ul 1 există deja." }
```

---

## 4. Lab 03 — Autentificare și sarcini

### Despre

Sistem complet de autentificare cu JWT și CRUD pentru sarcini personalizate per utilizator, stocate în SQLite. Sarcina unui utilizator nu este vizibilă altui utilizator.

Tokenul JWT expiră în **30 de minute**. La expirare trebuie să te autentifici din nou.

---

### 4.1 Înregistrare utilizator — `POST /inregistrare`

**Swagger UI:**
1. Click pe `POST /inregistrare` → `Try it out`
2. Body:
```json
{
  "email": "test@exemplu.com",
  "parola": "parola123"
}
```
3. Răspuns așteptat — `201 Created`:
```json
{ "mesaj": "Utilizatorul test@exemplu.com a fost înregistrat cu succes." }
```

**Cazuri de eroare:**
- Email deja înregistrat → `400 Bad Request`: `"Adresa de email este deja înregistrată."`
- Parolă sub 8 caractere → `422 Unprocessable Entity` (validare Pydantic)
- Email invalid (fără `@`) → `422 Unprocessable Entity`

Înregistrează un al doilea utilizator pentru a testa izolarea datelor:
```json
{
  "email": "alt@exemplu.com",
  "parola": "altparola123"
}
```

---

### 4.2 Autentificare și obținere token — `POST /autentificare`

**Swagger UI:**
1. Click pe `POST /autentificare` → `Try it out`
2. Completează câmpurile:
   - `username`: `test@exemplu.com`
   - `password`: `parola123`
   *(câmpul se numește `username` — este standardul OAuth2)*
3. Click `Execute`
4. Răspuns așteptat — `200 OK`:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```
5. Copiază valoarea din `access_token`.

**Caz de eroare:** Parolă greșită → `401 Unauthorized`: `"Email sau parolă incorectă."`

---

### 4.3 Autorizare globală în Swagger UI

Pentru a nu introduce tokenul la fiecare cerere:

1. În Swagger UI, click pe butonul `Authorize` (sus-dreapta, iconiță lacăt)
2. În câmpul `Value` scrie: `Bearer eyJhbGci...` (tokenul tău complet)
3. Click `Authorize` → `Close`

De acum toate cererile din Swagger UI includ automat headerul `Authorization: Bearer <token>`.

---

### 4.4 Creare sarcină — `POST /sarcini`

*(necesită autorizare — vezi 4.3)*

**Swagger UI:**
1. Click pe `POST /sarcini` → `Try it out`
2. Body:
```json
{
  "titlu": "Cumpărături",
  "descriere": "Lapte, pâine, ouă"
}
```
3. Răspuns așteptat — `201 Created`:
```json
{
  "id": 1,
  "titlu": "Cumpărături",
  "descriere": "Lapte, pâine, ouă",
  "finalizata": 0,
  "utilizator_id": 1
}
```

Adaugă mai multe sarcini pentru teste:
```json
{ "titlu": "Temă laborator", "descriere": "FastAPI + SQLite" }
{ "titlu": "Sport", "descriere": null }
```

---

### 4.5 Lista sarcini — `GET /sarcini`

**Swagger UI:**
1. Click pe `GET /sarcini` → `Try it out` → `Execute`
2. Răspuns așteptat — `200 OK` cu array-ul sarcinilor utilizatorului curent.

**Fără token:** Răspuns `401 Unauthorized` — demonstrează că endpoint-ul este protejat.

---

### 4.6 Lista sarcini nefinalizate — `GET /sarcini?doar_nefinalizate=true`

**Swagger UI:**
1. Click pe `GET /sarcini` → `Try it out`
2. În câmpul `doar_nefinalizate` selectează / scrie `true`
3. Click `Execute`
4. Răspuns — doar sarcinile cu `finalizata = 0`.

---

### 4.7 Detalii sarcină — `GET /sarcini/{id}`

**Swagger UI:**
1. Click pe `GET /sarcini/{sarcina_id}` → `Try it out`
2. `sarcina_id` = `1`
3. Răspuns așteptat — `200 OK` cu datele sarcinii.

**Caz de eroare:** ID care nu aparține utilizatorului curent → `404 Not Found`.

---

### 4.8 Actualizare sarcină — `PUT /sarcini/{id}`

**Swagger UI:**
1. Click pe `PUT /sarcini/{sarcina_id}` → `Try it out`
2. `sarcina_id` = `1`
3. Body (toate câmpurile sunt opționale — trimite doar ce vrei să modifici):
```json
{
  "titlu": "Cumpărături săptămânale",
  "descriere": "Lapte, pâine, ouă, brânză"
}
```
4. Răspuns așteptat — `200 OK` cu datele actualizate.

---

### 4.9 Finalizare sarcină — `PATCH /sarcini/{id}/finaliza`

**Swagger UI:**
1. Click pe `PATCH /sarcini/{sarcina_id}/finaliza` → `Try it out`
2. `sarcina_id` = `1`
3. Click `Execute`
4. Răspuns așteptat — `200 OK`:
```json
{
  "id": 1,
  "titlu": "Cumpărături săptămânale",
  "finalizata": 1,
  ...
}
```
5. Verifică cu `GET /sarcini?doar_nefinalizate=true` — sarcina finalizată nu mai apare.

---

### 4.10 Ștergere sarcină — `DELETE /sarcini/{id}`

**Swagger UI:**
1. Click pe `DELETE /sarcini/{sarcina_id}` → `Try it out`
2. `sarcina_id` = `3` (sarcina "Sport")
3. Răspuns așteptat — `200 OK`:
```json
{ "mesaj": "Sarcina cu ID-ul 3 a fost ștearsă." }
```
4. Verifică cu `GET /sarcini` — sarcina nu mai apare.

---

### 4.11 Testarea izolării între utilizatori

1. Autentifică-te cu `alt@exemplu.com` și obține un token nou.
2. Autorizează Swagger UI cu noul token (butonul `Authorize`).
3. Rulează `GET /sarcini` — lista este goală (utilizatorul nu are sarcini proprii).
4. Adaugă o sarcină cu al doilea utilizator.
5. Revino la primul utilizator (re-autorizează cu tokenul lui) — sarcina celui de-al doilea nu apare.

---

### 4.12 Testarea expirării tokenului

Tokenul expiră după 30 de minute. La expirare, orice cerere autentificată returnează:
```json
{ "detail": "Token expirat. Autentificați-vă din nou." }
```
Soluție: re-autentificare via `POST /autentificare` și actualizarea tokenului în `Authorize`.

---

## 5. Lab 04 — Interfața web

### Despre

Fișierul `index.html` este o aplicație SPA (Single Page Application) care comunică cu API-ul via `fetch()` din browser. Nu necesită instalare suplimentară — se deschide direct.

### Cerință: serverul FastAPI trebuie să ruleze

Înainte de orice, asigură-te că `./start.sh` rulează în terminal.

---

### 5.1 Deschiderea interfeței

**Metoda 1 — Live Server (recomandat):**
1. Deschide folderul `Flask_app` în VS Code
2. Instalează extensia `Live Server` (ID: `ritwickdey.liveserver`) dacă nu este instalată
3. Click dreapta pe `index.html` în panoul Explorer → `Open with Live Server`
4. Browserul deschide automat `http://localhost:5500/index.html`
5. Orice modificare salvată în `index.html` reîncarcă pagina automat

**Metoda 2 — deschidere directă:**
1. Dublu-click pe `index.html` în file manager
2. Browserul îl deschide cu protocolul `file://`
3. Funcționează deoarece `"null"` este inclus în `allow_origins` din `main.py`

---

### 5.2 Înregistrare cont nou

1. La deschidere apare formularul de **Înregistrare**
2. Completează:
   - Email: `utilizator@test.com`
   - Parolă: `parola123` (minim 8 caractere)
3. Click `Înregistrează-te`
4. Apare mesajul verde *"Cont creat! Te poți autentifica."*
5. După 1.5 secunde, formularul comută automat pe **Autentificare**

**Erori vizibile în interfață:**
- Email deja înregistrat → casetă roșie cu mesajul de eroare
- Nu se poate contacta serverul (uvicorn oprit) → casetă roșie

---

### 5.3 Autentificare

1. Pe formularul de Autentificare completează email-ul și parola
2. Click `Conectează-te`
3. La autentificare reușită:
   - Formularul dispare
   - Apare secțiunea **Sarcinile mele**
   - În navbar apar email-ul utilizatorului și butonul `Deconectare`
4. Tokenul JWT este salvat automat în `localStorage` al browserului

**Verificare localStorage** (DevTools → `F12` → tab `Application` → `Local Storage` → `http://localhost:5500`):
- Cheia `token` conține tokenul JWT

---

### 5.4 Adăugare sarcini

1. În câmpul `Titlu` scrie `Prima sarcină`
2. În `Descriere` (opțional) scrie `O descriere scurtă`
3. Click `Adaugă`
4. Sarcina apare imediat în listă cu badge-ul gri **În progres**
5. Câmpurile se golesc automat

Adaugă încă 2 sarcini pentru a testa toate funcționalitățile:
- `A doua sarcină` (fără descriere)
- `A treia sarcină` cu descriere

---

### 5.5 Finalizare sarcină

1. Click pe `Finalizează` lângă `Prima sarcină`
2. Badge-ul se schimbă din gri **În progres** în verde **Finalizată**
3. Butonul `Finalizează` devine dezactivat (nu se poate finaliza de două ori)

---

### 5.6 Filtrul „doar nefinalizate"

1. Bifează checkbox-ul `Afișează doar sarcinile nefinalizate`
2. `Prima sarcină` (finalizată) dispare din listă
3. Debifează → toate sarcinile repar

---

### 5.7 Editare sarcină

1. Click pe `Editează` lângă `A doua sarcină`
2. Titlul și descrierea se transformă în câmpuri de text editabile, pre-completate
3. Modifică titlul în `A doua sarcină — editată`
4. Click `Salvează`
5. Lista se reîncarcă cu titlul actualizat
6. Click `Anulează` dacă vrei să renunți la modificări

---

### 5.8 Căutare locală după titlu

1. În câmpul `Caută după titlu...` scrie `treia`
2. Lista se filtrează instant (fără cerere nouă la server) — apare doar `A treia sarcină`
3. Golește câmpul → toate sarcinile repar

---

### 5.9 Ștergere sarcină cu confirmare

1. Click pe `Șterge` lângă `A treia sarcină`
2. Apare dialogul de confirmare: *"Ești sigur că vrei să ștergi această sarcină?"*
3. Click `OK` → sarcina dispare din listă
4. Click `Anulează` → sarcina rămâne

---

### 5.10 Persistența datelor

1. Reîncarcă pagina (`F5`)
2. Sarcinile rămân — sunt salvate în `sarcini.db`, nu în memorie
3. Tokenul din `localStorage` este citit automat → nu e nevoie să te autentifici din nou

---

### 5.11 Deconectare

1. Click pe `Deconectare` în navbar
2. Tokenul este șters din `localStorage`
3. Aplicația revine la ecranul de autentificare
4. Dacă reîncarci pagina, rămâi pe ecranul de autentificare (token șters)

---

### 5.12 Inspecția cererilor HTTP (DevTools)

1. Apasă `F12` → tab **Network**
2. Efectuează orice operație (adaugă sarcină, finalizează etc.)
3. În lista de cereri apare cererea `fetch` către `localhost:8090`
4. Click pe cerere → poți vedea:
   - **Headers**: metoda, URL, `Authorization: Bearer ...`
   - **Payload**: corpul JSON trimis
   - **Response**: răspunsul complet al serverului

---

## 6. Referință rapidă endpoint-uri

| Lab | Metodă | Endpoint | Auth | Descriere |
|-----|--------|----------|------|-----------|
| — | GET | `/` | Nu | Pagina cu toate rutele |
| — | GET | `/docs` | Nu | Swagger UI |
| — | GET | `/redoc` | Nu | ReDoc |
| Lab 02 | GET | `/produse` | Nu | Lista produselor |
| Lab 02 | GET | `/produse/{id}` | Nu | Detalii produs |
| Lab 02 | POST | `/produse` | Nu | Adăugare produs |
| Lab 02 | PUT | `/produse/{id}` | Nu | Actualizare produs |
| Lab 02 | DELETE | `/produse/{id}` | Nu | Ștergere produs |
| Lab 03 | POST | `/inregistrare` | Nu | Înregistrare utilizator |
| Lab 03 | POST | `/autentificare` | Nu | Obținere token JWT |
| Lab 03 | GET | `/sarcini` | JWT | Lista sarcinilor |
| Lab 03 | GET | `/sarcini?doar_nefinalizate=true` | JWT | Doar nefinalizate |
| Lab 03 | GET | `/sarcini/{id}` | JWT | Detalii sarcină |
| Lab 03 | POST | `/sarcini` | JWT | Creare sarcină |
| Lab 03 | PUT | `/sarcini/{id}` | JWT | Actualizare sarcină |
| Lab 03 | PATCH | `/sarcini/{id}/finaliza` | JWT | Marcare finalizată |
| Lab 03 | DELETE | `/sarcini/{id}` | JWT | Ștergere sarcină |
| Lab 04 | — | `index.html` | — | Interfață web SPA |
