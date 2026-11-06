#!/bin/sh
# Ovoz vositalarini o'rnatish: Earshot (+ real-sound skill) va opus-sound-layer, aniq versiyalarda.
#   sh video/sound/setup.sh [papka]        (default: ../sound-tools, ya'ni shu repo yonida)
# Windows'da Git Bash'dan. Korporativ tarmoqda pip uchun truststore, git uchun schannelCheckRevoke=false.
set -e
DEST="${1:-$(cd "$(dirname "$0")/../../.." && pwd)/sound-tools}"
EARSHOT_SHA=591fa3e028032e6dce56620a20e932e35667e8d8      # earshot 0.4.0
LAYER_SHA=52ac266a24b7dfd3cd06a28c34d5af360a8d7586        # opus-sound-layer, 2026-11
mkdir -p "$DEST" && cd "$DEST"

fetch() {  # repo sha folder
  [ -d "$3/.git" ] || git -c http.schannelCheckRevoke=false clone -q "https://github.com/$1" "$3"
  git -C "$3" -c http.schannelCheckRevoke=false fetch -q origin && git -C "$3" checkout -q "$2"
  echo "$3 @ $(git -C "$3" rev-parse --short HEAD)"
}
fetch Leonxlnx/earshot "$EARSHOT_SHA" earshot
fetch Bodila51/opus-sound-layer "$LAYER_SHA" opus-sound-layer

# Earshot: o'z venv'i, torch faqat CPU (GPU shart emas). Birinchi model ishlatilganda ~1.1 GB yuklanadi.
PY="${PYTHON:-python}"
if [ ! -x earshot/.venv/Scripts/python ] && [ ! -x earshot/.venv/bin/python ]; then "$PY" -m venv earshot/.venv; fi
EP=earshot/.venv/Scripts/python; [ -x "$EP" ] || EP=earshot/.venv/bin/python
PIPX="--use-feature=truststore"
"$EP" -m pip install -q $PIPX --upgrade pip
"$EP" -m pip install -q $PIPX torch --index-url https://download.pytorch.org/whl/cpu
"$EP" -m pip install -q $PIPX -e "./earshot[mcp,llm]"
# opus-sound-layer skriptlari uv o'rniga shu venv bilan ham ishlaydi (numpy, scipy, soundfile, pyloudnorm, matplotlib)
"$EP" -m pip install -q $PIPX numpy scipy soundfile pyloudnorm matplotlib
"$EP" -m earshot doctor || true
echo "EARSHOT_PY=$DEST/$EP"
echo "LAYER=$DEST/opus-sound-layer"
