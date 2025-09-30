const sqliteVec = require("sqlite-vec");
const Database = require("better-sqlite3");

console.log("🧪 Testing sqlite-vec with DevStream database...\n");

try {
  console.log("1. Opening DevStream database...");
  const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');
  console.log("✅ Database opened");
  
  console.log("\n2. Loading sqlite-vec...");
  sqliteVec.load(db);
  console.log("✅ sqlite-vec loaded");
  
  console.log("\n3. Checking version...");
  const { vec_version } = db.prepare("SELECT vec_version() as vec_version").get();
  console.log(`✅ vec_version = ${vec_version}`);
  
  console.log("\n4. Checking semantic_memory table...");
  const count = db.prepare("SELECT COUNT(*) as count FROM semantic_memory").get();
  console.log(`✅ Found ${count.count} memories in database`);
  
  console.log("\n5. Testing with real embedding from DB...");
  const memory = db.prepare(`
    SELECT id, content_type, embedding 
    FROM semantic_memory 
    WHERE embedding IS NOT NULL 
    LIMIT 1
  `).get();
  
  if (memory) {
    console.log(`✅ Found memory: ${memory.id} (${memory.content_type})`);
    console.log(`   Embedding length: ${memory.embedding ? memory.embedding.length : 0} bytes`);
  } else {
    console.log("⚠️  No memories with embeddings found");
  }
  
  db.close();
  console.log("\n🎉 DevStream database test SUCCESS!");
  
} catch (error) {
  console.error("\n❌ Error:", error.message);
  console.error(error.stack);
  process.exit(1);
}
