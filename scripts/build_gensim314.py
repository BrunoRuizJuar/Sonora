"""Regenerate Gensim 4.4.0's old generated C using current Cython.

Run after pip download gensim==4.4.0 --no-deps --no-binary gensim
  -d runtime/build-e5 and installing Cython>=3.1, setuptools, wheel.
Only the downloaded build copy in runtime is modified; no model sources change.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'runtime/build-e5'
archive = BUILD / 'gensim-4.4.0.tar.gz'
with tarfile.open(archive) as tar:
    tar.extractall(BUILD, filter='data')
source = BUILD / 'gensim-4.4.0'
fastss_url = 'https://raw.githubusercontent.com/piskvorky/gensim/4.4.0/gensim/similarities/fastss.pyx'
# Upstream sdist omits this source; recover it from the same release tag.
fastss = urllib.request.urlopen(fastss_url).read()
(source / 'gensim/similarities/fastss.pyx').write_bytes(fastss)
# setup.py detects missing generated sources and invokes cythonize itself.
# Touch only the ten explicit extension files from the upstream setup.py.
extensions = [
    'models/word2vec_inner.c', 'corpora/_mmreader.c', 'models/fasttext_inner.c',
    '_matutils.c', 'models/nmf_pgd.c', 'similarities/fastss.c',
    'models/doc2vec_inner.cpp', 'models/word2vec_corpusfile.cpp',
    'models/fasttext_corpusfile.cpp', 'models/doc2vec_corpusfile.cpp',
]
for rel in extensions:
    target = (source / 'gensim' / rel).resolve()
    assert target.is_relative_to(BUILD.resolve())
    target.unlink(missing_ok=True)
wheel_dir = BUILD / 'wheels'
subprocess.run([sys.executable, '-m', 'pip', 'wheel', str(source), '--no-deps',
                '--no-build-isolation', '-w', str(wheel_dir)], check=True)
wheel, = wheel_dir.glob('gensim-4.4.0-*.whl')
subprocess.run([sys.executable, '-m', 'pip', 'install', '--no-deps', str(wheel)], check=True)
import Cython
manifest = {'sdist_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'fastss_source': fastss_url, 'fastss_sha256': hashlib.sha256(fastss).hexdigest(),
            'wheel_sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
            'cython': Cython.__version__, 'python': sys.version,
            'generated_sources': extensions}
(BUILD / 'build_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
