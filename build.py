"""Build a native Pinesweeper release for Windows or macOS."""

import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "release"


def main():
    if sys.platform not in {"win32", "darwin"}:
        raise SystemExit("Desktop releases must be built on Windows or macOS.")

    platform_name = "win64" if sys.platform == "win32" else "macOS"
    icon = "icon.ico" if sys.platform == "win32" else "icon.png"
    package_name = f"Pinesweeper-{platform_name}"

    for path in (ROOT / "build", ROOT / "dist", RELEASE / package_name):
        if path.exists():
            shutil.rmtree(path)
    RELEASE.mkdir(exist_ok=True)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onefile",
            "--windowed",
            "--name",
            "Pinesweeper",
            "--icon",
            icon,
            "--add-data",
            f"icon.png{os.pathsep}.",
            "main.py",
        ],
        cwd=ROOT,
        check=True,
    )

    package_dir = RELEASE / package_name
    package_dir.mkdir()
    app = (
        ROOT
        / "dist"
        / ("Pinesweeper.exe" if sys.platform == "win32" else "Pinesweeper.app")
    )
    if app.is_dir():
        shutil.copytree(app, package_dir / app.name)
    else:
        shutil.copy2(app, package_dir / app.name)
    shutil.copy2(ROOT / "README.md", package_dir / "README.md")

    archive = shutil.make_archive(
        str(RELEASE / package_name), "zip", RELEASE, package_name
    )
    print(f"Built {archive}")


if __name__ == "__main__":
    main()
