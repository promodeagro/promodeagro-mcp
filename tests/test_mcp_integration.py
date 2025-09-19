"""
Integration tests for MCP server functionality.
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal
from datetime import datetime

from mcp_stdio_server import MCPStdioServer
from src.models.ecommerce_models import (
    ProductBrowseRequest, CategoryCountsRequest, ProductBrowseResult,
    CategoryCountsResult, ProductInfo, CategoryInfo, ProductStock,
    ProductAttributes, ProductAvailability, SearchMetadata
)


class TestMCPStdioServerInitialization:
    """Test MCP Stdio Server initialization."""
    
    @patch('mcp_stdio_server.EcommerceService')
    def test_server_initialization(self, mock_service_class):
        """Test server initializes correctly."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        server = MCPStdioServer()
        
        assert server.capabilities == {"tools": {}}
        assert server.server_info["name"] == "E-commerce MCP Server"
        assert server.server_info["version"] == "1.0.0"
        assert "browse-products" in server.tools
        assert "get-category-counts" in server.tools
        assert server.service == mock_service
    
    def test_tools_definition_structure(self):
        """Test tools are properly defined."""
        with patch('mcp_stdio_server.EcommerceService'):
            server = MCPStdioServer()
            
            # Check browse-products tool
            browse_tool = server.tools["browse-products"]
            assert browse_tool["name"] == "browse-products"
            assert "browse and search products" in browse_tool["description"].lower()
            assert "inputSchema" in browse_tool
            assert browse_tool["inputSchema"]["type"] == "object"
            assert "properties" in browse_tool["inputSchema"]
            
            # Check get-category-counts tool
            counts_tool = server.tools["get-category-counts"]
            assert counts_tool["name"] == "get-category-counts"
            assert "category counts" in counts_tool["description"].lower()
            assert "inputSchema" in counts_tool
            
            # Verify schema properties for browse-products
            browse_properties = browse_tool["inputSchema"]["properties"]
            expected_properties = ["category", "search_term", "max_results", "include_out_of_stock", "min_price", "max_price"]
            for prop in expected_properties:
                assert prop in browse_properties
            
            # Verify required fields (should be empty for optional parameters)
            assert browse_tool["inputSchema"]["required"] == []


class TestMCPStdioServerHandlers:
    """Test MCP request handlers."""
    
    @patch('mcp_stdio_server.EcommerceService')
    @pytest.mark.asyncio
    async def test_handle_initialize(self, mock_service_class):
        """Test initialize handler."""
        server = MCPStdioServer()
        
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "cursor", "version": "1.0"}
        }
        
        result = await server.handle_initialize(params)
        
        assert result["protocolVersion"] == "2024-11-05"
        assert result["capabilities"] == {"tools": {}}
        assert result["serverInfo"]["name"] == "E-commerce MCP Server"
        assert result["serverInfo"]["version"] == "1.0.0"
        assert "instructions" in result
        assert "browse-products" in result["instructions"]
    
    @patch('mcp_stdio_server.EcommerceService')
    @pytest.mark.asyncio
    async def test_handle_tools_list(self, mock_service_class):
        """Test tools/list handler."""
        server = MCPStdioServer()
        
        result = await server.handle_tools_list({})
        
        assert "tools" in result
        assert len(result["tools"]) == 2
        
        tool_names = [tool["name"] for tool in result["tools"]]
        assert "browse-products" in tool_names
        assert "get-category-counts" in tool_names
        
        # Check tool structure
        browse_tool = next(t for t in result["tools"] if t["name"] == "browse-products")
        assert "description" in browse_tool
        assert "inputSchema" in browse_tool
        assert isinstance(browse_tool["inputSchema"], dict)
    
    @patch('mcp_stdio_server.EcommerceService')
    @pytest.mark.asyncio
    async def test_handle_tools_call_browse_products(self, mock_service_class):
        """Test tools/call handler for browse-products."""
        # Setup mock service
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        # Create sample result
        sample_product = ProductInfo(
            product_id='product-fruits-001',
            product_code='APL-FRU-001',
            name='Apples',
            description='Fresh Red Apples',
            category='Fruits',
            price=150.50,
            unit='kg',
            stock=ProductStock(available=100, status='In Stock', track_inventory=True),
            variants=[],
            has_variants=False,
            attributes=ProductAttributes(organic=True),
            availability=ProductAvailability()
        )
        
        sample_result = ProductBrowseResult(
            products=[sample_product],
            search_metadata=SearchMetadata(category_filter='fruits')
        )
        mock_service.browse_products.return_value = sample_result
        
        server = MCPStdioServer()
        
        params = {
            "name": "browse-products",
            "arguments": {
                "category": "fruits",
                "max_results": 10
            }
        }
        
        result = await server.handle_tools_call(params)
        
        # Verify service was called
        mock_service.browse_products.assert_called_once()
        call_args = mock_service.browse_products.call_args[0][0]
        assert isinstance(call_args, ProductBrowseRequest)
        assert call_args.category == "fruits"
        assert call_args.max_results == 10
        
        # Verify result structure
        assert "content" in result
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "text"
        
        # Parse and verify JSON content
        content_text = result["content"][0]["text"]
        content_data = json.loads(content_text)
        assert "products" in content_data
        assert len(content_data["products"]) == 1
        assert content_data["products"][0]["name"] == "Apples"
    
    @patch('mcp_stdio_server.EcommerceService')
    @pytest.mark.asyncio
    async def test_handle_tools_call_get_category_counts(self, mock_service_class):
        """Test tools/call handler for get-category-counts."""
        # Setup mock service
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        # Create sample result
        sample_categories = [
            CategoryInfo(name='Fruits', count=10, percentage=50.0),
            CategoryInfo(name='Vegetables', count=10, percentage=50.0)
        ]
        
        sample_result = CategoryCountsResult(
            categories=sample_categories,
            total_products=20,
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )
        mock_service.get_category_counts.return_value = sample_result
        
        server = MCPStdioServer()
        
        params = {
            "name": "get-category-counts",
            "arguments": {}
        }
        
        result = await server.handle_tools_call(params)
        
        # Verify service was called
        mock_service.get_category_counts.assert_called_once()
        call_args = mock_service.get_category_counts.call_args[0][0]
        assert isinstance(call_args, CategoryCountsRequest)
        
        # Verify result structure
        assert "content" in result
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "text"
        
        # Parse and verify JSON content
        content_text = result["content"][0]["text"]
        content_data = json.loads(content_text)
        assert "categories" in content_data
        assert "total_products" in content_data
        assert len(content_data["categories"]) == 2
        assert content_data["total_products"] == 20
    
    @patch('mcp_stdio_server.EcommerceService')
    @pytest.mark.asyncio
    async def test_handle_tools_call_unknown_tool(self, mock_service_class):
        """Test tools/call handler with unknown tool."""
        server = MCPStdioServer()
        
        params = {
            "name": "unknown-tool",
            "arguments": {}
        }
        
        with pytest.raises(Exception, match="Unknown tool: unknown-tool"):
            await server.handle_tools_call(params)
    
    @patch('mcp_stdio_server.EcommerceService')
    @pytest.mark.asyncio
    async def test_handle_tools_call_service_error(self, mock_service_class):
        """Test tools/call handler with service error."""
        # Setup mock service to raise error
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        mock_service.browse_products.side_effect = Exception("Database error")
        
        server = MCPStdioServer()
        
        params = {
            "name": "browse-products",
            "arguments": {"category": "fruits"}
        }
        
        result = await server.handle_tools_call(params)
        
        # Should return error in content
        assert "content" in result
        assert len(result["content"]) == 1
        assert "Error browsing products" in result["content"][0]["text"]
        assert "isError" in result
        assert result["isError"] is True


class TestMCPStdioServerRequestHandling:
    """Test full MCP request handling."""
    
    @patch('mcp_stdio_server.EcommerceService')
    @pytest.mark.asyncio
    async def test_handle_request_initialize(self, mock_service_class):
        """Test full request handling for initialize."""
        server = MCPStdioServer()
        
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "cursor", "version": "1.0"}
            }
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2024-11-05"
    
    @patch('mcp_stdio_server.EcommerceService')
    @pytest.mark.asyncio
    async def test_handle_request_tools_list(self, mock_service_class):
        """Test full request handling for tools/list."""
        server = MCPStdioServer()
        
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) == 2
    
    @patch('mcp_stdio_server.EcommerceService')
    @pytest.mark.asyncio
    async def test_handle_request_unknown_method(self, mock_service_class):
        """Test handling of unknown method."""
        server = MCPStdioServer()
        
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "unknown/method",
            "params": {}
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 3
        assert "error" in response
        assert response["error"]["code"] == -32603
        assert "Unknown method" in response["error"]["message"]
    
    @patch('mcp_stdio_server.EcommerceService')
    @pytest.mark.asyncio
    async def test_handle_request_service_error(self, mock_service_class):
        """Test handling of service errors."""
        # Setup mock service to raise error
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        mock_service.browse_products.side_effect = Exception("Critical error")
        
        server = MCPStdioServer()
        
        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "browse-products",
                "arguments": {"category": "fruits"}
            }
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 4
        assert "result" in response  # Error should be in result content, not as JSON-RPC error
        assert "content" in response["result"]


class TestToolParameterValidation:
    """Test parameter validation for MCP tools."""
    
    @patch('mcp_stdio_server.EcommerceService')
    @pytest.mark.asyncio
    async def test_browse_products_parameter_types(self, mock_service_class):
        """Test parameter type handling for browse-products."""
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        # Mock result
        mock_result = ProductBrowseResult(products=[], search_metadata=SearchMetadata())
        mock_service.browse_products.return_value = mock_result
        
        server = MCPStdioServer()
        
        # Test various parameter types
        params = {
            "name": "browse-products",
            "arguments": {
                "category": "fruits",           # string
                "search_term": "apple",         # string
                "max_results": 15,              # integer
                "include_out_of_stock": False,  # boolean
                "min_price": 50.0,              # float
                "max_price": 200.5              # float
            }
        }
        
        result = await server.handle_tools_call(params)
        
        # Verify service was called with correct parameter types
        call_args = mock_service.browse_products.call_args[0][0]
        assert isinstance(call_args.category, str)
        assert isinstance(call_args.search_term, str)
        assert isinstance(call_args.max_results, int)
        assert isinstance(call_args.include_out_of_stock, bool)
        assert isinstance(call_args.min_price, float)
        assert isinstance(call_args.max_price, float)
    
    @patch('mcp_stdio_server.EcommerceService')
    @pytest.mark.asyncio
    async def test_browse_products_optional_parameters(self, mock_service_class):
        """Test optional parameter handling."""
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        mock_result = ProductBrowseResult(products=[], search_metadata=SearchMetadata())
        mock_service.browse_products.return_value = mock_result
        
        server = MCPStdioServer()
        
        # Test with minimal parameters
        params = {
            "name": "browse-products",
            "arguments": {
                "category": "fruits"
                # All other parameters should use defaults
            }
        }
        
        result = await server.handle_tools_call(params)
        
        call_args = mock_service.browse_products.call_args[0][0]
        assert call_args.category == "fruits"
        assert call_args.search_term is None  # Default
        assert call_args.max_results == 20    # Default
        assert call_args.include_out_of_stock is True  # Default
        assert call_args.min_price is None    # Default
        assert call_args.max_price is None    # Default
    
    @patch('mcp_stdio_server.EcommerceService')
    @pytest.mark.asyncio
    async def test_get_category_counts_no_parameters(self, mock_service_class):
        """Test get-category-counts with no parameters."""
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        mock_result = CategoryCountsResult(
            categories=[],
            total_products=0,
            timestamp=datetime.now()
        )
        mock_service.get_category_counts.return_value = mock_result
        
        server = MCPStdioServer()
        
        params = {
            "name": "get-category-counts",
            "arguments": {}  # No parameters needed
        }
        
        result = await server.handle_tools_call(params)
        
        # Should work fine with empty arguments
        mock_service.get_category_counts.assert_called_once()
        call_args = mock_service.get_category_counts.call_args[0][0]
        assert isinstance(call_args, CategoryCountsRequest)
        assert "content" in result
