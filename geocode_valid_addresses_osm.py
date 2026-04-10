#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from georef_pipeline import DEFAULT_USER_AGENT, geocode_csv


DEFAULT_INPUT = Path("output/Georeferenziazione_perPROGRAMMA_validi.csv")
DEFAULT_OUTPUT = Path("output/Georeferenziazione_perPROGRAMMA_validi_geocoded.csv")
DEFAULT_CACHE = Path("output/nominatim_cache.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Geocodifica gli indirizzi validi tramite OpenStreetMap Nominatim "
            "e produce un CSV con coordinate e metadati del match."
        )
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help=f"CSV in input con gli indirizzi validi. Default: {DEFAULT_INPUT}",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"CSV in output con coordinate. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--cache",
        default=str(DEFAULT_CACHE),
        help=f"File JSON di cache delle query. Default: {DEFAULT_CACHE}",
    )
    parser.add_argument(
        "--email",
        help="Email da passare a Nominatim nelle richieste bulk. Consigliata.",
    )
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="User-Agent identificativo richiesto da Nominatim.",
    )
    parser.add_argument(
        "--country",
        default="Italia",
        help="Paese da usare nelle query. Default: Italia",
    )
    parser.add_argument(
        "--country-code",
        default="it",
        help="Country code ISO 3166-1 alpha-2 per limitare i risultati. Default: it",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.1,
        help="Attesa minima tra richieste consecutive. Default: 1.1",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Numero massimo di tentativi per query. Default: 3",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Processa solo le prime N righe del CSV.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Non chiama l'API: mostra le query che farebbe e genera l'output senza coordinate.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    cache_path = Path(args.cache)

    if not input_path.exists():
        raise FileNotFoundError(
            f"CSV input non trovato: {input_path}. Esegui prima analyze_georef_excel.py."
        )

    def progress(current: int, total: int, address: str, status: str) -> None:
        print(f"[{current}/{total}] {address} -> {status}", file=sys.stderr)

    result = geocode_csv(
        input_path,
        output_path,
        cache_path=cache_path,
        email=args.email,
        user_agent=args.user_agent,
        country=args.country,
        country_code=args.country_code,
        sleep_seconds=args.sleep_seconds,
        retries=args.retries,
        dry_run=args.dry_run,
        limit=args.limit,
        progress_callback=progress,
    )

    print(f"Input: {result['input_csv']}")
    print(f"Output: {result['output_csv']}")
    print(f"Cache: {result['cache_path']}")
    print(f"Righe processate: {result['rows']}")
    print(f"Match trovati: {result['matched']}")
    print(f"Non trovati: {result['not_found']}")
    if result["dry_run"]:
        print("Modalita dry-run: nessuna chiamata API eseguita.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
