#!/usr/bin/env python3
"""Test memory client"""

import asyncio
import sys

# Check imports
print("Python:", sys.executable)
try:
    import asyncpg
    print("✅ asyncpg imported")
except ImportError as e:
    print("❌ asyncpg import failed:", e)
    sys.exit(1)

try:
    import numpy as np
    print("✅ numpy imported")
except ImportError as e:
    print("❌ numpy import failed:", e)

# Test database connection
async def test_connection():
    try:
        db_url = "postgresql://superagent:superagent@localhost:5433/superagent"
        conn = await asyncpg.connect(db_url)
        
        # Test query
        result = await conn.fetchval("SELECT 'Hello from PostgreSQL!'")
        print(f"✅ Database connection: {result}")
        
        # Test vector table exists
        tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        table_names = [row['tablename'] for row in tables]
        print(f"✅ Tables: {table_names}")
        
        # Test vector extension
        extensions = await conn.fetch("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        if extensions:
            print("✅ pgvector extension loaded")
        else:
            print("❌ pgvector extension not found")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())