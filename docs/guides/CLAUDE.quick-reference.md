# DevStream Quick Reference - Metodologia di Lavoro

## 🔄 Workflow (4 Fasi)

```
1. 🎯 DISCUSS → Analisi obiettivi e specifiche
2. 📋 DIVIDE  → Fasi + micro-task granulari
3. 🔍 RESEARCH → Context7 per best practice
4. ✅ VERIFY  → Test severi e validazione
```

## 🛠 Tools Essenziali

```bash
# Context7 Research
mcp__context7__resolve-library-id "library-name"
mcp__context7__get-library-docs "/org/project" --topic="topic"

# Task Management
TodoWrite → Create granular task lists
Mark in_progress → Complete immediately

# Testing
Unit tests + Integration tests + Performance tests
Target: 95%+ coverage, zero mypy errors
```

## 📋 Task Structure

```json
{
  "content": "Implement specific feature",
  "status": "pending|in_progress|completed",
  "activeForm": "Implementing specific feature"
}
```

## 🎯 Quality Standards

- **Type Safety**: Full mypy compliance
- **Documentation**: Complete docstrings
- **Testing**: Comprehensive test coverage
- **Research**: Context7-validated solutions
- **Architecture**: SOLID principles

## 🚀 Success Pattern

```
Research → Design → Approve → Implement → Test → Document
```

**Risultato**: Production-ready code con best practice validate