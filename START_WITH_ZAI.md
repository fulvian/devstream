# 🚀 Quick Start: Claude Code con z.ai GLM-4.6

## ✅ Avvio Immediato

```bash
./start-devstream.sh start z.ai
```

## 📊 Features Attive

✅ **Modello**: GLM-4.6 (Zhipu AI)
✅ **Reasoning Mode**: ABILITATO (automatico)
✅ **Context Window**: 200K tokens
✅ **Tool Calling**: Supporto nativo
✅ **API**: z.ai native Anthropic-compatible

## 🎯 Cosa Succede

```
1. Load .env (ZAI_API_KEY)
2. Export DEVSTREAM_LLM_PROVIDER=z.ai
3. Export ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic
4. Export ANTHROPIC_API_KEY=5a51efd5...
5. Start Claude Code
6. Claude Code → z.ai API → GLM-4.6
```

## ✨ Reasoning Mode

**AUTOMATICO** - Non serve configurazione!

```json
// z.ai abilita automaticamente:
{
  "thinking": {
    "type": "enabled"  // DEFAULT per GLM-4.6
  }
}
```

**Visibile in**:
- Task complessi (design architetture, debugging)
- Response field `reasoning_content` (streaming)
- Processing time maggiore (thinking attivo)

## 🔄 Tornare ad Anthropic

```bash
./start-devstream.sh start anthropic
# oppure
./start-devstream.sh start  # default = anthropic
```

## 📚 Documentazione Completa

- **Setup**: `ZAI_NATIVE_SETUP_FINAL.md`
- **Guide**: `QUICKSTART_ZAI.md`
- **Tests**: `test_zai_e2e.sh`

---

**Ready**: ✅ Configurazione validata
**Test**: ✅ API HTTP 200
**Status**: 🟢 Production Ready
