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
2. Öffnen Sie das Programm und wählen Sie eine CSV-Datei oder einen Ordner mit mehreren CSV-Dateien aus.
3. Falls eine Spaltenauswahl angezeigt wird, prüfen Sie die Betrags-, S/H-, Konto- und Gegenkonto-Spalte.
4. Klicken Sie auf „Prüfen“.

Das Programm prüft die ausgewählten Dateien einzeln und zeigt:

- die Summe der Soll-Buchungen des Kontos;
- die Summe der Haben-Buchungen des Kontos;
- den `Saldo` als Soll minus Haben.

`Saldo: 0.00 EUR` zusammen mit `Prüfung: OK` bedeutet, dass die Datei die Prüfung bestanden hat.
Ein Buchungsstapel muss genau ein Konto in der ausgewählten Konto-Spalte enthalten.

Die Dateien werden nur lokal gelesen. Buchungsdaten werden nicht automatisch hochgeladen. Bewahren Sie echte Buchungs-CSV-Dateien sicher auf und geben Sie sie nicht an unbefugte Personen weiter.

## Unterstützte Dateien

Das Programm ist für DATEV-Buchungsstapel-CSV-Dateien vorgesehen. Beträge müssen
dem DATEV-Format entsprechen: positiv, ungleich null, ohne Tausendertrennzeichen
und mit Komma sowie zwei Nachkommastellen. Bei abweichenden Spaltennamen können
die passenden Spalten im Programm ausgewählt werden. Wenn die Datei trotzdem
nicht gelesen werden kann, wenden Sie sich bitte an die zuständige Betreuung.

Die macOS-Version unterstützt ausschließlich Apple-Silicon-Macs. Für Windows
wird ausschließlich eine 32-Bit-Version (x86) bereitgestellt.
