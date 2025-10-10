#!/usr/bin/env python3
"""
Full embedding backfill script for DevStream semantic memory
Processes all records without embeddings (41,948 records)
Estimated time: 2-3 hours
"""

import asyncio
import json
import sqlite3
import sys
import time
from pathlib import Path
from datetime import datetime

import aiohttp
import structlog
import sqlite_vec

# Initialize logging
logger = structlog.get_logger()

class EmbeddingBackfiller:
    def __init__(self, db_path: str, ollama_url: str = "http://localhost:11434"):
        self.db_path = Path(db_path)
        self.ollama_url = ollama_url
        self.model = "embeddinggemma:300m"
        self.batch_size = 16
        self.processed_count = 0
        self.error_count = 0

    async def test_connection(self):
        """Test database and Ollama connectivity"""
        logger.info("Testing connectivity for full backfill...")

        # Test database
        try:
            with sqlite3.connect(self.db_path) as db:
                db.enable_load_extension(True)
                sqlite_vec.load(db)

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

    async def get_records_batch(self, offset: int, limit: int):
        """Get a batch of records for backfill"""
        try:
            with sqlite3.connect(self.db_path) as db:
                db.enable_load_extension(True)
                sqlite_vec.load(db)

                records = db.execute("""
                    SELECT id, content, content_type, keywords
                    FROM semantic_memory
                    WHERE embedding IS NULL OR embedding = ''
                    ORDER BY created_at
                    LIMIT ? OFFSET ?
                """, (limit, offset)).fetchall()

                return records
        except Exception as e:
            logger.error("Failed to get records batch", error=str(e), offset=offset, limit=limit)
            return []

    async def generate_embeddings_batch(self, texts: list[str]):
        """Generate embeddings for multiple texts in a single request"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "input": texts
                }

                async with session.post(f"{self.ollama_url}/api/embed", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        embeddings = result["embeddings"]
                        logger.info("Batch embedding generation successful", count=len(embeddings))
                        return embeddings
                    else:
                        logger.error("Batch embedding generation failed", status=response.status)
                        return None
        except Exception as e:
            logger.error("Batch embedding generation error", error=str(e))
            return None

    async def update_records_batch(self, records, embeddings):
        """Update multiple records with embeddings in a single transaction"""
        try:
            with sqlite3.connect(self.db_path) as db:
                db.enable_load_extension(True)
                sqlite_vec.load(db)

                # Temporarily disable triggers to avoid conflicts during backfill
                db.execute("PRAGMA recursive_triggers = OFF")
                db.execute("DROP TRIGGER IF EXISTS sync_update_memory")
                db.execute("DROP TRIGGER IF EXISTS sync_insert_memory")

                # Start transaction
                db.execute("BEGIN TRANSACTION")

                # Update all records in batch
                for i, (record, embedding) in enumerate(zip(records, embeddings)):
                    record_id, content, content_type, keywords = record
                    embedding_json = json.dumps(embedding)

                    db.execute("""
                        UPDATE semantic_memory
                        SET embedding = ?
                        WHERE id = ?
                    """, (embedding_json, record_id))

                # Commit transaction
                db.commit()

                logger.info("Batch update successful", count=len(records))
                return True

        except Exception as e:
            logger.error("Batch update failed", error=str(e))
            return False

    async def process_batch(self, offset: int, batch_number: int, total_batches: int):
        """Process a single batch of records"""
        logger.info(f"Processing batch {batch_number}/{total_batches}", offset=offset)

        # Get records
        records = await self.get_records_batch(offset, self.batch_size)
        if not records:
            logger.info("No more records to process")
            return 0

        # Extract text content for embedding generation
        texts = [record[1] for record in records]  # content field is at index 1

        logger.info(f"Generating embeddings for {len(texts)} texts", batch=batch_number)

        # Generate embeddings
        embeddings = await self.generate_embeddings_batch(texts)
        if not embeddings:
            logger.error("Failed to generate embeddings for batch", batch=batch_number)
            return 0

        # Update records
        success = await self.update_records_batch(records, embeddings)
        if success:
            self.processed_count += len(records)
            logger.info(f"✅ Batch {batch_number} completed",
                       records_processed=len(records),
                       total_processed=self.processed_count,
                       progress=f"{(self.processed_count/total_batches)*100:.1f}%")
            return len(records)
        else:
            self.error_count += len(records)
            logger.error(f"❌ Batch {batch_number} update failed",
                       records_failed=len(records),
                       total_errors=self.error_count)
            return 0

    async def run_full_backfill(self):
        """Run the complete backfill process"""
        logger.info("Starting full backfill process")

        # Test connectivity
        total_without_embeddings = await self.test_connection()
        embedding_dim = await self.test_ollama()

        logger.info("Backfill summary",
                   total_records_without_embeddings=total_without_embeddings,
                   batch_size=self.batch_size,
                   embedding_dimension=embedding_dim,
                   estimated_time=f"{(total_without_embeddings/self.batch_size * 2.5/60):.1f} hours")

        # Calculate total batches
        total_batches = (total_without_embeddings + self.batch_size - 1) // self.batch_size

        start_time = time.time()

        # Process batches
        batch_number = 0
        offset = 0

        while offset < total_without_embeddings:
            batch_number += 1
            records_processed = await self.process_batch(offset, batch_number, total_batches)

            if records_processed == 0:
                logger.warning("No records processed in batch, ending backfill")
                break

            offset += records_processed

            # Add delay between batches to avoid overwhelming Ollama
            await asyncio.sleep(1)  # 1 second delay between batches

            # Log progress every 10 batches
            if batch_number % 10 == 0:
                elapsed_time = time.time() - start_time
                rate = self.processed_count / elapsed_time if elapsed_time > 0 else 0
                eta_minutes = (total_without_embeddings - self.processed_count) / rate / 60 if rate > 0 else 0
                logger.info("Progress update",
                           batch=batch_number,
                           processed=self.processed_count,
                           remaining=total_without_embeddings - self.processed_count,
                           elapsed=f"{elapsed_time/60:.1f}min",
                           rate=f"{rate:.1f} records/min",
                           eta=f"{eta_minutes:.1f}min")

        # Final summary
        end_time = time.time()
        elapsed_time = end_time - start_time

        logger.info("Full backfill completed",
                   success=self.processed_count,
                   errors=self.error_count,
                   total_time=f"{elapsed_time/60:.1f}min",
                   average_rate=f"{self.processed_count/elapsed_time:.1f} records/min",
                   coverage=f"{(self.processed_count/total_without_embeddings)*100:.1f}%")

        # Update coverage in database
        try:
            with sqlite3.connect(self.db_path) as db:
                db.enable_load_extension(True)
                sqlite_vec.load(db)

                final_count = db.execute("SELECT COUNT(*) FROM semantic_memory WHERE embedding IS NOT NULL AND embedding != ''").fetchone()[0]
                final_coverage = (final_count / (total_without_embeddings + self.processed_count)) * 100

                logger.info("Final coverage achieved",
                           with_embeddings=final_count,
                           coverage=f"{final_coverage:.1f}%")

        except Exception as e:
            logger.error("Failed to calculate final coverage", error=str(e))

        return self.error_count == 0

async def main():
    """Main backfill function"""
    db_path = "data/devstream.db"

    backfiller = EmbeddingBackfiller(db_path)

    try:
        print("🚀 Starting full embedding backfill...")
        print(f"   Database: {db_path}")
        print(f"   Model: embeddinggemma:300m")
        print(f"   Batch size: 16 records")
        print(f"   Estimated time: ~2-3 hours")
        print()

        success = await backfiller.run_full_backfill()

        if success:
            print("\n🎉 Full backfill completed successfully!")
            print(f"   ✅ Records processed: {backfiller.processed_count}")
            print(f"   ✅ Errors: {backfiller.error_count}")
            print(f"   ✅ Time elapsed: {(time.time() - start_time)/60:.1f} minutes")
        else:
            print("\n❌ Backfill completed with errors!")
            print(f"   ⚠️  Records processed: {backfiller.processed_count}")
            print(f"   ⚠️  Errors: {backfiller.error_count}")
            print(f"   ⚠️  Time elapsed: {(time.time() - start_time)/60:.1f} minutes")
            sys.exit(1)

    except Exception as e:
        logger.error("Backfill execution failed", error=str(e))
        print(f"\n❌ Backfill failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(main())
    end_time = time.time()
    print(f"\nTotal execution time: {(end_time - start_time)/60:.1f} minutes")