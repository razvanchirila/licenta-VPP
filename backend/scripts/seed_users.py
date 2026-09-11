"""Script to create users for houses 2-10."""
import asyncio
import sys
import os

# Add backend/ to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import init_db, get_session_context
from app.db.repositories import UserRepository
from app.services.auth import AuthService


# User definitions: (username, password, house_id, is_admin)
USERS = [
    # Admin for house 2
    ("admin2", "admin123", 2, True),
    
    # Regular users for houses 3-10
    ("user3", "user123", 3, False),
    ("user4", "user123", 4, False),
    ("user5", "user123", 5, False),
    ("user6", "user123", 6, False),
    ("user7", "user123", 7, False),
    ("user8", "user123", 8, False),
    ("user9", "user123", 9, False),
    ("user10", "user123", 10, False),
]


async def seed_users():
    """Create all users if they don't exist."""
    await init_db()
    
    async with get_session_context() as session:
        user_repo = UserRepository(session)
        
        created = 0
        skipped = 0
        
        for username, password, house_id, is_admin in USERS:
            # Check if user exists
            existing = await user_repo.get_by_username(username)
            if existing:
                print(f"  [SKIP] User '{username}' already exists")
                skipped += 1
                continue
            
            # Create user
            password_hash = AuthService.hash_password(password)
            user = await user_repo.create_user(
                username=username,
                password_hash=password_hash,
                house_id=house_id,
                is_admin=is_admin
            )
            
            role = "Admin" if is_admin else "User"
            print(f"  [OK] Created {role} '{username}' for House {house_id}")
            created += 1
        
        print(f"\nSummary: {created} created, {skipped} skipped")


if __name__ == "__main__":
    print("=" * 50)
    print("SEEDING USERS")
    print("=" * 50)
    print()
    
    asyncio.run(seed_users())
    
    print()
    print("=" * 50)
    print("CREDENTIALS:")
    print("=" * 50)
    print()
    print("Admin users:")
    print("  admin2 / admin123  (House 2)")
    print()
    print("Regular users:")
    print("  user3 / user123   (House 3)")
    print("  user4 / user123   (House 4)")
    print("  user5 / user123   (House 5)")
    print("  user6 / user123   (House 6)")
    print("  user7 / user123   (House 7)")
    print("  user8 / user123   (House 8)")
    print("  user9 / user123   (House 9)")
    print("  user10 / user123  (House 10)")
    print()
    print("Done!")
