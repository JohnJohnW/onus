-- Runs automatically the first time the Postgres data volume is initialized.
-- Enables the pgvector extension used by the Onus engine for embeddings.
CREATE EXTENSION IF NOT EXISTS vector;
