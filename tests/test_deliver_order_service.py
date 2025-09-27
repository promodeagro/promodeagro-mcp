"""Tests for deliver order service."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from decimal import Decimal

from src.services.deliver_order_service import DeliverOrderService
from src.models.deliver_order_model import (
    DeliverOrderRequest, DeliveryStatusRequest,
    DeliveryStatus, DeliveryProof
)


@pytest.fixture
def mock_delivery_service():
    """Create a delivery service with mocked DynamoDB"""
    with patch('boto3.resource') as mock_boto3:
        mock_dynamodb = Mock()
        mock_boto3.return_value = mock_dynamodb
        
        # Mock tables
        mock_orders_table = Mock()
        mock_delivery_table = Mock()
        mock_logistics_table = Mock()
        mock_analytics_table = Mock()
        mock_staff_table = Mock()
        
        mock_dynamodb.Table.side_effect = lambda name: {
            'AuroraSparkTheme-Orders': mock_orders_table,
            'AuroraSparkTheme-Delivery': mock_delivery_table,
            'AuroraSparkTheme-Logistics': mock_logistics_table,
            'AuroraSparkTheme-Analytics': mock_analytics_table,
            'AuroraSparkTheme-Staff': mock_staff_table
        }[name]
        
        service = DeliverOrderService()
        service.orders_table = mock_orders_table
        service.delivery_table = mock_delivery_table
        service.logistics_table = mock_logistics_table
        service.analytics_table = mock_analytics_table
        service.staff_table = mock_staff_table
        
        return service, {
            'orders_table': mock_orders_table,
            'delivery_table': mock_delivery_table,
            'logistics_table': mock_logistics_table,
            'analytics_table': mock_analytics_table,
            'staff_table': mock_staff_table
        }


class TestDeliverOrderService:
    """Test DeliverOrderService class"""
    
    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test service initializes with correct region"""
        with patch('boto3.resource') as mock_boto3:
            service = DeliverOrderService(region_name='us-east-1')
            mock_boto3.assert_called_once_with('dynamodb', region_name='us-east-1')
    
    @pytest.mark.asyncio
    async def test_successful_delivery(self, mock_delivery_service):
        """Test successful order delivery"""
        service, mocks = mock_delivery_service
        
        # Mock order data
        mock_order = {
            'orderID': 'test-order-123',
            'customerEmail': 'test@example.com',
            'status': 'out_for_delivery',
            'paymentMethod': 'online',
            'orderSummary': {'totalAmount': Decimal('100.00')}
        }
        
        # Mock scan response for order lookup
        mocks['orders_table'].scan.return_value = {
            'Items': [mock_order]
        }
        
        # Create delivery request
        request = DeliverOrderRequest(
            order_id='test-order-123',
            delivery_status=DeliveryStatus.SUCCESSFUL,
            customer_verified=True,
            payment_collected=True,
            delivery_proof=DeliveryProof(signature_obtained=True, photo_taken=True),
            customer_feedback="Great service!"
        )
        
        # Test delivery
        result = await service.deliver_order(request, "emp-123")
        
        # Verify result
        assert result.success is True
        assert "delivered successfully" in result.message
        assert result.delivery_result.status == "delivered"
        assert result.delivery_result.customer_feedback == "Great service!"
        
        # Verify database update was called
        mocks['orders_table'].update_item.assert_called_once()
        mocks['analytics_table'].put_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_failed_delivery(self, mock_delivery_service):
        """Test failed order delivery"""
        service, mocks = mock_delivery_service
        
        # Mock order data
        mock_order = {
            'orderID': 'test-order-456',
            'customerEmail': 'test@example.com',
            'status': 'out_for_delivery',
            'paymentMethod': 'cod',
            'orderSummary': {'totalAmount': Decimal('150.00')}
        }
        
        mocks['orders_table'].scan.return_value = {
            'Items': [mock_order]
        }
        
        # Create failed delivery request
        request = DeliverOrderRequest(
            order_id='test-order-456',
            delivery_status=DeliveryStatus.FAILED,
            customer_verified=False,
            failure_reason="Customer not available at address"
        )
        
        # Test delivery
        result = await service.deliver_order(request, "emp-456")
        
        # Verify result
        assert result.success is True
        assert "Failed delivery recorded" in result.message
        assert result.delivery_result.status == "failed"
        
        # Verify database update
        mocks['orders_table'].update_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cod_delivery_without_payment(self, mock_delivery_service):
        """Test COD delivery without payment collection should fail validation"""
        service, mocks = mock_delivery_service
        
        # Mock COD order
        mock_order = {
            'orderID': 'test-order-cod',
            'customerEmail': 'test@example.com',
            'status': 'out_for_delivery',
            'paymentMethod': 'cod',
            'orderSummary': {'totalAmount': Decimal('200.00')}
        }
        
        mocks['orders_table'].scan.return_value = {
            'Items': [mock_order]
        }
        
        # Create request without payment collection
        request = DeliverOrderRequest(
            order_id='test-order-cod',
            delivery_status=DeliveryStatus.SUCCESSFUL,
            customer_verified=True,
            payment_collected=False  # This should fail validation
        )
        
        # Test delivery
        result = await service.deliver_order(request)
        
        # Should fail validation
        assert result.success is False
        assert "Payment collection is required for COD orders" in result.message
    
    @pytest.mark.asyncio
    async def test_order_not_found(self, mock_delivery_service):
        """Test delivery for non-existent order"""
        service, mocks = mock_delivery_service
        
        # Mock empty scan response
        mocks['orders_table'].scan.return_value = {'Items': []}
        
        request = DeliverOrderRequest(
            order_id='non-existent-order',
            delivery_status=DeliveryStatus.SUCCESSFUL,
            customer_verified=True
        )
        
        result = await service.deliver_order(request)
        
        assert result.success is False
        assert "not found or not eligible" in result.message
    
    @pytest.mark.asyncio
    async def test_get_delivery_status(self, mock_delivery_service):
        """Test getting delivery status"""
        service, mocks = mock_delivery_service
        
        # Mock delivered order
        mock_order = {
            'orderID': 'delivered-order',
            'customerEmail': 'test@example.com',
            'status': 'delivered',
            'deliveryTime': '2023-01-01T12:00:00Z',
            'deliveredBy': 'emp-123',
            'orderNumber': 'ORD-001',
            'customerInfo': {'name': 'John Doe'},
            'orderSummary': {'totalAmount': Decimal('100.00')},
            'paymentMethod': 'online',
            'deliveryAddress': {'street': '123 Main St'}
        }
        
        mocks['orders_table'].scan.return_value = {
            'Items': [mock_order]
        }
        
        request = DeliveryStatusRequest(order_id='delivered-order')
        result = await service.get_delivery_status(request)
        
        assert result.order_id == 'delivered-order'
        assert result.current_status == 'delivered'
        assert result.delivery_details['delivery_time'] == '2023-01-01T12:00:00Z'
        assert result.order_info['customer_info']['name'] == 'John Doe'
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, mock_delivery_service):
        """Test handling of database errors"""
        service, mocks = mock_delivery_service
        
        # Mock database error
        mocks['orders_table'].scan.side_effect = Exception("Database connection error")
        
        request = DeliverOrderRequest(
            order_id='test-order',
            delivery_status=DeliveryStatus.SUCCESSFUL,
            customer_verified=True
        )
        
        result = await service.deliver_order(request)
        
        assert result.success is False
        assert "Failed to process delivery" in result.message
        assert "Database connection error" in result.error_details
