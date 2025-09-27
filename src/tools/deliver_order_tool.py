"""Deliver Order tools for the MCP Server."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger
from mcp.server.fastmcp import FastMCP

from ..models.deliver_order_model import (
    DeliverOrderRequest, DeliverOrderResponse, DeliveryResult,
    BulkDeliverOrderRequest, BulkDeliverOrderResponse,
    DeliveryStatusRequest, DeliveryStatusResponse,
    DeliveryStatus, DeliveryProof
)
from ..services.deliver_order_service import DeliverOrderService


def deliver_order_tools(mcp: FastMCP) -> None:
    """Register the deliver order tools."""
    
    @mcp.tool(description="Deliver a single order with status update, payment collection, and delivery confirmation")
    async def deliver_order(
        order_id: str,
        delivery_status: str,
        customer_verified: bool,
        payment_collected: Optional[bool] = None,
        signature_obtained: Optional[bool] = False,
        photo_taken: Optional[bool] = False,
        failure_reason: Optional[str] = None,
        customer_feedback: Optional[str] = None,
        delivery_notes: Optional[str] = None,
        delivered_by: Optional[str] = None
    ) -> Dict:
        """
        Deliver a single order and update its status.
        
        Args:
            order_id: Unique order identifier
            delivery_status: Delivery outcome ('successful', 'failed', or 'returned')
            customer_verified: Whether customer identity was verified
            payment_collected: Whether payment was collected (required for COD orders)
            signature_obtained: Whether customer signature was obtained
            photo_taken: Whether delivery photo was taken
            failure_reason: Reason for failed/returned delivery (required for failed/returned)
            customer_feedback: Optional customer feedback
            delivery_notes: Additional delivery notes
            delivered_by: Employee ID of the delivery person
            
        Returns:
            Dictionary containing:
            - success: Whether the delivery was processed successfully
            - message: Result message
            - delivery_result: Detailed delivery information
            - order_details: Updated order status
        """
        try:
            logger.info(f"Processing delivery for order {order_id} with status {delivery_status}")
            
            # Validate delivery status
            if delivery_status not in ['successful', 'failed', 'returned']:
                return {
                    "success": False,
                    "message": "Invalid delivery status. Must be 'successful', 'failed', or 'returned'",
                    "error_details": "Invalid delivery status parameter"
                }
            
            # Create delivery proof if signature or photo provided
            delivery_proof = None
            if signature_obtained or photo_taken:
                delivery_proof = DeliveryProof(
                    signature_obtained=signature_obtained,
                    photo_taken=photo_taken,
                    timestamp=datetime.utcnow().isoformat()
                )
            
            # Create delivery request
            request = DeliverOrderRequest(
                order_id=order_id,
                delivery_status=DeliveryStatus(delivery_status),
                customer_verified=customer_verified,
                payment_collected=payment_collected,
                delivery_proof=delivery_proof,
                failure_reason=failure_reason,
                customer_feedback=customer_feedback,
                delivery_notes=delivery_notes
            )
            
            # Initialize service and process delivery
            service = DeliverOrderService()
            result = await service.deliver_order(request, delivered_by)
            
            # Convert result to dictionary format
            response = _convert_delivery_result_to_dict(result)
            logger.info(f"Delivery processing completed for order {order_id}: {result.success}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error in deliver_order tool: {str(e)}")
            return {
                "success": False,
                "message": f"Delivery processing failed: {str(e)}",
                "error_details": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @mcp.tool(description="Process multiple order deliveries in bulk")
    async def bulk_deliver_orders(
        deliveries: List[Dict],
        delivered_by: Optional[str] = None
    ) -> Dict:
        """
        Process multiple order deliveries in a single operation.
        
        Args:
            deliveries: List of delivery requests, each containing:
                - order_id: Order identifier
                - delivery_status: 'successful', 'failed', or 'returned'
                - customer_verified: Whether customer was verified
                - payment_collected: Whether payment was collected (optional)
                - signature_obtained: Whether signature was obtained (optional)
                - photo_taken: Whether photo was taken (optional)
                - failure_reason: Reason for failure/return (optional)
                - customer_feedback: Customer feedback (optional)
                - delivery_notes: Additional notes (optional)
            delivered_by: Employee ID of the delivery person
            
        Returns:
            Dictionary containing:
            - success: Whether all deliveries were processed successfully
            - message: Overall result message
            - total_deliveries: Total number of delivery attempts
            - successful_deliveries: Number of successful deliveries
            - failed_deliveries: Number of failed delivery attempts
            - delivery_results: List of individual delivery results
        """
        try:
            logger.info(f"Processing bulk delivery for {len(deliveries)} orders")
            
            # Convert delivery dictionaries to request objects
            delivery_requests = []
            for delivery in deliveries:
                try:
                    # Create delivery proof if needed
                    delivery_proof = None
                    if delivery.get('signature_obtained') or delivery.get('photo_taken'):
                        delivery_proof = DeliveryProof(
                            signature_obtained=delivery.get('signature_obtained', False),
                            photo_taken=delivery.get('photo_taken', False),
                            timestamp=datetime.utcnow().isoformat()
                        )
                    
                    request = DeliverOrderRequest(
                        order_id=delivery['order_id'],
                        delivery_status=DeliveryStatus(delivery['delivery_status']),
                        customer_verified=delivery['customer_verified'],
                        payment_collected=delivery.get('payment_collected'),
                        delivery_proof=delivery_proof,
                        failure_reason=delivery.get('failure_reason'),
                        customer_feedback=delivery.get('customer_feedback'),
                        delivery_notes=delivery.get('delivery_notes')
                    )
                    delivery_requests.append(request)
                    
                except Exception as e:
                    logger.error(f"Error parsing delivery request for order {delivery.get('order_id', 'unknown')}: {str(e)}")
                    # Skip invalid requests but continue with others
                    continue
            
            if not delivery_requests:
                return {
                    "success": False,
                    "message": "No valid delivery requests found",
                    "total_deliveries": 0,
                    "successful_deliveries": 0,
                    "failed_deliveries": 0,
                    "delivery_results": []
                }
            
            # Create bulk request
            bulk_request = BulkDeliverOrderRequest(
                deliveries=delivery_requests,
                delivered_by=delivered_by
            )
            
            # Process bulk deliveries
            service = DeliverOrderService()
            result = await service.bulk_deliver_orders(bulk_request)
            
            # Convert result to dictionary format
            response = _convert_bulk_delivery_result_to_dict(result)
            logger.info(f"Bulk delivery processing completed: {result.successful_deliveries}/{result.total_deliveries} successful")
            
            return response
            
        except Exception as e:
            logger.error(f"Error in bulk_deliver_orders tool: {str(e)}")
            return {
                "success": False,
                "message": f"Bulk delivery processing failed: {str(e)}",
                "error_details": str(e),
                "total_deliveries": len(deliveries) if deliveries else 0,
                "successful_deliveries": 0,
                "failed_deliveries": len(deliveries) if deliveries else 0,
                "delivery_results": [],
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @mcp.tool(description="Get current delivery status and details for an order")
    async def get_delivery_status(
        order_id: str
    ) -> Dict:
        """
        Get the current delivery status and details for an order.
        
        Args:
            order_id: Unique order identifier
            
        Returns:
            Dictionary containing:
            - order_id: Order identifier
            - current_status: Current delivery status
            - delivery_details: Delivery details if completed
            - order_info: Basic order information
        """
        try:
            logger.info(f"Getting delivery status for order {order_id}")
            
            # Create status request
            request = DeliveryStatusRequest(order_id=order_id)
            
            # Get delivery status
            service = DeliverOrderService()
            result = await service.get_delivery_status(request)
            
            # Convert result to dictionary format
            response = _convert_delivery_status_to_dict(result)
            logger.info(f"Retrieved delivery status for order {order_id}: {result.current_status}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error in get_delivery_status tool: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to get delivery status: {str(e)}",
                "error_details": str(e),
                "order_id": order_id,
                "timestamp": datetime.utcnow().isoformat()
            }


def _convert_delivery_result_to_dict(result: DeliverOrderResponse) -> Dict:
    """Convert DeliverOrderResponse to dictionary format"""
    response = {
        "success": result.success,
        "message": result.message,
        "timestamp": result.timestamp
    }
    
    if result.delivery_result:
        response["delivery_result"] = {
            "order_id": result.delivery_result.order_id,
            "status": result.delivery_result.status,
            "message": result.delivery_result.message,
            "timestamp": result.delivery_result.timestamp,
            "payment_collected": result.delivery_result.payment_collected,
            "delivery_proof": result.delivery_result.delivery_proof,
            "customer_feedback": result.delivery_result.customer_feedback
        }
    
    if result.order_details:
        response["order_details"] = result.order_details
    
    if result.error_details:
        response["error_details"] = result.error_details
    
    return response


def _convert_bulk_delivery_result_to_dict(result: BulkDeliverOrderResponse) -> Dict:
    """Convert BulkDeliverOrderResponse to dictionary format"""
    response = {
        "success": result.success,
        "message": result.message,
        "total_deliveries": result.total_deliveries,
        "successful_deliveries": result.successful_deliveries,
        "failed_deliveries": result.failed_deliveries,
        "timestamp": result.timestamp
    }
    
    response["delivery_results"] = []
    for delivery_result in result.delivery_results:
        response["delivery_results"].append({
            "order_id": delivery_result.order_id,
            "status": delivery_result.status,
            "message": delivery_result.message,
            "timestamp": delivery_result.timestamp,
            "payment_collected": delivery_result.payment_collected,
            "delivery_proof": delivery_result.delivery_proof,
            "customer_feedback": delivery_result.customer_feedback
        })
    
    if result.error_details:
        response["error_details"] = result.error_details
    
    return response


def _convert_delivery_status_to_dict(result: DeliveryStatusResponse) -> Dict:
    """Convert DeliveryStatusResponse to dictionary format"""
    return {
        "success": True,
        "order_id": result.order_id,
        "current_status": result.current_status,
        "delivery_details": result.delivery_details,
        "order_info": result.order_info,
        "timestamp": result.timestamp
    }
