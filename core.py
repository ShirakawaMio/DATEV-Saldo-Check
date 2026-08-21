import csv
import io
import re
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal


AMOUNT_COLUMN = "Umsatz (ohne Soll/Haben-Kz)"
SIDE_COLUMN = "Soll/Haben-Kennzeichen"
ACCOUNT_COLUMN = "Konto"
COUNTERACCOUNT_COLUMN = "Gegenkonto (ohne BU-Schlüssel)"
DOCUMENT_DATE_COLUMN = "Belegdatum"
DEFAULT_TARGET_COUNTERACCOUNT = "1360"


@dataclass(frozen=True)
class CounteraccountEntry:
    document_date: str
    amount: Decimal


@dataclass(frozen=True)
class SaldoAnalysis:
    account: str
    account_s_total: Decimal
    account_h_total: Decimal
    s_count: int
    h_count: int
    counteraccount_entries: tuple[CounteraccountEntry, ...]

    @property
    def saldo(self):
        return self.account_s_total - self.account_h_total

    def saldo_tuple(self):
        return (
            self.account,
            self.account_s_total,
            self.account_h_total,
            self.s_count,
            self.h_count,
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


@contextmanager
def open_csv_source(source, encoding):
    if isinstance(source, tuple):
        archive_path, member_name = source
        with zipfile.ZipFile(archive_path) as archive:
            with archive.open(member_name, "r") as binary_file:
                with io.TextIOWrapper(
                    binary_file,
                    encoding=encoding,
                    newline="",
                ) as csv_file:
                    yield csv_file
        return

    with source.open("r", encoding=encoding, newline="") as csv_file:
        yield csv_file


def read_header(source, encoding):
    with open_csv_source(source, encoding) as csv_file:
        reader = csv.reader(csv_file, delimiter=";", strict=True)
        try:
            next(reader)  # DATEV EXTF metadata row
            return next(reader)
        except StopIteration as exc:
            raise ValueError(
                "Die CSV-Datei enthält keine Metadaten- und Kopfzeile."
            ) from exc


def calculate_saldo(
    source,
    *,
    encoding,
    amount_column=AMOUNT_COLUMN,
    side_column=SIDE_COLUMN,
    account_column=ACCOUNT_COLUMN,
    counteraccount_column=COUNTERACCOUNT_COLUMN,
):
    return analyze_saldo(
        source,
        encoding=encoding,
        amount_column=amount_column,
        side_column=side_column,
        account_column=account_column,
        counteraccount_column=counteraccount_column,
        target_counteraccount=None,
    ).saldo_tuple()


def analyze_saldo(
    source,
    *,
    encoding,
    target_counteraccount=DEFAULT_TARGET_COUNTERACCOUNT,
    amount_column=AMOUNT_COLUMN,
    side_column=SIDE_COLUMN,
    account_column=ACCOUNT_COLUMN,
    counteraccount_column=COUNTERACCOUNT_COLUMN,
    document_date_column=DOCUMENT_DATE_COLUMN,
):
    # The S/H flag applies to Konto. A file must represent one Konto so its
    # movement can be checked as S minus H without mixing different accounts.
    account_totals = {"S": Decimal("0"), "H": Decimal("0")}
    counts = {"S": 0, "H": 0}
    accounts = set()
    counteraccount_entries = []

    if target_counteraccount is not None:
        target_counteraccount = target_counteraccount.strip()
        if not target_counteraccount:
            raise ValueError("Das zu prüfende Gegenkonto darf nicht leer sein.")

    with open_csv_source(source, encoding) as csv_file:
        reader = csv.reader(csv_file, delimiter=";", strict=True)

        try:
            next(reader)  # DATEV EXTF metadata row
            header = next(reader)
        except StopIteration as exc:
            raise ValueError(
                "Die CSV-Datei enthält keine Metadaten- und Kopfzeile."
            ) from exc

        required_columns = [
            amount_column,
            side_column,
            account_column,
            counteraccount_column,
        ]
        if target_counteraccount is not None:
            required_columns.append(document_date_column)

        missing_columns = [
            column
            for column in required_columns
            if column not in header
        ]
        if missing_columns:
            raise ValueError(f"Fehlende Spalten: {', '.join(missing_columns)}")

        amount_index = header.index(amount_column)
        side_index = header.index(side_column)
        account_index = header.index(account_column)
        counteraccount_index = header.index(counteraccount_column)
        required_indices = [
            amount_index,
            side_index,
            account_index,
            counteraccount_index,
        ]
        if target_counteraccount is not None:
            document_date_index = header.index(document_date_column)
            required_indices.append(document_date_index)
        required_index = max(required_indices)

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

            counteraccount = row[counteraccount_index].strip()
            if not counteraccount:
                raise ValueError(f"Leeres Gegenkonto in CSV-Zeile {line_number}.")

            amount = parse_amount(row[amount_index], line_number=line_number)
            accounts.add(account)
            account_totals[side] += amount
            counts[side] += 1

            if (
                target_counteraccount is not None
                and counteraccount == target_counteraccount
            ):
                document_date = row[document_date_index].strip()
                if not document_date:
                    raise ValueError(
                        f"Leeres Belegdatum in CSV-Zeile {line_number}."
                    )
                counteraccount_entries.append(
                    CounteraccountEntry(
                        document_date=document_date,
                        amount=amount,
                    )
                )

    if not accounts:
        raise ValueError("Die CSV-Datei enthält keine Buchungen.")
    if len(accounts) != 1:
        raise ValueError(
            "Die CSV-Datei enthält mehrere Konten; "
            "ein gemeinsamer Saldo wäre nicht eindeutig."
        )

    return SaldoAnalysis(
        account=next(iter(accounts)),
        account_s_total=account_totals["S"],
        account_h_total=account_totals["H"],
        s_count=counts["S"],
        h_count=counts["H"],
        counteraccount_entries=tuple(counteraccount_entries),
    )


def find_csv_files(input_path):
    if input_path.is_file():
        if input_path.suffix.lower() == ".zip":
            return find_zip_csv_files(input_path)
        return [input_path]
    if input_path.is_dir():
        sources = []
        for path in sorted(input_path.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() == ".csv":
                sources.append(path)
            elif path.suffix.lower() == ".zip":
                sources.extend(find_zip_csv_files(path))
        return sources
    raise FileNotFoundError(f"Datei oder Ordner nicht gefunden: {input_path}")


def find_zip_csv_files(archive_path):
    with zipfile.ZipFile(archive_path) as archive:
        return [
            (archive_path, info.filename)
            for info in archive.infolist()
            if not info.is_dir()
            and info.filename.lower().endswith(".csv")
        ]


def source_label(source):
    if isinstance(source, tuple):
        return f"{source[0]}::{source[1]}"
    return str(source)


def is_collection_input(input_path):
    return input_path.is_dir() or input_path.suffix.lower() == ".zip"


def sum_saldos(results):
    total = Decimal("0")
    for result in results:
        if isinstance(result, SaldoAnalysis):
            total += result.saldo
        else:
            total += result[1] - result[2]
    return total
