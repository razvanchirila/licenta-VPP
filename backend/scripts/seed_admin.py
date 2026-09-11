"""Script to create default admin user."""
import asyncio
import sys
import os

# Add backend/ to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import init_db, get_session_context
from app.db.repositories import UserRepository
from app.services.auth import AuthService


async def create_admin_user(username: str = "admin", password: str = "admin123"):
    """Create default admin user if not exists."""
    await init_db()
    
    async with get_session_context() as session:
        user_repo = UserRepository(session)
        
        # Check if admin exists
        existing = await user_repo.get_by_username(username)
        if existing:
            print(f"Admin user '{username}' already exists")
            return
        
        # Create admin user
        password_hash = AuthService.hash_password(password)
        user = await user_repo.create_user(
            username=username,
            password_hash=password_hash,
            is_admin=True
        )
        
        print(f"Admin user created:")
        print(f"  Username: {username}")
        print(f"  Password: {password}")
        print(f"  User ID: {user.id}")


if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else "admin"
    password = sys.argv[2] if len(sys.argv) > 2 else "admin123"
    
    print("Creating admin user...")
    asyncio.run(create_admin_user(username, password))
    print("Done!")
