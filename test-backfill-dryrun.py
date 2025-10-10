#!/usr/bin/env python3
"""
Test script for embedding backfill - Dry run with 5 records
Tests the backfill process before running on full dataset
"""

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

import aiohttp
import structlog
import sqlite_vec

# Initialize logging
logger = structlog.get_logger()

class EmbeddingBackfillTester:
    def __init__(self, db_path: str, ollama_url: str = "http://localhost:11434"):
        self.db_path = Path(db_path)
        self.ollama_url = ollama_url
        self.model = "embeddinggemma:300m"

    async def test_connection(self):
        """Test database and Ollama connectivity"""
        logger.info("Testing connectivity...")

        # Test database
        try:
            with sqlite3.connect(self.db_path) as db:
                count = db.execute("SELECT COUNT(*) FROM semantic_memory WHERE embedding IS NULL OR embedding = ''").fetchone()[0]
                logger.info("Database accessible", records_without_embeddings=count)
                return count
        except Exception as e:
            logger.error("Database connection failed", error=str(e))
            raise

    async def test_ollama(self):
        """Test Ollama embedding endpoint"""
        logger.info("Testing Ollama embedding endpoint...")

        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "input": "test message"
                }

                async with session.post(f"{self.ollama_url}/api/embed", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        embedding_dim = len(result["embeddings"][0])
                        logger.info("Ollama working", embedding_dim=embedding_dim, model=self.model)
                        return embedding_dim
                    else:
                        logger.error("Ollama request failed", status=response.status)
                        raise Exception(f"Ollama returned {response.status}")
        except Exception as e:
            logger.error("Ollama connection failed", error=str(e))
            raise

    async def get_sample_records(self, limit: int = 5):
        """Get sample records for backfill testing"""
        logger.info("Getting sample records for backfill test", limit=limit)

        with sqlite3.connect(self.db_path) as db:
            records = db.execute("""
                SELECT id, content, content_type, keywords
                FROM semantic_memory
                WHERE embedding IS NULL OR embedding = ''
                LIMIT ?
            """, (limit,)).fetchall()

            logger.info("Retrieved sample records", count=len(records))
            return records

    async def generate_embedding(self, text: str):
        """Generate embedding for a single text"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "input": text
                }

                async with session.post(f"{self.ollama_url}/api/embed", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return json.dumps(result["embeddings"][0])
                    else:
                        logger.error("Embedding generation failed", status=response.status, text=text[:50])
                        return None
        except Exception as e:
            logger.error("Embedding generation error", error=str(e), text=text[:50])
            return None

    async def backfill_record(self, record):
        """Backfill a single record"""
        record_id, content, content_type, keywords = record

        logger.info("Processing record", id=record_id, content_type=content_type, content_preview=content[:100])

        # Generate embedding
        embedding_json = await self.generate_embedding(content)
        if not embedding_json:
            return False, "Embedding generation failed"

        # Update database
        try:
            with sqlite3.connect(self.db_path) as db:
                # Load sqlite-vec extension
                db.enable_load_extension(True)
                sqlite_vec.load(db)

                logger.info("sqlite-vec extension loaded", id=record_id)

                # Temporarily disable triggers to avoid conflicts during backfill
                db.execute("PRAGMA recursive_triggers = OFF")
                db.execute("DROP TRIGGER IF EXISTS sync_update_memory")
                db.execute("DROP TRIGGER IF EXISTS sync_insert_memory")

                # Update semantic_memory table
                db.execute("""
                    UPDATE semantic_memory
                    SET embedding = ?
                    WHERE id = ?
                """, (embedding_json, record_id))
                db.commit()

            logger.info("Record updated successfully", id=record_id)
            return True, "Success"

        except Exception as e:
            logger.error("Database update failed", id=record_id, error=str(e))
            return False, str(e)

    async def run_dryrun(self, limit: int = 5):
        """Run dry-run backfill test"""
        logger.info("Starting dry-run backfill test", limit=limit)

        # Test connectivity
        total_without_embeddings = await self.test_connection()
        embedding_dim = await self.test_ollama()

        # Get sample records
        records = await self.get_sample_records(limit)
        if not records:
            logger.warning("No records found for backfill test")
            return True

        logger.info("Starting backfill test", records_to_process=len(records))

        # Process records
        success_count = 0
        error_count = 0

        for i, record in enumerate(records, 1):
            logger.info(f"Processing record {i}/{len(records)}")
            success, message = await self.backfill_record(record)

            if success:
                success_count += 1
                logger.info("✅ Record processed successfully", id=record[0])
            else:
                error_count += 1
                logger.error("❌ Record processing failed", id=record[0], error=message)

        # Summary
        logger.info("Dry-run backfill test completed",
                   success=success_count,
                   errors=error_count,
                   total_processed=len(records),
                   embedding_dimension=embedding_dim,
                   remaining_without_embeddings=total_without_embeddings - success_count)

        return error_count == 0

async def main():
    """Main test function"""
    db_path = "data/devstream.db"

    tester = EmbeddingBackfillTester(db_path)

    try:
        success = await tester.run_dryrun(limit=5)
        if success:
            logger.info("🎉 Dry-run backfill test PASSED")
            print("\n✅ Dry-run test successful! Ready for full backfill.")
        else:
            logger.error("❌ Dry-run backfill test FAILED")
            print("\n❌ Dry-run test failed. Check logs and fix issues before full backfill.")
            sys.exit(1)

    except Exception as e:
        logger.error("Test execution failed", error=str(e))
        print(f"\n❌ Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())