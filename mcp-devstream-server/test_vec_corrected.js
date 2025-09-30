const sqliteVec = require("sqlite-vec");
const Database = require("better-sqlite3");

console.log("🧪 Testing sqlite-vec with Buffer...\n");

try {
  const db = new Database(":memory:");
  sqliteVec.load(db);
  
  const { vec_version } = db.prepare("SELECT vec_version() as vec_version").get();
  console.log(`✅ vec_version = ${vec_version}`);
  
  db.prepare(`CREATE TABLE test_vectors (id INTEGER PRIMARY KEY, embedding BLOB)`).run();
  
  // Use Buffer.from() to convert Float32Array to Buffer
  const vec1 = new Float32Array([1.0, 2.0, 3.0]);
  const buf1 = Buffer.from(vec1.buffer);
  
  db.prepare("INSERT INTO test_vectors (embedding) VALUES (?)").run(buf1);
  console.log("✅ Vector inserted");
  
  // Query with distance
  const query = new Float32Array([1.0, 2.0, 3.0]);
  const queryBuf = Buffer.from(query.buffer);
  
  const results = db.prepare(`
    SELECT id, vec_distance_L2(embedding, ?) as distance
    FROM test_vectors
  `).all(queryBuf);
  
  console.log("✅ Query results:", results);
  
  db.close();
  console.log("\n🎉 SUCCESS!");
  
} catch (error) {
  console.error("\n❌ Error:", error.message);
  process.exit(1);
}
