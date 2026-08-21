import io
import csv
import sys
import tempfile
import zipfile
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import (  # noqa: E402
    ACCOUNT_COLUMN,
    AMOUNT_COLUMN,
    COUNTERACCOUNT_COLUMN,
    CounteraccountEntry,
    DOCUMENT_DATE_COLUMN,
    SaldoAnalysis,
    SIDE_COLUMN,
    analyze_saldo,
    calculate_saldo,
    find_csv_files,
    parse_amount,
    sum_counteraccount_entries,
    sum_saldos,
)
from ui import short_source_label  # noqa: E402


def write_csv(path, headers, rows):
    with path.open("w", encoding="iso-8859-1", newline="") as csv_file:
        writer = csv.writer(csv_file, delimiter=";", lineterminator="\n")
        writer.writerow(["EXTF", 700, 21, "Buchungsstapel", 12])
        writer.writerow(headers)
        writer.writerows(rows)


def write_zip(path, headers, rows):
    csv_buffer = io.StringIO(newline="")
    writer = csv.writer(csv_buffer, delimiter=";", lineterminator="\n")
    writer.writerow(["EXTF", 700, 21, "Buchungsstapel", 12])
    writer.writerow(headers)
    writer.writerows(rows)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "nested/inside.csv",
            csv_buffer.getvalue().encode("iso-8859-1"),
        )


def test_parse_amount():
    assert parse_amount("1234,56", line_number=1) == Decimal("1234.56")
    assert parse_amount("0,01", line_number=1) == Decimal("0.01")

    for value in ("", "0,00", "-1,00", "1.234,56", "1234.56", "NaN", "Infinity"):
        try:
            parse_amount(value, line_number=1)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid DATEV amount accepted: {value!r}")


def test_account_saldo():
    with tempfile.TemporaryDirectory() as temporary_directory:
        path = Path(temporary_directory) / "balanced.csv"
        write_csv(
            path,
            [AMOUNT_COLUMN, SIDE_COLUMN, ACCOUNT_COLUMN, COUNTERACCOUNT_COLUMN],
            [
                ["100,00", "S", "1200", "20000"],
                ["40,00", "H", "1200", "20000"],
            ],
        )

        result = calculate_saldo(path, encoding="iso-8859-1")

    assert result == (
        "1200",
        Decimal("100.00"),
        Decimal("40.00"),
        1,
        1,
    )


def test_custom_column_names():
    with tempfile.TemporaryDirectory() as temporary_directory:
        path = Path(temporary_directory) / "custom.csv"
        write_csv(
            path,
            ["amount", "direction", "account", "counter"],
            [["10,50", "S", "1200", "20000"]],
        )

        result = calculate_saldo(
            path,
            encoding="iso-8859-1",
            amount_column="amount",
            side_column="direction",
            account_column="account",
            counteraccount_column="counter",
        )

    assert result == (
        "1200",
        Decimal("10.50"),
        Decimal("0"),
        1,
        0,
    )


def test_recursive_csv_discovery():
    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        nested = root / "nested"
        nested.mkdir()
        (root / "one.csv").write_text("", encoding="utf-8")
        (nested / "two.CSV").write_text("", encoding="utf-8")
        (root / "ignored.txt").write_text("", encoding="utf-8")

        files = find_csv_files(root)

    assert len(files) == 2
    assert {path.name for path in files} == {"one.csv", "two.CSV"}


def test_zip_csv_discovery_and_calculation():
    with tempfile.TemporaryDirectory() as temporary_directory:
        archive_path = Path(temporary_directory) / "buchungen.zip"
        write_zip(
            archive_path,
            [AMOUNT_COLUMN, SIDE_COLUMN, ACCOUNT_COLUMN, COUNTERACCOUNT_COLUMN],
            [
                ["100,00", "S", "1200", "20000"],
                ["100,00", "H", "1200", "20000"],
            ],
        )

        sources = find_csv_files(archive_path)
        result = calculate_saldo(sources[0], encoding="iso-8859-1")

    assert sources == [(archive_path, "nested/inside.csv")]
    assert result == (
        "1200",
        Decimal("100.00"),
        Decimal("100.00"),
        1,
        1,
    )


def test_short_source_label():
    regular_source = Path("exports") / "2026-06" / "bookings.csv"
    zip_source = (
        Path("exports") / "Amazon_FR_2026-06.zip",
        "nested/EXTF_Buchungen.csv",
    )

    assert short_source_label(regular_source) == "2026-06/bookings.csv"
    assert (
        short_source_label(zip_source)
        == "Amazon_FR_2026-06.zip::EXTF_Buchungen.csv"
    )


def test_counteraccount_entries_and_total():
    with tempfile.TemporaryDirectory() as temporary_directory:
        path = Path(temporary_directory) / "counteraccount.csv"
        write_csv(
            path,
            [
                AMOUNT_COLUMN,
                SIDE_COLUMN,
                ACCOUNT_COLUMN,
                COUNTERACCOUNT_COLUMN,
                DOCUMENT_DATE_COLUMN,
            ],
            [
                ["100,00", "S", "1200", "1360", "01082026"],
                ["40,50", "H", "1200", "1360", "02082026"],
                ["10,00", "H", "1200", "20000", "03082026"],
            ],
        )

        result = analyze_saldo(path, encoding="iso-8859-1")
        custom_result = analyze_saldo(
            path,
            encoding="iso-8859-1",
            target_counteraccount="20000",
        )

    assert [
        (entry.document_date, entry.amount)
        for entry in result.counteraccount_entries
    ] == [
        ("01082026", Decimal("100.00")),
        ("02082026", Decimal("40.50")),
    ]
    assert result.counteraccount_total == Decimal("140.50")

    assert [
        (entry.document_date, entry.amount)
        for entry in custom_result.counteraccount_entries
    ] == [("03082026", Decimal("10.00"))]


def test_counteraccount_collection_total():
    first = analyze_test_result(
        [("01082026", Decimal("10.00")), ("02082026", Decimal("20.00"))]
    )
    second = analyze_test_result([("03082026", Decimal("30.00"))])

    assert sum_counteraccount_entries([first, second]) == (
        Decimal("60.00"),
        3,
    )


def analyze_test_result(entries):
    return SaldoAnalysis(
        account="1200",
        account_s_total=Decimal("0"),
        account_h_total=Decimal("0"),
        s_count=0,
        h_count=0,
        counteraccount_entries=tuple(
            CounteraccountEntry(document_date=date, amount=amount)
            for date, amount in entries
        ),
    )


def test_sum_saldos():
    results = [
        ("1200", Decimal("100.00"), Decimal("40.00"), 1, 1),
        ("1201", Decimal("25.00"), Decimal("85.00"), 1, 1),
    ]

    assert sum_saldos(results) == Decimal("0")
    assert sum_saldos(results[:1]) == Decimal("60.00")


def test_empty_counteraccount_is_rejected():
    with tempfile.TemporaryDirectory() as temporary_directory:
        path = Path(temporary_directory) / "invalid.csv"
        write_csv(
            path,
            [AMOUNT_COLUMN, SIDE_COLUMN, ACCOUNT_COLUMN, COUNTERACCOUNT_COLUMN],
            [["10,00", "S", "1200", ""]],
        )

        try:
            calculate_saldo(path, encoding="iso-8859-1")
        except ValueError as exc:
            assert "Gegenkonto" in str(exc)
        else:
            raise AssertionError("A missing Gegenkonto must be rejected.")


def test_empty_account_is_rejected():
    with tempfile.TemporaryDirectory() as temporary_directory:
        path = Path(temporary_directory) / "empty-account.csv"
        write_csv(
            path,
            [AMOUNT_COLUMN, SIDE_COLUMN, ACCOUNT_COLUMN, COUNTERACCOUNT_COLUMN],
            [["10,00", "S", "", "20000"]],
        )

        try:
            calculate_saldo(path, encoding="iso-8859-1")
        except ValueError as exc:
            assert "Konto" in str(exc)
        else:
            raise AssertionError("A missing Konto must be rejected.")


def test_invalid_side_is_rejected():
    with tempfile.TemporaryDirectory() as temporary_directory:
        path = Path(temporary_directory) / "invalid-side.csv"
        write_csv(
            path,
            [AMOUNT_COLUMN, SIDE_COLUMN, ACCOUNT_COLUMN, COUNTERACCOUNT_COLUMN],
            [["10,00", "s", "1200", "20000"]],
        )

        try:
            calculate_saldo(path, encoding="iso-8859-1")
        except ValueError as exc:
            assert "Soll/Haben" in str(exc)
        else:
            raise AssertionError("An invalid S/H indicator must be rejected.")


def test_multiple_accounts_are_rejected():
    with tempfile.TemporaryDirectory() as temporary_directory:
        path = Path(temporary_directory) / "multiple-accounts.csv"
        write_csv(
            path,
            [AMOUNT_COLUMN, SIDE_COLUMN, ACCOUNT_COLUMN, COUNTERACCOUNT_COLUMN],
            [
                ["10,00", "S", "1200", "20000"],
                ["10,00", "H", "1201", "20000"],
            ],
        )

        try:
            calculate_saldo(path, encoding="iso-8859-1")
        except ValueError as exc:
            assert "mehrere Konten" in str(exc)
        else:
            raise AssertionError("Multiple accounts must not be combined.")


def main():
    tests = (
        test_parse_amount,
        test_account_saldo,
        test_custom_column_names,
        test_recursive_csv_discovery,
        test_zip_csv_discovery_and_calculation,
        test_short_source_label,
        test_counteraccount_entries_and_total,
        test_counteraccount_collection_total,
        test_sum_saldos,
        test_empty_counteraccount_is_rejected,
        test_empty_account_is_rejected,
        test_invalid_side_is_rejected,
        test_multiple_accounts_are_rejected,
    )
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"{len(tests)} tests passed")


if __name__ == "__main__":
    main()
