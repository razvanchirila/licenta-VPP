"""
Create user accounts in the database from DATABASE_URL (PostgreSQL). Run from anywhere:

    python backend/scripts/seed.py admin  <username> <password>          one admin (no house)
    python backend/scripts/seed.py user   <username> <password> <house>  one user for a house
    python backend/scripts/seed.py demo   [password]                    admin + user1..user10 (houses 1-10)

The demo password is the argument, else DEMO_PASSWORD from the environment, else 123. For the demo accounts
an existing user keeps its data but gets the demo password, so changing DEMO_PASSWORD and restarting the api
container rotates it. Other existing usernames are skipped. The houses themselves are created by the backend
at first start (here too, so the script can run before the server ever did).
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import close_db, get_session_context, init_db  # noqa: E402
from app.db.init_data import seed_houses  # noqa: E402
from app.db.repositories import UserRepository  # noqa: E402
from app.services.auth import hash_password, verify_password  # noqa: E402
from app.services.users import create_user  # noqa: E402

DEFAULT_DEMO_PASSWORD = "123"
Entry = tuple[str, str, int | None, bool]     # (username, password, house_id, is_admin)


def demo_password() -> str:
    return os.environ.get("DEMO_PASSWORD") or DEFAULT_DEMO_PASSWORD


async def run(entries: list[Entry], reset_password: bool = False) -> None:
    await init_db()
    async with get_session_context() as session:
        await seed_houses(session)
        repo = UserRepository(session)
        for username, password, house_id, is_admin in entries:
            role = "admin" if is_admin else f"casa {house_id}"
            if await create_user(session, username, password, house_id, is_admin):
                status = "creat"
            else:
                status = "exista"
                user = await repo.get_by_username(username)
                if reset_password and not verify_password(password, user.password_hash):
                    user.password_hash = hash_password(password)
                    await session.flush()
                    status = "parola"
            print(f"  {status:<6}  {username:<12} ({role})")
    await close_db()


def parse(argv: list[str]) -> list[Entry] | None:
    """Accounts to create, or None when the arguments are not understood."""
    if len(argv) < 2:
        return None
    cmd = argv[1]
    if cmd == "demo":
        password = argv[2] if len(argv) > 2 else demo_password()
        return [("admin", password, None, True)] + [(f"user{i}", password, i, False) for i in range(1, 11)]
    if cmd == "admin" and len(argv) >= 4:
        return [(argv[2], argv[3], None, True)]
    if cmd == "user" and len(argv) >= 5:
        return [(argv[2], argv[3], int(argv[4]), False)]
    return None


def main(argv: list[str]) -> int:
    entries = parse(argv)
    if entries is None:
        print(__doc__)
        return 1
    asyncio.run(run(entries, reset_password=argv[1] == "demo"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
