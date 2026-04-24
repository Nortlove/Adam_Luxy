"""
Seed the initial super admin user.

Run: python -m adam.api.admin.migrations.002_seed_super_admin
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


async def seed():
    from adam.api.admin.db import get_db, get_pool
    from adam.api.admin.auth import hash_password
    import uuid

    await get_pool()
    db = get_db()

    existing = await db.fetch_one("SELECT id FROM users WHERE email = $1", "admin@informativ.co")
    if existing:
        print(f"Super admin already exists: {existing['id']}")
        return

    user_id = str(uuid.uuid4())
    pw_hash = hash_password("informativ2026")

    await db.execute(
        "INSERT INTO users (id, email, password_hash, full_name, role, created_at, updated_at) "
        "VALUES ($1, $2, $3, $4, $5, datetime('now'), datetime('now'))",
        user_id, "admin@informativ.co", pw_hash, "Chris Nocera", "super_admin",
    )
    print(f"Super admin created: {user_id}")
    print("  Email: admin@informativ.co")
    print("  Password: informativ2026")
    print("  CHANGE THIS PASSWORD IMMEDIATELY IN PRODUCTION")


if __name__ == "__main__":
    asyncio.run(seed())
