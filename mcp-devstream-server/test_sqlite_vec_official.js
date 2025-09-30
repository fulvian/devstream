const sqliteVec = require("sqlite-vec");
const Database = require("better-sqlite3");

console.log("🧪 Testing official sqlite-vec npm package...\n");

try {
  console.log("1. Creating database...");
  const db = new Database(":memory:");
  console.log("✅ Database created");
  
  console.log("\n2. Loading sqlite-vec extension...");
  sqliteVec.load(db);
  console.log("✅ Extension loaded");
  
  console.log("\n3. Checking version...");
  const { vec_version } = db.prepare("SELECT vec_version() as vec_version").get();
  console.log(`✅ vec_version = ${vec_version}`);
  
  console.log("\n4. Creating test vector table...");
  db.prepare(`
    CREATE TABLE test_vectors (
      id INTEGER PRIMARY KEY,
      embedding BLOB
    )
  `).run();
  console.log("✅ Table created");
  
  console.log("\n5. Inserting test vectors...");
  const vec1 = new Float32Array([1.0, 2.0, 3.0]);
  const vec2 = new Float32Array([4.0, 5.0, 6.0]);
  db.prepare("INSERT INTO test_vectors (embedding) VALUES (?)").run(vec1.buffer);
  db.prepare("INSERT INTO test_vectors (embedding) VALUES (?)").run(vec2.buffer);
  console.log("✅ Vectors inserted");
  
  console.log("\n6. Testing vector distance...");
  const query = new Float32Array([1.0, 2.0, 3.0]);
  const results = db.prepare(`
    SELECT id, vec_distance_L2(embedding, ?) as distance
    FROM test_vectors
    ORDER BY distance
    LIMIT 2
  `).all(query.buffer);
  console.log("✅ Distance results:", results);
  
  console.log("\n7. Closing database...");
  db.close();
  console.log("✅ Database closed");
  
  console.log("\n🎉 SUCCESS! sqlite-vec works perfectly with better-sqlite3!");
  process.exit(0);
  
} catch (error) {
  console.error("\n❌ Error:", error.message);
  console.error(error.stack);
  process.exit(1);
}
