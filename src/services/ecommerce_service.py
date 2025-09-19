"""
E-commerce Service - Product browsing and catalog management for Aurora Spark e-commerce platform.
"""

import boto3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from decimal import Decimal

from loguru import logger

from ..models.ecommerce_models import (
    ProductBrowseRequest, CategoryCountsRequest, ProductBrowseResult, CategoryCountsResult,
    ProductInfo, ProductVariant, ProductStock, ProductAttributes, ProductAvailability,
    CategoryInfo, SearchMetadata
)


class EcommerceService:
    """Service for e-commerce product catalog operations."""

    def __init__(self, region_name: str = None):
        """Initialize the e-commerce service."""
        self.region_name = region_name or os.getenv('AWS_REGION', 'ap-south-1')
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region_name)
        
        # Initialize table references
        self.products_table = self.dynamodb.Table('AuroraSparkTheme-Products')

    async def browse_products(self, request: ProductBrowseRequest) -> ProductBrowseResult:
        """Browse and search products based on request parameters."""
        try:
            logger.info(f"Browsing products - Category: {request.category}, Search: {request.search_term}")
            
            # Validate request parameters
            max_results = min(max(request.max_results, 1), 100)  # Clamp between 1 and 100
            
            # Query products based on category or scan all
            if request.category:
                response = self.products_table.query(
                    IndexName='CategoryIndex',
                    KeyConditionExpression='category = :category',
                    ExpressionAttributeValues={':category': request.category.lower()}
                )
            else:
                response = self.products_table.scan()
            
            raw_products = response.get('Items', [])
            
            # Filter and process products
            filtered_products = []
            categories_found = set()
            
            for raw_product in raw_products:
                # Check if product meets basic criteria
                if not self._is_product_available(raw_product):
                    continue
                
                # Apply search filter
                if request.search_term and not self._matches_search_term(raw_product, request.search_term):
                    continue
                
                # Process product data
                product_info = self._process_raw_product(raw_product)
                
                # Apply price filters
                if not self._matches_price_range(product_info, request.min_price, request.max_price):
                    continue
                
                # Apply stock filter
                if not request.include_out_of_stock and product_info.stock.available <= 0:
                    continue
                
                filtered_products.append(product_info)
                categories_found.add(product_info.category.lower())
            
            # Sort by name and apply limit
            filtered_products.sort(key=lambda x: x.name)
            total_found = len(filtered_products)
            filtered_products = filtered_products[:max_results]
            
            # Get all available categories
            all_categories = await self._get_all_categories()
            
            # Create search metadata
            search_metadata = SearchMetadata(
                category_filter=request.category,
                search_term=request.search_term,
                price_range={"min_price": request.min_price, "max_price": request.max_price},
                include_out_of_stock=request.include_out_of_stock,
                max_results=max_results
            )
            
            return ProductBrowseResult(
                status="success",
                products=filtered_products,
                total_found=total_found,
                returned_count=len(filtered_products),
                categories={
                    "available_categories": list(all_categories),
                    "categories_in_results": list(categories_found)
                },
                search_metadata=search_metadata,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error browsing products: {str(e)}")
            return ProductBrowseResult(
                status="error",
                products=[],
                total_found=0,
                returned_count=0,
                categories={"available_categories": [], "categories_in_results": []},
                search_metadata=SearchMetadata(),
                timestamp=datetime.now(),
                error_message=str(e)
            )

    async def get_category_counts(self, request: CategoryCountsRequest) -> CategoryCountsResult:
        """Get product counts by category."""
        try:
            logger.info("Getting category counts")
            
            # Scan all active products
            response = self.products_table.scan(
                FilterExpression='#status = :status AND isActive = :active',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'active',
                    ':active': True
                }
            )
            
            raw_products = response.get('Items', [])
            
            # Count products by category
            category_counts = {}
            total_products = 0
            
            for raw_product in raw_products:
                category = raw_product.get('category', 'uncategorized').title()
                category_counts[category] = category_counts.get(category, 0) + 1
                total_products += 1
            
            # Format response
            categories_list = []
            for category, count in sorted(category_counts.items()):
                percentage = round((count / total_products * 100), 2) if total_products > 0 else 0
                categories_list.append(CategoryInfo(
                    name=category,
                    count=count,
                    percentage=percentage
                ))
            
            return CategoryCountsResult(
                status="success",
                categories=categories_list,
                total_products=total_products,
                total_categories=len(category_counts),
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error getting category counts: {str(e)}")
            return CategoryCountsResult(
                status="error",
                categories=[],
                total_products=0,
                total_categories=0,
                timestamp=datetime.now(),
                error_message=str(e)
            )

    def _is_product_available(self, raw_product: Dict[str, Any]) -> bool:
        """Check if product is available for browsing."""
        return (raw_product.get('status') == 'active' and 
                raw_product.get('isActive', True))

    def _matches_search_term(self, raw_product: Dict[str, Any], search_term: str) -> bool:
        """Check if product matches search term."""
        search_term_lower = search_term.lower()
        product_name = raw_product.get('name', '').lower()
        product_desc = raw_product.get('description', '').lower()
        product_code = raw_product.get('productCode', '').lower()
        
        return any(search_term_lower in field for field in [product_name, product_desc, product_code])

    def _matches_price_range(self, product_info: ProductInfo, min_price: Optional[float], max_price: Optional[float]) -> bool:
        """Check if product matches price range criteria."""
        if min_price is not None and product_info.price < min_price:
            return False
        if max_price is not None and product_info.price > max_price:
            return False
        return True

    def _process_raw_product(self, raw_product: Dict[str, Any]) -> ProductInfo:
        """Convert raw DynamoDB product data to ProductInfo model."""
        # Get product price
        price = self._get_product_price(raw_product)
        
        # Process stock information
        inventory = raw_product.get('inventory', {})
        current_stock = self._get_simulated_stock(inventory)
        stock = ProductStock(
            available=current_stock,
            status="In Stock" if current_stock > 0 else "Out of Stock",
            track_inventory=inventory.get('trackInventory', False)
        )
        
        # Process variants
        variants = []
        if raw_product.get('hasVariants') and raw_product.get('variants'):
            for variant_data in raw_product.get('variants', []):
                variant = ProductVariant(
                    variant_id=variant_data.get('variantID', ''),
                    name=variant_data.get('variantName', 'Unknown'),
                    attributes=variant_data.get('attributes', {}),
                    price=variant_data.get('pricing', {}).get('sellingPrice', price),
                    stock_available=50 if variant_data.get('inventory', {}).get('trackInventory', False) else 0
                )
                variants.append(variant)
        
        # Process attributes
        attributes = ProductAttributes(
            perishable=raw_product.get('perishable', False),
            shelf_life_days=raw_product.get('shelfLifeDays'),
            quality_grade=raw_product.get('qualityGrade'),
            organic=raw_product.get('attributes', {}).get('organic', False),
            brand=raw_product.get('attributes', {}).get('brand')
        )
        
        # Process availability
        availability = ProductAvailability(
            is_active=raw_product.get('isActive', True),
            status=raw_product.get('status', 'unknown'),
            b2c_available=raw_product.get('isB2cAvailable', True)
        )
        
        return ProductInfo(
            product_id=raw_product.get('productID', ''),
            product_code=raw_product.get('productCode', ''),
            name=raw_product.get('name', 'Unknown Product'),
            description=raw_product.get('description', ''),
            category=raw_product.get('category', 'uncategorized').title(),
            price=price,
            unit=raw_product.get('unit', 'piece'),
            stock=stock,
            variants=variants,
            has_variants=raw_product.get('hasVariants', False),
            attributes=attributes,
            availability=availability
        )

    def _get_product_price(self, raw_product: Dict[str, Any]) -> float:
        """Get product price, handling missing pricing data."""
        pricing = raw_product.get('pricing', {})
        price = pricing.get('sellingPrice', 0)
        
        # If no price at product level, try to get from first variant
        if not price and raw_product.get('hasVariants') and raw_product.get('variants'):
            variants = raw_product.get('variants', [])
            if variants:
                first_variant = variants[0]
                variant_pricing = first_variant.get('pricing', {})
                price = variant_pricing.get('sellingPrice', 0)
        
        return float(price) if price else 0.0

    def _get_simulated_stock(self, inventory: Dict[str, Any]) -> int:
        """Get simulated stock level."""
        # Simulate stock levels since real inventory tracking might not be implemented
        min_stock = inventory.get('minStock', 0)
        max_stock = inventory.get('maxStock', 0)
        
        if inventory.get('trackInventory', False) and max_stock:
            # Simulate 70% of max stock
            return int(float(max_stock) * 0.7)
        else:
            # Return 0 if inventory tracking is disabled
            return 0

    async def _get_all_categories(self) -> List[str]:
        """Get all available product categories."""
        try:
            # Scan to get all categories (in production, this might be cached or stored separately)
            response = self.products_table.scan(
                ProjectionExpression='category',
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': 'active'}
            )
            
            categories = set()
            for item in response.get('Items', []):
                category = item.get('category', 'uncategorized')
                categories.add(category.title())
            
            return sorted(list(categories))
            
        except Exception as e:
            logger.error(f"Error getting categories: {str(e)}")
            return []
