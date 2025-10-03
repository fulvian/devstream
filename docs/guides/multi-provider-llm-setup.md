# Multi-Provider LLM Setup Guide

**Version**: 1.0.0 | **Last Updated**: 2025-10-03 | **Status**: Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Configuration](#configuration)
   - [z.ai Setup](#zai-setup)
   - [Synthetic Setup](#synthetic-setup)
   - [Anthropic Setup (Default)](#anthropic-setup-default)
4. [Usage](#usage)
5. [Troubleshooting](#troubleshooting)
6. [Future Providers](#future-providers-phase-2)
7. [Architecture Notes](#architecture-notes)

---

## Overview

### What is Multi-Provider LLM Integration?

DevStream supports **alternative LLM providers** as drop-in replacements for Anthropic's Claude API. This allows you to:

- **Reduce costs** by using alternative providers with lower pricing
- **Access specific models** not available through Anthropic (e.g., GLM-4.6, HuggingFace models)
- **Maintain availability** when primary provider has outages
- **Experiment** with different model architectures

### Supported Providers (Phase 1)

| Provider | Status | Best For | Cost |
|----------|--------|----------|------|
| **Anthropic** | ✅ Default | Production, highest quality | $$ |
| **z.ai** | ✅ Supported | GLM-4.6 models, cost reduction | $ |
| **Synthetic** | ✅ Supported | HuggingFace models, experimentation | $ |
| **nano-gpt** | 🚧 Phase 2 | Lightweight custom models | $ |
| **OpenRouter** | 🚧 Phase 2 | Multi-provider aggregation | $$ |

### Why Use Alternative Providers?

**Use z.ai when:**
- ✅ You want 50%+ cost reduction vs Anthropic
- ✅ GLM-4.6 model capabilities match your use case
- ✅ You prioritize response speed (glm-4.5-air)

**Use Synthetic when:**
- ✅ You want access to HuggingFace model ecosystem
- ✅ Experimenting with cutting-edge models
- ✅ You need flexible model selection

**Use Anthropic (default) when:**
- ✅ Production workloads requiring highest quality
- ✅ Complex reasoning tasks
- ✅ Official support and SLA guarantees

---

## Prerequisites

### Required Software

1. **Claude Code CLI** (v1.0.0+)
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```

2. **DevStream Project**
   ```bash
   git clone https://github.com/yourusername/devstream.git
   cd devstream
   ```

3. **curl** (for API validation)
   - macOS: Pre-installed
   - Linux: `sudo apt install curl`

### Required API Keys

Obtain API keys from your chosen provider:

| Provider | Registration URL | API Key Location |
|----------|------------------|------------------|
| **z.ai** | https://z.ai/ | https://z.ai/manage-apikey/apikey-list |
| **Synthetic** | https://synthetic.new/ | https://synthetic.new/dashboard |
| **Anthropic** | https://console.anthropic.com/ | https://console.anthropic.com/settings/keys |

---

## Configuration

### z.ai Setup

#### Step 1: Get API Key

1. Register at **https://z.ai/**
2. Navigate to **API Key Management**: https://z.ai/manage-apikey/apikey-list
3. Click **"Create New Key"** → Copy the generated key

#### Step 2: Configure `.env.llm-providers`

Open `.env.llm-providers` in the project root and fill in:

```bash
# Z.AI PROVIDER CONFIGURATION
ZAI_BASE_URL=https://api.z.ai/api/anthropic
ZAI_API_KEY=your-z-ai-api-key-here  # ← PASTE YOUR KEY HERE
ZAI_MODEL_OPUS=glm-4.6
ZAI_MODEL_SONNET=glm-4.6
ZAI_MODEL_HAIKU=glm-4.5-air
```

#### Step 3: Set as Default Provider (Optional)

To make z.ai your default provider, edit `.env.llm-providers`:

```bash
DEVSTREAM_LLM_PROVIDER=z.ai
```

#### Model Mappings

z.ai automatically maps Anthropic models to GLM equivalents:

| Anthropic Model | z.ai Equivalent | Use Case |
|-----------------|-----------------|----------|
| `claude-opus-4-5` | `glm-4.6` | Complex reasoning, long contexts |
| `claude-sonnet-4-5` | `glm-4.6` | Balanced performance/cost |
| `claude-haiku-4-5` | `glm-4.5-air` | Ultra-fast responses, simple tasks |

#### Validation Strategy

z.ai uses **fast validation** (key existence check only):
- ✅ **Pros**: Near-instant startup (<100ms validation)
- ⚠️ **Cons**: Invalid key detected only at first API call

### Synthetic Setup

#### Step 1: Get API Key

1. Register at **https://synthetic.new/**
2. Navigate to **Dashboard**: https://synthetic.new/dashboard
3. Copy your **API Key** from the dashboard

#### Step 2: Configure Root `.env`

Create or edit `.env` in the project root:

```bash
# SYNTHETIC PROVIDER CONFIGURATION
SYNTHETIC_API_KEY=your-synthetic-api-key-here  # ← PASTE YOUR KEY HERE
```

#### Step 3: Configure `.env.llm-providers`

Open `.env.llm-providers` and customize:

```bash
# SYNTHETIC PROVIDER CONFIGURATION
SYNTHETIC_BASE_URL=https://api.synthetic.new/anthropic/v1
SYNTHETIC_MODEL=hf:zai-org/GLM-4.6  # ← CUSTOMIZE MODEL HERE
SYNTHETIC_TIER=pro  # Options: standard | pro | usage-based
```

#### Step 4: Set as Default Provider (Optional)

```bash
DEVSTREAM_LLM_PROVIDER=synthetic
```

#### Model Selection

Synthetic supports **HuggingFace models** via `hf:` prefix:

```bash
# Example: Use Meta's Llama model
SYNTHETIC_MODEL=hf:meta-llama/Llama-3-8B

# Example: Use Mistral model
SYNTHETIC_MODEL=hf:mistralai/Mistral-7B-v0.1

# Example: Use default GLM-4.6
SYNTHETIC_MODEL=hf:zai-org/GLM-4.6
```

Browse available models: **https://huggingface.co/models**

#### Validation Strategy

Synthetic uses **full validation** (API connectivity test):
- ✅ **Pros**: Detects invalid keys/unreachable endpoints at startup
- ⚠️ **Cons**: Slower startup (~2-5 seconds for validation)

### Anthropic Setup (Default)

#### Step 1: Get API Key

1. Register at **https://console.anthropic.com/**
2. Navigate to **Settings → API Keys**
3. Click **"Create Key"** → Copy the key (starts with `sk-ant-`)

#### Step 2: Configure Environment

Add to your shell profile (`~/.bashrc`, `~/.zshrc`, or `~/.profile`):

```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Reload your shell:
```bash
source ~/.bashrc  # or ~/.zshrc
```

#### Step 3: Verify Configuration

```bash
echo $ANTHROPIC_API_KEY
# Should output: sk-ant-your-key-here
```

**No additional configuration required** - this is the default provider.

---

## Usage

### Quick Start

#### Option 1: Use Specific Provider (One-Time)

```bash
# Use z.ai for this session
./scripts/start-devstream.sh z.ai

# Use Synthetic for this session
./scripts/start-devstream.sh synthetic

# Use Anthropic (default) for this session
./scripts/start-devstream.sh anthropic
```

#### Option 2: Set Default Provider (Persistent)

Edit `.env.llm-providers`:

```bash
# Set default provider
DEVSTREAM_LLM_PROVIDER=synthetic  # or z.ai, or anthropic
```

Then simply run:

```bash
./scripts/start-devstream.sh
# Uses provider set in .env.llm-providers
```

### CLI Examples

#### Example 1: Cost-Optimized Development (z.ai)

```bash
# Configure z.ai once
# 1. Edit .env.llm-providers: ZAI_API_KEY=your-key
# 2. Edit .env.llm-providers: DEVSTREAM_LLM_PROVIDER=z.ai

# Launch DevStream
./scripts/start-devstream.sh

# Output:
# ✅ Provider: z.ai (GLM Models)
#    Base URL: https://api.z.ai/api/anthropic
#    Model Mappings:
#      • claude-opus-4-5 → glm-4.6
#      • claude-sonnet-4-5 → glm-4.6
#      • claude-haiku-4-5 → glm-4-flash
```

#### Example 2: Experimental Models (Synthetic)

```bash
# Configure Synthetic for HuggingFace model
# 1. Edit .env: SYNTHETIC_API_KEY=your-key
# 2. Edit .env.llm-providers: SYNTHETIC_MODEL=hf:meta-llama/Llama-3-8B

# Launch with Synthetic
./scripts/start-devstream.sh synthetic

# Output:
# 🔍 Testing Synthetic API connectivity...
# ✅ Synthetic API is reachable (HTTP 200)
# ✅ Provider: Synthetic.new
#    Base URL: https://api.synthetic.new/anthropic/v1
#    Model: claude-sonnet-4-5 (Synthetic)
#    Tier: pro
```

#### Example 3: Switch Providers Mid-Development

```bash
# Start with z.ai (cost-effective)
./scripts/start-devstream.sh z.ai
# ... work on feature ...
# (exit Claude Code)

# Switch to Anthropic for complex reasoning
./scripts/start-devstream.sh anthropic
# ... continue with higher-quality model ...
```

### Environment Variable Override

You can override the default provider using an environment variable:

```bash
# One-time override (no config file edit)
export DEVSTREAM_LLM_PROVIDER=synthetic
./scripts/start-devstream.sh

# Or inline
DEVSTREAM_LLM_PROVIDER=z.ai ./scripts/start-devstream.sh
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Missing API Key

**Symptom:**
```
❌ Error: ZAI_API_KEY is not set
Please configure ZAI_API_KEY in .env.llm-providers or .env
```

**Solution:**
1. Open `.env.llm-providers` (for z.ai) or `.env` (for Synthetic)
2. Add your API key:
   ```bash
   # For z.ai
   ZAI_API_KEY=your-key-here

   # For Synthetic
   SYNTHETIC_API_KEY=your-key-here
   ```
3. Verify key was saved: `grep API_KEY .env.llm-providers`

#### Issue 2: Synthetic API Unreachable

**Symptom:**
```
❌ Error: Cannot reach Synthetic API (connection timeout/failed)
Check your network connection and SYNTHETIC_BASE_URL
```

**Solution:**

**Step 1: Verify API Key**
```bash
# Check key is set
grep SYNTHETIC_API_KEY .env
# Should output: SYNTHETIC_API_KEY=your-key-here
```

**Step 2: Test API Manually**
```bash
curl -X POST https://api.synthetic.new/anthropic/v1/messages \
  -H "x-api-key: your-synthetic-api-key-here" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-sonnet-4-5",
    "max_tokens": 10,
    "messages": [{"role": "user", "content": "test"}]
  }'
```

**Expected Response:**
- ✅ `200 OK`: API working
- ✅ `401 Unauthorized`: API reachable (check key)
- ✅ `400 Bad Request`: API reachable (syntax error)
- ❌ `Connection timeout`: Network issue

**Step 3: Check Network**
```bash
# Test DNS resolution
nslookup api.synthetic.new

# Test connectivity
ping api.synthetic.new
```

#### Issue 3: Provider Not Recognized

**Symptom:**
```
⚠️ Unknown provider: synthtic
Valid options: anthropic | z.ai | synthetic
Falling back to Anthropic default
```

**Solution:**
Check spelling matches exactly: `z.ai`, `synthetic`, or `anthropic` (case-sensitive)

```bash
# ❌ Wrong
./scripts/start-devstream.sh synthtic
./scripts/start-devstream.sh Z.AI

# ✅ Correct
./scripts/start-devstream.sh synthetic
./scripts/start-devstream.sh z.ai
```

#### Issue 4: Permission Denied

**Symptom:**
```
bash: ./scripts/start-devstream.sh: Permission denied
```

**Solution:**
```bash
# Make script executable
chmod +x scripts/start-devstream.sh

# Verify permissions
ls -la scripts/start-devstream.sh
# Should show: -rwxr-xr-x (executable)
```

#### Issue 5: Invalid z.ai Key (Detected Late)

**Symptom:**
- ✅ Script starts successfully
- ❌ First API call fails with authentication error

**Solution:**
z.ai uses **fast validation** (no API test at startup). Invalid keys are detected at first use.

```bash
# Verify key format (should be long alphanumeric string)
echo $ZAI_API_KEY

# Test key manually
curl -X POST https://api.z.ai/api/anthropic/v1/messages \
  -H "x-api-key: your-zai-key-here" \
  -H "Content-Type: application/json" \
  -d '{"model":"glm-4.6","messages":[{"role":"user","content":"test"}],"max_tokens":1}'
```

If authentication fails, regenerate key at: https://z.ai/manage-apikey/apikey-list

### Debugging Tools

#### Check Exported Environment Variables

```bash
# After running start-devstream.sh
echo $ANTHROPIC_BASE_URL
# Expected:
#   z.ai: https://api.z.ai/api/anthropic
#   Synthetic: https://api.synthetic.new/anthropic/v1
#   Anthropic: (empty or https://api.anthropic.com)

echo $ANTHROPIC_AUTH_TOKEN
# Should output your API key (first 10 chars safe to check)
```

#### Verify Configuration Loading

```bash
# Test .env.llm-providers loading
source .env.llm-providers
echo $DEVSTREAM_LLM_PROVIDER
# Should output: z.ai, synthetic, or anthropic

echo $ZAI_BASE_URL
# Should output: https://api.z.ai/api/anthropic
```

#### Check DevStream Logs

```bash
# View DevStream hook logs
tail -f ~/.claude/logs/devstream/hook_execution.log

# Search for provider mentions
grep -i "provider" ~/.claude/logs/devstream/*.log
```

---

## Future Providers (Phase 2)

### Planned Support

#### nano-gpt Provider

**Status**: 🚧 Not Yet Implemented

**Use Case**: Lightweight custom models for resource-constrained environments

**Planned Configuration**:
```bash
# .env.llm-providers (Phase 2)
NANOGPT_BASE_URL=http://localhost:8080
NANOGPT_API_KEY=your-key
NANOGPT_MODEL=nano-gpt-3.5
```

**Estimated Release**: Q2 2025

#### OpenRouter Provider

**Status**: 🚧 Not Yet Implemented

**Use Case**: Multi-provider aggregation with automatic fallback

**Planned Configuration**:
```bash
# .env.llm-providers (Phase 2)
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=your-key
OPENROUTER_MODEL=anthropic/claude-sonnet-4-5
```

**Features**:
- Automatic provider fallback (Anthropic → OpenAI → Cohere)
- Cost optimization (route to cheapest provider)
- Load balancing across providers

**Estimated Release**: Q2 2025

---

## Architecture Notes

### How Multi-Provider Works

DevStream uses **Anthropic Base URL Override** to route Claude API calls through alternative providers:

```
Claude Code CLI
    ↓
ANTHROPIC_BASE_URL override (z.ai or Synthetic)
    ↓
Alternative Provider (translates to native API)
    ↓
Native LLM (GLM-4.6, HuggingFace models, etc.)
    ↓
Response formatted as Claude API response
    ↓
Claude Code CLI (receives response)
```

### Provider Scripts Architecture

**Launcher Hierarchy**:
```
scripts/start-devstream.sh (Main launcher)
    ├── Provider Selection Logic (normalize aliases)
    ├── Validation Functions
    │   ├── validate_api_key() - Check key presence
    │   └── test_synthetic_api() - Full connectivity test
    └── Provider Configuration
        ├── scripts/providers/zai.sh (z.ai config)
        └── scripts/providers/synthetic.sh (Synthetic config)
```

**Configuration Files**:
```
.env.llm-providers (Provider settings)
    ├── DEVSTREAM_LLM_PROVIDER (default provider)
    ├── ZAI_* variables (z.ai config)
    ├── SYNTHETIC_* variables (Synthetic config)
    └── ANTHROPIC_* variables (Anthropic config)

.env (Project-wide secrets)
    ├── SYNTHETIC_API_KEY (Synthetic key)
    └── ANTHROPIC_API_KEY (Anthropic key)
```

### Validation Strategies

| Provider | Strategy | Startup Time | Error Detection |
|----------|----------|--------------|-----------------|
| **z.ai** | Fast (key check only) | ~100ms | At first API call |
| **Synthetic** | Full (API test) | ~2-5 seconds | At startup |
| **Anthropic** | Environment check | ~50ms | At first API call |

**Design Decision**: Synthetic uses full validation because its API is less stable than z.ai. This ensures early failure detection.

### Environment Variable Precedence

**Priority Order** (highest to lowest):
1. **CLI Argument**: `./start-devstream.sh synthetic`
2. **Environment Variable**: `export DEVSTREAM_LLM_PROVIDER=z.ai`
3. **Config File**: `.env.llm-providers` → `DEVSTREAM_LLM_PROVIDER=anthropic`
4. **Default**: `anthropic`

Example:
```bash
# Config file says: DEVSTREAM_LLM_PROVIDER=z.ai
# But CLI overrides:
./scripts/start-devstream.sh synthetic
# Result: Synthetic provider used (CLI takes precedence)
```

---

## Best Practices

### Development Workflow

✅ **Do:**
- Use **z.ai for development** (cost-effective, fast)
- Use **Anthropic for production** (highest quality, SLA)
- Use **Synthetic for experimentation** (access to new models)
- **Test provider switches** before production deployment
- **Monitor API costs** across providers

❌ **Don't:**
- Don't commit API keys to git (use `.env`, `.env.llm-providers`)
- Don't use Synthetic for production (less stable than Anthropic)
- Don't switch providers mid-task without testing
- Don't assume all providers support same features

### Cost Optimization

**Scenario: Multi-Phase Development**

1. **Prototyping** (z.ai - ultra-fast responses)
   ```bash
   DEVSTREAM_LLM_PROVIDER=z.ai ./scripts/start-devstream.sh
   ```

2. **Feature Development** (z.ai - cost-effective)
   ```bash
   ./scripts/start-devstream.sh z.ai
   ```

3. **Code Review** (Anthropic - highest quality)
   ```bash
   ./scripts/start-devstream.sh anthropic
   ```

4. **Production** (Anthropic - SLA guarantees)
   ```bash
   export DEVSTREAM_LLM_PROVIDER=anthropic
   ./scripts/start-devstream.sh
   ```

**Estimated Cost Savings**: 50-70% vs Anthropic-only workflow

---

## Support

### Documentation

- **DevStream Docs**: `docs/guides/`
- **Context7 Integration**: `docs/guides/context7-integration.md`
- **Troubleshooting**: `docs/user-guide/troubleshooting.md`

### Community

- **Issues**: https://github.com/yourusername/devstream/issues
- **Discussions**: https://github.com/yourusername/devstream/discussions

### Provider Support

| Provider | Support Channel |
|----------|-----------------|
| **z.ai** | https://z.ai/support |
| **Synthetic** | https://synthetic.new/support |
| **Anthropic** | https://support.anthropic.com/ |

---

**Guide Version**: 1.0.0 | **Last Updated**: 2025-10-03
