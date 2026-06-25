#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "== FullTrack Manager: setup Linux =="

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERRO: python3 nao encontrado. Instale com: sudo apt install python3 python3-venv python3-pip"
  exit 1
fi

if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

. venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo
echo "== Verificando navegador =="
if command -v chromium-browser >/dev/null 2>&1; then
  echo "OK: chromium-browser -> $(command -v chromium-browser)"
elif command -v chromium >/dev/null 2>&1; then
  echo "OK: chromium -> $(command -v chromium)"
elif command -v google-chrome >/dev/null 2>&1; then
  echo "OK: google-chrome -> $(command -v google-chrome)"
elif command -v google-chrome-stable >/dev/null 2>&1; then
  echo "OK: google-chrome-stable -> $(command -v google-chrome-stable)"
else
  echo "AVISO: Chrome/Chromium nao encontrado."
  echo "Ubuntu/Debian: sudo apt install chromium chromium-driver"
fi

if command -v chromedriver >/dev/null 2>&1; then
  echo "OK: chromedriver -> $(command -v chromedriver)"
else
  echo "AVISO: chromedriver nao encontrado."
  echo "Ubuntu/Debian: sudo apt install chromium-driver"
fi

echo
echo "Setup concluido."
echo "Para rodar:"
echo "  source venv/bin/activate"
echo "  python3 app.py"
