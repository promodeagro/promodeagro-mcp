#!/usr/bin/env python3
"""
MCP HTTP Transport Server for Alert Correlation Engine
This implements the proper MCP HTTP transport protocol for Cursor compatibility.
"""

import asyncio
import json
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import traceback
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import uuid
import logging
import argparse
from loguru import logger

# Add the MCP server to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Parse command-line arguments
parser = argparse.ArgumentParser(description="E-commerce MCP HTTP Server")
parser.add_argument("--debug", action="store_true", help="Enable debug logging")
parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
parser.add_argument("--host", default="0.0.0.0", help="Host to bind the server to")
args = parser.parse_args()

# Configure logging with environment variable support
LOG_DIR = Path(os.getenv('LOG_DIR', Path(__file__).parent / "logs"))

# Safely create log directory
try:
    LOG_DIR.mkdir(exist_ok=True, parents=True)
    logger.info(f"Log directory: {LOG_DIR}")
    logger.info("Log files will be rotated daily and kept for 30 days")
    use_file_logging = True
except (PermissionError, OSError) as e:
    logger.warning(f"Cannot create log directory {LOG_DIR}: {e}")
    logger.info("File logging disabled, using console-only logging")
    use_file_logging = False

# Set log level based on debug flag
LOG_LEVEL = "DEBUG" if args.debug else "INFO"

# Configure loguru for both console and file output
logger.remove()  # Remove default handler

# Add console handler
logger.add(
    sys.stdout,
    level=LOG_LEVEL,
    format="{time:HH:mm:ss} | {level} | SERVER | {module}:{function} | {message}",
    colorize=True,
    catch=True
)

# Add server log file handler (only if directory creation was successful)
if use_file_logging:
    server_log_file = LOG_DIR / f"server_{datetime.now().strftime('%Y-%m-%d')}.log"
    logger.add(
        server_log_file,
        level=LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | SERVER | {module}:{function}:{line} | {message}",
        rotation="100 MB",
        retention="30 days",
        compression="gz",
        catch=True
    )
    logger.info(f"File logging enabled: {server_log_file}")
else:
    logger.info("File logging disabled - using console output only")

# Create a separate dual logger for server operations  
class DualLogger:
    def __init__(self):
        self.use_file_logging = use_file_logging
        if self.use_file_logging:
            self.server_log = LOG_DIR / f"server_{datetime.now().strftime('%Y-%m-%d')}.log"
        
    def _write_to_file(self, level: str, message: str):
        """Write to server log file if file logging is enabled."""
        if not self.use_file_logging:
            return
            
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"{timestamp} | {level} | SERVER | {message}\n"
            with open(self.server_log, "a", encoding="utf-8") as f:
                f.write(log_entry)
                f.flush()
        except Exception as e:
            print(f"Server logging error: {e}")
        
    def info(self, message: str):
        print(f"[SERVER] {message}")
        logger.info(message)
        self._write_to_file("INFO", message)
        
    def debug(self, message: str):
        if LOG_LEVEL == "DEBUG":
            print(f"[SERVER DEBUG] {message}")
        logger.debug(message)
        self._write_to_file("DEBUG", message)
        
    def error(self, message: str):
        print(f"[SERVER ERROR] {message}")
        logger.error(message)
        self._write_to_file("ERROR", message)

dual_logger = DualLogger()

# Also configure Python's logging to capture uvicorn and other HTTP errors
logging.basicConfig(
    level=logging.DEBUG if args.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "uvicorn.log"),
        logging.StreamHandler()
    ]
)

dual_logger.info("=== E-commerce MCP HTTP Server Starting ===")
dual_logger.info(f"Log directory: {LOG_DIR}")
dual_logger.info(f"Log files will be rotated daily and kept for 30 days")

# Import MCP server and tools directly
try:
    from src.server import create_server
    from src.tools.ecommerce_tools import (
        browse_products_tool, get_category_counts_tool
    )
    from src.services.ecommerce_service import EcommerceService
    from src.models.ecommerce_models import ProductBrowseRequest, CategoryCountsRequest
    dual_logger.info("✅ E-commerce MCP server and tools imported successfully")
    print("✅ E-commerce MCP server and tools imported successfully")
except ImportError as e:
    print(f"❌ Error importing E-commerce MCP server: {e}")
    traceback.print_exc()
    sys.exit(1)

# FastAPI app
app = FastAPI(
    title="E-commerce MCP HTTP Transport",
    description="MCP HTTP transport server for AI-powered telecommunications site analysis and alert correlation",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests and responses."""
    start_time = datetime.now()
    
    # Log incoming request
    if request.method == "OPTIONS":
        dual_logger.debug(f"📋 HTTP OPTIONS: {request.method} {request.url}")
    else:
        dual_logger.info(f"📥 HTTP Request: {request.method} {request.url}")
        dual_logger.debug(f"Request headers: {dict(request.headers)}")
    
    # Process request
    try:
        response = await call_next(request)
        
        # Log successful response
        duration = (datetime.now() - start_time).total_seconds()
        if request.method == "OPTIONS":
            dual_logger.debug(f"📋 HTTP OPTIONS Response: {response.status_code} ({duration:.3f}s)")
        else:
            dual_logger.info(f"📤 HTTP Response: {response.status_code} ({duration:.3f}s)")
        
        return response
        
    except Exception as e:
        # Log error response
        duration = (datetime.now() - start_time).total_seconds()
        dual_logger.error(f"❌ HTTP Request failed: {request.method} {request.url} ({duration:.3f}s)")
        logger.error(f"Exception: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        raise

# Store server state
server_state = {
    "initialized": False,
    "session_id": None,
    "client_info": None
}

# Tool registry with direct function references
TOOLS = {
    "browse-products": {
        "description": "Browse and search products in the Aurora Spark e-commerce catalog with filtering and search capabilities",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by product category (e.g., 'vegetables', 'fruits', 'dairy')"
                },
                "search_term": {
                    "type": "string",
                    "description": "Search in product names and descriptions"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of products to return (default: 20, max: 100)",
                    "default": 20
                },
                "include_out_of_stock": {
                    "type": "boolean",
                    "description": "Whether to include out of stock products",
                    "default": True
                },
                "min_price": {
                    "type": "number",
                    "description": "Minimum price filter"
                },
                "max_price": {
                    "type": "number",
                    "description": "Maximum price filter"
                }
            },
            "required": []
        }
    },
    "get-category-counts": {
        "description": "Get product counts by category for Aurora Spark e-commerce catalog",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}




















# E-commerce tool wrapper functions
async def browse_products_wrapper(**kwargs):
    """Wrapper for browse-products tool."""
    try:
        # Import the e-commerce service and models
        from src.services.ecommerce_service import EcommerceService
        from src.models.ecommerce_models import ProductBrowseRequest
        from src.tools.ecommerce_tools import _convert_browse_result_to_dict
        from datetime import datetime
        
        # Remove default None values
        clean_kwargs = {k: v for k, v in kwargs.items() if v is not None}
        
        dual_logger.info(f"🔄 HTTP browsing products - Category: {clean_kwargs.get('category')}, Search: {clean_kwargs.get('search_term')}")
        
        # Create browse request
        request = ProductBrowseRequest(
            category=clean_kwargs.get('category'),
            search_term=clean_kwargs.get('search_term'),
            max_results=clean_kwargs.get('max_results', 20),
            include_out_of_stock=clean_kwargs.get('include_out_of_stock', True),
            min_price=clean_kwargs.get('min_price'),
            max_price=clean_kwargs.get('max_price')
        )
        
        # Initialize service and perform browsing
        service = EcommerceService()
        result = await service.browse_products(request)
        
        # Convert result to dictionary format
        response = _convert_browse_result_to_dict(result)
        dual_logger.info(f"✅ HTTP product browsing completed - Found {result.total_found} products")
        
        return response
        
    except Exception as e:
        dual_logger.error(f"❌ Error browsing products via HTTP: {str(e)}")
        return {
            "status": "error",
            "error_message": str(e),
            "products": [],
            "total_found": 0,
            "returned_count": 0,
            "categories": {
                "available_categories": [],
                "categories_in_results": []
            },
            "timestamp": datetime.now().isoformat()
        }


async def get_category_counts_wrapper(**kwargs):
    """Wrapper for get-category-counts tool."""
    try:
        # Import the e-commerce service and models
        from src.services.ecommerce_service import EcommerceService
        from src.models.ecommerce_models import CategoryCountsRequest
        from src.tools.ecommerce_tools import _convert_category_counts_result_to_dict
        from datetime import datetime
        
        dual_logger.info("🔄 HTTP getting category counts")
        
        # Create category counts request
        request = CategoryCountsRequest()
        
        # Initialize service and get category counts
        service = EcommerceService()
        result = await service.get_category_counts(request)
        
        # Convert result to dictionary format
        response = _convert_category_counts_result_to_dict(result)
        dual_logger.info(f"✅ HTTP category counts completed - Found {result.total_categories} categories")
        
        return response
        
    except Exception as e:
        dual_logger.error(f"❌ Error getting category counts via HTTP: {str(e)}")
        return {
            "status": "error",
            "error_message": str(e),
            "categories": [],
            "total_products": 0,
            "total_categories": 0,
            "timestamp": datetime.now().isoformat()
        }


# Direct tool function mapping
TOOL_FUNCTIONS = {
    "browse-products": browse_products_wrapper,
    "get-category-counts": get_category_counts_wrapper,
}

class MCPContext:
    """MCP context for tool execution."""
    def __init__(self):
        self.errors = []
    
    async def error(self, message: str):
        """Handle error messages."""
        self.errors.append(message)
        print(f"MCP Error: {message}")

# Global context
ctx = MCPContext()

def get_tool_function(tool_name: str):
    """Get the actual tool function for execution."""
    return TOOL_FUNCTIONS.get(tool_name)

@app.get("/")
async def root():
    """Root endpoint with server information."""
    return {
        "service": "E-commerce MCP HTTP Transport",
        "version": "1.0.0",
        "protocol": "mcp",
        "transport": "http",
        "status": "running",
        "mcp_version": "2024-11-05",
        "tools_count": len(TOOLS),
        "timestamp": datetime.now().isoformat(),
        "description": "AI-powered e-commerce product catalog operations with product browsing and category management"
    }

@app.post("/")
async def handle_root_mcp(request: Request):
    """Handle MCP requests at root path (some clients expect this)."""
    try:
        data = await request.json()
        method = data.get("method", "")
        
        # Route to appropriate MCP endpoint
        if method == "initialize":
            return await initialize_server(request)
        elif method == "tools/list":
            return await list_tools(request)
        elif method == "tools/call":
            return await call_tool(request)
        elif method == "ping":
            return await ping_server(request)
        else:
            return {
                "jsonrpc": "2.0",
                "id": data.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    except Exception as e:
        print(f"Error handling root MCP request: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                }
            }
        )

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "mcp_server": "running",
        "initialized": server_state["initialized"],
        "tools_available": len(TOOLS),
        "timestamp": datetime.now().isoformat()
    }

@app.options("/tools")
async def options_tools():
    """Handle OPTIONS requests for tools endpoint."""
    return {
        "methods": ["GET", "OPTIONS"],
        "endpoint": "tools",
        "description": "List all available MCP tools",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/tools")
async def get_tools():
    """REST API endpoint to list available tools."""
    tools = []
    for tool_name, tool_info in TOOLS.items():
        tools.append({
            "name": tool_name,
            "description": tool_info["description"],
            "schema": tool_info["inputSchema"]
        })
    
    return {
        "tools": tools,
        "count": len(tools),
        "timestamp": datetime.now().isoformat()
    }

@app.options("/tools/{tool_name}")
async def options_tool_rest(tool_name: str):
    """Handle OPTIONS requests for tool endpoints."""
    # Check if tool exists
    if tool_name not in TOOLS:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    
    return {
        "methods": ["POST", "OPTIONS"],
        "tool_name": tool_name,
        "description": TOOLS[tool_name]["description"],
        "timestamp": datetime.now().isoformat()
    }

@app.post("/tools/{tool_name}")
async def call_tool_rest(tool_name: str, request: Request):
    """REST API endpoint to call a specific tool."""
    try:
        data = await request.json()
        
        # Check if tool exists
        if tool_name not in TOOLS:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        
        tool_info = TOOLS[tool_name]
        
        # Get tool function
        tool_func = get_tool_function(tool_name)
        if not tool_func:
            raise HTTPException(status_code=500, detail=f"Tool function for '{tool_name}' not found")
        
        # Apply defaults for missing arguments
        schema_props = tool_info["inputSchema"]["properties"]
        final_args = {}
        
        for prop_name, prop_info in schema_props.items():
            if prop_name in data:
                final_args[prop_name] = data[prop_name]
            elif "default" in prop_info:
                final_args[prop_name] = prop_info["default"]
        
        # Log the tool call
        dual_logger.info(f"🔧 REST API Tool Call: {tool_name}")
        dual_logger.debug(f"Tool arguments: {json.dumps(final_args, indent=2, default=str)}")
        
        # Call the tool function
        result = await tool_func(**final_args)
        
        # Convert result to JSON-serializable format
        if hasattr(result, 'dict'):
            result_data = result.dict()
        elif hasattr(result, '__dict__'):
            result_data = result.__dict__
        else:
            result_data = result
        
        # Log successful result
        dual_logger.info(f"✅ REST API Tool {tool_name} completed successfully")
        dual_logger.debug(f"Result type: {type(result_data)}")
        
        return {
            "result": result_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        dual_logger.error(f"❌ REST API Tool {tool_name} execution failed: {str(e)}")
        dual_logger.error(f"Exception details: {traceback.format_exc()}")
        
        print(f"Error calling tool {tool_name}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/mcp/server/initialize")
async def initialize_server(request: Request):
    """Initialize MCP server."""
    try:
        data = await request.json()
        
        # Extract client info
        client_info = data.get("params", {}).get("clientInfo", {})
        protocol_version = data.get("params", {}).get("protocolVersion", "2024-11-05")
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Update server state
        server_state.update({
            "initialized": True,
            "session_id": session_id,
            "client_info": client_info
        })
        
        print(f"✅ E-commerce MCP server initialized for client: {client_info.get('name', 'Unknown')}")
        
        # Return initialization response
        return {
            "jsonrpc": "2.0",
            "id": data.get("id"),
            "result": {
                "protocolVersion": protocol_version,
                "capabilities": {
                    "tools": {
                        "listChanged": False
                    }
                },
                "serverInfo": {
                    "name": "E-commerce MCP Server",
                    "version": "1.0.0"
                },
                "instructions": """
# E-commerce MCP Server

Provides AI-powered tools for e-commerce product catalog operations.

Available tools:
- browse-products: Browse and search products in the Aurora Spark e-commerce catalog with filtering capabilities
- get-category-counts: Get product counts by category for Aurora Spark e-commerce catalog
                """
            }
        }
        
    except Exception as e:
        print(f"Error initializing server: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mcp/server/ping")
async def ping_server(request: Request):
    """Handle ping requests."""
    try:
        data = await request.json()
        return {
            "jsonrpc": "2.0",
            "id": data.get("id"),
            "result": {}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mcp/tools/list")
async def list_tools(request: Request):
    """List available MCP tools."""
    try:
        data = await request.json()
        
        # Build tools list from our registry
        tools = []
        for tool_name, tool_info in TOOLS.items():
            tool_data = {
                "name": tool_name,
                "description": tool_info["description"],
                "inputSchema": tool_info["inputSchema"]
            }
            tools.append(tool_data)
        
        return {
            "jsonrpc": "2.0", 
            "id": data.get("id"),
            "result": {
                "tools": tools
            }
        }
        
    except Exception as e:
        print(f"Error listing tools: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mcp/request")
async def unified_mcp_request(request: Request):
    """Unified MCP request endpoint for langgraph connector compatibility."""
    try:
        data = await request.json()
        method = data.get("method", "")
        params = data.get("params", {})
        request_id = data.get("id")
        
        dual_logger.info(f"🔧 Unified MCP Request: {method}")
        dual_logger.debug(f"Request params: {json.dumps(params, indent=2, default=str)}")
        
        # Route to appropriate handler based on method
        if method == "initialize":
            return await handle_mcp_initialize(data)
        elif method == "tools/list":
            return await handle_mcp_tools_list(data)
        elif method == "tools/call":
            return await handle_mcp_tools_call(data)
        elif method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {}
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
            
    except Exception as e:
        dual_logger.error(f"❌ Unified MCP request failed: {str(e)}")
        return {
            "jsonrpc": "2.0",
            "id": data.get("id", None),
            "error": {
                "code": -32700,
                "message": "Parse error"
            }
        }

@app.post("/mcp/notification")
async def mcp_notification(request: Request):
    """Handle MCP notifications."""
    try:
        data = await request.json()
        method = data.get("method", "")
        
        dual_logger.info(f"📢 MCP Notification: {method}")
        
        # For notifications, we just acknowledge them
        # No response is needed for notifications
        return JSONResponse(content={}, status_code=200)
        
    except Exception as e:
        dual_logger.error(f"❌ MCP notification failed: {str(e)}")
        return JSONResponse(content={}, status_code=500)

async def handle_mcp_initialize(data: Dict[str, Any]):
    """Handle MCP initialize request."""
    params = data.get("params", {})
    client_info = params.get("clientInfo", {})
    protocol_version = params.get("protocolVersion", "2024-11-05")
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    
    # Update server state
    server_state.update({
        "initialized": True,
        "session_id": session_id,
        "client_info": client_info
    })
    
    dual_logger.info(f"✅ MCP server initialized for client: {client_info.get('name', 'Unknown')}")
    
    return {
        "jsonrpc": "2.0",
        "id": data.get("id"),
        "result": {
            "protocolVersion": protocol_version,
            "capabilities": {
                "tools": {
                    "listChanged": False
                }
            },
            "serverInfo": {
                "name": "E-commerce MCP Server",
                "version": "1.0.0"
            }
        }
    }

async def handle_mcp_tools_list(data: Dict[str, Any]):
    """Handle MCP tools/list request."""
    tools = []
    for tool_name, tool_info in TOOLS.items():
        tool_data = {
            "name": tool_name,
            "description": tool_info["description"],
            "inputSchema": tool_info["inputSchema"]
        }
        tools.append(tool_data)
    
    return {
        "jsonrpc": "2.0", 
        "id": data.get("id"),
        "result": {
            "tools": tools
        }
    }

async def handle_mcp_tools_call(data: Dict[str, Any]):
    """Handle MCP tools/call request."""
    params = data.get("params", {})
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    if not tool_name:
        return {
            "jsonrpc": "2.0",
            "id": data.get("id"),
            "error": {
                "code": -32602,
                "message": "Tool name is required"
            }
        }
    
    # Get tool from registry
    tool_info = TOOLS.get(tool_name)
    if not tool_info:
        return {
            "jsonrpc": "2.0",
            "id": data.get("id"),
            "error": {
                "code": -32601,
                "message": f"Tool '{tool_name}' not found"
            }
        }
    
    # Get tool function
    tool_func = get_tool_function(tool_name)
    if not tool_func:
        return {
            "jsonrpc": "2.0",
            "id": data.get("id"),
            "error": {
                "code": -32603,
                "message": f"Tool function for '{tool_name}' not found"
            }
        }

    # Reset context errors
    ctx.errors = []
    
    # Log the tool call with detailed information
    logger.info(f"🔧 MCP Tool Call: {tool_name}")
    logger.debug(f"Tool arguments: {json.dumps(arguments, indent=2, default=str)}")
    
    try:
        # Apply defaults for missing arguments
        schema_props = tool_info["inputSchema"]["properties"]
        final_args = {}
        
        for prop_name, prop_info in schema_props.items():
            if prop_name in arguments:
                final_args[prop_name] = arguments[prop_name]
            elif "default" in prop_info:
                final_args[prop_name] = prop_info["default"]
        
        result = await tool_func(**final_args)
        
        # Convert result to JSON-serializable format
        if hasattr(result, 'dict'):
            result_data = result.dict()
        elif hasattr(result, '__dict__'):
            result_data = result.__dict__
        else:
            result_data = result
        
        # Log the successful result
        logger.info(f"✅ Tool {tool_name} completed successfully")
        logger.debug(f"Tool result type: {type(result_data)}")
        
        return {
            "jsonrpc": "2.0",
            "id": data.get("id"),
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result_data, indent=2, default=str)
                    }
                ]
            }
        }
        
    except Exception as tool_error:
        # Return tool execution error
        error_msg = f"Tool execution failed: {str(tool_error)}"
        if ctx.errors:
            error_msg += f"\nContext errors: {'; '.join(ctx.errors)}"
        
        # Log the error with full details
        logger.error(f"❌ Tool {tool_name} execution failed: {error_msg}")
        logger.error(f"Exception details: {traceback.format_exc()}")
        
        return {
            "jsonrpc": "2.0",
            "id": data.get("id"),
            "error": {
                "code": -32603,
                "message": error_msg
            }
        }

@app.post("/mcp/tools/call")
async def call_tool(request: Request):
    """Call an MCP tool (legacy endpoint for compatibility)."""
    try:
        data = await request.json()
        return await handle_mcp_tools_call(data)
        
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": data.get("id", None),
            "error": {
                "code": -32700,
                "message": "Parse error"
            }
        }

if __name__ == "__main__":
    dual_logger.info("🚀 Starting E-commerce MCP HTTP Transport Server...")
    dual_logger.info(f"📡 Server will be available at: http://0.0.0.0:{args.port}")
    dual_logger.info(f"🔗 MCP Server Info: http://0.0.0.0:{args.port}/mcp/server/info")
    dual_logger.info(f"🏥 Health check: http://0.0.0.0:{args.port}/health")
    dual_logger.info(f"📋 Tools list: http://0.0.0.0:{args.port}/tools")
    dual_logger.info(f"🔧 Available tools: {', '.join(TOOLS.keys())}")
    
    print("🚀 Starting E-commerce MCP HTTP Transport Server...")
    print(f"📡 Server will be available at: http://0.0.0.0:{args.port}")
    print(f"🔗 MCP Server Info: http://0.0.0.0:{args.port}/")
    print(f"🏥 Health check: http://0.0.0.0:{args.port}/health")
    print(f"📋 Tools list: http://0.0.0.0:{args.port}/tools")
    print(f"🔧 Available tools: {', '.join(TOOLS.keys())}")
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        access_log=True,
        log_level=LOG_LEVEL.lower()
    ) 