# DevStream MCP Server

Model Context Protocol server for DevStream task management and memory system integration with Claude Code.

## 🚀 Quick Start

### Installation

```bash
# Install globally via npm
npm install -g @devstream/mcp-server

# Or run directly with npx
npx @devstream/mcp-server /path/to/devstream.db
```

### Usage

```bash
# Start the server with your DevStream database
devstream-mcp /Users/fulvioventura/devstream/data/devstream.db
```

## 🔧 Claude Code Integration

### Add to Claude Code

```bash
# Add DevStream MCP server to Claude Code
claude mcp add devstream npx -- @devstream/mcp-server /Users/fulvioventura/devstream/data/devstream.db
```

### Natural Language Commands

Once configured, you can use these natural language commands in Claude Code:

#### Task Management
- *"Mostrami i task DevStream"* - List all tasks
- *"Crea task per ottimizzare WebSocket"* - Create new task
- *"Segna questo task come completato"* - Update task status
- *"Mostrami solo i task ad alta priorità"* - Filter by priority

#### Plan Management
- *"Mostrami i piani DevStream"* - List intervention plans
- *"Qual è lo stato del progetto Rusty?"* - Get project status

#### Memory Management
- *"Salva questa informazione in memoria"* - Store knowledge
- *"Cerca nella memoria DevStream informazioni su WebSocket"* - Search memory

## 🛠 Available Tools

### Task Tools

- **`devstream_list_tasks`** - List and filter DevStream tasks
- **`devstream_create_task`** - Create new tasks in specific phases
- **`devstream_update_task`** - Update task status and add notes

### Plan Tools

- **`devstream_list_plans`** - List intervention plans with progress

### Memory Tools

- **`devstream_store_memory`** - Store information in semantic memory
- **`devstream_search_memory`** - Search memory with relevance scoring

## 📊 Features

- ✅ **Natural Language Interface** - Works seamlessly with Claude Code
- ✅ **Real-time Database Integration** - Direct connection to DevStream SQLite
- ✅ **Cross-Project Support** - Works from any directory
- ✅ **Type-Safe Operations** - Full TypeScript implementation
- ✅ **Semantic Memory** - Intelligent storage and retrieval
- ✅ **Progress Tracking** - Comprehensive task and plan management

## 🏗 Architecture

```
Claude Code → MCP Protocol → DevStream MCP Server → SQLite DevStream DB
```

The server exposes DevStream functionality through the Model Context Protocol, allowing natural language interaction with:

- **Task Management System** - Create, update, and track micro-tasks
- **Intervention Plans** - Manage multi-phase development projects
- **Semantic Memory** - Store and retrieve project knowledge
- **Progress Analytics** - Track completion rates and time spent

## 🔧 Development

### Build from Source

```bash
git clone https://github.com/devstream/mcp-devstream-server
cd mcp-devstream-server
npm install
npm run build
```

### Test Database Connection

```bash
node test-database.js /path/to/your/devstream.db
```

### Development Mode

```bash
npm run dev /path/to/your/devstream.db
```

## 📋 Requirements

- Node.js 18+
- DevStream database (SQLite)
- Claude Code (for MCP integration)

## 🤝 Integration Examples

### Project-Scoped Configuration

Create `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "devstream": {
      "command": "npx",
      "args": [
        "@devstream/mcp-server",
        "/Users/fulvioventura/devstream/data/devstream.db"
      ]
    }
  }
}
```

### Global Configuration

Add to your Claude Code global config:

```json
{
  "mcpServers": {
    "devstream": {
      "command": "devstream-mcp",
      "args": ["/Users/fulvioventura/devstream/data/devstream.db"]
    }
  }
}
```

## 📈 Performance

- **Response Time**: < 100ms per tool call
- **Memory Usage**: < 100MB server footprint
- **Database Queries**: Optimized with indexes and prepared statements
- **Concurrent Support**: Multiple Claude Code sessions

## 🔒 Security

- Read-only operations by default
- Parameterized queries prevent SQL injection
- No network exposure (stdio transport only)
- Sandboxed execution environment

## 📚 Documentation

- [DevStream Project](https://github.com/devstream/devstream)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Claude Code MCP Guide](https://docs.claude.com/claude-code/mcp)

## 🆘 Troubleshooting

### Common Issues

**Connection Failed**
```bash
# Verify database path and permissions
ls -la /path/to/devstream.db
```

**Tools Not Available**
```bash
# Check MCP server registration
claude mcp list
```

**Performance Issues**
```bash
# Test database performance
node test-database.js /path/to/devstream.db
```

### Support

For issues and feature requests, please visit:
- [GitHub Issues](https://github.com/devstream/mcp-devstream-server/issues)
- [DevStream Community](https://github.com/devstream/devstream/discussions)

---

**Made with ❤️ by the DevStream Team**
*Empowering development workflow through intelligent task management*