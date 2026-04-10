#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from georef_pipeline import analyze_input_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analizza un file Excel o CSV di georeferenziazione, classifica le righe "
            "e genera report CSV/JSON."
        )
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        help="Percorso del file .xlsx/.csv. Se omesso usa l'unico .xlsx trovato nella cartella.",
    )
    parser.add_argument(
        "--sheet",
        help="Nome del foglio da analizzare. Se omesso usa il primo foglio.",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Cartella dove salvare i risultati. Default: output",
    )
    return parser.parse_args()


def resolve_input_file(explicit_path: str | None) -> Path:
    if explicit_path:
        path = Path(explicit_path)
        if not path.exists():
            raise FileNotFoundError(f"File non trovato: {path}")
        return path

    candidates = sorted(
        path
        for path in Path.cwd().iterdir()
        if path.suffix.lower() in {".xlsx", ".xlsm", ".csv"} and not path.name.startswith("~$")
    )
    if not candidates:
        raise FileNotFoundError("Nessun file .xlsx/.csv trovato nella cartella corrente.")
    if len(candidates) > 1:
        names = ", ".join(path.name for path in candidates)
        raise RuntimeError(
            f"Trovati piu file di input ({names}). Specificane uno come argomento."
        )
    return candidates[0]


def main() -> int:
    args = parse_args()
    input_file = resolve_input_file(args.input_file)
    output_dir = Path(args.output_dir)

    analysis = analyze_input_file(input_file, output_dir, sheet_name=args.sheet)
    print(f"Analisi completata: {input_file.resolve()}")
    print(f"Origine analizzata: {analysis['source_name']}")
    print(f"Righe dati: {len(analysis['records'])}")
    for category, records in analysis["categories"].items():
        print(f"- {category}: {len(records)}")
    print(f"Output salvati in: {output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
