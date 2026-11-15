"""Tiny helper to build and execute evidence notebooks reproducibly.

Each ``build_*.py`` declares cells as (kind, source) pairs; this module writes the
``.ipynb`` and executes it with nbclient in the repo root (so outputs are real).
"""
from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def md(text: str):
    return ("markdown", text.strip("\n"))


def code(text: str):
    return ("code", text.strip("\n"))


def build(cells, path: Path, execute: bool = True, timeout: int = 7200) -> Path:
    import nbformat
    from nbclient import NotebookClient

    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "sonora", "display_name": "SONORA (.venv)", "language": "python"}
    nb.metadata["language_info"] = {"name": "python"}
    for kind, src in cells:
        nb.cells.append(nbformat.v4.new_markdown_cell(src) if kind == "markdown" else nbformat.v4.new_code_cell(src))
    if execute:
        t0 = time.time()
        client = NotebookClient(nb, timeout=timeout, kernel_name="sonora",
                                resources={"metadata": {"path": str(ROOT)}})
        client.execute()
        print(f"Ejecutado en {time.time() - t0:.0f}s")
    path.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, path)
    return path


if __name__ == "__main__":
    sys.exit("Usa build_e1.py, build_e2.py, ...")
