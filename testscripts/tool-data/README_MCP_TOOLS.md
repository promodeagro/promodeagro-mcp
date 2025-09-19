# E-commerce MCP Server - Tool Testing Scripts

This directory contains comprehensive shell scripts for testing and documenting all MCP (Model Context Protocol) tools available in the E-commerce MCP Server.

## 📋 Available Scripts

### 🔍 Tool Discovery & Listing

#### `list_all_tools.sh`
**Purpose**: Lists all available MCP tools with their basic information and status
**Features**:
- Server health checks
- Tool endpoint discovery 
- Accessibility testing
- Tool categorization
- API documentation generation

**Usage**:
```bash
./list_all_tools.sh                          # Local server (localhost:8000)
./list_all_tools.sh http://192.168.1.100:9000  # Remote server
./list_all_tools.sh https://example.com:8080   # Remote server with HTTPS
```

**Output**:
- Complete list of 2 MCP tools
- Tool descriptions and endpoints
- Availability status for each tool
- Quick API reference

---

### 📖 Detailed Tool Information

#### `get_tool_details.sh`
**Purpose**: Get detailed information for specific MCP tools
**Features**:
- Tool-specific parameter documentation
- Request/response examples
- Endpoint testing
- Usage guidelines

**Usage**:
```bash
./get_tool_details.sh [tool-name]               # Local server
./get_tool_details.sh browse-products           # Specific tool on local server
./get_tool_details.sh all                       # All tools on local server
./get_tool_details.sh http://remote-host:8080 get-category-counts  # Specific tool on remote server
./get_tool_details.sh https://example.com:9000 all      # All tools on remote server
```

**Available Tools**:
- `browse-products` - Browse and search products in the Aurora Spark e-commerce catalog with filtering and search capabilities
- `get-category-counts` - Get product counts by category for Aurora Spark e-commerce catalog
- `all` - Show details for all tools

---

### 📋 Parameter Reference

#### `show_tool_parameters.sh`
**Purpose**: Shows detailed parameter information for all MCP tools
**Features**:
- Complete parameter documentation
- Data type specifications
- Required vs optional parameters
- Validation rules
- JSON payload examples

**Usage**:
```bash
./show_tool_parameters.sh                       # Local server (localhost:8000)
./show_tool_parameters.sh http://192.168.1.100:8000     # Remote server
./show_tool_parameters.sh https://example.com:3000      # Remote server with custom port
```

**Output**:
- Parameter details for all 2 tools
- Quick reference guide
- Validation guidelines
- Copy-paste examples

---

### 🧪 Comprehensive Testing

#### `test_tool_availability.sh`
**Purpose**: Comprehensive testing of all MCP tools
**Features**:
- Server connectivity tests
- Tool endpoint functionality
- Parameter validation
- Response format validation
- Integration testing
- Error handling tests
- Performance metrics
- Detailed test reporting

**Usage**:
```bash
./test_tool_availability.sh                     # Local server (localhost:8000)
./test_tool_availability.sh http://10.0.0.50:8000        # Remote server
./test_tool_availability.sh https://staging.company.com:8080  # Remote staging server
```

**Test Categories**:
1. **Server Connectivity** - Basic server health and endpoint availability
2. **Tool Functionality** - Individual tool testing (OPTIONS, POST, JSON handling)
3. **Parameter Validation** - Required parameter checking and format validation
4. **Response Format** - JSON structure and status field validation
5. **Integration Scenarios** - Cross-tool functionality testing
6. **Error Handling** - 404s, invalid methods, timeouts
7. **Performance** - Response time measurements

---

## 🚀 Quick Start Guide

### 1. Check Server Status
```bash
# Local server
./list_all_tools.sh

# Remote server
./list_all_tools.sh http://your-server.com:8080
```

### 2. Get Tool Overview
```bash
# Local server - see all available tools and their status
./list_all_tools.sh

# Remote server - check tools on production/staging
./list_all_tools.sh http://prod-server.company.com:8000
```

### 3. Get Specific Tool Information
```bash
# Local server - get detailed info for a specific tool
./get_tool_details.sh analyze-site-patterns

# Remote server - get tool info from remote environment
./get_tool_details.sh http://staging.company.com:8080 compare-sites
```

### 4. View Parameters Reference
```bash
# Local server - see parameter documentation for all tools
./show_tool_parameters.sh

# Remote server - check parameters on remote server
./show_tool_parameters.sh https://example.com:3000
```

### 5. Run Comprehensive Tests
```bash
# Local server - test all tools comprehensively
./test_tool_availability.sh

# Remote server - run full test suite on remote environment
./test_tool_availability.sh http://prod-server.company.com:8000
```

---

## 🔧 E-commerce MCP Tools

### Product Catalog Tools
- **`browse-products`** - Browse and search products in the Aurora Spark e-commerce catalog with filtering and search capabilities including category filtering, keyword search, price ranges, and stock availability filters
- **`get-category-counts`** - Get product counts by category for Aurora Spark e-commerce catalog to understand inventory distribution and product availability across different categories

#### E-commerce Examples
```bash
# Browse products
./get_tool_details.sh browse-products

# Get category counts
./get_tool_details.sh get-category-counts

# Test e-commerce tools
./test_tool_availability.sh # Tests all 2 tools
```

---

## 🌐 Remote Execution Support

All scripts now support connecting to remote MCP servers using a single **URL parameter format**.

### Uniform Command Format

**All scripts now use the same simple format:**
```bash
./script_name.sh [URL] [additional_args]
```

**Smart URL Detection:**
- **AWS Load Balancers**: Automatically detects `.elb.` or `.amazonaws.com` and uses port 80/443
- **Localhost/IP addresses**: Uses development port 8000 by default
- **Explicit ports**: Always respected when specified
- **Other domains**: Uses standard ports 80/443

### Examples Across All Script Categories

#### Tool Data Scripts
```bash
# Basic usage (local server)
./list_all_tools.sh
./get_tool_details.sh
./show_tool_parameters.sh
./test_tool_availability.sh

# AWS Load Balancer (automatically uses port 80)
./list_all_tools.sh http://alert--Backe-J3vD6CohaowE-1847151533.us-east-1.elb.amazonaws.com
./test_tool_availability.sh https://my-app.us-west-2.elb.amazonaws.com

# Localhost/IP (automatically uses port 8000)
./list_all_tools.sh http://localhost
./test_tool_availability.sh http://192.168.1.100

# Explicit port specification (always respected)
./list_all_tools.sh http://localhost:3000
./get_tool_details.sh http://192.168.1.100:9000 browse-products
./show_tool_parameters.sh https://api.company.com:8080
```

#### E-commerce Tool Scripts
```bash
# Basic usage (local server)
./test_browse_products.sh
./test_get_category_counts.sh

# Remote server usage
./test_browse_products.sh http://18.191.87.212:8000
./test_get_category_counts.sh http://192.168.1.100:9000
./test_all_tools.sh https://prod-server.company.com
```

### URL Format Support

**Supported URL formats:**
- `http://host:port` - Standard HTTP connection
- `https://host:port` - Secure HTTPS connection
- `http://host` - Uses default port 8000
- `https://host` - Uses default port 8000

### Migration from Old Formats

**Before (inconsistent formats):**
```bash
# Old host/port format (tool-data scripts)
./list_all_tools.sh -h 192.168.1.100 -p 9000
./get_tool_details.sh --host example.com --port 8080

# Old hardcoded localhost (other scripts)
# Required manual editing of SERVER_URL in scripts
```

**After (uniform URL format):**
```bash
# New unified URL format (all scripts)
./list_all_tools.sh http://192.168.1.100:9000
./get_tool_details.sh http://example.com:8080 browse-products
./test_all_tools.sh http://192.168.1.100:9000
./test_tool_availability.sh http://example.com:8080
```

### Benefits of Uniform URL Format

- **🎯 Consistency**: Same format across all 15+ test scripts
- **🚀 Simplicity**: Single URL parameter instead of separate host/port
- **🔒 Security**: Support for both HTTP and HTTPS
- **⚡ Speed**: No need to edit scripts or remember different parameter formats
- **🌐 Flexibility**: Easy switching between local, staging, and production environments
- **📝 Documentation**: Clear, predictable usage patterns

### Help and Usage

Every script supports `--help` for usage information:
```bash
./list_all_tools.sh --help
./get_tool_details.sh --help
./show_tool_parameters.sh --help
./test_tool_availability.sh --help
```

---

## 📊 Server Configuration

**Default Settings**:
- Server URL: `http://localhost:8000` (when no URL provided)
- All scripts fall back to localhost if no URL is specified

**Starting the Server**:
```bash
python mcp_http_server.py
```

---

## 🛠️ Prerequisites

### Required Tools
- `curl` - For HTTP requests
- `jq` - For JSON parsing
- `bash` - Shell environment

### Installation (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install curl jq
```

### Installation (macOS)
```bash
brew install curl jq
```

---

## 📚 Example Usage Scenarios

### Scenario 1: New Developer Setup
```bash
# 1. Check if server is running and tools are available
./list_all_tools.sh

# 2. Get familiar with available tools
./get_tool_details.sh all

# 3. Run quick tests to verify everything works
./test_tool_availability.sh
```

### Scenario 2: Debugging Tool Issues
```bash
# 1. Test specific tool that's having issues
./get_tool_details.sh browse-products

# 2. Check parameter requirements
./show_tool_parameters.sh

# 3. Run comprehensive tests
./test_tool_availability.sh
```

### Scenario 3: Integration Testing
```bash
# 1. Verify all tools are accessible
./list_all_tools.sh

# 2. Run full test suite before deployment
./test_tool_availability.sh
```

---

## 🔍 Troubleshooting

### Common Issues

#### Server Not Running
```bash
# Error: MCP server is not accessible
# Solution: Start the server
python mcp_http_server.py
```

#### Tools Not Accessible
```bash
# Check server status first
curl -s http://localhost:8000

# Verify tools endpoint
curl -s http://localhost:8000/tools
```

#### Permission Issues
```bash
# Make scripts executable
chmod +x *.sh
```

### Debug Commands
```bash
# Test specific tool manually
curl -X POST http://localhost:8000/tools/analyze-site-patterns \
  -H 'Content-Type: application/json' \
  -d '{"site_code": "CZA0021"}'

# Check server logs
# (Refer to your server startup logs)
```

---

## 📊 Test Results Interpretation

### Success Rates
- **90%+**: Excellent - Ready for production
- **70-89%**: Good - Minor issues to address
- **<70%**: Critical issues - Requires investigation

### Common Test Failures
1. **Connectivity Issues** - Server not running or network problems
2. **Parameter Validation** - Missing required parameters
3. **Response Format** - JSON structure issues
4. **Performance** - Slow response times (>5 seconds)

---

## 🔄 Script Maintenance

### Updating Server URL
Edit the configuration section in each script:
```bash
SERVER_URL="http://your-server:port"
TOOLS_ENDPOINT="$SERVER_URL/tools"
```

### Adding New Tools
When new tools are added to the MCP server:
1. Update tool lists in all scripts
2. Add tool-specific parameter documentation
3. Add test cases for new tools

---

## 📞 Support

For issues with these testing scripts:
1. Check server logs for detailed error information
2. Verify all prerequisites are installed
3. Ensure MCP server is running and accessible
4. Review the troubleshooting section above

For TMF ODA Transformer specific issues:
- Refer to the main project documentation
- Check server configuration and AWS credentials
- Review journey and job management guides

---

## ✅ Script Summary

| Script | Purpose | Output | Time |
|--------|---------|--------|------|
| `list_all_tools.sh` | Tool discovery & overview | Tool list with status | ~30s |
| `get_tool_details.sh` | Detailed tool documentation | Comprehensive tool info | ~10s |
| `show_tool_parameters.sh` | Parameter reference | Complete parameter docs | ~5s |
| `test_tool_availability.sh` | Comprehensive testing | Full test report | ~2-5min |

**Total Testing Time**: ~3-6 minutes for complete MCP server validation

All scripts are designed to be:
- ✅ **Self-contained** - No external dependencies beyond curl/jq
- ✅ **Error-resilient** - Handle server issues gracefully
- ✅ **Informative** - Provide clear, actionable output
- ✅ **Fast** - Complete testing in under 5 minutes 