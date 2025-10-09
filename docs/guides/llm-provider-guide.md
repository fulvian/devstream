# LLM Provider Guide - DevStream

**Version**: 2.0.0 | **Date**: 2025-10-06 | **Status**: Production Ready

---

## 🎯 Overview

DevStream supports 2 LLM providers with dual subscription model:

| Provider | Auth | Subscription | Model | Use Case |
|----------|------|--------------|-------|----------|
| **Anthropic** | OAuth | Max Plan | Sonnet 4.5 | Default, production |
| **z.ai** | API Key | Coding Plan | GLM-4.6 | Alternative, cost-effective |

**IMPORTANT**: Subscriptions are separate and independent. You cannot use Anthropic Max Plan with z.ai.

---

## 🚀 Quick Start

### Anthropic Max Plan (Default)

```bash
# 1. Login OAuth
claude login

# 2. Verify
claude auth status

# 3. Start DevStream
./start-devstream.sh start
```

### z.ai Provider

```bash
# 1. Get API key from https://z.ai/manage-apikey/apikey-list

# 2. Add to .env
echo "ZAI_API_KEY=your-key-here" >> .env

# 3. Start DevStream
./start-devstream.sh start z.ai
```

---

## 🔄 Provider Switching

### Switch to z.ai
```bash
./start-devstream.sh restart z.ai
```

### Switch to Anthropic
```bash
./start-devstream.sh restart anthropic
```

**Preservation**: Claude Code settings (hooks, mcpServers) are automatically preserved.

---

## 🔐 Authentication Architecture

### Anthropic Max Plan
- **Method**: OAuth via `claude login`
- **Variables**: ALL unset (ANTHROPIC_BASE_URL, ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN)
- **Verification**: `claude auth status`
- **Critical**: NEVER set ANTHROPIC_API_KEY (bypasses Max Plan)

### z.ai Provider
- **Method**: API Key from z.ai console
- **Variables**:
  - `ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic`
  - `ANTHROPIC_AUTH_TOKEN=$ZAI_API_KEY` (NOT API_KEY)
- **Source**: https://docs.z.ai/scenario-example/develop-tools/claude

---

## 📊 Model Mapping

| Claude Request | Anthropic | z.ai | Description |
|---------------|-----------|------|-------------|
| claude-opus-* | Opus 3.5 | glm-4.6 | Flagship reasoning |
| claude-sonnet-4-5* | Sonnet 4.5 | glm-4.6 | Production |
| claude-haiku-* | Haiku 3.5 | glm-4.5-air | Fast responses |

---

## 🛠️ Configuration

### Environment Variables (.env)

```bash
# Z.AI Configuration (MANDATORY for z.ai provider)
ZAI_API_KEY=your-api-key-here

# Context7 Integration
CONTEXT7_API_KEY=ctx7sk-...

# GitHub Integration
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...

# DevStream System
DEVSTREAM_DB_PATH=./data/devstream.db
DEVSTREAM_MEMORY_ENABLED=true
DEVSTREAM_CONTEXT7_ENABLED=true
DEVSTREAM_AUTO_DELEGATION_ENABLED=true
```

### Claude Code Settings (.claude/settings.json)

**Provider-specific settings are managed automatically** by start-devstream.sh:
- `configure_claude_settings_for_zai()` - Sets GLM-4.6 model routing
- `reset_claude_settings_to_default()` - Restores Sonnet 4.5

**User settings preserved**:
- `hooks` - DevStream memory hooks
- `mcpServers` - MCP server configurations
- Custom preferences

---

## 🚨 Troubleshooting

### Anthropic Issues

**Problem**: "Not logged into Claude.ai"
```bash
# Solution
claude login
claude auth status
```

**Problem**: "Max Plan not working after z.ai switch"
```bash
# Solution: Reset environment
./start-devstream.sh restart anthropic
env | grep ANTHROPIC  # Should output nothing

# If still issues
claude logout && claude login
```

### z.ai Issues

**Problem**: "ZAI_API_KEY not configured"
```bash
# Solution
cat .env | grep ZAI_API_KEY
# If missing:
echo "ZAI_API_KEY=your-key" >> .env
```

**Problem**: "API 401 Unauthorized"
- Verify credit at https://z.ai/
- Check API key validity at https://z.ai/manage-apikey/apikey-list
- Verify Coding Plan subscription active

---

## 📚 Resources

### Anthropic
- **Dashboard**: https://claude.ai/
- **Login**: `claude login`
- **Docs**: https://docs.anthropic.com/

### z.ai
- **Dashboard**: https://z.ai/
- **API Keys**: https://z.ai/manage-apikey/apikey-list
- **Docs**: https://docs.z.ai/
- **Models**: https://open.bigmodel.cn/

---

## 🏗️ Technical Details

### Authentication Flow

```
User runs: ./start-devstream.sh start [provider]
    ↓
Load .env (ZAI_API_KEY, CONTEXT7_API_KEY, etc.)
    ↓
switch_auth_provider(provider)
    ↓
┌──────────────────┬────────────────────┐
│ anthropic        │ z.ai               │
├──────────────────┼────────────────────┤
│ unset BASE_URL   │ export BASE_URL    │
│ unset API_KEY    │ export AUTH_TOKEN  │
│ unset AUTH_TOKEN │ validate ZAI_KEY   │
│ verify OAuth     │ configure settings │
└──────────────────┴────────────────────┘
    ↓
Start Claude Code with provider configuration
```

### Settings Management

**Automatic Configuration**:
- `configure_claude_settings_for_zai()` (start-devstream.sh) - Configures environment for z.ai provider
- `reset_claude_settings_to_default()` (start-devstream.sh) - Resets to Anthropic OAuth

**Settings Preserved During Provider Switching**:
- Hooks (PreToolUse, PostToolUse, UserPromptSubmit, SessionStart)
- MCP Servers
- Custom user preferences

---

## 🔒 Security Best Practices

1. **Single Source of Truth**: All API keys in `.env` (root)
2. **No Hardcoding**: Never hardcode keys in scripts
3. **Git Ignore**: Ensure `.env` in `.gitignore`
4. **OAuth Preference**: Use Anthropic OAuth when possible (more secure)
5. **API Key Rotation**: Rotate z.ai keys periodically
6. **Environment Isolation**: Unset all provider vars when switching

---

**Version**: 2.0.0
**Status**: ✅ Production Ready
**Last Updated**: 2025-10-06
**Architecture**: Dual Subscription Model
