# 🚀 E-commerce MCP Server - Cursor IDE Integration

This guide shows how to integrate the E-commerce MCP Server with Cursor IDE using traditional Python virtual environments.

## 🎯 Quick Setup

### 1. **Prerequisites**
```bash
# Ensure Python 3.10+ is installed
python3 --version

# Ensure pip is available
pip --version
```

### 2. **Start the MCP Server**
```bash
cd /opt/mycode/promode/promodeagro-mcp
./start-mcp-server.sh
```

### 3. **Configure Cursor IDE**

Add this configuration to your Cursor settings (`Ctrl/Cmd + ,` → search "mcp"):

#### **Method A: Via Cursor Settings UI**
1. Open Cursor IDE
2. Go to Settings (`Ctrl/Cmd + ,`)
3. Search for "MCP" or "Model Context Protocol"
4. Add a new MCP server with these details:
   - **Name**: `ecommerce-catalog`
   - **Command**: `/opt/mycode/promode/promodeagro-mcp/.venv/bin/python`
   - **Args**: `["/opt/mycode/promode/promodeagro-mcp/mcp_http_server.py"]`
   - **Transport**: HTTP
   - **Host**: `localhost`
   - **Port**: `8000`

#### **Method B: Via settings.json**
Add this to your Cursor `settings.json`:

```json
{
  "mcp.servers": {
    "ecommerce-catalog": {
      "command": "/opt/mycode/promode/promodeagro-mcp/.venv/bin/python",
      "args": [
        "/opt/mycode/promode/promodeagro-mcp/mcp_http_server.py",
        "--host",
        "localhost",
        "--port", 
        "8000"
      ],
      "env": {
        "PYTHONPATH": "/opt/mycode/promode/promodeagro-mcp",
        "AWS_REGION": "ap-south-1",
        "LOG_LEVEL": "INFO"
      },
      "transport": {
        "type": "http",
        "host": "localhost",
        "port": 8000
      }
    }
  }
}
```

#### **Method C: Standalone HTTP Connection**
If you prefer to run the server independently:

1. Start the server manually:
```bash
./start-mcp-server.sh
```

2. Add HTTP transport configuration to Cursor:
```json
{
  "mcp.servers": {
    "ecommerce-catalog": {
      "transport": {
        "type": "http",
        "host": "localhost",
        "port": 8000
      }
    }
  }
}
```

## 🛠️ Available Tools

Once configured, you'll have access to these MCP tools in Cursor:

### 📦 **browse-products**
Browse and search products in the e-commerce catalog.

**Parameters:**
- `category` (string, optional): Filter by category (e.g., "vegetables", "fruits")
- `search_term` (string, optional): Search in product names/descriptions
- `max_results` (integer, optional): Maximum results to return (default: 20, max: 100)
- `include_out_of_stock` (boolean, optional): Include out of stock products (default: true)
- `min_price` (number, optional): Minimum price filter
- `max_price` (number, optional): Maximum price filter

**Example Usage in Cursor:**
```
"Find organic vegetables under $25"
"Show me the top 10 fruits in stock"
"Browse dairy products with search term 'fresh'"
```

### 📊 **get-category-counts**
Get product counts by category for inventory analysis.

**Parameters:** None required

**Example Usage in Cursor:**
```
"What product categories are available and how many products are in each?"
"Show me category statistics for the product catalog"
```

## 🧪 Test Your Setup

### 1. **Test Server Directly**
```bash
# Health check
curl http://localhost:8000/health

# List tools
curl http://localhost:8000/tools

# Test browse products
curl -X POST http://localhost:8000/tools/browse-products \
  -H "Content-Type: application/json" \
  -d '{"category": "fruits", "max_results": 5}'
```

### 2. **Run Test Scripts**
```bash
# Test individual tools
./testscripts/tools-test/test_browse_products.sh
./testscripts/tools-test/test_get_category_counts.sh

# Comprehensive test
./testscripts/tools-test/test_all_ecommerce_tools.sh
```

### 3. **Test in Cursor**
After configuration, try these prompts in Cursor:
- "Browse products in the vegetables category"
- "What categories are available in the product catalog?"
- "Find products under $20"

## 🔧 Troubleshooting

### **Server Won't Start**
```bash
# Check Python version
python3 --version

# Check virtual environment
ls -la /opt/mycode/promode/promodeagro-mcp/.venv/

# Check dependencies
cd /opt/mycode/promode/promodeagro-mcp
source .venv/bin/activate
pip list
```

### **Cursor Can't Connect**
1. Verify server is running: `curl http://localhost:8000/health`
2. Check firewall/port availability
3. Restart Cursor IDE after configuration changes
4. Check Cursor logs for MCP connection errors

### **Tools Not Working**
1. Test tools directly with curl (see test section above)
2. Check AWS credentials if using DynamoDB features
3. Review server logs for errors
4. Run test scripts to verify functionality

## 🚀 Advanced Configuration

### **Custom Port**
```bash
MCP_SERVER_PORT=9000 ./start-mcp-server.sh
```

### **Production Environment**
```bash
AWS_REGION=us-east-1 LOG_LEVEL=WARNING ./start-mcp-server.sh
```

### **Background Service**
```bash
# Run in background
nohup ./start-mcp-server.sh > mcp-server.log 2>&1 &

# Check status
curl http://localhost:8000/health
```

## 📊 Server Information

- **Name**: E-commerce Product Catalog MCP Server
- **Version**: 1.0.0  
- **Transport**: HTTP
- **Default Port**: 8000
- **Health Endpoint**: `/health`
- **Tools Endpoint**: `/tools`
- **MCP Protocol**: `/mcp/request`

## 🎯 Next Steps

1. **Configure Cursor** with the settings above
2. **Start the MCP server** using `./start-mcp-server.sh`
3. **Test the integration** with sample prompts
4. **Explore e-commerce tools** in your Cursor workflows

Happy coding with your new E-commerce MCP Server in Cursor! 🛍️✨
