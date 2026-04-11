#!/usr/bin/env bash
set -e

PORT=8090
VENV_DIR=".venv"

# ── culori ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[+]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*"; exit 1; }

# ── python ───────────────────────────────────────────────────────────────────
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    error "Python nu a fost găsit. Instalează python3 și încearcă din nou."
fi

info "Folosesc: $($PYTHON --version)"

# ── venv ─────────────────────────────────────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    info "Creez mediul virtual în '$VENV_DIR'..."
    $PYTHON -m venv "$VENV_DIR"
else
    info "Mediul virtual există deja — îl refolosesc."
fi

# ── activare ─────────────────────────────────────────────────────────────────
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# ── dependențe ───────────────────────────────────────────────────────────────
if [ -f "requirements.txt" ]; then
    info "Instalez dependențele din requirements.txt..."
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
else
    error "Nu am găsit requirements.txt în directorul curent."
fi

# ── baza de date (creare automată la primul start) ───────────────────────────
info "Verific baza de date (se creează automat dacă nu există)..."

# ── pornire server ────────────────────────────────────────────────────────────
info "Pornesc serverul pe http://localhost:${PORT}"
echo ""
echo -e "  API:      ${GREEN}http://localhost:${PORT}${NC}"
echo -e "  Docs:     ${GREEN}http://localhost:${PORT}/docs${NC}"
echo -e "  Frontend: ${GREEN}deschide index.html cu Live Server din VS Code${NC}"
echo ""
warn "Apasă Ctrl+C pentru a opri serverul."
echo ""

uvicorn src.main:app --reload --host 0.0.0.0 --port "$PORT"
