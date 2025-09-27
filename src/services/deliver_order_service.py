"""
Deliver Order Service - Business logic for delivery operations.
"""

import boto3
import uuid
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
from loguru import logger

from ..models.deliver_order_model import (
    DeliverOrderRequest, DeliverOrderResponse, DeliveryResult,
    BulkDeliverOrderRequest, BulkDeliverOrderResponse,
    DeliveryStatusRequest, DeliveryStatusResponse,
    DeliveryStatus, DeliveryProof, PaymentCollection
)


class DeliverOrderService:
    """Service for handling delivery operations"""
    
    def __init__(self, region_name: str = None):
        """Initialize the delivery service"""
        self.region_name = region_name or os.getenv('AWS_REGION', 'ap-south-1')
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region_name)
        
        # Initialize table references
        self.orders_table = self.dynamodb.Table('AuroraSparkTheme-Orders')
        self.delivery_table = self.dynamodb.Table('AuroraSparkTheme-Delivery')
        self.logistics_table = self.dynamodb.Table('AuroraSparkTheme-Logistics')
        self.analytics_table = self.dynamodb.Table('AuroraSparkTheme-Analytics')
        self.staff_table = self.dynamodb.Table('AuroraSparkTheme-Staff')
    
    async def deliver_order(self, request: DeliverOrderRequest, delivered_by: str = None) -> DeliverOrderResponse:
        """Process a single order delivery"""
        try:
            logger.info(f"Processing delivery for order {request.order_id} with status {request.delivery_status}")
            
            # Validate and get order
            order = await self._get_and_validate_order(request.order_id)
            if not order:
                return DeliverOrderResponse(
                    success=False,
                    message=f"Order {request.order_id} not found or not eligible for delivery",
                    error_details="Order not found in system"
                )
            
            # Validate delivery request
            validation_result = self._validate_delivery_request(request, order)
            if not validation_result[0]:
                return DeliverOrderResponse(
                    success=False,
                    message=validation_result[1],
                    error_details="Delivery request validation failed"
                )
            
            # Process delivery based on status
            if request.delivery_status == DeliveryStatus.SUCCESSFUL:
                result = await self._process_successful_delivery(request, order, delivered_by)
            elif request.delivery_status == DeliveryStatus.FAILED:
                result = await self._process_failed_delivery(request, order, delivered_by)
            elif request.delivery_status == DeliveryStatus.RETURNED:
                result = await self._process_returned_delivery(request, order, delivered_by)
            else:
                return DeliverOrderResponse(
                    success=False,
                    message=f"Invalid delivery status: {request.delivery_status}",
                    error_details="Unsupported delivery status"
                )
            
            # Update analytics
            await self._update_delivery_analytics(request, order, delivered_by)
            
            logger.info(f"Successfully processed delivery for order {request.order_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing delivery for order {request.order_id}: {str(e)}")
            return DeliverOrderResponse(
                success=False,
                message=f"Failed to process delivery: {str(e)}",
                error_details=str(e)
            )
    
    async def bulk_deliver_orders(self, request: BulkDeliverOrderRequest) -> BulkDeliverOrderResponse:
        """Process multiple order deliveries"""
        try:
            logger.info(f"Processing bulk delivery for {len(request.deliveries)} orders")
            
            delivery_results = []
            successful_count = 0
            failed_count = 0
            
            for delivery_request in request.deliveries:
                result = await self.deliver_order(delivery_request, request.delivered_by)
                
                delivery_result = DeliveryResult(
                    order_id=delivery_request.order_id,
                    status="success" if result.success else "failed",
                    message=result.message,
                    timestamp=datetime.utcnow().isoformat(),
                    payment_collected=result.delivery_result.payment_collected if result.delivery_result else None,
                    delivery_proof=result.delivery_result.delivery_proof if result.delivery_result else None,
                    customer_feedback=result.delivery_result.customer_feedback if result.delivery_result else None
                )
                
                delivery_results.append(delivery_result)
                
                if result.success:
                    successful_count += 1
                else:
                    failed_count += 1
            
            return BulkDeliverOrderResponse(
                success=failed_count == 0,
                message=f"Processed {len(request.deliveries)} deliveries: {successful_count} successful, {failed_count} failed",
                total_deliveries=len(request.deliveries),
                successful_deliveries=successful_count,
                failed_deliveries=failed_count,
                delivery_results=delivery_results
            )
            
        except Exception as e:
            logger.error(f"Error processing bulk deliveries: {str(e)}")
            return BulkDeliverOrderResponse(
                success=False,
                message=f"Bulk delivery processing failed: {str(e)}",
                total_deliveries=len(request.deliveries),
                successful_deliveries=0,
                failed_deliveries=len(request.deliveries),
                delivery_results=[],
                error_details=str(e)
            )
    
    async def get_delivery_status(self, request: DeliveryStatusRequest) -> DeliveryStatusResponse:
        """Get current delivery status of an order"""
        try:
            order = await self._get_order_by_id(request.order_id)
            if not order:
                raise ValueError(f"Order {request.order_id} not found")
            
            current_status = order.get('status', 'unknown')
            delivery_details = None
            
            # Get delivery details if order has been delivered
            if current_status in ['delivered', 'failed_delivery', 'returned']:
                delivery_details = {
                    'delivery_time': order.get('deliveryTime'),
                    'delivered_by': order.get('deliveredBy'),
                    'delivery_proof': order.get('deliveryProof'),
                    'payment_record': order.get('paymentRecord'),
                    'customer_feedback': order.get('customerFeedback'),
                    'failure_reason': order.get('failureReason')
                }
            
            return DeliveryStatusResponse(
                order_id=request.order_id,
                current_status=current_status,
                delivery_details=delivery_details,
                order_info={
                    'order_number': order.get('orderNumber'),
                    'customer_info': order.get('customerInfo'),
                    'total_amount': float(order.get('orderSummary', {}).get('totalAmount', 0)),
                    'payment_method': order.get('paymentMethod', 'unknown'),
                    'delivery_address': order.get('deliveryAddress')
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting delivery status for order {request.order_id}: {str(e)}")
            raise
    
    async def _get_and_validate_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order and validate it's eligible for delivery"""
        try:
            order = await self._get_order_by_id(order_id)
            if not order:
                return None
            
            # Check if order is in a deliverable state
            current_status = order.get('status', '')
            deliverable_statuses = ['out_for_delivery', 'confirmed', 'packed', 'shipped']
            
            if current_status not in deliverable_statuses:
                logger.warning(f"Order {order_id} has status {current_status}, not eligible for delivery")
                return None
            
            return order
            
        except Exception as e:
            logger.error(f"Error validating order {order_id}: {str(e)}")
            return None
    
    async def _get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order by ID"""
        try:
            # First try to get by orderID directly
            response = self.orders_table.scan(
                FilterExpression='orderID = :order_id',
                ExpressionAttributeValues={':order_id': order_id},
                Limit=1
            )
            
            items = response.get('Items', [])
            return items[0] if items else None
            
        except Exception as e:
            logger.error(f"Error getting order {order_id}: {str(e)}")
            return None
    
    def _validate_delivery_request(self, request: DeliverOrderRequest, order: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate delivery request"""
        try:
            # Check customer verification for successful deliveries
            if request.delivery_status == DeliveryStatus.SUCCESSFUL and not request.customer_verified:
                return False, "Customer verification is required for successful deliveries"
            
            # Check payment collection for COD orders
            payment_method = order.get('paymentMethod', '').lower()
            if (request.delivery_status == DeliveryStatus.SUCCESSFUL and 
                payment_method == 'cod' and 
                request.payment_collected is False):
                return False, "Payment collection is required for COD orders"
            
            # Check failure reason for failed deliveries
            if request.delivery_status == DeliveryStatus.FAILED and not request.failure_reason:
                return False, "Failure reason is required for failed deliveries"
            
            return True, "Validation passed"
            
        except Exception as e:
            logger.error(f"Error validating delivery request: {str(e)}")
            return False, f"Validation error: {str(e)}"
    
    async def _process_successful_delivery(self, request: DeliverOrderRequest, order: Dict[str, Any], delivered_by: str) -> DeliverOrderResponse:
        """Process successful delivery"""
        try:
            delivery_timestamp = datetime.now(timezone.utc).isoformat()
            order_id = request.order_id
            payment_method = order.get('paymentMethod', '').lower()
            total_amount = float(order.get('orderSummary', {}).get('totalAmount', 0))
            
            # Prepare update expression
            update_expression = 'SET #status = :status, #delivery_time = :delivery_time, updatedAt = :updated'
            expression_values = {
                ':status': 'delivered',
                ':delivery_time': delivery_timestamp,
                ':updated': delivery_timestamp
            }
            expression_names = {
                '#status': 'status',
                '#delivery_time': 'deliveryTime'
            }
            
            # Add delivered_by if provided
            if delivered_by:
                update_expression += ', #delivered_by = :delivered_by'
                expression_names['#delivered_by'] = 'deliveredBy'
                expression_values[':delivered_by'] = delivered_by
            
            # Add delivery proof if provided
            if request.delivery_proof:
                delivery_proof = {
                    'signature': request.delivery_proof.signature_obtained,
                    'photo': request.delivery_proof.photo_taken,
                    'timestamp': delivery_timestamp
                }
                update_expression += ', #delivery_proof = :delivery_proof'
                expression_names['#delivery_proof'] = 'deliveryProof'
                expression_values[':delivery_proof'] = delivery_proof
            
            # Add customer feedback if provided
            if request.customer_feedback:
                update_expression += ', #customer_feedback = :feedback'
                expression_names['#customer_feedback'] = 'customerFeedback'
                expression_values[':feedback'] = request.customer_feedback
            
            # Handle COD payment collection
            payment_collected_amount = None
            if payment_method == 'cod' and request.payment_collected:
                payment_record = {
                    'paymentID': str(uuid.uuid4()),
                    'orderID': order_id,
                    'amount': total_amount,
                    'method': 'cod',
                    'status': 'completed',
                    'collectedBy': delivered_by,
                    'collectionTime': delivery_timestamp
                }
                
                update_expression += ', #payment_record = :payment_record, paymentStatus = :payment_status'
                expression_names['#payment_record'] = 'paymentRecord'
                expression_values[':payment_record'] = payment_record
                expression_values[':payment_status'] = 'completed'
                payment_collected_amount = total_amount
            
            # Update the order
            self.orders_table.update_item(
                Key={'orderID': order_id, 'customerEmail': order.get('customerEmail')},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values
            )
            
            # Create delivery result
            delivery_result = DeliveryResult(
                order_id=order_id,
                status="delivered",
                message="Order delivered successfully",
                timestamp=delivery_timestamp,
                payment_collected=payment_collected_amount,
                delivery_proof=request.delivery_proof.dict() if request.delivery_proof else None,
                customer_feedback=request.customer_feedback
            )
            
            return DeliverOrderResponse(
                success=True,
                message=f"Order {order_id} delivered successfully",
                delivery_result=delivery_result,
                order_details={'status': 'delivered', 'delivery_time': delivery_timestamp}
            )
            
        except Exception as e:
            logger.error(f"Error processing successful delivery: {str(e)}")
            raise
    
    async def _process_failed_delivery(self, request: DeliverOrderRequest, order: Dict[str, Any], delivered_by: str) -> DeliverOrderResponse:
        """Process failed delivery"""
        try:
            delivery_timestamp = datetime.now(timezone.utc).isoformat()
            order_id = request.order_id
            
            # Update order with failure information
            update_expression = 'SET #status = :status, failureReason = :reason, updatedAt = :updated, failedDeliveryTime = :failed_time'
            expression_values = {
                ':status': 'failed_delivery',
                ':reason': request.failure_reason,
                ':updated': delivery_timestamp,
                ':failed_time': delivery_timestamp
            }
            expression_names = {'#status': 'status'}
            
            # Add delivered_by if provided
            if delivered_by:
                update_expression += ', attemptedBy = :attempted_by'
                expression_values[':attempted_by'] = delivered_by
            
            # Add delivery notes if provided
            if request.delivery_notes:
                update_expression += ', deliveryNotes = :notes'
                expression_values[':notes'] = request.delivery_notes
            
            self.orders_table.update_item(
                Key={'orderID': order_id, 'customerEmail': order.get('customerEmail')},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values
            )
            
            delivery_result = DeliveryResult(
                order_id=order_id,
                status="failed",
                message=f"Delivery failed: {request.failure_reason}",
                timestamp=delivery_timestamp
            )
            
            return DeliverOrderResponse(
                success=True,
                message=f"Failed delivery recorded for order {order_id}",
                delivery_result=delivery_result,
                order_details={'status': 'failed_delivery', 'failure_reason': request.failure_reason}
            )
            
        except Exception as e:
            logger.error(f"Error processing failed delivery: {str(e)}")
            raise
    
    async def _process_returned_delivery(self, request: DeliverOrderRequest, order: Dict[str, Any], delivered_by: str) -> DeliverOrderResponse:
        """Process returned delivery"""
        try:
            delivery_timestamp = datetime.now(timezone.utc).isoformat()
            order_id = request.order_id
            
            # Update order with return information
            update_expression = 'SET #status = :status, returnReason = :reason, updatedAt = :updated, returnedTime = :returned_time'
            expression_values = {
                ':status': 'returned',
                ':reason': request.failure_reason,  # Using failure_reason for return reason
                ':updated': delivery_timestamp,
                ':returned_time': delivery_timestamp
            }
            expression_names = {'#status': 'status'}
            
            # Add delivered_by if provided
            if delivered_by:
                update_expression += ', returnedBy = :returned_by'
                expression_values[':returned_by'] = delivered_by
            
            # Add delivery notes if provided
            if request.delivery_notes:
                update_expression += ', returnNotes = :notes'
                expression_values[':notes'] = request.delivery_notes
            
            self.orders_table.update_item(
                Key={'orderID': order_id, 'customerEmail': order.get('customerEmail')},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values
            )
            
            delivery_result = DeliveryResult(
                order_id=order_id,
                status="returned",
                message=f"Order returned to warehouse: {request.failure_reason}",
                timestamp=delivery_timestamp
            )
            
            return DeliverOrderResponse(
                success=True,
                message=f"Order {order_id} returned to warehouse",
                delivery_result=delivery_result,
                order_details={'status': 'returned', 'return_reason': request.failure_reason}
            )
            
        except Exception as e:
            logger.error(f"Error processing returned delivery: {str(e)}")
            raise
    
    async def _update_delivery_analytics(self, request: DeliverOrderRequest, order: Dict[str, Any], delivered_by: str):
        """Update delivery analytics"""
        try:
            analytics_data = {
                'analyticsID': str(uuid.uuid4()),
                'type': 'delivery',
                'orderID': request.order_id,
                'deliveryStatus': request.delivery_status.value,
                'deliveredBy': delivered_by,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'orderValue': float(order.get('orderSummary', {}).get('totalAmount', 0)),
                'paymentMethod': order.get('paymentMethod', 'unknown'),
                'customerVerified': request.customer_verified,
                'deliveryProofProvided': bool(request.delivery_proof),
                'customerFeedbackProvided': bool(request.customer_feedback)
            }
            
            # Add failure reason for failed/returned deliveries
            if request.delivery_status in [DeliveryStatus.FAILED, DeliveryStatus.RETURNED]:
                analytics_data['failureReason'] = request.failure_reason
            
            # Store analytics data
            self.analytics_table.put_item(Item=analytics_data)
            
        except Exception as e:
            logger.error(f"Error updating delivery analytics: {str(e)}")
            # Don't fail the main operation for analytics errors
