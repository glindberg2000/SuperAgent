#!/bin/bash
# Setup PostgreSQL with pgvector for SuperAgent

echo "🚀 Setting up PostgreSQL with pgvector..."

# Check if container already exists
if docker ps -a | grep -q superagent-postgres; then
    echo "⚠️  Container 'superagent-postgres' already exists. Removing..."
    docker stop superagent-postgres
    docker rm superagent-postgres
fi

# Create volume for data persistence
docker volume create superagent-pgdata

# Start PostgreSQL with pgvector
echo "📦 Starting PostgreSQL with pgvector on port 5433..."
docker run -d \
  --name superagent-postgres \
  -p 5433:5432 \
  -e POSTGRES_USER=superagent \
  -e POSTGRES_PASSWORD=superagent \
  -e POSTGRES_DB=superagent \
  -v superagent-pgdata:/var/lib/postgresql/data \
  ankane/pgvector:latest

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

# Create the schema
echo "📝 Creating database schema..."
docker exec -i superagent-postgres psql -U superagent -d superagent << 'EOF'
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create memories table
CREATE TABLE IF NOT EXISTS memories (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100),
    content TEXT,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS memories_embedding_idx ON memories 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create simple info table to verify connection
CREATE TABLE IF NOT EXISTS info (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert test data
INSERT INTO info (key, value) VALUES ('version', '1.0.0');
INSERT INTO info (key, value) VALUES ('status', 'ready');

EOF

echo "✅ PostgreSQL with pgvector is ready!"
echo ""
echo "Connection details:"
echo "  Host: localhost"
echo "  Port: 5433"
echo "  Database: superagent"
echo "  User: superagent"
echo "  Password: superagent"
echo ""
echo "Python connection string:"
echo "  postgresql://superagent:superagent@localhost:5433/superagent"
echo ""
echo "To connect with psql:"
echo "  psql -h localhost -p 5433 -U superagent -d superagent"