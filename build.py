"""Build a standalone Windows release of Pinesweeper.

    pip install pyinstaller pillow
    python build.py

Produces:
    dist/Pinesweeper.exe          single-file windowed executable
    release/Pinesweeper-win64.zip  zip containing the exe + README
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    print("$", " ".join(cmd))
    subprocess.check_call(cmd)


def main():
    icon_png = os.path.join(ROOT, "icon.png")
    icon_ico = os.path.join(ROOT, "icon.ico")
    if not (os.path.exists(icon_png) and os.path.exists(icon_ico)):
        sys.exit("icon.png / icon.ico missing at repo root")

    run([
        sys.executable, "-m", "PyInstaller",
        "--onefile", "--windowed",
        "--name", "Pinesweeper",
        "--icon", "icon.ico",
        "--add-data", "icon.png;.",
        "--clean", "--noconfirm",
        "main.py",
    ])

    stage = os.path.join(ROOT, "release", "Pinesweeper")
    if os.path.exists(os.path.join(ROOT, "release")):
        shutil.rmtree(os.path.join(ROOT, "release"))
    os.makedirs(stage)
    shutil.copy(os.path.join(ROOT, "dist", "Pinesweeper.exe"), stage)
    shutil.copy(os.path.join(ROOT, "README.md"), stage)

    zip_base = os.path.join(ROOT, "release", "Pinesweeper-win64")
    shutil.make_archive(zip_base, "zip", os.path.join(ROOT, "release"), "Pinesweeper")
    print("built", zip_base + ".zip")


if __name__ == "__main__":
    main()
