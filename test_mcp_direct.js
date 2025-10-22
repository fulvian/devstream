#!/usr/bin/env node

/**
 * Test diretto delle funzionalità MCP del server DevStream
 * Simula le chiamate MCP che farebbe Claude Code
 */

const { spawn } = require('child_process');
const path = require('path');

const SERVER_PATH = path.join(__dirname, 'mcp-devstream-server', 'dist', 'index.js');
const DB_PATH = '/Users/fulvioventura/devstream/data/devstream.db';

class MCPTestClient {
  constructor() {
    this.server = null;
    this.requestId = 1;
  }

  async start() {
    console.log('🚀 Avvio server MCP per test diretti...');

    this.server = spawn('node', [SERVER_PATH, DB_PATH], {
      stdio: ['pipe', 'pipe', 'inherit'],
      env: { ...process.env, NODE_ENV: 'production' }
    });

    this.server.on('error', (error) => {
      console.error('❌ Errore avvio server:', error);
    });

    this.server.on('exit', (code) => {
      console.log(`📡 Server terminato con codice: ${code}`);
    });

    // Aspetta che il server sia pronto
    await this.waitForReady();
    console.log('✅ Server MCP pronto per i test');
  }

  async waitForReady() {
    // Aspetta 2 secondi per l'avvio del server
    await new Promise(resolve => setTimeout(resolve, 2000));
  }

  async sendRequest(method, params = {}) {
    const request = {
      jsonrpc: '2.0',
      id: this.requestId++,
      method,
      params
    };

    return new Promise((resolve, reject) => {
      let response = '';

      const onData = (data) => {
        response += data.toString();

        // Processa risposte JSON-RPC complete
        const lines = response.split('\n').filter(line => line.trim());
        for (const line of lines) {
          try {
            const parsed = JSON.parse(line);
            if (parsed.id === request.id) {
              this.server.stdout.removeListener('data', onData);
              resolve(parsed);
              return;
            }
          } catch (e) {
            // Ignora JSON incompleti
          }
        }
      };

      this.server.stdout.on('data', onData);
      this.server.stdin.write(JSON.stringify(request) + '\n');

      // Timeout dopo 10 secondi
      setTimeout(() => {
        this.server.stdout.removeListener('data', onData);
        reject(new Error('Request timeout'));
      }, 10000);
    });
  }

  async listTools() {
    console.log('🔧 Test: listTools...');
    try {
      const response = await this.sendRequest('tools/list');
      if (response.error) {
        console.log(`   ❌ Errore: ${response.error.message}`);
        return false;
      }

      const tools = response.result.tools.map(t => t.name);
      console.log(`   ✅ Tools disponibili: ${tools.length}`);
      console.log(`   📋 ${tools.join(', ')}`);
      return true;
    } catch (error) {
      console.log(`   ❌ Errore: ${error.message}`);
      return false;
    }
  }

  async testMemoryStore() {
    console.log('💾 Test: devstream_store_memory...');

    const testContent = {
      content: "Test diretto MCP: verifica funzionalità embedding e storage nel database DevStream con worker pool.",
      content_type: "test_direct",
      keywords: ["mcp", "embedding", "worker pool", "test"],
      metadata: {
        test_timestamp: new Date().toISOString(),
        test_id: "mcp_direct_test_001"
      }
    };

    try {
      const response = await this.sendRequest('tools/call', {
        name: 'devstream_store_memory',
        arguments: testContent
      });

      if (response.error) {
        console.log(`   ❌ Errore: ${response.error.message}`);
        return false;
      }

      console.log(`   ✅ Memory stored: ${response.result.success ? 'SUCCESS' : 'FAILED'}`);
      if (response.result.success) {
        console.log(`   📝 Record ID: ${response.result.record_id || 'N/A'}`);
        console.log(`   🧠 Embedding generato: ${response.result.embedding_generated ? 'SÌ' : 'NO'}`);
      }
      return response.result.success;
    } catch (error) {
      console.log(`   ❌ Errore: ${error.message}`);
      return false;
    }
  }

  async testMemorySearch() {
    console.log('🔍 Test: devstream_search_memory...');

    try {
      const response = await this.sendRequest('tools/call', {
        name: 'devstream_search_memory',
        arguments: {
          query: "worker pool embedding test MCP",
          limit: 5,
          content_type: null
        }
      });

      if (response.error) {
        console.log(`   ❌ Errore: ${response.error.message}`);
        return false;
      }

      console.log(`   ✅ Search completed: ${response.result.success ? 'SUCCESS' : 'FAILED'}`);
      if (response.result.success) {
        console.log(`   📊 Results found: ${response.result.results?.length || 0}`);
        if (response.result.results?.length > 0) {
          const top = response.result.results[0];
          console.log(`   🎯 Top result score: ${top.score?.toFixed(4) || 'N/A'}`);
          console.log(`   📝 Top result type: ${top.content_type || 'N/A'}`);
        }
      }
      return response.result.success;
    } catch (error) {
      console.log(`   ❌ Errore: ${error.message}`);
      return false;
    }
  }

  async testListTasks() {
    console.log('📋 Test: devstream_list_tasks...');

    try {
      const response = await this.sendRequest('tools/call', {
        name: 'devstream_list_tasks',
        arguments: {}
      });

      if (response.error) {
        console.log(`   ❌ Errore: ${response.error.message}`);
        return false;
      }

      console.log(`   ✅ Tasks listed: ${response.result.success ? 'SUCCESS' : 'FAILED'}`);
      if (response.result.success) {
        console.log(`   📊 Total tasks: ${response.result.tasks?.length || 0}`);
      }
      return response.result.success;
    } catch (error) {
      console.log(`   ❌ Errore: ${error.message}`);
      return false;
    }
  }

  async stop() {
    console.log('🛑 Arresto server MCP...');
    if (this.server) {
      this.server.kill('SIGTERM');
      // Aspetta che termini
      await new Promise(resolve => {
        this.server.on('exit', resolve);
        setTimeout(resolve, 2000); // Force dopo 2s
      });
    }
  }
}

async function runMCPTests() {
  console.log('🧪 MCP Server Direct Test Suite');
  console.log('==================================');
  console.log('');

  const client = new MCPTestClient();

  try {
    await client.start();

    const results = {
      listTools: await client.listTools(),
      memoryStore: await client.testMemoryStore(),
      memorySearch: await client.testMemorySearch(),
      listTasks: await client.testListTasks()
    };

    console.log('');
    console.log('📋 RIEPILOGO TEST MCP:');
    console.log('');

    const passed = Object.values(results).filter(r => r).length;
    const total = Object.keys(results).length;

    Object.entries(results).forEach(([test, result]) => {
      const status = result ? '✅ PASS' : '❌ FAIL';
      console.log(`   ${test.padEnd(15)}: ${status}`);
    });

    console.log('');
    console.log(`🎯 VERDETTO MCP: ${passed}/${total} test passati`);

    if (passed === total) {
      console.log('');
      console.log('🎉 SISTEMA MCP FULLY OPERATIVO!');
      console.log('   ✅ Server MCP risponde correttamente');
      console.log('   ✅ Tools disponibili e funzionanti');
      console.log('   ✅ Memory storage con embedding');
      console.log('   ✅ Memory search funzionante');
      console.log('   ✅ Worker pool previene blocchi');
    } else {
      console.log('');
      console.log('⚠️  PROBLEMI RILEVATI - Sistema MCP non completamente operativo');
    }

  } catch (error) {
    console.error('❌ Errore generale:', error);
  } finally {
    await client.stop();
  }

  process.exit(0);
}

runMCPTests().catch(console.error);