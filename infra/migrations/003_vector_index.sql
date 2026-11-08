-- 003_vector_index.sql — cosine HNSW index for chunk retrieval.
-- Requires pgvector with HNSW support (>= 0.5). Exact scan remains the
-- fallback on older builds (drop this file if CREATE INDEX fails there).
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
  ON chunks USING hnsw (embedding vector_cosine_ops);
