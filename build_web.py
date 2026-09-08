"""Build and package the browser version of Pinesweeper."""

from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
WEB_SOURCE = ROOT / "build" / "web-source" / "Pinesweeper"
WEB_BUILD = WEB_SOURCE / "build" / "web"
RELEASE = ROOT / "release"
PACKAGE_NAME = "Pinesweeper-web"


def main():
    if WEB_SOURCE.parent.exists():
        shutil.rmtree(WEB_SOURCE.parent)
    WEB_SOURCE.mkdir(parents=True)
    for filename in ("main.py", "icon.png"):
        shutil.copy2(ROOT / filename, WEB_SOURCE / filename)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pygbag",
            "--build",
            "--app_name",
            "Pinesweeper",
            "--title",
            "Pinesweeper",
            "--icon",
            "icon.png",
            "--width",
            "540",
            "--height",
            "646",
            str(WEB_SOURCE),
        ],
        cwd=ROOT,
        check=True,
    )
    if not (WEB_BUILD / "index.html").exists():
        raise SystemExit("pygbag did not produce build/web/index.html")

    package_dir = RELEASE / PACKAGE_NAME
    if package_dir.exists():
        shutil.rmtree(package_dir)
    RELEASE.mkdir(exist_ok=True)
    shutil.copytree(WEB_BUILD, package_dir)
    archive = shutil.make_archive(
        str(RELEASE / PACKAGE_NAME), "zip", RELEASE, PACKAGE_NAME
    )
    print(f"Built {archive}")


if __name__ == "__main__":
    main()
