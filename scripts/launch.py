"""Start the whole project for a demo: backend (API + dashboard) and the Flutter web app.

Called by start.bat after the Python environment exists. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
MOBILE = ROOT / "mobile"
WEB_BUILD = MOBILE / "build" / "web"
LOGS = ROOT / "logs"
PYTHON = sys.executable

API = "http://127.0.0.1:8000"
APP_PORT = 3000
APP = f"http://127.0.0.1:{APP_PORT}"
FLUTTER_HOME = Path("C:/flutter")
DB_FILES = ("vpp.db", "vpp.db-wal", "vpp.db-shm")


def step(text: str) -> None:
    print(f"\n== {text}", flush=True)


def port_in_use(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def get_json(url: str, token: str | None = None, data: dict | None = None) -> dict:
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method="POST" if body is not None else "GET")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode())


def ensure_env() -> None:
    env = BACKEND / ".env"
    if not env.exists():
        shutil.copyfile(BACKEND / ".env.example", env)
        print("backend/.env creat din .env.example")


def reset_database(keep: bool) -> None:
    if not keep:
        for name in DB_FILES:
            (BACKEND / name).unlink(missing_ok=True)
    subprocess.run([PYTHON, str(BACKEND / "scripts" / "seed.py"), "demo"], check=True)


def find_flutter() -> str | None:
    found = shutil.which("flutter")
    if found:
        return found
    candidate = FLUTTER_HOME / "bin" / "flutter.bat"
    return str(candidate) if candidate.exists() else None


def install_flutter(assume_yes: bool) -> str | None:
    if not shutil.which("git"):
        print("Flutter nu este instalat si nici git; aplicatia mobila nu porneste (dashboard-ul merge).")
        return None
    if not assume_yes:
        answer = input(f"Flutter nu este instalat. Il descarc in {FLUTTER_HOME} (~2 GB, cateva minute)? [D/n] ")
        if answer.strip().lower() in ("n", "nu", "no"):
            return None
    subprocess.run(["git", "clone", "--depth", "1", "-b", "stable",
                    "https://github.com/flutter/flutter.git", str(FLUTTER_HOME)], check=True)
    flutter = str(FLUTTER_HOME / "bin" / "flutter.bat")
    subprocess.run([flutter, "config", "--no-analytics", "--enable-web"], check=True)
    return flutter


def newest_mtime(paths: list[Path]) -> float:
    latest = 0.0
    for path in paths:
        files = path.rglob("*") if path.is_dir() else [path]
        for f in files:
            if f.is_file():
                latest = max(latest, f.stat().st_mtime)
    return latest


def build_web_app(flutter: str) -> bool:
    """Rebuild only when the sources or the build options changed since the last build."""
    defines = [f"--dart-define=API_URL={API}/api"]
    weather_key = os.environ.get("WEATHER_API_KEY")
    if weather_key:
        defines.append(f"--dart-define=WEATHER_API_KEY={weather_key}")
    stamp = WEB_BUILD / ".build-options"
    index = WEB_BUILD / "index.html"
    sources = [MOBILE / "lib", MOBILE / "web", MOBILE / "assets", MOBILE / "pubspec.yaml"]
    up_to_date = (index.exists() and stamp.exists() and stamp.read_text() == " ".join(defines)
                  and newest_mtime(sources) < index.stat().st_mtime)
    if up_to_date:
        print("aplicatia web e deja compilata")
        return True
    subprocess.run([flutter, "pub", "get"], cwd=MOBILE, check=True, stdout=subprocess.DEVNULL)
    result = subprocess.run([flutter, "build", "web", "--release", "--no-wasm-dry-run", *defines], cwd=MOBILE, check=False)
    if result.returncode != 0:
        print("Compilarea aplicatiei Flutter a esuat; dashboard-ul merge in continuare.")
        return False
    stamp.write_text(" ".join(defines))
    return True


def start_process(args: list[str], cwd: Path, log_name: str) -> subprocess.Popen:
    LOGS.mkdir(exist_ok=True)
    log = open(LOGS / log_name, "w", encoding="utf-8")  # noqa: SIM115 - stays open for the child process
    return subprocess.Popen(args, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)


def wait_for_backend(backend: subprocess.Popen, timeout_s: float = 90) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if backend.poll() is not None:
            return False
        try:
            get_json(f"{API}/health")
            return True
        except OSError:
            time.sleep(1)
    return False


def ensure_simulation_running() -> None:
    token = get_json(f"{API}/api/auth/login", data={"username": "admin", "password": "123"})["access_token"]
    if not get_json(f"{API}/api/sim/status", token).get("running"):
        get_json(f"{API}/api/sim/start", token, data={})


def tail(log_name: str, lines: int = 20) -> str:
    path = LOGS / log_name
    return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]) if path.exists() else ""


def banner(with_app: bool) -> None:
    print("\n" + "=" * 64)
    print(" Gata. Proiectul ruleaza.")
    print(f"   Dashboard operator:  {API}          admin / 123")
    if with_app:
        print(f"   Aplicatia Flutter:   {APP}          user1 / 123  (user1..user10)")
    print(f"   Documentatie API:    {API}/docs")
    print(f"   Loguri:              {LOGS}")
    print(" Inchide cu Ctrl+C sau inchizand fereastra.")
    print("=" * 64, flush=True)


def stop(processes: list[subprocess.Popen]) -> None:
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
    for proc in processes:
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-db", action="store_true", help="pastreaza baza de date existenta")
    parser.add_argument("--no-mobile", action="store_true", help="fara aplicatia Flutter")
    parser.add_argument("--no-browser", action="store_true", help="nu deschide browserul")
    parser.add_argument("--yes", action="store_true", help="instaleaza Flutter fara intrebare")
    parser.add_argument("--check", action="store_true", help="porneste, verifica si opreste (test)")
    args = parser.parse_args()

    if port_in_use(8000):
        try:
            get_json(f"{API}/health")
            print(f"Backend-ul ruleaza deja pe {API}. Inchide fereastra veche sau deschide direct adresa.")
        except OSError:
            print("Portul 8000 este ocupat de alt program. Opreste-l si ruleaza din nou.")
        return 1

    step("Configurare")
    ensure_env()

    step("Baza de date si conturile demo")
    reset_database(args.keep_db)

    with_app = False
    if not args.no_mobile:
        step("Aplicatia Flutter")
        if port_in_use(APP_PORT):
            print(f"Portul {APP_PORT} este ocupat; pornesc fara aplicatia Flutter.")
        else:
            flutter = find_flutter() or install_flutter(args.yes)
            with_app = bool(flutter) and build_web_app(flutter)

    step("Pornesc backend-ul")
    processes = [start_process([PYTHON, "main.py"], BACKEND, "backend.log")]
    if not wait_for_backend(processes[0]):
        print("Backend-ul nu a pornit. Ultimele linii din logs/backend.log:\n" + tail("backend.log"))
        stop(processes)
        return 1
    ensure_simulation_running()

    if with_app:
        processes.append(start_process(
            [PYTHON, "-m", "http.server", str(APP_PORT), "--bind", "127.0.0.1", "--directory", str(WEB_BUILD)],
            ROOT, "app.log"))
        time.sleep(1)

    if args.check:
        ok = get_json(f"{API}/api/auth/login", data={"username": "user1", "password": "123"}).get("access_token")
        app_ok = not with_app or urllib.request.urlopen(APP, timeout=5).status == 200
        print(f"verificare: login {'ok' if ok else 'esuat'}, aplicatie {'ok' if app_ok else 'esuat'}")
        stop(processes)
        return 0 if ok and app_ok else 1

    banner(with_app)
    if not args.no_browser:
        webbrowser.open(API)
        if with_app:
            webbrowser.open(APP)

    try:
        while True:
            for proc, log_name in zip(processes, ("backend.log", "app.log"), strict=False):
                if proc.poll() is not None:
                    print(f"\nUn proces s-a oprit. Ultimele linii din logs/{log_name}:\n" + tail(log_name))
                    stop(processes)
                    return 1
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nOpresc ...")
        stop(processes)
        return 0


if __name__ == "__main__":
    sys.exit(main())
