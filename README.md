# Check Saldo

[中文说明](README-ZH.md)

Ein einfaches Programm zur Prüfung, ob DATEV-Buchungsstapel ausgeglichen sind.

## Download

- [macOS Apple Silicon herunterladen](https://github.com/ShirakawaMio/check-saldo/releases/latest/download/check-saldo-gui-macos-arm64.zip)
- [Windows 32-Bit (x86) herunterladen](https://github.com/ShirakawaMio/check-saldo/releases/latest/download/check-saldo-gui-windows-x86.zip)
- [Linux 64-Bit herunterladen](https://github.com/ShirakawaMio/check-saldo/releases/latest/download/check-saldo-gui-linux-x64.zip)
- [Alle Versionen und Veröffentlichungshinweise](https://github.com/ShirakawaMio/check-saldo/releases)

## Anleitung

1. Laden Sie das Programm für Ihr Betriebssystem herunter.
2. Öffnen Sie das Programm und wählen Sie eine CSV-Datei, ein ZIP-Archiv oder einen Ordner mit mehreren CSV-Dateien aus.
3. Prüfen Sie die Betrags-, S/H-, Konto-, Gegenkonto- und Belegdatum-Spalte.
4. Geben Sie bei „Gegenkonto prüfen“ das gewünschte Gegenkonto ein. Der Standardwert ist `1360`.
5. Klicken Sie auf „Prüfen“.

Das Programm prüft die ausgewählten Dateien einzeln und zeigt:

- die Summe der Soll-Buchungen des Kontos;
- die Summe der Haben-Buchungen des Kontos;
- den `Saldo` als Soll minus Haben;
- für das ausgewählte Gegenkonto jede Buchung mit Umsatz und Belegdatum.

`Saldo: 0.00 EUR` zusammen mit `Prüfung: OK` bedeutet, dass die Datei die Prüfung bestanden hat.
Ein Buchungsstapel muss genau ein Konto in der ausgewählten Konto-Spalte enthalten.

Bei der Auswahl eines Ordners oder ZIP-Archivs wird unter den Einzelergebnissen
zusätzlich die Summe aller erfolgreich berechneten Saldo angezeigt. `0.00 EUR`
beim Saldo bedeutet `OK`, ein anderer Saldo bedeutet `FEHLER`.

In der Kommandozeile kann das Gegenkonto mit `--gegenkonto` gewählt werden,
zum Beispiel `python main.py --gegenkonto 1360 export.zip`.

Die Dateien werden nur lokal gelesen. Buchungsdaten werden nicht automatisch hochgeladen. Bewahren Sie echte Buchungs-CSV-Dateien sicher auf.

## Unterstützte Dateien

Das Programm ist für DATEV-Buchungsstapel-CSV-Dateien und ZIP-Archive mit solchen
CSV-Dateien vorgesehen. Beträge müssen
dem DATEV-Format entsprechen: positiv, ungleich null, ohne Tausendertrennzeichen
und mit Komma sowie zwei Nachkommastellen. Bei abweichenden Spaltennamen können
die passenden Spalten im Programm ausgewählt werden. Wenn die Datei trotzdem
nicht gelesen werden kann, wenden Sie sich bitte an die zuständige Betreuung.
