#!/bin/bash

# E-commerce MCP Server Startup Script
# This script starts the MCP server using traditional Python virtual environment

set -e

# Configuration
PROJECT_DIR="/opt/mycode/promode/promodeagro-mcp"
SERVER_PORT="${MCP_SERVER_PORT:-8000}"
SERVER_HOST="${MCP_SERVER_HOST:-0.0.0.0}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"
VENV_DIR="$PROJECT_DIR/.venv"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting E-commerce MCP Server${NC}"
echo -e "${BLUE}📍 Project Directory: $PROJECT_DIR${NC}"
echo -e "${BLUE}🌐 Server: $SERVER_HOST:$SERVER_PORT${NC}"
echo -e "${BLUE}📝 Log Level: $LOG_LEVEL${NC}"
echo ""

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ python3 is not installed${NC}"
    exit 1
fi

# Check if we're in the correct directory
if [[ ! -f "$PROJECT_DIR/mcp_http_server.py" ]]; then
    echo -e "${RED}❌ MCP server file not found: $PROJECT_DIR/mcp_http_server.py${NC}"
    exit 1
fi

# Check if requirements.txt exists
if [[ ! -f "$PROJECT_DIR/requirements.txt" ]]; then
    echo -e "${RED}❌ requirements.txt not found: $PROJECT_DIR/requirements.txt${NC}"
    exit 1
fi

# Change to project directory
cd "$PROJECT_DIR"

echo -e "${BLUE}🔧 Setting up Python virtual environment...${NC}"

# Create virtual environment if it doesn't exist
if [[ ! -d "$VENV_DIR" ]]; then
    echo -e "${YELLOW}📦 Creating virtual environment at $VENV_DIR${NC}"
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
echo -e "${YELLOW}🔌 Activating virtual environment${NC}"
source "$VENV_DIR/bin/activate"

# Upgrade pip within the virtual environment
echo -e "${YELLOW}⬆️ Upgrading pip${NC}"
"$VENV_DIR/bin/pip3" install --upgrade pip

# Install/upgrade dependencies
echo -e "${YELLOW}📥 Installing dependencies from requirements.txt${NC}"
"$VENV_DIR/bin/pip3" install -r requirements.txt

echo -e "${BLUE}🎯 Environment setup complete${NC}"
echo ""

# Export environment variables
export PYTHONPATH="$PROJECT_DIR"
export AWS_REGION="${AWS_REGION:-ap-south-1}"
export LOG_LEVEL="$LOG_LEVEL"

echo -e "${GREEN}✅ Starting E-commerce MCP HTTP Server${NC}"
echo -e "${YELLOW}📊 Available Tools:${NC}"
echo -e "  • ${BLUE}browse-products${NC} - Browse Aurora Spark product catalog"
echo -e "  • ${BLUE}get-category-counts${NC} - Get product category statistics"
echo ""
echo -e "${YELLOW}🔗 Server Endpoints:${NC}"
echo -e "  • ${BLUE}Health Check${NC}: http://$SERVER_HOST:$SERVER_PORT/health"
echo -e "  • ${BLUE}Tools List${NC}: http://$SERVER_HOST:$SERVER_PORT/tools"
echo -e "  • ${BLUE}MCP Protocol${NC}: http://$SERVER_HOST:$SERVER_PORT/mcp/request"
echo ""
echo -e "${YELLOW}💡 Press Ctrl+C to stop the server${NC}"
echo ""

# Run the MCP server with the activated virtual environment
exec python mcp_http_server.py --host "$SERVER_HOST" --port "$SERVER_PORT"
