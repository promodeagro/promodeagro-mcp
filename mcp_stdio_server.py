#!/usr/bin/env python3
"""
MCP Stdio Transport Server for E-commerce Catalog
This implements the proper MCP stdio transport protocol for Cursor compatibility.
"""

import asyncio
import json
import sys
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add the project to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import our e-commerce services and models
from src.services.ecommerce_service import EcommerceService
from src.models.ecommerce_models import ProductBrowseRequest, CategoryCountsRequest

# Configure logging to stderr to avoid interfering with stdio communication
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # Important: log to stderr, not stdout
)
logger = logging.getLogger(__name__)

class MCPStdioServer:
    """MCP Server using stdio transport for Cursor compatibility"""
    
    def __init__(self):
        self.capabilities = {
            "tools": {}
        }
        self.server_info = {
            "name": "E-commerce MCP Server",
            "version": "1.0.0"
        }
        self.tools = self._get_tools()
        self.service = EcommerceService()
        
    def _get_tools(self) -> Dict[str, Any]:
        """Get available tools definitions"""
        return {
            "browse-products": {
                "name": "browse-products",
                "description": "Browse and search products in the e-commerce catalog with filtering and search capabilities",
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
                "name": "get-category-counts",
                "description": "Get product counts by category for e-commerce catalog",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize request"""
        logger.info("MCP Server initializing...")
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": self.capabilities,
            "serverInfo": self.server_info,
            "instructions": "\n# E-commerce MCP Server\n\nProvides AI-powered tools for e-commerce product catalog operations.\n\nAvailable tools:\n- browse-products: Browse and search products in the e-commerce catalog with filtering capabilities\n- get-category-counts: Get product counts by category for e-commerce catalog\n"
        }

    async def handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        logger.info("Listing available tools")
        tools_list = [
            {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": tool["inputSchema"]
            }
            for tool in self.tools.values()
        ]
        return {"tools": tools_list}

    async def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        logger.info(f"Calling tool: {tool_name}")
        
        if tool_name == "browse-products":
            return await self._handle_browse_products(arguments)
        elif tool_name == "get-category-counts":
            return await self._handle_get_category_counts(arguments)
        else:
            raise Exception(f"Unknown tool: {tool_name}")

    async def _handle_browse_products(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle browse-products tool call"""
        try:
            # Create request object
            request = ProductBrowseRequest(
                category=arguments.get("category"),
                search_term=arguments.get("search_term"),
                max_results=arguments.get("max_results", 20),
                include_out_of_stock=arguments.get("include_out_of_stock", True),
                min_price=arguments.get("min_price"),
                max_price=arguments.get("max_price")
            )
            
            # Call service
            result = await self.service.browse_products(request)
            
            # Convert to dictionary for JSON serialization
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "products": [
                                {
                                    "product_id": p.product_id,
                                    "name": p.name,
                                    "description": p.description,
                                    "category": p.category,
                                    "price": p.price,
                                    "unit": p.unit,
                                    "stock": {
                                        "available": p.stock.available,
                                        "status": p.stock.status,
                                        "track_inventory": p.stock.track_inventory
                                    },
                                    "variants": [
                                        {
                                            "variant_id": v.variant_id,
                                            "name": v.name,
                                            "price": v.price,
                                            "stock_available": v.stock_available
                                        }
                                        for v in p.variants
                                    ] if p.variants else [],
                                    "attributes": {
                                        "organic": p.attributes.organic,
                                        "brand": p.attributes.brand,
                                        "perishable": p.attributes.perishable,
                                        "shelf_life_days": p.attributes.shelf_life_days
                                    },
                                    "availability": {
                                        "is_active": p.availability.is_active,
                                        "status": p.availability.status,
                                        "b2c_available": p.availability.b2c_available
                                    }
                                }
                                for p in result.products
                            ],
                            "search_metadata": {
                                "category_filter": result.search_metadata.category_filter,
                                "search_term": result.search_metadata.search_term,
                                "price_range": result.search_metadata.price_range,
                                "include_out_of_stock": result.search_metadata.include_out_of_stock,
                                "max_results": result.search_metadata.max_results
                            }
                        }, indent=2)
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in browse_products: {str(e)}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error browsing products: {str(e)}"
                    }
                ],
                "isError": True
            }

    async def _handle_get_category_counts(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get-category-counts tool call"""
        try:
            # Create request object
            request = CategoryCountsRequest()
            
            # Call service
            result = await self.service.get_category_counts(request)
            
            # Convert to dictionary for JSON serialization
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "categories": [
                                {
                                    "name": c.name,
                                    "count": c.count,
                                    "percentage": c.percentage
                                }
                                for c in result.categories
                            ],
                            "total_products": result.total_products,
                            "timestamp": result.timestamp.isoformat()
                        }, indent=2)
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in get_category_counts: {str(e)}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error getting category counts: {str(e)}"
                    }
                ],
                "isError": True
            }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP request"""
        method = request.get("method")
        params = request.get("params", {})
        
        try:
            if method == "initialize":
                result = await self.handle_initialize(params)
            elif method == "tools/list":
                result = await self.handle_tools_list(params)
            elif method == "tools/call":
                result = await self.handle_tools_call(params)
            else:
                raise Exception(f"Unknown method: {method}")
            
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error handling {method}: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }

    async def run(self):
        """Main server loop reading from stdin and writing to stdout"""
        logger.info("🚀 Starting E-commerce MCP Stdio Server...")
        logger.info("📡 Listening on stdin for MCP requests...")
        logger.info("🔧 Available tools: browse-products, get-category-counts")
        
        try:
            while True:
                # Read line from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                
                if not line:  # EOF
                    break
                    
                line = line.strip()
                if not line:  # Empty line
                    continue
                
                try:
                    # Parse JSON-RPC request
                    request = json.loads(line)
                    logger.info(f"📥 Received request: {request.get('method')}")
                    
                    # Handle request
                    response = await self.handle_request(request)
                    
                    # Send response to stdout
                    response_line = json.dumps(response, separators=(',', ':'))
                    print(response_line, flush=True)  # Important: flush immediately
                    logger.info(f"📤 Sent response for: {request.get('method')}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        }
                    }
                    print(json.dumps(error_response, separators=(',', ':')), flush=True)
                
        except KeyboardInterrupt:
            logger.info("🛑 Server shutting down...")
        except Exception as e:
            logger.error(f"💥 Server error: {str(e)}")
            raise

if __name__ == "__main__":
    server = MCPStdioServer()
    asyncio.run(server.run())
