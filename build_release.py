import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
MACOS_ARCH = "arm64"


def build_target(target):
    is_gui = target == "gui"
    name = "check-saldo-gui" if is_gui else "check-saldo"
    entrypoint = ROOT / ("check_saldo_gui.py" if is_gui else "check_saldo.py")
    workpath = BUILD / name

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        name,
        "--distpath",
        str(DIST),
        "--workpath",
        str(workpath),
        "--specpath",
        str(BUILD),
        "--paths",
        str(ROOT),
    ]
    if is_gui and sys.platform == "darwin":
        command.append("--onedir")
    else:
        command.append("--onefile")
    command.append("--windowed" if is_gui else "--console")

    if sys.platform == "darwin":
        command.extend(("--target-architecture", MACOS_ARCH))

    command.append(str(entrypoint))
    print("Building:", " ".join(command))
    environment = os.environ.copy()
    environment["PYINSTALLER_CONFIG_DIR"] = str(BUILD / "pyinstaller-config")
    subprocess.run(command, cwd=ROOT, check=True, env=environment)

    if sys.platform == "win32":
        binary = DIST / f"{name}.exe"
        platform_name = "windows"
        architecture = "x86" if sys.maxsize <= 2**32 else "x64"
    elif sys.platform == "darwin":
        app = DIST / f"{name}.app"
        binary = app if app.exists() else DIST / name
        platform_name = "macos"
        architecture = MACOS_ARCH
    else:
        binary = DIST / name
        platform_name = "linux"
        architecture = "x64"

    if not binary.exists():
        raise FileNotFoundError(f"PyInstaller output not found: {binary}")

    archive_base = DIST / f"{name}-{platform_name}-{architecture}"
    archive = shutil.make_archive(
        str(archive_base),
        "zip",
        root_dir=binary.parent,
        base_dir=binary.name,
    )
    print(f"Created: {archive}")


def main():
    parser = argparse.ArgumentParser(description="Build check-saldo release packages.")
    parser.add_argument(
        "--target",
        choices=("gui", "cli", "all"),
        default="gui",
        help="Build the GUI, CLI, or both (default: gui).",
    )
    args = parser.parse_args()

    DIST.mkdir(exist_ok=True)
    BUILD.mkdir(exist_ok=True)
    targets = ("gui", "cli") if args.target == "all" else (args.target,)
    for target in targets:
        build_target(target)


if __name__ == "__main__":
    main()
