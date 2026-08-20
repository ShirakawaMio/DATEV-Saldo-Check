#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Berechnet Konto-Bewegung und DATEV-Stapel-Saldo aus einer EXTF-CSV-Datei.

import argparse
import csv
import re
import sys
from decimal import Decimal
from pathlib import Path


AMOUNT_COLUMN = "Umsatz (ohne Soll/Haben-Kz)"
SIDE_COLUMN = "Soll/Haben-Kennzeichen"
ACCOUNT_COLUMN = "Konto"
COUNTERACCOUNT_COLUMN = "Gegenkonto (ohne BU-Schlüssel)"
DEFAULT_INPUT = Path(__file__).parent / "data" / (
    "EXTF_Buchungsstapel_Amazon_202607_20260805100008_1.csv"
)


def parse_amount(raw_value, *, line_number):
    # DATEV Buchungsstapel requires a positive, non-zero amount with two
    # decimal places and no thousands separator.
    value = raw_value.strip()
    if not re.fullmatch(r"(?!0{1,10},00$)\d{1,10},\d{2}", value):
        raise ValueError(
            f"Ungültiger DATEV-Betrag in CSV-Zeile {line_number}: "
            f"{raw_value!r}"
        )

    return Decimal(value.replace(",", "."))


def read_header(path, encoding):
    with path.open("r", encoding=encoding, newline="") as csv_file:
        reader = csv.reader(csv_file, delimiter=";", strict=True)
        try:
            next(reader)  # DATEV EXTF metadata row
            return next(reader)
        except StopIteration as exc:
            raise ValueError(
                "Die CSV-Datei enthält keine Metadaten- und Kopfzeile."
            ) from exc


def calculate_saldo(
    path,
    *,
    encoding,
    amount_column=AMOUNT_COLUMN,
    side_column=SIDE_COLUMN,
    account_column=ACCOUNT_COLUMN,
    counteraccount_column=COUNTERACCOUNT_COLUMN,
):
    # The S/H flag applies to Konto. A file must represent one Konto so its
    # movement can be checked as S minus H without mixing different accounts.
    account_totals = {"S": Decimal("0"), "H": Decimal("0")}
    counts = {"S": 0, "H": 0}
    accounts = set()

    with path.open("r", encoding=encoding, newline="") as csv_file:
        reader = csv.reader(csv_file, delimiter=";", strict=True)

        try:
            next(reader)  # DATEV EXTF metadata row
            header = next(reader)
        except StopIteration as exc:
            raise ValueError("Die CSV-Datei enthält keine Metadaten- und Kopfzeile.") from exc

        missing_columns = [
            column
            for column in (
                amount_column,
                side_column,
                account_column,
                counteraccount_column,
            )
            if column not in header
        ]
        if missing_columns:
            raise ValueError(f"Fehlende Spalten: {', '.join(missing_columns)}")

        amount_index = header.index(amount_column)
        side_index = header.index(side_column)
        account_index = header.index(account_column)
        counteraccount_index = header.index(counteraccount_column)
        required_index = max(
            amount_index,
            side_index,
            account_index,
            counteraccount_index,
        )

        for line_number, row in enumerate(reader, start=3):
            if not row or not any(cell.strip() for cell in row):
                continue
            if len(row) <= required_index:
                raise ValueError(f"Zu wenige Spalten in CSV-Zeile {line_number}.")

            side = row[side_index].strip()
            if side not in account_totals:
                raise ValueError(
                    f"Ungültiges Soll/Haben-Kennzeichen in CSV-Zeile "
                    f"{line_number}: {row[side_index]!r}"
                )

            account = row[account_index].strip()
            if not account:
                raise ValueError(f"Leeres Konto in CSV-Zeile {line_number}.")

            if not row[counteraccount_index].strip():
                raise ValueError(
                    f"Leeres Gegenkonto in CSV-Zeile {line_number}."
                )

            amount = parse_amount(row[amount_index], line_number=line_number)
            accounts.add(account)
            account_totals[side] += amount
            counts[side] += 1

    if not accounts:
        raise ValueError("Die CSV-Datei enthält keine Buchungen.")
    if len(accounts) != 1:
        raise ValueError(
            "Die CSV-Datei enthält mehrere Konten; "
            "ein gemeinsamer Saldo wäre nicht eindeutig."
        )

    return (
        next(iter(accounts)),
        account_totals["S"],
        account_totals["H"],
        counts["S"],
        counts["H"],
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
            "DATEV-CSV-Datei oder Ordner; Ordner werden rekursiv durchsucht "
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


def find_csv_files(input_path):
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        return sorted(
            path
            for path in input_path.rglob("*")
            if path.is_file() and path.suffix.lower() == ".csv"
        )
    raise FileNotFoundError(f"Datei oder Ordner nicht gefunden: {input_path}")


def sum_saldos(results):
    total = Decimal("0")
    for result in results:
        total += result[1] - result[2]
    return total


def print_result(path, result):
    (
        account,
        account_s_total,
        account_h_total,
        s_count,
        h_count,
    ) = result
    saldo = account_s_total - account_h_total
    print(f"Datei: {path}")
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


def run_gui():
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except ImportError as exc:
        print(f"GUI nicht verfügbar: {exc}", file=sys.stderr)
        return 2

    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(f"GUI konnte nicht gestartet werden: {exc}", file=sys.stderr)
        return 2

    root.title("DATEV Saldo prüfen")
    root.geometry("820x600")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(3, weight=1)

    path_var = tk.StringVar()
    encoding_var = tk.StringVar(value="iso-8859-1")
    amount_var = tk.StringVar(value=AMOUNT_COLUMN)
    side_var = tk.StringVar(value=SIDE_COLUMN)
    account_var = tk.StringVar(value=ACCOUNT_COLUMN)
    counteraccount_var = tk.StringVar(value=COUNTERACCOUNT_COLUMN)
    status_var = tk.StringVar(value="Datei oder Ordner auswählen.")
    column_combos = []

    def get_files():
        raw_path = path_var.get().strip()
        if not raw_path:
            raise ValueError("Bitte zuerst eine Datei oder einen Ordner auswählen.")
        files = find_csv_files(Path(raw_path))
        if not files:
            raise ValueError("Im ausgewählten Ordner wurden keine CSV-Dateien gefunden.")
        return files

    def show_error(message):
        status_var.set(message)
        messagebox.showerror("Fehler", message, parent=root)

    def load_columns():
        try:
            files = get_files()
            encoding = encoding_var.get().strip() or "iso-8859-1"
            header = read_header(files[0], encoding)
        except (OSError, UnicodeError, csv.Error, ValueError) as exc:
            show_error(str(exc))
            return

        for combo in column_combos:
            combo["values"] = header

        for variable, default in (
            (amount_var, AMOUNT_COLUMN),
            (side_var, SIDE_COLUMN),
            (account_var, ACCOUNT_COLUMN),
            (counteraccount_var, COUNTERACCOUNT_COLUMN),
        ):
            if variable.get() not in header:
                variable.set(default if default in header else header[0])

        status_var.set(
            f"{len(files)} Datei(en) gefunden; Spalten aus {files[0].name} geladen."
        )

    def choose_file():
        selected = filedialog.askopenfilename(
            title="CSV-Datei auswählen",
            filetypes=(("CSV-Dateien", "*.csv"), ("Alle Dateien", "*.*")),
        )
        if selected:
            path_var.set(selected)
            load_columns()

    def choose_folder():
        selected = filedialog.askdirectory(title="Ordner auswählen")
        if selected:
            path_var.set(selected)
            load_columns()

    def run_check():
        try:
            files = get_files()
            encoding = encoding_var.get().strip() or "iso-8859-1"
            amount_column = amount_var.get().strip()
            side_column = side_var.get().strip()
            account_column = account_var.get().strip()
            counteraccount_column = counteraccount_var.get().strip()
            if not all(
                (amount_column, side_column, account_column, counteraccount_column)
            ):
                raise ValueError("Bitte alle vier Spalten auswählen.")
        except (OSError, UnicodeError, csv.Error, ValueError) as exc:
            show_error(str(exc))
            return

        output.delete("1.0", tk.END)
        has_error = False
        has_imbalance = False
        is_folder = Path(path_var.get().strip()).is_dir()
        results = []

        for index, path in enumerate(files):
            if index:
                output.insert(tk.END, "\n")
            try:
                result = calculate_saldo(
                    path,
                    encoding=encoding,
                    amount_column=amount_column,
                    side_column=side_column,
                    account_column=account_column,
                    counteraccount_column=counteraccount_column,
                )
            except (OSError, UnicodeError, csv.Error, ValueError) as exc:
                output.insert(tk.END, f"Fehler in {path}: {exc}\n")
                has_error = True
                continue

            (
                account,
                account_s_total,
                account_h_total,
                s_count,
                h_count,
            ) = result
            saldo = account_s_total - account_h_total
            results.append(result)
            output.insert(tk.END, f"Datei: {path}\n")
            output.insert(tk.END, f"Konto: {account}\n")
            output.insert(
                tk.END,
                f"Konto-Summe S ({s_count} Buchungen): {account_s_total:.2f} EUR\n",
            )
            output.insert(
                tk.END,
                f"Konto-Summe H ({h_count} Buchungen): {account_h_total:.2f} EUR\n",
            )
            output.insert(tk.END, f"Saldo (S - H): {saldo:.2f} EUR\n")
            if saldo == 0:
                output.insert(tk.END, f"Prüfung: OK — Saldo = {saldo:.2f} EUR\n")
            else:
                output.insert(
                    tk.END,
                    f"Prüfung: FEHLER — Saldo = {saldo:.2f} EUR "
                    "statt 0.00 EUR\n",
                )
                has_imbalance = True

        if is_folder:
            total_saldo = sum_saldos(results)
            output.insert(tk.END, "\n")
            output.insert(tk.END, f"Summe aller Saldo: {total_saldo:.2f} EUR\n")
            if total_saldo == 0 and not has_error:
                output.insert(
                    tk.END,
                    f"Gesamtprüfung: OK — Summe aller Saldo = "
                    f"{total_saldo:.2f} EUR\n",
                )
            else:
                output.insert(
                    tk.END,
                    f"Gesamtprüfung: FEHLER — Summe aller Saldo = "
                    f"{total_saldo:.2f} EUR statt 0.00 EUR\n",
                )

        if has_error:
            status_var.set("Fertig: Mindestens eine Datei konnte nicht geprüft werden.")
        elif has_imbalance:
            status_var.set("Fertig: Mindestens eine Datei ist nicht ausgeglichen.")
        else:
            status_var.set(f"Fertig: {len(files)} Datei(en) geprüft, alle OK.")

        output.see(tk.END)

    path_frame = tk.Frame(root)
    path_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
    path_frame.columnconfigure(0, weight=1)
    tk.Label(path_frame, text="Datei/Ordner:").grid(row=0, column=0, sticky="w")
    tk.Entry(path_frame, textvariable=path_var).grid(
        row=1, column=0, sticky="ew", padx=(0, 4)
    )
    tk.Button(path_frame, text="Datei", command=choose_file).grid(
        row=1, column=1, padx=2
    )
    tk.Button(path_frame, text="Ordner", command=choose_folder).grid(
        row=1, column=2, padx=2
    )

    options_frame = tk.Frame(root)
    options_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
    tk.Label(options_frame, text="Encoding:").grid(row=0, column=0, sticky="w")
    tk.Entry(options_frame, textvariable=encoding_var, width=18).grid(
        row=0, column=1, sticky="w", padx=(4, 0)
    )

    columns_frame = tk.LabelFrame(root, text="CSV-Spalten")
    columns_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
    column_specs = (
        ("Betrag:", amount_var),
        ("S/H:", side_var),
        ("Konto:", account_var),
        ("Gegenkonto:", counteraccount_var),
    )
    for row, (label, variable) in enumerate(column_specs):
        tk.Label(columns_frame, text=label, width=14, anchor="w").grid(
            row=row, column=0, padx=4, pady=2, sticky="w"
        )
        combo = ttk.Combobox(
            columns_frame, textvariable=variable, state="readonly", width=72
        )
        combo.grid(row=row, column=1, padx=4, pady=2, sticky="ew")
        column_combos.append(combo)
    columns_frame.columnconfigure(1, weight=1)

    button_frame = tk.Frame(root)
    button_frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 4))
    button_frame.rowconfigure(1, weight=1)
    button_frame.columnconfigure(0, weight=1)
    tk.Button(button_frame, text="Spalten laden", command=load_columns).grid(
        row=0, column=0, sticky="w", pady=(0, 4)
    )
    output = tk.Text(button_frame, height=18, wrap="none")
    output.grid(row=1, column=0, sticky="nsew")

    footer = tk.Frame(root)
    footer.grid(row=4, column=0, sticky="ew", padx=8, pady=8)
    tk.Label(footer, textvariable=status_var, anchor="w").pack(side="left", fill="x", expand=True)
    tk.Button(footer, text="Prüfen", command=run_check).pack(side="right")

    root.mainloop()
    return 0


def main():
    args = build_parser().parse_args()

    if args.gui:
        return run_gui()

    try:
        files = find_csv_files(args.input_path)
    except OSError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2

    if not files:
        print(f"Fehler: Keine CSV-Dateien gefunden: {args.input_path}", file=sys.stderr)
        return 2

    has_error = False
    has_imbalance = False
    is_folder = args.input_path.is_dir()
    results = []
    for index, path in enumerate(files):
        if index:
            print()
        try:
            result = calculate_saldo(path, encoding=args.encoding)
        except (OSError, UnicodeError, csv.Error, ValueError) as exc:
            print(f"Fehler in {path}: {exc}", file=sys.stderr)
            has_error = True
            continue

        results.append(result)
        if not print_result(path, result):
            has_imbalance = True

    if is_folder:
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
