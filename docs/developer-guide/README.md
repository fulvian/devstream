# Developer Guide

**Target Audience**: Contributors, maintainers, advanced users
**Status**: Production Documentation
**Last Updated**: 2025-10-01

## Overview

This directory contains comprehensive developer documentation for contributing to and extending DevStream. Whether you're fixing bugs, adding features, or building custom integrations, these guides provide the technical depth you need.

## Documentation Structure

| Guide | Type | Audience | Purpose |
|-------|------|----------|---------|
| **[Architecture](./architecture.md)** | Explanatory + Reference | All Contributors | System design, components, data flow |
| **[Setup Development](./setup-development.md)** | How-To | New Contributors | Environment setup, IDE config, debugging |
| **[Testing](./testing.md)** | Reference + How-To | All Contributors | Testing strategy, writing tests, coverage |
| **[Hook System](./hook-system.md)** | Explanatory + How-To | Hook Developers | Hook development, patterns, debugging |
| **[MCP Server](./mcp-server.md)** | Reference + How-To | MCP Developers | MCP server architecture, adding tools |
| **[Release Process](./release-process.md)** | Procedures | Maintainers | Versioning, releases, migrations |

## Quick Start Paths

### Path 1: First-Time Contributor (Bug Fix)

```
1. Read: Setup Development (setup-development.md)
   ↓
2. Setup: Environment + IDE configuration
   ↓
3. Read: Testing (testing.md) → Unit Tests section
   ↓
4. Fix: Make changes + write tests
   ↓
5. Verify: Run test suite (95%+ coverage)
   ↓
6. Submit: Create pull request
```

**Time Estimate**: 2-4 hours (including setup)

### Path 2: Hook Developer (Custom Hook)

```
1. Read: Architecture (architecture.md) → Hook System Architecture
   ↓
2. Read: Hook System (hook-system.md) → Creating Custom Hooks
   ↓
3. Read: Testing (testing.md) → Testing Hooks
   ↓
4. Develop: Write custom hook + tests
   ↓
5. Verify: Test hook execution
   ↓
6. Document: Add hook documentation
```

**Time Estimate**: 4-8 hours (experienced developer)

### Path 3: MCP Tool Developer (New Tool)

```
1. Read: Architecture (architecture.md) → MCP Server Architecture
   ↓
2. Read: MCP Server (mcp-server.md) → Adding New Tools
   ↓
3. Read: Testing (testing.md) → Integration Tests
   ↓
4. Develop: Implement tool + database queries + tests
   ↓
5. Verify: Run MCP server tests
   ↓
6. Document: Update tool documentation
```

**Time Estimate**: 8-16 hours (full feature)

### Path 4: Release Manager (Production Release)

```
1. Read: Release Process (release-process.md) → Release Workflow
   ↓
2. Plan: Create release tracking issue + milestone
   ↓
3. Execute: Follow Phase 1-6 release process
   ↓
4. Monitor: Post-release validation
   ↓
5. Document: Update changelog + migration guide
```

**Time Estimate**: 1-2 weeks (end-to-end)

## Documentation Philosophy

### Diátaxis Framework

DevStream documentation follows the **Diátaxis framework** (https://diataxis.fr/):

```
              STUDY                          WORK
         (Acquisition)                    (Application)

THEORY   ┌─────────────┐              ┌─────────────┐
         │ EXPLANATION │              │   HOW-TO    │
         │ (Learning)  │              │ (Problem)   │
         └─────────────┘              └─────────────┘

PRACTICE ┌─────────────┐              ┌─────────────┐
         │  TUTORIAL   │              │  REFERENCE  │
         │ (Learning)  │              │  (Info)     │
         └─────────────┘              └─────────────┘
```

**Applied to DevStream**:

| Documentation Type | DevStream Example | Purpose |
|-------------------|-------------------|---------|
| **Explanation** | Architecture deep dives | Understanding system design |
| **How-To** | Setup development, debugging | Solving specific problems |
| **Tutorial** | (User guides, not dev docs) | Learning workflows |
| **Reference** | API docs, testing guide | Looking up information |

## Contributing to Documentation

### Documentation Standards

**Quality Checklist**:
- ✅ **Clarity**: Simple language, avoid jargon (or define it)
- ✅ **Actionable**: Clear steps, reproducible examples
- ✅ **Complete**: Cover happy path + edge cases + errors
- ✅ **Maintainable**: Update docs with code changes
- ✅ **Searchable**: Keywords, tags, clear titles
- ✅ **Visual**: Diagrams for architecture, flows (Mermaid)
- ✅ **Examples**: Real code snippets that work

### When to Update Documentation

| Code Change | Documentation Update Required |
|-------------|-------------------------------|
| New feature | Architecture + How-To + Testing |
| Breaking change | Architecture + Migration Guide |
| API change | Reference documentation |
| Bug fix (minor) | No update (unless behavior change) |
| Configuration change | Setup Development |
| New hook/tool | Hook System or MCP Server |

### Documentation Review Process

1. **Self-Review**: Check against quality checklist
2. **Technical Review**: Verify code examples work
3. **Clarity Review**: Have non-expert read for clarity
4. **Approval**: 1+ maintainer approval required
5. **Merge**: Squash merge to keep history clean

## Cross-References

### Architecture → Implementation

- **Architecture (architecture.md)** explains *why* and *what*
- **Hook System (hook-system.md)** explains *how* to implement hooks
- **MCP Server (mcp-server.md)** explains *how* to implement tools
- **Testing (testing.md)** explains *how* to validate implementation

### Setup → Development → Release

```
Setup Development
     ↓
  (Develop)
     ↓
  Testing
     ↓
  (Validate)
     ↓
Release Process
```

## External References

### Essential Reading

| Resource | Purpose |
|----------|---------|
| [Model Context Protocol Docs](https://modelcontextprotocol.io/) | MCP specification |
| [cchooks Documentation](https://github.com/anthropics/claude-code-hooks) | Hook framework |
| [sqlite-vec Documentation](https://github.com/asg017/sqlite-vec) | Vector search |
| [Context7 Research](https://context7.dev/) | Context injection patterns |

### DevStream Specific

| Document | Location |
|----------|----------|
| **User Guides** | `docs/guides/` |
| **Architecture Decisions** | `docs/architecture/decisions/` |
| **API Reference** | `docs/api/` |
| **Deployment Guides** | `docs/deployment/` |

## Getting Help

### Contribution Questions

- **General Questions**: GitHub Discussions → Q&A category
- **Bug Reports**: GitHub Issues (use bug template)
- **Feature Proposals**: GitHub Discussions → Ideas category
- **Documentation Issues**: GitHub Issues → Documentation label

### Contact Maintainers

- **Email**: devstream-maintainers@example.com
- **Slack**: #devstream-dev channel
- **Office Hours**: Fridays 2-4pm UTC (calendar link)

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-01 | Initial developer guide release |

---

**Feedback**: Found an issue or have a suggestion? [Open an issue](https://github.com/yourusername/devstream/issues/new?labels=documentation)

**Contributing**: Want to improve these docs? See [CONTRIBUTING.md](../../CONTRIBUTING.md)
