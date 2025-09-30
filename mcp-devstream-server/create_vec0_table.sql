-- Context7-compliant vec0 virtual table for semantic_memory embeddings
-- Based on sqlite-vec best practices for 768-dimensional embeddings

CREATE VIRTUAL TABLE IF NOT EXISTS vec_semantic_memory USING vec0(
  -- Primary key: use rowid to link back to semantic_memory.rowid
  memory_rowid INTEGER PRIMARY KEY,
  
  -- Vector embedding: 768 dimensions (embeddinggemma:300m)
  embedding float[768],
  
  -- Partition key: shard by content_type for faster filtering
  content_type TEXT PARTITION KEY,
  
  -- Metadata columns: indexed, can be used in WHERE clauses
  relevance_score FLOAT,
  created_at TEXT,
  
  -- Auxiliary columns: unindexed, for display purposes
  +memory_id TEXT,
  +content_preview TEXT
);
