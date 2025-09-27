"""Tests for deliver order tools."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.tools.deliver_order_tool import deliver_order_tools
from src.models.deliver_order_model import (
    DeliverOrderResponse, DeliveryResult, DeliveryStatusResponse
)


@pytest.fixture
def mock_mcp():
    """Create a mock FastMCP instance"""
    mcp = Mock()
    mcp.tool = Mock()
    return mcp


@pytest.fixture
def mock_delivery_service():
    """Create a mock delivery service"""
    with patch('src.tools.deliver_order_tool.DeliverOrderService') as mock_service_class:
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        return mock_service


class TestDeliverOrderTools:
    """Test deliver order tools registration and functionality"""
    
    def test_tools_registration(self, mock_mcp):
        """Test that tools are registered correctly"""
        deliver_order_tools(mock_mcp)
        
        # Verify that tool decorator was called multiple times
        assert mock_mcp.tool.call_count >= 2  # At least deliver_order and get_delivery_status
    
    @pytest.mark.asyncio
    async def test_deliver_order_tool_successful(self, mock_delivery_service):
        """Test successful order delivery through tool"""
        # Mock successful service response
        mock_result = DeliverOrderResponse(
            success=True,
            message="Order delivered successfully",
            delivery_result=DeliveryResult(
                order_id="test-order-123",
                status="delivered",
                message="Order delivered successfully",
                timestamp="2023-01-01T12:00:00Z",
                payment_collected=100.0,
                customer_feedback="Great service!"
            )
        )
        
        mock_delivery_service.deliver_order = AsyncMock(return_value=mock_result)
        
        # Import the actual tool function for testing
        from src.tools.deliver_order_tool import deliver_order_tools
        
        # Create a mock MCP and register tools
        mcp = Mock()
        registered_tools = []
        
        def mock_tool_decorator(description):
            def decorator(func):
                registered_tools.append((func.__name__, func))
                return func
            return decorator
        
        mcp.tool = mock_tool_decorator
        deliver_order_tools(mcp)
        
        # Find the deliver_order function
        deliver_order_func = None
        for name, func in registered_tools:
            if name == "deliver_order":
                deliver_order_func = func
                break
        
        assert deliver_order_func is not None
        
        # Test the function
        with patch('src.tools.deliver_order_tool.DeliverOrderService', return_value=mock_delivery_service):
            result = await deliver_order_func(
                order_id="test-order-123",
                delivery_status="successful",
                customer_verified=True,
                payment_collected=True,
                signature_obtained=True,
                photo_taken=True,
                customer_feedback="Great service!",
                delivered_by="emp-123"
            )
        
        # Verify result
        assert result["success"] is True
        assert "delivered successfully" in result["message"]
        assert result["delivery_result"]["order_id"] == "test-order-123"
        assert result["delivery_result"]["payment_collected"] == 100.0
    
    @pytest.mark.asyncio
    async def test_deliver_order_tool_failed(self, mock_delivery_service):
        """Test failed order delivery through tool"""
        # Mock failed service response
        mock_result = DeliverOrderResponse(
            success=True,
            message="Failed delivery recorded",
            delivery_result=DeliveryResult(
                order_id="test-order-456",
                status="failed",
                message="Delivery failed: Customer not available",
                timestamp="2023-01-01T12:00:00Z"
            )
        )
        
        mock_delivery_service.deliver_order = AsyncMock(return_value=mock_result)
        
        # Import and test the tool
        from src.tools.deliver_order_tool import deliver_order_tools
        
        mcp = Mock()
        registered_tools = []
        
        def mock_tool_decorator(description):
            def decorator(func):
                registered_tools.append((func.__name__, func))
                return func
            return decorator
        
        mcp.tool = mock_tool_decorator
        deliver_order_tools(mcp)
        
        # Find the deliver_order function
        deliver_order_func = None
        for name, func in registered_tools:
            if name == "deliver_order":
                deliver_order_func = func
                break
        
        # Test failed delivery
        with patch('src.tools.deliver_order_tool.DeliverOrderService', return_value=mock_delivery_service):
            result = await deliver_order_func(
                order_id="test-order-456",
                delivery_status="failed",
                customer_verified=False,
                failure_reason="Customer not available at address"
            )
        
        # Verify result
        assert result["success"] is True
        assert "Failed delivery recorded" in result["message"]
        assert result["delivery_result"]["status"] == "failed"
    
    @pytest.mark.asyncio
    async def test_invalid_delivery_status(self, mock_delivery_service):
        """Test tool with invalid delivery status"""
        from src.tools.deliver_order_tool import deliver_order_tools
        
        mcp = Mock()
        registered_tools = []
        
        def mock_tool_decorator(description):
            def decorator(func):
                registered_tools.append((func.__name__, func))
                return func
            return decorator
        
        mcp.tool = mock_tool_decorator
        deliver_order_tools(mcp)
        
        # Find the deliver_order function
        deliver_order_func = None
        for name, func in registered_tools:
            if name == "deliver_order":
                deliver_order_func = func
                break
        
        # Test with invalid status
        result = await deliver_order_func(
            order_id="test-order",
            delivery_status="invalid_status",
            customer_verified=True
        )
        
        # Should return error
        assert result["success"] is False
        assert "Invalid delivery status" in result["message"]
    
    @pytest.mark.asyncio
    async def test_get_delivery_status_tool(self, mock_delivery_service):
        """Test get delivery status tool"""
        # Mock service response
        mock_result = DeliveryStatusResponse(
            order_id="test-order-123",
            current_status="delivered",
            delivery_details={
                "delivery_time": "2023-01-01T12:00:00Z",
                "delivered_by": "emp-123"
            },
            order_info={
                "order_number": "ORD-001",
                "customer_info": {"name": "John Doe"},
                "total_amount": 100.0
            }
        )
        
        mock_delivery_service.get_delivery_status = AsyncMock(return_value=mock_result)
        
        # Import and test the tool
        from src.tools.deliver_order_tool import deliver_order_tools
        
        mcp = Mock()
        registered_tools = []
        
        def mock_tool_decorator(description):
            def decorator(func):
                registered_tools.append((func.__name__, func))
                return func
            return decorator
        
        mcp.tool = mock_tool_decorator
        deliver_order_tools(mcp)
        
        # Find the get_delivery_status function
        get_status_func = None
        for name, func in registered_tools:
            if name == "get_delivery_status":
                get_status_func = func
                break
        
        assert get_status_func is not None
        
        # Test the function
        with patch('src.tools.deliver_order_tool.DeliverOrderService', return_value=mock_delivery_service):
            result = await get_status_func(order_id="test-order-123")
        
        # Verify result
        assert result["success"] is True
        assert result["order_id"] == "test-order-123"
        assert result["current_status"] == "delivered"
        assert result["order_info"]["customer_info"]["name"] == "John Doe"
    
    @pytest.mark.asyncio
    async def test_service_error_handling(self, mock_delivery_service):
        """Test tool error handling when service fails"""
        # Mock service to raise exception
        mock_delivery_service.deliver_order = AsyncMock(side_effect=Exception("Service error"))
        
        from src.tools.deliver_order_tool import deliver_order_tools
        
        mcp = Mock()
        registered_tools = []
        
        def mock_tool_decorator(description):
            def decorator(func):
                registered_tools.append((func.__name__, func))
                return func
            return decorator
        
        mcp.tool = mock_tool_decorator
        deliver_order_tools(mcp)
        
        # Find the deliver_order function
        deliver_order_func = None
        for name, func in registered_tools:
            if name == "deliver_order":
                deliver_order_func = func
                break
        
        # Test with service error
        with patch('src.tools.deliver_order_tool.DeliverOrderService', return_value=mock_delivery_service):
            result = await deliver_order_func(
                order_id="test-order",
                delivery_status="successful",
                customer_verified=True
            )
        
        # Should handle error gracefully
        assert result["success"] is False
        assert "Delivery processing failed" in result["message"]
        assert "Service error" in result["error_details"]
