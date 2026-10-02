"""
Start command of the api container: waits for the database, creates the demo accounts
(existing ones are skipped, so a restart keeps the data) and then runs main.py.
"""
import asyncio
import os
import subprocess
import sys
import time

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)

from sqlalchemy import text  # noqa: E402

from app.db.database import close_db, get_engine  # noqa: E402

WAIT_SECONDS = 60


async def ping() -> None:
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
    finally:
        await close_db()


def wait_for_database() -> None:
    deadline = time.monotonic() + WAIT_SECONDS
    while True:
        try:
            asyncio.run(ping())
            return
        except Exception as e:
            if time.monotonic() > deadline:
                sys.exit(f"Baza de date nu raspunde dupa {WAIT_SECONDS} s: {e}")
            print(f"Astept baza de date ({type(e).__name__}) ...", flush=True)
            time.sleep(2)


def main() -> None:
    wait_for_database()
    subprocess.run([sys.executable, "scripts/seed.py", "demo"], cwd=BACKEND, check=True)
    os.chdir(BACKEND)
    os.execv(sys.executable, [sys.executable, "main.py"])


if __name__ == "__main__":
    main()
