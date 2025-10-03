#!/usr/bin/env node
/**
 * Synthetic API Proxy - Model Name Translator
 *
 * Purpose: Intercepts Claude Code requests and translates Claude model names
 *          to Synthetic HuggingFace model names (adds "hf:" prefix)
 *
 * Usage: node synthetic-proxy.js
 * Then configure Claude Code to use: http://localhost:3100
 */

const http = require('http');
const https = require('https');

const PORT = 3100;
const SYNTHETIC_API_KEY = process.env.SYNTHETIC_API_KEY;
const SYNTHETIC_MODEL = process.env.SYNTHETIC_MODEL || 'hf:zai-org/GLM-4.6';
const TARGET_HOST = 'api.synthetic.new';

if (!SYNTHETIC_API_KEY) {
  console.error('❌ Error: SYNTHETIC_API_KEY environment variable not set');
  process.exit(1);
}

const server = http.createServer((req, res) => {
  console.log(`\n📨 ${req.method} ${req.url}`);

  let body = '';
  req.on('data', chunk => {
    body += chunk.toString();
  });

  req.on('end', () => {
    try {
      // Parse request body
      const requestData = JSON.parse(body || '{}');

      // Translate model name: any Claude model → Synthetic HF model
      if (requestData.model) {
        console.log(`🔄 Model translation: ${requestData.model} → ${SYNTHETIC_MODEL}`);
        requestData.model = SYNTHETIC_MODEL;
      }

      // Proxy request to Synthetic
      const options = {
        hostname: TARGET_HOST,
        port: 443,
        path: '/anthropic' + req.url,
        method: req.method,
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': SYNTHETIC_API_KEY,
          'Content-Length': Buffer.byteLength(JSON.stringify(requestData))
        }
      };

      const proxyReq = https.request(options, proxyRes => {
        console.log(`✅ Synthetic response: ${proxyRes.statusCode}`);

        res.writeHead(proxyRes.statusCode, proxyRes.headers);
        proxyRes.pipe(res);
      });

      proxyReq.on('error', err => {
        console.error(`❌ Proxy error: ${err.message}`);
        res.writeHead(500);
        res.end(JSON.stringify({ error: err.message }));
      });

      proxyReq.write(JSON.stringify(requestData));
      proxyReq.end();

    } catch (err) {
      console.error(`❌ Parse error: ${err.message}`);
      res.writeHead(400);
      res.end(JSON.stringify({ error: 'Invalid JSON' }));
    }
  });
});

server.listen(PORT, () => {
  console.log(`
🚀 Synthetic Proxy Server Running
   Local:  http://localhost:${PORT}
   Target: https://${TARGET_HOST}/anthropic
   Model:  ${SYNTHETIC_MODEL}

⚙️  Configure Claude Code:
   export ANTHROPIC_BASE_URL="http://localhost:${PORT}"
   export ANTHROPIC_AUTH_TOKEN="synthetic-proxy"
`);
});
