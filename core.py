import csv
import re
from decimal import Decimal


AMOUNT_COLUMN = "Umsatz (ohne Soll/Haben-Kz)"
SIDE_COLUMN = "Soll/Haben-Kennzeichen"
ACCOUNT_COLUMN = "Konto"
COUNTERACCOUNT_COLUMN = "Gegenkonto (ohne BU-Schlüssel)"


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
            raise ValueError(
                "Die CSV-Datei enthält keine Metadaten- und Kopfzeile."
            ) from exc

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
                raise ValueError(f"Leeres Gegenkonto in CSV-Zeile {line_number}.")

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
