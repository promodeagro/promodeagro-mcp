"""Tests for deliver order models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.models.deliver_order_model import (
    DeliverOrderRequest, DeliverOrderResponse, DeliveryResult,
    BulkDeliverOrderRequest, BulkDeliverOrderResponse,
    DeliveryStatusRequest, DeliveryStatusResponse,
    DeliveryStatus, DeliveryProof, PaymentCollection,
    SuccessfulDeliveryValidation, FailedDeliveryValidation
)


class TestDeliveryProof:
    """Test DeliveryProof model"""
    
    def test_delivery_proof_creation(self):
        """Test creating delivery proof"""
        proof = DeliveryProof(
            signature_obtained=True,
            photo_taken=False,
            timestamp="2023-01-01T12:00:00Z"
        )
        assert proof.signature_obtained is True
        assert proof.photo_taken is False
        assert proof.timestamp == "2023-01-01T12:00:00Z"
    
    def test_delivery_proof_defaults(self):
        """Test delivery proof with defaults"""
        proof = DeliveryProof()
        assert proof.signature_obtained is False
        assert proof.photo_taken is False
        assert proof.timestamp is None


class TestDeliverOrderRequest:
    """Test DeliverOrderRequest model"""
    
    def test_successful_delivery_request(self):
        """Test valid successful delivery request"""
        request = DeliverOrderRequest(
            order_id="test-order-123",
            delivery_status=DeliveryStatus.SUCCESSFUL,
            customer_verified=True,
            payment_collected=True
        )
        assert request.order_id == "test-order-123"
        assert request.delivery_status == DeliveryStatus.SUCCESSFUL
        assert request.customer_verified is True
        assert request.payment_collected is True
    
    def test_failed_delivery_request(self):
        """Test valid failed delivery request"""
        request = DeliverOrderRequest(
            order_id="test-order-456",
            delivery_status=DeliveryStatus.FAILED,
            customer_verified=False,
            failure_reason="Customer not available"
        )
        assert request.order_id == "test-order-456"
        assert request.delivery_status == DeliveryStatus.FAILED
        assert request.failure_reason == "Customer not available"
    
    def test_failed_delivery_without_reason(self):
        """Test failed delivery without failure reason should raise error"""
        with pytest.raises(ValidationError) as exc_info:
            DeliverOrderRequest(
                order_id="test-order-789",
                delivery_status=DeliveryStatus.FAILED,
                customer_verified=False
            )
        assert "failure_reason is required for failed deliveries" in str(exc_info.value)
    
    def test_delivery_with_proof(self):
        """Test delivery request with proof"""
        proof = DeliveryProof(signature_obtained=True, photo_taken=True)
        request = DeliverOrderRequest(
            order_id="test-order-proof",
            delivery_status=DeliveryStatus.SUCCESSFUL,
            customer_verified=True,
            delivery_proof=proof,
            customer_feedback="Great service!"
        )
        assert request.delivery_proof.signature_obtained is True
        assert request.delivery_proof.photo_taken is True
        assert request.customer_feedback == "Great service!"


class TestDeliverOrderResponse:
    """Test DeliverOrderResponse model"""
    
    def test_successful_response(self):
        """Test successful delivery response"""
        delivery_result = DeliveryResult(
            order_id="test-order-123",
            status="delivered",
            message="Order delivered successfully",
            timestamp="2023-01-01T12:00:00Z"
        )
        
        response = DeliverOrderResponse(
            success=True,
            message="Delivery completed",
            delivery_result=delivery_result
        )
        
        assert response.success is True
        assert response.message == "Delivery completed"
        assert response.delivery_result.order_id == "test-order-123"
        assert response.delivery_result.status == "delivered"
    
    def test_failed_response(self):
        """Test failed delivery response"""
        response = DeliverOrderResponse(
            success=False,
            message="Delivery failed",
            error_details="Order not found"
        )
        
        assert response.success is False
        assert response.message == "Delivery failed"
        assert response.error_details == "Order not found"
        assert response.delivery_result is None


class TestBulkDeliverOrderRequest:
    """Test BulkDeliverOrderRequest model"""
    
    def test_bulk_delivery_request(self):
        """Test valid bulk delivery request"""
        deliveries = [
            DeliverOrderRequest(
                order_id="order-1",
                delivery_status=DeliveryStatus.SUCCESSFUL,
                customer_verified=True
            ),
            DeliverOrderRequest(
                order_id="order-2",
                delivery_status=DeliveryStatus.FAILED,
                customer_verified=False,
                failure_reason="Customer not home"
            )
        ]
        
        request = BulkDeliverOrderRequest(
            deliveries=deliveries,
            delivered_by="emp-123"
        )
        
        assert len(request.deliveries) == 2
        assert request.delivered_by == "emp-123"
    
    def test_empty_bulk_delivery_request(self):
        """Test bulk delivery request with empty deliveries"""
        with pytest.raises(ValidationError) as exc_info:
            BulkDeliverOrderRequest(deliveries=[])
        assert "At least one delivery must be specified" in str(exc_info.value)


class TestDeliveryStatusRequest:
    """Test DeliveryStatusRequest model"""
    
    def test_delivery_status_request(self):
        """Test valid delivery status request"""
        request = DeliveryStatusRequest(order_id="test-order-123")
        assert request.order_id == "test-order-123"


class TestDeliveryStatusResponse:
    """Test DeliveryStatusResponse model"""
    
    def test_delivery_status_response(self):
        """Test delivery status response"""
        response = DeliveryStatusResponse(
            order_id="test-order-123",
            current_status="delivered",
            order_info={"customer_name": "John Doe", "total_amount": 100.0}
        )
        
        assert response.order_id == "test-order-123"
        assert response.current_status == "delivered"
        assert response.order_info["customer_name"] == "John Doe"
        assert response.delivery_details is None


class TestValidationSchemas:
    """Test validation schemas"""
    
    def test_successful_delivery_validation(self):
        """Test successful delivery validation"""
        # Valid case
        validation = SuccessfulDeliveryValidation(customer_verified=True)
        assert validation.customer_verified is True
        
        # Invalid case
        with pytest.raises(ValidationError) as exc_info:
            SuccessfulDeliveryValidation(customer_verified=False)
        assert "Customer verification is required" in str(exc_info.value)
    
    def test_failed_delivery_validation(self):
        """Test failed delivery validation"""
        # Valid case
        validation = FailedDeliveryValidation(failure_reason="Customer not available")
        assert validation.failure_reason == "Customer not available"
        
        # Invalid case - no reason
        with pytest.raises(ValidationError) as exc_info:
            FailedDeliveryValidation(failure_reason="")
        assert "Detailed failure reason is required" in str(exc_info.value)
        
        # Invalid case - reason too short
        with pytest.raises(ValidationError) as exc_info:
            FailedDeliveryValidation(failure_reason="No")
        assert "minimum 5 characters" in str(exc_info.value)
