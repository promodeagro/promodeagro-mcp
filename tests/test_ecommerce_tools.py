"""
Tests for E-commerce MCP tools.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal
from datetime import datetime

from src.tools.ecommerce_tools import browse_products_tool, get_category_counts_tool
from src.models.ecommerce_models import (
    ProductBrowseRequest, CategoryCountsRequest, ProductBrowseResult,
    CategoryCountsResult, ProductInfo, CategoryInfo, ProductStock,
    ProductAttributes, ProductAvailability, ProductVariant, SearchMetadata
)


class TestBrowseProductsTool:
    """Test browse-products MCP tool."""
    
    @pytest.mark.asyncio
    @patch('src.tools.ecommerce_tools.EcommerceService')
    async def test_browse_products_tool_basic(self, mock_service_class):
        """Test basic browse products tool functionality."""
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
            attributes=ProductAttributes(),
            availability=ProductAvailability()
        )
        
        sample_result = ProductBrowseResult(
            products=[sample_product],
            search_metadata=SearchMetadata(category_filter='fruits', max_results=20)
        )
        
        mock_service.browse_products.return_value = sample_result
        
        # Create a mock FastMCP instance
        mock_mcp = Mock()
        mock_tool_func = AsyncMock()
        mock_mcp.tool.return_value = mock_tool_func
        
        # Register the tool
        browse_products_tool(mock_mcp)
        
        # Verify tool was registered
        mock_mcp.tool.assert_called_once()
        tool_decorator = mock_mcp.tool.call_args[1]
        assert 'description' in tool_decorator
        assert 'e-commerce catalog' in tool_decorator['description'].lower()
        
        # Get the registered function
        registered_func = mock_mcp.tool.call_args[0][0]
        
        # Test the function
        result = await registered_func(category='fruits')
        
        # Verify service was called correctly
        mock_service.browse_products.assert_called_once()
        call_args = mock_service.browse_products.call_args[0][0]
        assert isinstance(call_args, ProductBrowseRequest)
        assert call_args.category == 'fruits'
        
        # Verify result structure
        assert isinstance(result, dict)
        assert 'products' in result
        assert len(result['products']) == 1
        assert result['products'][0]['name'] == 'Apples'
    
    @pytest.mark.asyncio
    @patch('src.tools.ecommerce_tools.EcommerceService')
    async def test_browse_products_tool_with_all_parameters(self, mock_service_class):
        """Test browse products tool with all parameters."""
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        # Mock empty result
        empty_result = ProductBrowseResult(
            products=[],
            search_metadata=SearchMetadata(
                category_filter='vegetables',
                search_term='organic',
                price_range={'min': 50.0, 'max': 200.0},
                include_out_of_stock=False,
                max_results=15
            )
        )
        mock_service.browse_products.return_value = empty_result
        
        mock_mcp = Mock()
        browse_products_tool(mock_mcp)
        registered_func = mock_mcp.tool.call_args[0][0]
        
        # Test with all parameters
        result = await registered_func(
            category='vegetables',
            search_term='organic',
            max_results=15,
            include_out_of_stock=False,
            min_price=50.0,
            max_price=200.0
        )
        
        # Verify service call
        call_args = mock_service.browse_products.call_args[0][0]
        assert call_args.category == 'vegetables'
        assert call_args.search_term == 'organic'
        assert call_args.max_results == 15
        assert call_args.include_out_of_stock is False
        assert call_args.min_price == 50.0
        assert call_args.max_price == 200.0
        
        # Verify result
        assert isinstance(result, dict)
        assert 'products' in result
        assert len(result['products']) == 0
        assert 'search_metadata' in result
    
    @pytest.mark.asyncio
    @patch('src.tools.ecommerce_tools.EcommerceService')
    async def test_browse_products_tool_error_handling(self, mock_service_class):
        """Test browse products tool error handling."""
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        # Mock service to raise exception
        mock_service.browse_products.side_effect = Exception("Database error")
        
        mock_mcp = Mock()
        browse_products_tool(mock_mcp)
        registered_func = mock_mcp.tool.call_args[0][0]
        
        # Test error handling
        with pytest.raises(Exception, match="Database error"):
            await registered_func(category='fruits')
    
    @pytest.mark.asyncio
    @patch('src.tools.ecommerce_tools.EcommerceService')
    async def test_browse_products_tool_default_parameters(self, mock_service_class):
        """Test browse products tool with default parameters."""
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        mock_result = ProductBrowseResult(
            products=[],
            search_metadata=SearchMetadata()
        )
        mock_service.browse_products.return_value = mock_result
        
        mock_mcp = Mock()
        browse_products_tool(mock_mcp)
        registered_func = mock_mcp.tool.call_args[0][0]
        
        # Test with no parameters (should use defaults)
        result = await registered_func()
        
        # Verify default values were used
        call_args = mock_service.browse_products.call_args[0][0]
        assert call_args.category is None
        assert call_args.search_term is None
        assert call_args.max_results == 20  # Default
        assert call_args.include_out_of_stock is True  # Default
        assert call_args.min_price is None
        assert call_args.max_price is None


class TestGetCategoryCountsTool:
    """Test get-category-counts MCP tool."""
    
    @pytest.mark.asyncio
    @patch('src.tools.ecommerce_tools.EcommerceService')
    async def test_get_category_counts_tool_basic(self, mock_service_class):
        """Test basic get category counts tool functionality."""
        # Setup mock service
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        # Create sample result
        sample_categories = [
            CategoryInfo(name='Fruits', count=10, percentage=40.0),
            CategoryInfo(name='Vegetables', count=8, percentage=32.0),
            CategoryInfo(name='Dairy', count=5, percentage=20.0),
            CategoryInfo(name='Grains', count=2, percentage=8.0)
        ]
        
        sample_result = CategoryCountsResult(
            categories=sample_categories,
            total_products=25,
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        mock_service.get_category_counts.return_value = sample_result
        
        # Create a mock FastMCP instance
        mock_mcp = Mock()
        
        # Register the tool
        get_category_counts_tool(mock_mcp)
        
        # Verify tool was registered
        mock_mcp.tool.assert_called_once()
        tool_decorator = mock_mcp.tool.call_args[1]
        assert 'description' in tool_decorator
        assert 'category counts' in tool_decorator['description'].lower()
        
        # Get the registered function
        registered_func = mock_mcp.tool.call_args[0][0]
        
        # Test the function
        result = await registered_func()
        
        # Verify service was called correctly
        mock_service.get_category_counts.assert_called_once()
        call_args = mock_service.get_category_counts.call_args[0][0]
        assert isinstance(call_args, CategoryCountsRequest)
        
        # Verify result structure
        assert isinstance(result, dict)
        assert 'categories' in result
        assert 'total_products' in result
        assert 'timestamp' in result
        
        assert len(result['categories']) == 4
        assert result['total_products'] == 25
        
        # Check category structure
        fruits_category = next(c for c in result['categories'] if c['name'] == 'Fruits')
        assert fruits_category['count'] == 10
        assert fruits_category['percentage'] == 40.0
    
    @pytest.mark.asyncio
    @patch('src.tools.ecommerce_tools.EcommerceService')
    async def test_get_category_counts_tool_empty_result(self, mock_service_class):
        """Test get category counts tool with empty result."""
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        # Mock empty result
        empty_result = CategoryCountsResult(
            categories=[],
            total_products=0,
            timestamp=datetime.now()
        )
        mock_service.get_category_counts.return_value = empty_result
        
        mock_mcp = Mock()
        get_category_counts_tool(mock_mcp)
        registered_func = mock_mcp.tool.call_args[0][0]
        
        # Test with empty database
        result = await registered_func()
        
        # Verify result
        assert isinstance(result, dict)
        assert len(result['categories']) == 0
        assert result['total_products'] == 0
        assert 'timestamp' in result
    
    @pytest.mark.asyncio
    @patch('src.tools.ecommerce_tools.EcommerceService')
    async def test_get_category_counts_tool_error_handling(self, mock_service_class):
        """Test get category counts tool error handling."""
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        # Mock service to raise exception
        mock_service.get_category_counts.side_effect = Exception("Database connection failed")
        
        mock_mcp = Mock()
        get_category_counts_tool(mock_mcp)
        registered_func = mock_mcp.tool.call_args[0][0]
        
        # Test error handling
        with pytest.raises(Exception, match="Database connection failed"):
            await registered_func()


class TestToolHelperFunctions:
    """Test helper functions used by the MCP tools."""
    
    def test_convert_browse_result_to_dict(self):
        """Test _convert_browse_result_to_dict function."""
        from src.tools.ecommerce_tools import _convert_browse_result_to_dict
        
        # Create sample data
        sample_product = ProductInfo(
            product_id='product-fruits-001',
            product_code='APL-FRU-001',
            name='Apples',
            description='Fresh Red Apples',
            category='Fruits',
            price=150.50,
            unit='kg',
            stock=ProductStock(available=100, status='In Stock', track_inventory=True),
            variants=[
                ProductVariant(
                    variant_id='var-001',
                    name='Red Apples',
                    attributes={'color': 'red'},
                    price=160.00,
                    stock_available=50
                )
            ],
            has_variants=True,
            attributes=ProductAttributes(organic=True, brand='FreshFarm'),
            availability=ProductAvailability(is_active=True, status='active', b2c_available=True)
        )
        
        sample_result = ProductBrowseResult(
            products=[sample_product],
            search_metadata=SearchMetadata(
                category_filter='fruits',
                search_term='apple',
                price_range={'min': 100.0, 'max': 200.0},
                include_out_of_stock=True,
                max_results=20
            )
        )
        
        # Convert to dict
        result_dict = _convert_browse_result_to_dict(sample_result)
        
        # Verify structure
        assert isinstance(result_dict, dict)
        assert 'products' in result_dict
        assert 'search_metadata' in result_dict
        
        # Verify product data
        product_dict = result_dict['products'][0]
        assert product_dict['product_id'] == 'product-fruits-001'
        assert product_dict['name'] == 'Apples'
        assert product_dict['price'] == 150.50
        assert product_dict['stock']['available'] == 100
        assert product_dict['stock']['status'] == 'In Stock'
        assert len(product_dict['variants']) == 1
        assert product_dict['variants'][0]['name'] == 'Red Apples'
        assert product_dict['attributes']['organic'] is True
        assert product_dict['availability']['is_active'] is True
        
        # Verify search metadata
        metadata_dict = result_dict['search_metadata']
        assert metadata_dict['category_filter'] == 'fruits'
        assert metadata_dict['search_term'] == 'apple'
        assert metadata_dict['price_range']['min'] == 100.0
        assert metadata_dict['max_results'] == 20
    
    def test_convert_category_counts_result_to_dict(self):
        """Test _convert_category_counts_result_to_dict function."""
        from src.tools.ecommerce_tools import _convert_category_counts_result_to_dict
        
        # Create sample data
        sample_categories = [
            CategoryInfo(name='Fruits', count=10, percentage=50.0),
            CategoryInfo(name='Vegetables', count=10, percentage=50.0)
        ]
        
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        sample_result = CategoryCountsResult(
            categories=sample_categories,
            total_products=20,
            timestamp=timestamp
        )
        
        # Convert to dict
        result_dict = _convert_category_counts_result_to_dict(sample_result)
        
        # Verify structure
        assert isinstance(result_dict, dict)
        assert 'categories' in result_dict
        assert 'total_products' in result_dict
        assert 'timestamp' in result_dict
        
        # Verify categories
        assert len(result_dict['categories']) == 2
        fruits_category = next(c for c in result_dict['categories'] if c['name'] == 'Fruits')
        assert fruits_category['count'] == 10
        assert fruits_category['percentage'] == 50.0
        
        # Verify other fields
        assert result_dict['total_products'] == 20
        assert result_dict['timestamp'] == timestamp.isoformat()
    
    def test_convert_product_info_to_dict(self):
        """Test _convert_product_info_to_dict function."""
        from src.tools.ecommerce_tools import _convert_product_info_to_dict
        
        # Create sample product with full data
        sample_product = ProductInfo(
            product_id='product-fruits-001',
            product_code='APL-FRU-001',
            name='Apples',
            description='Fresh Red Apples',
            category='Fruits',
            price=150.50,
            unit='kg',
            stock=ProductStock(available=100, status='In Stock', track_inventory=True),
            variants=[
                ProductVariant(
                    variant_id='var-001',
                    name='Red Apples',
                    attributes={'color': 'red', 'size': 'large'},
                    price=160.00,
                    stock_available=25
                )
            ],
            has_variants=True,
            attributes=ProductAttributes(
                perishable=True,
                shelf_life_days=7,
                quality_grade='Premium',
                organic=True,
                brand='FreshFarm'
            ),
            availability=ProductAvailability(
                is_active=True,
                status='active',
                b2c_available=True
            )
        )
        
        # Convert to dict
        product_dict = _convert_product_info_to_dict(sample_product)
        
        # Verify all fields
        assert product_dict['product_id'] == 'product-fruits-001'
        assert product_dict['product_code'] == 'APL-FRU-001'
        assert product_dict['name'] == 'Apples'
        assert product_dict['description'] == 'Fresh Red Apples'
        assert product_dict['category'] == 'Fruits'
        assert product_dict['price'] == 150.50
        assert product_dict['unit'] == 'kg'
        assert product_dict['has_variants'] is True
        
        # Verify nested objects
        assert product_dict['stock']['available'] == 100
        assert product_dict['stock']['status'] == 'In Stock'
        assert product_dict['stock']['track_inventory'] is True
        
        assert len(product_dict['variants']) == 1
        variant = product_dict['variants'][0]
        assert variant['variant_id'] == 'var-001'
        assert variant['name'] == 'Red Apples'
        assert variant['price'] == 160.00
        assert variant['stock_available'] == 25
        assert variant['attributes']['color'] == 'red'
        
        assert product_dict['attributes']['organic'] is True
        assert product_dict['attributes']['brand'] == 'FreshFarm'
        assert product_dict['attributes']['shelf_life_days'] == 7
        
        assert product_dict['availability']['is_active'] is True
        assert product_dict['availability']['status'] == 'active'
