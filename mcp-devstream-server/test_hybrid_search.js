const Database = require('better-sqlite3');
const sqliteVec = require('sqlite-vec');
const { Ollama } = require('ollama');

const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');
sqliteVec.load(db);

const ollama = new Ollama({ host: 'http://localhost:11434' });

console.log('🧪 Testing DevStream Hybrid Search (Context7 RRF Pattern)\n');
console.log('='.repeat(70) + '\n');

async function generateEmbedding(text) {
  try {
    const response = await ollama.embeddings({
      model: 'embeddinggemma:300m',
      prompt: text
    });
    return response.embedding;
  } catch (error) {
    console.error('Embedding generation failed:', error.message);
    return null;
  }
}

async function testHybridSearch(query) {
  console.log(`🔍 Query: "${query}"\n`);
  
  const embedding = await generateEmbedding(query);
  if (!embedding) {
    console.log('❌ Could not generate query embedding\n');
    return;
  }
  
  const embeddingBuffer = Buffer.from(new Float32Array(embedding).buffer);
  
  // Context7 RRF Pattern
  const sql = `
    WITH vec_matches AS (
      SELECT
        memory_id,
        ROW_NUMBER() OVER (ORDER BY distance) as rank_number,
        distance
      FROM vec_semantic_memory
      WHERE embedding MATCH ?
        AND k = 10
    ),
    fts_matches AS (
      SELECT
        memory_id,
        ROW_NUMBER() OVER (ORDER BY rank) as rank_number,
        rank as score
      FROM fts_semantic_memory
      WHERE fts_semantic_memory MATCH ?
      LIMIT 10
    ),
    combined AS (
      SELECT
        semantic_memory.id,
        semantic_memory.content,
        semantic_memory.content_type,
        vec_matches.rank_number as vec_rank,
        fts_matches.rank_number as fts_rank,
        (
          COALESCE(1.0 / (60 + fts_matches.rank_number), 0.0) * 1.0
          + COALESCE(1.0 / (60 + vec_matches.rank_number), 0.0) * 1.0
        ) as combined_rank,
        vec_matches.distance as vec_distance,
        fts_matches.score as fts_score
      FROM fts_matches
      FULL OUTER JOIN vec_matches ON vec_matches.memory_id = fts_matches.memory_id
      JOIN semantic_memory ON semantic_memory.id = COALESCE(fts_matches.memory_id, vec_matches.memory_id)
      ORDER BY combined_rank DESC
    )
    SELECT * FROM combined
  `;
  
  const results = db.prepare(sql).all(embeddingBuffer, query);
  
  console.log(`📊 Results: ${results.length}\n`);
  
  results.slice(0, 5).forEach((r, i) => {
    const rankScore = (r.combined_rank * 100).toFixed(1);
    console.log(`${i + 1}. ${r.content_type.toUpperCase()} (RRF: ${rankScore})`);
    
    if (r.vec_rank && r.fts_rank) {
      console.log(`   Vector: #${r.vec_rank} | Keyword: #${r.fts_rank}`);
    } else if (r.vec_rank) {
      console.log(`   Vector Only: #${r.vec_rank} (distance: ${r.vec_distance.toFixed(4)})`);
    } else if (r.fts_rank) {
      console.log(`   Keyword Only: #${r.fts_rank}`);
    }
    
    console.log(`   ${r.content.substring(0, 100)}...\n`);
  });
}

async function main() {
  // Test queries
  const queries = [
    'vector search sqlite',
    'Claude Code integration',
    'embedding generation ollama'
  ];
  
  for (const query of queries) {
    await testHybridSearch(query);
    console.log('-'.repeat(70) + '\n');
  }
  
  db.close();
  console.log('✅ Hybrid search tests completed!');
}

main().catch(console.error);
