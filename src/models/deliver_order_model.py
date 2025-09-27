"""
Deliver Order Models - Data structures for delivery operations.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class DeliveryStatus(str, Enum):
    """Delivery status options"""
    SUCCESSFUL = "successful"
    FAILED = "failed"
    RETURNED = "returned"


class DeliveryProof(BaseModel):
    """Delivery proof information"""
    signature_obtained: bool = Field(default=False, description="Whether customer signature was obtained")
    photo_taken: bool = Field(default=False, description="Whether delivery photo was taken")
    timestamp: Optional[str] = Field(default=None, description="Timestamp when proof was collected")


class PaymentCollection(BaseModel):
    """Payment collection details for COD orders"""
    amount: float = Field(..., gt=0, description="Amount collected")
    method: str = Field(default="cod", description="Payment method")
    collected_by: Optional[str] = Field(default=None, description="Employee ID who collected payment")
    collection_time: Optional[str] = Field(default=None, description="Payment collection timestamp")


class DeliverOrderRequest(BaseModel):
    """Request model for deliver order operation"""
    order_id: str = Field(..., description="Unique order identifier")
    delivery_status: DeliveryStatus = Field(..., description="Delivery outcome status")
    customer_verified: bool = Field(..., description="Whether customer identity was verified")
    payment_collected: Optional[bool] = Field(default=None, description="Whether payment was collected (required for COD)")
    delivery_proof: Optional[DeliveryProof] = Field(default=None, description="Delivery proof details")
    failure_reason: Optional[str] = Field(default=None, description="Reason for failed delivery")
    customer_feedback: Optional[str] = Field(default=None, description="Optional customer feedback")
    delivery_notes: Optional[str] = Field(default=None, description="Additional delivery notes")
    
    # Note: Cross-field validation is handled in the service layer for better error handling


class DeliveryResult(BaseModel):
    """Individual delivery operation result"""
    order_id: str = Field(..., description="Order identifier")
    status: str = Field(..., description="Delivery status")
    message: str = Field(..., description="Result message")
    timestamp: str = Field(..., description="Delivery completion timestamp")
    payment_collected: Optional[float] = Field(default=None, description="Amount collected if applicable")
    delivery_proof: Optional[Dict[str, Any]] = Field(default=None, description="Delivery proof details")
    customer_feedback: Optional[str] = Field(default=None, description="Customer feedback if provided")


class DeliverOrderResponse(BaseModel):
    """Response model for deliver order operation"""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Operation result message")
    delivery_result: Optional[DeliveryResult] = Field(default=None, description="Delivery operation details")
    order_details: Optional[Dict[str, Any]] = Field(default=None, description="Updated order information")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Response timestamp")
    error_details: Optional[str] = Field(default=None, description="Error details if operation failed")


class BulkDeliverOrderRequest(BaseModel):
    """Request model for bulk delivery operations"""
    deliveries: List[DeliverOrderRequest] = Field(..., description="List of delivery operations")
    delivered_by: Optional[str] = Field(default=None, description="Employee ID performing deliveries")
    
    @field_validator('deliveries')
    @classmethod
    def validate_deliveries_not_empty(cls, v):
        if not v:
            raise ValueError("At least one delivery must be specified")
        return v


class BulkDeliverOrderResponse(BaseModel):
    """Response model for bulk delivery operations"""
    success: bool = Field(..., description="Whether all operations were successful")
    message: str = Field(..., description="Overall operation result message")
    total_deliveries: int = Field(..., description="Total number of delivery attempts")
    successful_deliveries: int = Field(..., description="Number of successful deliveries")
    failed_deliveries: int = Field(..., description="Number of failed delivery attempts")
    delivery_results: List[DeliveryResult] = Field(..., description="Individual delivery results")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Response timestamp")
    error_details: Optional[str] = Field(default=None, description="Error details if any operations failed")


class DeliveryStatusRequest(BaseModel):
    """Request model for checking delivery status"""
    order_id: str = Field(..., description="Order identifier to check")


class DeliveryStatusResponse(BaseModel):
    """Response model for delivery status check"""
    order_id: str = Field(..., description="Order identifier")
    current_status: str = Field(..., description="Current delivery status")
    delivery_details: Optional[Dict[str, Any]] = Field(default=None, description="Delivery details if completed")
    order_info: Dict[str, Any] = Field(..., description="Order information")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Response timestamp")


# Validation schemas for different delivery scenarios
class SuccessfulDeliveryValidation(BaseModel):
    """Validation schema for successful deliveries"""
    customer_verified: bool = Field(..., description="Customer must be verified")
    delivery_proof: Optional[DeliveryProof] = Field(default=None, description="Delivery proof recommended")
    
    @field_validator('customer_verified')
    @classmethod
    def customer_must_be_verified(cls, v):
        if not v:
            raise ValueError("Customer verification is required for successful deliveries")
        return v


class FailedDeliveryValidation(BaseModel):
    """Validation schema for failed deliveries"""
    failure_reason: str = Field(..., description="Failure reason is required")
    customer_verified: bool = Field(default=False, description="Customer verification attempted")
    
    @field_validator('failure_reason')
    @classmethod
    def failure_reason_required(cls, v):
        if not v or len(v.strip()) < 5:
            raise ValueError("Detailed failure reason is required (minimum 5 characters)")
        return v


class ReturnedDeliveryValidation(BaseModel):
    """Validation schema for returned deliveries"""
    failure_reason: str = Field(..., description="Return reason is required")
    customer_verified: bool = Field(default=False, description="Customer verification attempted")
    delivery_notes: Optional[str] = Field(default=None, description="Notes about return process")
