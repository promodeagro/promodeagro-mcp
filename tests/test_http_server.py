"""
Tests for HTTP MCP server functionality.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from decimal import Decimal
from datetime import datetime

# Import the HTTP server app
from mcp_http_server import app
from src.models.ecommerce_models import (
    ProductBrowseResult, CategoryCountsResult, ProductInfo, CategoryInfo,
    ProductStock, ProductAttributes, ProductAvailability, SearchMetadata
)


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_ecommerce_service():
    """Mock EcommerceService for HTTP server tests."""
    with patch('mcp_http_server.ecommerce_service') as mock_service:
        yield mock_service


class TestHTTPServerEndpoints:
    """Test HTTP server endpoints."""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["mcp_server"] == "running"
        assert "tools_available" in data
        assert "timestamp" in data
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "E-commerce MCP HTTP Transport"
        assert data["version"] == "1.0.0"
        assert "available_endpoints" in data
        assert "/tools" in data["available_endpoints"]
    
    def test_tools_endpoint(self, client):
        """Test tools list endpoint."""
        response = client.get("/tools")
        
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert len(data["tools"]) == 2
        
        tool_names = [tool["name"] for tool in data["tools"]]
        assert "browse-products" in tool_names
        assert "get-category-counts" in tool_names
    
    def test_mcp_server_info_endpoint(self, client):
        """Test MCP server info endpoint."""
        response = client.get("/mcp/server/info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "E-commerce MCP Server"
        assert data["version"] == "1.0.0"
        assert "capabilities" in data
        assert "tools" in data["capabilities"]


class TestMCPProtocolEndpoints:
    """Test MCP protocol endpoints."""
    
    def test_mcp_server_initialize(self, client):
        """Test MCP server initialize endpoint."""
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "1.0"}
            }
        }
        
        response = client.post("/mcp/server/initialize", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert "result" in data
        assert data["result"]["protocolVersion"] == "2024-11-05"
        assert data["result"]["serverInfo"]["name"] == "E-commerce MCP Server"
    
    def test_mcp_tools_list(self, client):
        """Test MCP tools list endpoint."""
        request_data = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        response = client.post("/mcp/tools/list", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 2
        assert "result" in data
        assert "tools" in data["result"]
        assert len(data["result"]["tools"]) == 2
    
    @patch('mcp_http_server.ecommerce_service')
    def test_mcp_tools_call_browse_products(self, mock_service, client):
        """Test MCP tools call for browse-products."""
        # Setup mock
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
            attributes=ProductAttributes(),
            availability=ProductAvailability()
        )
        
        mock_result = ProductBrowseResult(
            products=[sample_product],
            search_metadata=SearchMetadata(category_filter='fruits')
        )
        
        mock_service.browse_products = AsyncMock(return_value=mock_result)
        
        request_data = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "browse-products",
                "arguments": {
                    "category": "fruits",
                    "max_results": 10
                }
            }
        }
        
        response = client.post("/mcp/tools/call", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 3
        assert "result" in data
    
    @patch('mcp_http_server.ecommerce_service')
    def test_mcp_tools_call_get_category_counts(self, mock_service, client):
        """Test MCP tools call for get-category-counts."""
        # Setup mock
        sample_categories = [
            CategoryInfo(name='Fruits', count=10, percentage=50.0),
            CategoryInfo(name='Vegetables', count=10, percentage=50.0)
        ]
        
        mock_result = CategoryCountsResult(
            categories=sample_categories,
            total_products=20,
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        mock_service.get_category_counts = AsyncMock(return_value=mock_result)
        
        request_data = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "get-category-counts",
                "arguments": {}
            }
        }
        
        response = client.post("/mcp/tools/call", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 4
        assert "result" in data


class TestDirectToolEndpoints:
    """Test direct tool endpoints (non-MCP)."""
    
    @patch('mcp_http_server.ecommerce_service')
    def test_direct_browse_products_post(self, mock_service, client):
        """Test direct POST to browse-products endpoint."""
        # Setup mock
        sample_product = ProductInfo(
            product_id='product-fruits-001',
            product_code='APL-FRU-001',
            name='Apples',
            description='Fresh Red Apples',
            category='Fruits',
            price=150.50,
            unit='kg',
            stock=ProductStock(available=100, status='In Stock'),
            variants=[],
            has_variants=False,
            attributes=ProductAttributes(),
            availability=ProductAvailability()
        )
        
        mock_result = ProductBrowseResult(
            products=[sample_product],
            search_metadata=SearchMetadata()
        )
        
        mock_service.browse_products = AsyncMock(return_value=mock_result)
        
        request_data = {
            "category": "fruits",
            "max_results": 10
        }
        
        response = client.post("/tools/browse-products", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert len(data["products"]) == 1
        assert data["products"][0]["name"] == "Apples"
    
    @patch('mcp_http_server.ecommerce_service')
    def test_direct_get_category_counts_post(self, mock_service, client):
        """Test direct POST to get-category-counts endpoint."""
        # Setup mock
        sample_categories = [
            CategoryInfo(name='Fruits', count=15, percentage=60.0),
            CategoryInfo(name='Vegetables', count=10, percentage=40.0)
        ]
        
        mock_result = CategoryCountsResult(
            categories=sample_categories,
            total_products=25,
            timestamp=datetime.now()
        )
        
        mock_service.get_category_counts = AsyncMock(return_value=mock_result)
        
        response = client.post("/tools/get-category-counts", json={})
        
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "total_products" in data
        assert len(data["categories"]) == 2
        assert data["total_products"] == 25


class TestErrorHandling:
    """Test error handling in HTTP server."""
    
    def test_invalid_json_request(self, client):
        """Test handling of invalid JSON in MCP requests."""
        # Send invalid JSON to MCP endpoint
        response = client.post(
            "/mcp/tools/call",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        # Should return 422 for unprocessable entity
        assert response.status_code == 422
    
    def test_missing_required_fields(self, client):
        """Test handling of missing required fields in MCP requests."""
        request_data = {
            "jsonrpc": "2.0",
            # Missing id and method
            "params": {}
        }
        
        response = client.post("/mcp/tools/call", json=request_data)
        
        # Should return validation error
        assert response.status_code == 422
    
    @patch('mcp_http_server.ecommerce_service')
    def test_service_error_handling(self, mock_service, client):
        """Test handling of service layer errors."""
        # Setup mock to raise exception
        mock_service.browse_products = AsyncMock(side_effect=Exception("Database error"))
        
        request_data = {
            "category": "fruits"
        }
        
        response = client.post("/tools/browse-products", json=request_data)
        
        # Should return 500 for internal server error
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "Database error" in str(data)
    
    def test_unknown_tool_call(self, client):
        """Test calling unknown tool via MCP."""
        request_data = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "unknown-tool",
                "arguments": {}
            }
        }
        
        response = client.post("/mcp/tools/call", json=request_data)
        
        assert response.status_code == 200  # MCP protocol returns 200 with error in response
        data = response.json()
        assert "error" in data or ("result" in data and "error" in str(data["result"]))


class TestCORSAndMiddleware:
    """Test CORS and middleware functionality."""
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/health")
        
        # CORS headers should be present
        assert response.status_code in [200, 204]
        # Note: Actual CORS header testing would need proper CORS configuration
    
    def test_logging_middleware(self, client):
        """Test that requests are logged (implicit test via successful responses)."""
        # Make a request and verify it completes successfully
        # The logging middleware should not interfere with normal operation
        response = client.get("/health")
        assert response.status_code == 200
        
        # If logging middleware was broken, this would fail
        response = client.get("/tools")
        assert response.status_code == 200


class TestParameterValidation:
    """Test parameter validation in HTTP endpoints."""
    
    @patch('mcp_http_server.ecommerce_service')
    def test_browse_products_parameter_types(self, mock_service, client):
        """Test parameter type validation for browse-products."""
        mock_service.browse_products = AsyncMock(return_value=ProductBrowseResult(
            products=[], search_metadata=SearchMetadata()
        ))
        
        # Test with various parameter types
        request_data = {
            "category": "fruits",
            "search_term": "apple", 
            "max_results": 15,
            "include_out_of_stock": False,
            "min_price": 50.0,
            "max_price": 200.5
        }
        
        response = client.post("/tools/browse-products", json=request_data)
        assert response.status_code == 200
        
        # Verify service was called
        mock_service.browse_products.assert_called_once()
    
    @patch('mcp_http_server.ecommerce_service')
    def test_browse_products_invalid_max_results(self, mock_service, client):
        """Test validation of max_results parameter."""
        # Test with negative max_results
        request_data = {
            "category": "fruits",
            "max_results": -5  # Invalid
        }
        
        response = client.post("/tools/browse-products", json=request_data)
        
        # Should handle gracefully (implementation dependent)
        # Either reject with 422 or clamp to valid range
        assert response.status_code in [200, 422]
    
    def test_empty_post_body(self, client):
        """Test handling of empty POST body."""
        response = client.post("/tools/browse-products")
        
        # Should return validation error for missing content type or body
        assert response.status_code == 422
