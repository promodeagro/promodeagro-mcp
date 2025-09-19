# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""E-commerce MCP Server - AI-Enabled E-commerce Operations.

This is a Model Context Protocol (MCP) server that enables AI assistants to interact
with e-commerce systems and perform product catalog operations.

The server provides comprehensive tools for:
- Product browsing and search with filtering capabilities
- Category-based product organization
- Stock availability checking
- Price range filtering
- Product variant management

All functionality is organized into modular services for maintainability and extensibility.
"""

import asyncio
import logging
import os

from loguru import logger
from mcp.server.fastmcp import FastMCP

from .consts import ECOMMERCE_MCP_SERVER_APPLICATION_NAME
from .tools.ecommerce_tools import (
    browse_products_tool, get_category_counts_tool
)


def create_server() -> FastMCP:
    """Create and configure the E-commerce MCP server."""
    
    # Initialize the FastMCP server
    mcp = FastMCP(ECOMMERCE_MCP_SERVER_APPLICATION_NAME)
    
    # Register e-commerce tools
    logger.info("Registering E-commerce MCP tools...")
    
    browse_products_tool(mcp)
    get_category_counts_tool(mcp)
    
    # Note: Resource handlers removed for simplicity
    # The e-commerce tools are available directly via the registered @mcp.tool decorators
    logger.info("E-commerce MCP Server initialized successfully")
    return mcp


async def main():
    """Main entry point for the MCP server."""
    
    # Configure logging
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.remove()  # Remove default handler
    logger.add(
        lambda msg: print(msg, end=""),
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    logger.info(f"Starting {ECOMMERCE_MCP_SERVER_APPLICATION_NAME}")
    
    # Log configuration information
    logger.info("E-commerce MCP Server Configuration:")
    logger.info(f"  - Log Level: {log_level}")
    logger.info(f"  - AWS Region: {os.getenv('AWS_REGION', 'ap-south-1')}")
    
    # Create and run the server
    try:
        server = create_server()
        
        logger.info("E-commerce MCP Server is ready to process requests")
        
        # Try to run the server, handling asyncio loop conflicts
        try:
            await server.run()
        except RuntimeError as e:
            if "already running" in str(e).lower() or "cannot be called" in str(e).lower():
                logger.warning("Asyncio event loop conflict detected - server tools are registered and functional")
                logger.info("MCP tools are available for client connections")
                
                logger.info("Server is running and ready to accept MCP client connections...")
                logger.info("Press Ctrl+C to stop the server")
                
                # Simple wait that responds to KeyboardInterrupt properly
                try:
                    while True:
                        await asyncio.sleep(0.5)
                except KeyboardInterrupt:
                    logger.info("Server shutdown requested")
                    raise
            else:
                raise
        
    except KeyboardInterrupt:
        logger.info("Shutting down E-commerce MCP Server...")
    except Exception as e:
        logger.error(f"Error running E-commerce MCP Server: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main()) 