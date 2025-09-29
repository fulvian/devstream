#!/usr/bin/env node

/**
 * Test script for DevStream database operations
 * Tests basic connectivity and schema validation
 */

const { DevStreamDatabase } = require('./dist/database.js');

async function testDatabase() {
  const dbPath = process.argv[2] || '/Users/fulvioventura/devstream/data/devstream.db';

  console.log('🔍 Testing DevStream Database Connection...');
  console.log(`Database: ${dbPath}\n`);

  const db = new DevStreamDatabase(dbPath);

  try {
    // Test 1: Initialize connection
    console.log('1️⃣ Testing database initialization...');
    await db.initialize();
    console.log('✅ Database connection successful\n');

    // Test 2: Test connection and schema
    console.log('2️⃣ Testing schema validation...');
    const connectionTest = await db.testConnection();
    if (connectionTest.success) {
      console.log('✅ Schema validation successful');
      console.log(`📊 Tables found: ${connectionTest.tables.join(', ')}\n`);
    } else {
      console.log(`❌ Schema validation failed: ${connectionTest.error}\n`);
      return;
    }

    // Test 3: Query intervention plans
    console.log('3️⃣ Testing intervention plans query...');
    const plans = await db.query('SELECT * FROM intervention_plans LIMIT 3');
    console.log(`✅ Found ${plans.length} intervention plans`);
    plans.forEach(plan => {
      console.log(`   📋 ${plan.title} (${plan.status})`);
    });
    console.log();

    // Test 4: Query tasks
    console.log('4️⃣ Testing micro tasks query...');
    const tasks = await db.query(`
      SELECT mt.*, p.name as phase_name
      FROM micro_tasks mt
      JOIN phases p ON mt.phase_id = p.id
      LIMIT 3
    `);
    console.log(`✅ Found ${tasks.length} micro tasks`);
    tasks.forEach(task => {
      console.log(`   📝 ${task.title} (${task.status}) - Phase: ${task.phase_name}`);
    });
    console.log();

    // Test 5: Query memory entries
    console.log('5️⃣ Testing semantic memory query...');
    const memories = await db.query('SELECT * FROM semantic_memory LIMIT 3');
    console.log(`✅ Found ${memories.length} memory entries`);
    memories.forEach(memory => {
      const preview = memory.content.substring(0, 50) + (memory.content.length > 50 ? '...' : '');
      console.log(`   💾 ${memory.content_type}: ${preview}`);
    });
    console.log();

    console.log('🎉 All database tests passed successfully!');
    console.log('🚀 DevStream MCP Server is ready for deployment\n');

  } catch (error) {
    console.error('❌ Database test failed:', error.message);
    process.exit(1);
  } finally {
    await db.close();
  }
}

// Run tests
testDatabase().catch(console.error);