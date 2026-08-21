import csv
import sys
import zipfile
from pathlib import Path

from core import (
    ACCOUNT_COLUMN,
    AMOUNT_COLUMN,
    COUNTERACCOUNT_COLUMN,
    DEFAULT_TARGET_COUNTERACCOUNT,
    DOCUMENT_DATE_COLUMN,
    SIDE_COLUMN,
    analyze_saldo,
    find_csv_files,
    is_collection_input,
    read_header,
    source_label,
    sum_counteraccount_entries,
    sum_saldos,
)


def short_source_label(source):
    if isinstance(source, tuple):
        archive_path, member_name = source
        return f"{archive_path.name}::{Path(member_name).name}"

    source_path = Path(source)
    if source_path.parent.name:
        return f"{source_path.parent.name}/{source_path.name}"
    return source_path.name


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
    document_date_var = tk.StringVar(value=DOCUMENT_DATE_COLUMN)
    target_counteraccount_var = tk.StringVar(
        value=DEFAULT_TARGET_COUNTERACCOUNT
    )
    status_var = tk.StringVar(value="Datei oder Ordner auswählen.")
    column_combos = []

    def get_files():
        raw_path = path_var.get().strip()
        if not raw_path:
            raise ValueError("Bitte zuerst eine Datei oder einen Ordner auswählen.")
        files = find_csv_files(Path(raw_path))
        if not files:
            raise ValueError(
                "Im ausgewählten Ordner oder ZIP-Archiv wurden keine "
                "CSV-Dateien gefunden."
            )
        return files

    def show_error(message):
        status_var.set(message)
        messagebox.showerror("Fehler", message, parent=root)

    def load_columns():
        try:
            files = get_files()
            encoding = encoding_var.get().strip() or "iso-8859-1"
            header = read_header(files[0], encoding)
        except (
            OSError,
            UnicodeError,
            csv.Error,
            ValueError,
            zipfile.BadZipFile,
        ) as exc:
            show_error(str(exc))
            return

        for combo in column_combos:
            combo["values"] = header

        for variable, default in (
            (amount_var, AMOUNT_COLUMN),
            (side_var, SIDE_COLUMN),
            (account_var, ACCOUNT_COLUMN),
            (counteraccount_var, COUNTERACCOUNT_COLUMN),
            (document_date_var, DOCUMENT_DATE_COLUMN),
        ):
            if variable.get() not in header:
                variable.set(default if default in header else header[0])

        status_var.set(
            f"{len(files)} Datei(en) gefunden; Spalten aus "
            f"{short_source_label(files[0])} geladen."
        )

    def choose_file():
        selected = filedialog.askopenfilename(
            title="CSV- oder ZIP-Datei auswählen",
            filetypes=(
                ("CSV-Dateien", "*.csv"),
                ("ZIP-Dateien", "*.zip"),
                ("Alle Dateien", "*.*"),
            ),
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
            document_date_column = document_date_var.get().strip()
            target_counteraccount = target_counteraccount_var.get().strip()
            if not all(
                (
                    amount_column,
                    side_column,
                    account_column,
                    counteraccount_column,
                    document_date_column,
                )
            ):
                raise ValueError("Bitte alle fünf Spalten auswählen.")
            if not target_counteraccount:
                raise ValueError("Das zu prüfende Gegenkonto darf nicht leer sein.")
        except (
            OSError,
            UnicodeError,
            csv.Error,
            ValueError,
            zipfile.BadZipFile,
        ) as exc:
            show_error(str(exc))
            return

        output.delete("1.0", tk.END)
        has_error = False
        has_imbalance = False
        is_collection = is_collection_input(Path(path_var.get().strip()))
        results = []

        for index, path in enumerate(files):
            if index:
                output.insert(tk.END, "\n")
            try:
                result = analyze_saldo(
                    path,
                    encoding=encoding,
                    target_counteraccount=target_counteraccount,
                    amount_column=amount_column,
                    side_column=side_column,
                    account_column=account_column,
                    counteraccount_column=counteraccount_column,
                    document_date_column=document_date_column,
                )
            except (
                OSError,
                UnicodeError,
                csv.Error,
                ValueError,
                zipfile.BadZipFile,
            ) as exc:
                output.insert(
                    tk.END,
                    f"Fehler in {source_label(path)}: {exc}\n",
                )
                has_error = True
                continue

            saldo = result.saldo
            results.append(result)
            output.insert(tk.END, f"Datei: {source_label(path)}\n")
            output.insert(tk.END, f"Konto: {result.account}\n")
            output.insert(
                tk.END,
                f"Konto-Summe S ({result.s_count} Buchungen): "
                f"{result.account_s_total:.2f} EUR\n",
            )
            output.insert(
                tk.END,
                f"Konto-Summe H ({result.h_count} Buchungen): "
                f"{result.account_h_total:.2f} EUR\n",
            )
            output.insert(tk.END, f"Saldo (S - H): {saldo:.2f} EUR\n")
            output.insert(tk.END, f"Gegenkonto {target_counteraccount}:\n")
            for entry in result.counteraccount_entries:
                output.insert(
                    tk.END,
                    f"  Belegdatum: {entry.document_date} | "
                    f"Umsatz: {entry.amount:.2f} EUR\n",
                )
            output.insert(
                tk.END,
                f"Gegenkonto-Summe {target_counteraccount} "
                f"({len(result.counteraccount_entries)} Buchungen): "
                f"{result.counteraccount_total:.2f} EUR\n",
            )
            if saldo == 0:
                output.insert(tk.END, f"Prüfung: OK — Saldo = {saldo:.2f} EUR\n")
            else:
                output.insert(
                    tk.END,
                    f"Prüfung: FEHLER — Saldo = {saldo:.2f} EUR "
                    "statt 0.00 EUR\n",
                )
                has_imbalance = True

        if is_collection:
            total_saldo = sum_saldos(results)
            counteraccount_total, counteraccount_count = (
                sum_counteraccount_entries(results)
            )
            output.insert(tk.END, "\n")
            output.insert(tk.END, f"Summe aller Saldo: {total_saldo:.2f} EUR\n")
            output.insert(
                tk.END,
                f"Gesamtsumme Gegenkonto {target_counteraccount} "
                f"({counteraccount_count} Buchungen): "
                f"{counteraccount_total:.2f} EUR\n",
            )
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
    tk.Label(options_frame, text="Gegenkonto prüfen:").grid(
        row=0, column=2, sticky="w", padx=(20, 0)
    )
    tk.Entry(
        options_frame,
        textvariable=target_counteraccount_var,
        width=18,
    ).grid(row=0, column=3, sticky="w", padx=(4, 0))

    columns_frame = tk.LabelFrame(root, text="CSV-Spalten")
    columns_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
    column_specs = (
        ("Betrag:", amount_var),
        ("S/H:", side_var),
        ("Konto:", account_var),
        ("Gegenkonto:", counteraccount_var),
        ("Belegdatum:", document_date_var),
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
    footer.columnconfigure(0, weight=1)
    tk.Label(footer, textvariable=status_var, anchor="w", width=1).grid(
        row=0, column=0, sticky="ew", padx=(0, 8)
    )
    tk.Button(footer, text="Prüfen", command=run_check).grid(
        row=0, column=1, sticky="e"
    )

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(run_gui())
