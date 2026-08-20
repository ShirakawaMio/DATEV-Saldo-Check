# Check Saldo

[Deutsche Anleitung](README.md)

这是一个用于检查 DATEV 账务 CSV 是否平衡的小工具。

## 下载

- [下载 macOS Apple Silicon 版本](https://github.com/ShirakawaMio/check-saldo/releases/latest/download/check-saldo-gui-macos-arm64.zip)
- [下载 Windows 32 位（x86）版本](https://github.com/ShirakawaMio/check-saldo/releases/latest/download/check-saldo-gui-windows-x86.zip)
- [下载 Linux 64 位版本](https://github.com/ShirakawaMio/check-saldo/releases/latest/download/check-saldo-gui-linux-x64.zip)
- [查看全部版本和发布说明](https://github.com/ShirakawaMio/check-saldo/releases)

## 给使用者的说明

1. 下载与你的电脑系统对应的程序包。
2. 打开程序，选择一个 CSV 文件、ZIP 压缩包，或者选择一个包含多个 CSV 的文件夹。
3. 如果程序显示了列选择，请确认金额列、S/H 列、Konto 列和 Gegenkonto 列。
4. 点击检查。

程序会逐个检查选中的文件，并显示：

- 该账户的 Soll 合计；
- 该账户的 Haben 合计；
- 按 Soll 减 Haben 计算的 `Saldo`。

显示 `Saldo: 0.00 EUR` 和 `Prüfung: OK`，表示该文件通过检查。
一个 Buchungsstapel 在所选 Konto 列中必须只包含一个账户；程序不会把多个账户合并成误导性的余额。

选择文件夹时，逐个文件的结果下面还会显示所有成功计算出的 Saldo 总和。
总和为 `0.00 EUR` 时显示 `OK`，其他金额显示 `FEHLER`。

程序只在本机读取文件，不会自动上传账务数据。真实账务 CSV 请保存在安全位置，不要发送给无关人员。

## 支持范围

程序针对 DATEV Buchungsstapel CSV 以及包含此类 CSV 的 ZIP 压缩包。金额必须为正数且不能为零，不得使用千位分隔符，并使用逗号和两位小数。如果列名不同，可以在程序中选择对应列；如果仍然无法读取，请联系维护人员。

macOS 版本仅支持 Apple Silicon Mac。Windows 仅提供 32 位（x86）版本。
