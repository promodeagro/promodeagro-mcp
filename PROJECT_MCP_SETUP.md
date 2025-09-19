# 🚀 Project-Specific MCP Configuration with uv

This guide shows how to use the project-specific MCP configuration instead of global configuration, using `uv` for dependency management.

## 🎯 Quick Setup

### 1. **Install uv (if not already installed)**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # or restart your terminal
```

### 2. **Verify uv installation**
```bash
uv --version
```

### 3. **Install dependencies and test the server**
```bash
cd /opt/mycode/promode/promodeagro-mcp

# Sync dependencies with uv
uv sync

# Test the server
uv run python mcp_http_server.py --host localhost --port 8000
```

### 4. **Configure Cursor for Project-Specific MCP**

There are two approaches to use project-specific MCP configuration:

#### **Method A: Use project-specific MCP configuration (Recommended)**

The project already includes a `.cursor/mcp.json` file that Cursor will automatically detect when you open this workspace.

If you need to create it manually:

1. Open your Cursor workspace
2. Create/edit `.cursor/mcp.json` in your workspace root:
```bash
mkdir -p /opt/mycode/promode/promodeagro-mcp/.cursor
```

3. Copy the MCP configuration:
```json
{
  "mcpServers": {
    "ecommerce-catalog": {
      "command": "uv",
      "args": [
        "run", 
        "--project", 
        "/opt/mycode/promode/promodeagro-mcp",
        "python", 
        "mcp_http_server.py",
        "--host",
        "localhost",
        "--port",
        "8000"
      ],
      "env": {
        "PYTHONPATH": "/opt/mycode/promode/promodeagro-mcp",
        "LOG_LEVEL": "INFO",
        "AWS_REGION": "ap-south-1"
      }
    }
  }
}
```

#### **Method B: Global Cursor settings**

Add this to your global Cursor settings (`Ctrl/Cmd + ,` → search "mcp"):

```json
{
  "mcp.servers": {
    "ecommerce-catalog": {
      "command": "uv",
      "args": [
        "run", 
        "--project", 
        "/opt/mycode/promode/promodeagro-mcp",
        "python", 
        "mcp_http_server.py",
        "--host",
        "localhost",
        "--port",
        "8000"
      ],
      "env": {
        "PYTHONPATH": "/opt/mycode/promode/promodeagro-mcp",
        "LOG_LEVEL": "INFO",
        "AWS_REGION": "ap-south-1"
      }
    }
  }
}
```

### 5. **Alternative: Use existing mcp-config.json**

The project includes a ready-to-use `mcp-config.json` file that you can reference or copy:

```bash
# View the project config
cat /opt/mycode/promode/promodeagro-mcp/mcp-config.json

# Copy to Cursor workspace config
cp /opt/mycode/promode/promodeagro-mcp/mcp-config.json /opt/mycode/promode/promodeagro-mcp/.cursor/mcp.json
```

## 🛠️ Available Tools

Once configured, you'll have access to these MCP tools in Cursor:

### 📦 **browse-products**
Browse and search products in the Aurora Spark e-commerce catalog.

**Parameters:**
- `category` (string, optional): Filter by category
- `search_term` (string, optional): Search in product names/descriptions  
- `max_results` (integer, optional): Maximum results (default: 20, max: 100)
- `include_out_of_stock` (boolean, optional): Include out of stock products
- `min_price` (number, optional): Minimum price filter
- `max_price` (number, optional): Maximum price filter

**Example Usage:**
```
"Find organic vegetables under $25"
"Show me the top 10 fruits in stock"
"Browse dairy products with search term 'fresh'"
```

### 📊 **get-category-counts**
Get product counts by category for inventory analysis.

**Parameters:** None required

**Example Usage:**
```
"What product categories are available?"
"Show me category statistics for the product catalog"
```

## 🧪 Test Your Setup

### 1. **Test Server Directly with uv**
```bash
cd /opt/mycode/promode/promodeagro-mcp

# Start server with uv
uv run python mcp_http_server.py --host localhost --port 8000 &

# Health check
curl http://localhost:8000/health

# List tools
curl http://localhost:8000/tools

# Test browse products
curl -X POST http://localhost:8000/tools/browse-products \
  -H "Content-Type: application/json" \
  -d '{"category": "fruits", "max_results": 5}'

# Kill background server
pkill -f mcp_http_server
```

### 2. **Test in Cursor**
After configuration, try these prompts in Cursor:
- "Browse products in the vegetables category"
- "What categories are available in the product catalog?"
- "Find products under $20"

## 🔧 Troubleshooting

### **uv not found**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

### **Dependencies not syncing**
```bash
cd /opt/mycode/promode/promodeagro-mcp
uv sync --force
```

### **Server won't start**
```bash
# Check dependencies
uv sync

# Test direct run
uv run python mcp_http_server.py --host localhost --port 8001

# Check logs
tail -f logs/server_*.log
```

### **Cursor can't connect**
1. Verify server is running: `curl http://localhost:8000/health`
2. Check port availability: `lsof -i :8000`
3. Restart Cursor IDE after configuration changes
4. Check Cursor logs for MCP connection errors

## ✅ Advantages of Project-Specific Configuration

- **Isolated dependencies**: Each project manages its own dependencies
- **Version consistency**: uv ensures reproducible builds
- **No global conflicts**: Project dependencies don't interfere with system packages
- **Easy sharing**: Project includes all configuration needed
- **Fast setup**: uv is faster than traditional pip installs

## 🚀 Advanced Usage

### **Custom Port**
```json
{
  "mcpServers": {
    "ecommerce-catalog": {
      "command": "uv",
      "args": [
        "run", 
        "--project", 
        "/opt/mycode/promode/promodeagro-mcp",
        "python", 
        "mcp_http_server.py",
        "--port",
        "9000"
      ]
    }
  }
}
```

### **Development Mode**
```bash
# Install dev dependencies
uv sync --extra dev

# Run with debug logging
uv run python mcp_http_server.py --host localhost --port 8000 --log-level DEBUG
```

### **Production Deployment**
```bash
# Install without dev dependencies
uv sync --no-dev

# Set production environment
export LOG_LEVEL=WARNING
export AWS_REGION=us-east-1
uv run python mcp_http_server.py
```

## 📊 Server Information

- **Name**: E-commerce Product Catalog MCP Server
- **Version**: 1.0.0  
- **Transport**: HTTP
- **Default Port**: 8000
- **Package Manager**: uv
- **Python**: 3.10+

Happy coding with your project-specific E-commerce MCP Server in Cursor! 🛍️✨
