"""E-commerce tools for the Aurora Spark Customer Portal MCP Server."""

import os
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger
from mcp.server.fastmcp import FastMCP

from ..models.ecommerce_models import (
    ProductBrowseRequest, CategoryCountsRequest, ProductBrowseResult, CategoryCountsResult
)
from ..services.ecommerce_service import EcommerceService


def browse_products_tool(mcp: FastMCP) -> None:
    """Register the browse products tool."""
    
    @mcp.tool(description="Browse and search products in the e-commerce catalog with filtering and search capabilities")
    async def browse_products(
        category: Optional[str] = None,
        search_term: Optional[str] = None,
        max_results: int = 20,
        include_out_of_stock: bool = True,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> Dict:
        """
        Browse and search products in the e-commerce catalog.
        
        Args:
            category: Filter by product category (e.g., 'vegetables', 'fruits', 'dairy')
            search_term: Search in product names and descriptions
            max_results: Maximum number of products to return (default: 20, max: 100)
            include_out_of_stock: Whether to include out of stock products (default: True)
            min_price: Minimum price filter
            max_price: Maximum price filter
            
        Returns:
            Dictionary containing:
            - products: List of matching products with details
            - total_found: Total number of products found
            - categories: Available categories
            - search_metadata: Search and filter information
        """
        try:
            logger.info(f"Starting product browsing - Category: {category}, Search: {search_term}")
            
            # Create browse request
            request = ProductBrowseRequest(
                category=category,
                search_term=search_term,
                max_results=max_results,
                include_out_of_stock=include_out_of_stock,
                min_price=min_price,
                max_price=max_price
            )
            
            # Initialize service and perform browsing
            service = EcommerceService()
            result = await service.browse_products(request)
            
            # Convert result to dictionary format
            response = _convert_browse_result_to_dict(result)
            logger.info(f"Product browsing completed successfully - Found {result.total_found} products")
            
            return response
            
        except Exception as e:
            logger.error(f"Error browsing products: {str(e)}")
            return {
                "status": "error",
                "error_message": str(e),
                "products": [],
                "total_found": 0,
                "returned_count": 0,
                "categories": {
                    "available_categories": [],
                    "categories_in_results": []
                },
                "timestamp": datetime.now().isoformat()
            }


def get_category_counts_tool(mcp: FastMCP) -> None:
    """Register the category counts tool."""
    
    @mcp.tool(description="Get product counts by category for e-commerce catalog")
    async def get_category_counts() -> Dict:
        """
        Get product counts by category to understand catalog distribution.
        
        Returns:
            Dictionary containing:
            - categories: List of categories with product counts
            - total_products: Total number of active products
            - total_categories: Number of categories
        """
        try:
            logger.info("Starting category counts analysis")
            
            # Create category counts request
            request = CategoryCountsRequest()
            
            # Initialize service and get category counts
            service = EcommerceService()
            result = await service.get_category_counts(request)
            
            # Convert result to dictionary format
            response = _convert_category_counts_result_to_dict(result)
            logger.info(f"Category counts analysis completed - Found {result.total_categories} categories")
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting category counts: {str(e)}")
            return {
                "status": "error",
                "error_message": str(e),
                "categories": [],
                "total_products": 0,
                "total_categories": 0,
                "timestamp": datetime.now().isoformat()
            }


def _convert_browse_result_to_dict(result: ProductBrowseResult) -> Dict:
    """Convert ProductBrowseResult to dictionary format."""
    if result.status == "error":
        return {
            "status": result.status,
            "error_message": result.error_message,
            "products": [],
            "total_found": 0,
            "returned_count": 0,
            "categories": {
                "available_categories": [],
                "categories_in_results": []
            },
            "timestamp": result.timestamp.isoformat()
        }
    
    return {
        "status": result.status,
        "products": [_convert_product_info_to_dict(product) for product in result.products],
        "total_found": result.total_found,
        "returned_count": result.returned_count,
        "categories": result.categories,
        "search_metadata": {
            "category_filter": result.search_metadata.category_filter,
            "search_term": result.search_metadata.search_term,
            "price_range": result.search_metadata.price_range,
            "include_out_of_stock": result.search_metadata.include_out_of_stock,
            "max_results": result.search_metadata.max_results
        },
        "timestamp": result.timestamp.isoformat()
    }


def _convert_category_counts_result_to_dict(result: CategoryCountsResult) -> Dict:
    """Convert CategoryCountsResult to dictionary format."""
    if result.status == "error":
        return {
            "status": result.status,
            "error_message": result.error_message,
            "categories": [],
            "total_products": 0,
            "total_categories": 0,
            "timestamp": result.timestamp.isoformat()
        }
    
    return {
        "status": result.status,
        "categories": [
            {
                "name": category.name,
                "count": category.count,
                "percentage": category.percentage
            }
            for category in result.categories
        ],
        "total_products": result.total_products,
        "total_categories": result.total_categories,
        "timestamp": result.timestamp.isoformat()
    }


def _convert_product_info_to_dict(product: 'ProductInfo') -> Dict:
    """Convert ProductInfo to dictionary format."""
    return {
        "product_id": product.product_id,
        "product_code": product.product_code,
        "name": product.name,
        "description": product.description,
        "category": product.category,
        "price": product.price,
        "unit": product.unit,
        "stock": {
            "available": product.stock.available,
            "status": product.stock.status,
            "track_inventory": product.stock.track_inventory
        },
        "variants": [
            {
                "variant_id": variant.variant_id,
                "name": variant.name,
                "attributes": variant.attributes,
                "price": variant.price,
                "stock_available": variant.stock_available
            }
            for variant in product.variants
        ],
        "has_variants": product.has_variants,
        "attributes": {
            "perishable": product.attributes.perishable,
            "shelf_life_days": product.attributes.shelf_life_days,
            "quality_grade": product.attributes.quality_grade,
            "organic": product.attributes.organic,
            "brand": product.attributes.brand
        },
        "availability": {
            "is_active": product.availability.is_active,
            "status": product.availability.status,
            "b2c_available": product.availability.b2c_available
        }
    }
