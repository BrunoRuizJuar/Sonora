#!/usr/bin/env bash
# Compila KenLM (lmplz, build_binary, query) en WSL, FUERA del repositorio.
#   wsl -d Ubuntu-24.04 -- bash /ruta/montada/scripts/kenlm/build_kenlm.sh
# Requisito (sudo, una vez):
#   sudo apt-get install -y build-essential cmake libboost-system-dev libboost-thread-dev \
#     libboost-program-options-dev libboost-test-dev libeigen3-dev zlib1g-dev libbz2-dev liblzma-dev
set -euo pipefail
PREFIX="${KENLM_HOME:-$HOME/opt/kenlm}"
if [ ! -d "$PREFIX/.git" ]; then
  mkdir -p "$(dirname "$PREFIX")"
  git clone https://github.com/kpu/kenlm.git "$PREFIX"
fi
cd "$PREFIX"
git rev-parse HEAD > "$PREFIX/SONORA_COMMIT"
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DKENLM_MAX_ORDER=6 > cmake.log
make -j"$(nproc)" lmplz build_binary query > make.log
ls -l bin/lmplz bin/build_binary bin/query
echo "KenLM $(cat "$PREFIX/SONORA_COMMIT") listo en $PREFIX/build/bin"
