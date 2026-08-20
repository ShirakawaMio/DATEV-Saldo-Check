#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

import argparse
import csv
import sys
import zipfile
from pathlib import Path

from core import (
    calculate_saldo,
    find_csv_files,
    is_collection_input,
    source_label,
    sum_saldos,
)


DEFAULT_INPUT = Path(__file__).parent / "data" / (
    "EXTF_Buchungsstapel_Amazon_202607_20260805100008_1.csv"
)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Berechnet den Saldo eines Kontos in einem DATEV-Buchungsstapel "
            "als Summe Soll minus Summe Haben."
        )
    )
    parser.add_argument(
        "input_path",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT,
        help=(
            "DATEV-CSV-Datei, ZIP-Archiv oder Ordner; Ordner werden rekursiv "
            "durchsucht "
            f"(Standard: {DEFAULT_INPUT.name})"
        ),
    )
    parser.add_argument(
        "--encoding",
        default="iso-8859-1",
        help="Dateikodierung (Standard: iso-8859-1)",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Einfache grafische Oberfläche zum Auswählen von Pfad und Spalten",
    )
    return parser


def print_result(path, result):
    (
        account,
        account_s_total,
        account_h_total,
        s_count,
        h_count,
    ) = result
    saldo = account_s_total - account_h_total
    print(f"Datei: {source_label(path)}")
    print(f"Konto: {account}")
    print(
        f"Konto-Summe S ({s_count} Buchungen): "
        f"{account_s_total:.2f} EUR"
    )
    print(
        f"Konto-Summe H ({h_count} Buchungen): "
        f"{account_h_total:.2f} EUR"
    )
    print(f"Saldo (S - H): {saldo:.2f} EUR")

    if saldo == 0:
        print(f"Prüfung: OK — Saldo = {saldo:.2f} EUR")
        return True

    print(f"Prüfung: FEHLER — Saldo = {saldo:.2f} EUR statt 0.00 EUR")
    return False


def main():
    args = build_parser().parse_args()

    if args.gui:
        from ui import run_gui

        return run_gui()

    try:
        files = find_csv_files(args.input_path)
    except (OSError, zipfile.BadZipFile) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2

    if not files:
        print(f"Fehler: Keine CSV-Dateien gefunden: {args.input_path}", file=sys.stderr)
        return 2

    has_error = False
    has_imbalance = False
    is_collection = is_collection_input(args.input_path)
    results = []
    for index, path in enumerate(files):
        if index:
            print()
        try:
            result = calculate_saldo(path, encoding=args.encoding)
        except (
            OSError,
            UnicodeError,
            csv.Error,
            ValueError,
            zipfile.BadZipFile,
        ) as exc:
            print(f"Fehler in {source_label(path)}: {exc}", file=sys.stderr)
            has_error = True
            continue

        results.append(result)
        if not print_result(path, result):
            has_imbalance = True

    if is_collection:
        total_saldo = sum_saldos(results)
        print()
        print(f"Summe aller Saldo: {total_saldo:.2f} EUR")
        if total_saldo == 0 and not has_error:
            print(
                f"Gesamtprüfung: OK — Summe aller Saldo = "
                f"{total_saldo:.2f} EUR"
            )
        else:
            print(
                f"Gesamtprüfung: FEHLER — Summe aller Saldo = "
                f"{total_saldo:.2f} EUR statt 0.00 EUR"
            )

    if has_error:
        return 2
    if has_imbalance:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
