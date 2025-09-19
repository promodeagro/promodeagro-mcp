"""
Tests for EcommerceService class.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal
from datetime import datetime

from src.services.ecommerce_service import EcommerceService
from src.models.ecommerce_models import (
    ProductBrowseRequest, CategoryCountsRequest, ProductBrowseResult,
    CategoryCountsResult, ProductInfo, CategoryInfo
)


class TestEcommerceServiceInitialization:
    """Test EcommerceService initialization."""
    
    @patch('src.services.ecommerce_service.boto3.resource')
    def test_service_initialization(self, mock_boto3):
        """Test service initializes with DynamoDB tables."""
        mock_dynamodb = Mock()
        mock_boto3.return_value = mock_dynamodb
        
        service = EcommerceService()
        
        mock_boto3.assert_called_once_with('dynamodb', region_name='ap-south-1')
        mock_dynamodb.Table.assert_any_call('EcommerceApp-Products')
        mock_dynamodb.Table.assert_any_call('EcommerceApp-Inventory')
    
    @patch('src.services.ecommerce_service.boto3.resource')
    def test_service_with_custom_region(self, mock_boto3):
        """Test service with custom AWS region."""
        mock_dynamodb = Mock()
        mock_boto3.return_value = mock_dynamodb
        
        service = EcommerceService(region='us-east-1')
        
        mock_boto3.assert_called_once_with('dynamodb', region_name='us-east-1')


class TestBrowseProducts:
    """Test browse_products functionality."""
    
    @pytest.mark.asyncio
    async def test_browse_products_all_categories(self, ecommerce_service_with_mocks, mock_multiple_products):
        """Test browsing all products without category filter."""
        service = ecommerce_service_with_mocks
        service.products_table.scan.return_value = mock_multiple_products
        
        request = ProductBrowseRequest(max_results=10)
        result = await service.browse_products(request)
        
        assert isinstance(result, ProductBrowseResult)
        assert len(result.products) == 3
        assert result.products[0].name in ['Apples', 'Bananas', 'Carrots']
        
        # Verify scan was called with correct parameters
        service.products_table.scan.assert_called_once()
        call_args = service.products_table.scan.call_args
        assert 'Limit' in call_args[1]
        assert call_args[1]['Limit'] == 10
    
    @pytest.mark.asyncio
    async def test_browse_products_with_category_filter(self, ecommerce_service_with_mocks, mock_multiple_products):
        """Test browsing products with category filter."""
        service = ecommerce_service_with_mocks
        
        # Filter mock data to only fruits
        fruits_data = {
            'Items': [item for item in mock_multiple_products['Items'] if item['category'] == 'fruits']
        }
        service.products_table.scan.return_value = fruits_data
        
        request = ProductBrowseRequest(category='fruits', max_results=10)
        result = await service.browse_products(request)
        
        assert len(result.products) == 2  # Apples and Bananas
        for product in result.products:
            assert product.category == 'Fruits'  # Note: title case conversion
        
        # Verify filter expression was used
        service.products_table.scan.assert_called_once()
        call_args = service.products_table.scan.call_args
        assert 'FilterExpression' in call_args[1]
    
    @pytest.mark.asyncio
    async def test_browse_products_with_search_term(self, ecommerce_service_with_mocks, mock_multiple_products):
        """Test browsing products with search term."""
        service = ecommerce_service_with_mocks
        
        # Mock data filtered for search term
        apple_data = {
            'Items': [item for item in mock_multiple_products['Items'] if 'Apples' in item['name']]
        }
        service.products_table.scan.return_value = apple_data
        
        request = ProductBrowseRequest(search_term='apple', max_results=10)
        result = await service.browse_products(request)
        
        assert len(result.products) == 1
        assert 'apple' in result.products[0].name.lower()
    
    @pytest.mark.asyncio
    async def test_browse_products_with_price_range(self, ecommerce_service_with_mocks, mock_multiple_products):
        """Test browsing products with price range."""
        service = ecommerce_service_with_mocks
        
        # Mock data filtered for price range (80-120)
        price_filtered_data = {
            'Items': [item for item in mock_multiple_products['Items'] 
                     if 80 <= float(item['pricing']['sellingPrice']) <= 120]
        }
        service.products_table.scan.return_value = price_filtered_data
        
        request = ProductBrowseRequest(min_price=80.0, max_price=120.0, max_results=10)
        result = await service.browse_products(request)
        
        assert len(result.products) >= 1
        for product in result.products:
            assert 80.0 <= product.price <= 120.0
    
    @pytest.mark.asyncio
    async def test_browse_products_exclude_out_of_stock(self, ecommerce_service_with_mocks, mock_multiple_products):
        """Test browsing products excluding out of stock items."""
        service = ecommerce_service_with_mocks
        
        # Mock data with some out-of-stock items
        mixed_stock_data = {
            'Items': [
                {
                    **mock_multiple_products['Items'][0],
                    'inventory': {'trackInventory': True, 'maxStock': Decimal('0')}  # Out of stock
                },
                mock_multiple_products['Items'][1]  # In stock
            ]
        }
        service.products_table.scan.return_value = mixed_stock_data
        
        request = ProductBrowseRequest(include_out_of_stock=False, max_results=10)
        result = await service.browse_products(request)
        
        # Should only return items with stock
        for product in result.products:
            assert product.stock.available > 0
    
    @pytest.mark.asyncio
    async def test_browse_products_empty_result(self, ecommerce_service_with_mocks):
        """Test browsing products with no results."""
        service = ecommerce_service_with_mocks
        service.products_table.scan.return_value = {'Items': []}
        
        request = ProductBrowseRequest(category='nonexistent', max_results=10)
        result = await service.browse_products(request)
        
        assert isinstance(result, ProductBrowseResult)
        assert len(result.products) == 0
        assert result.search_metadata.category_filter == 'nonexistent'
    
    @pytest.mark.asyncio
    async def test_browse_products_database_error(self, ecommerce_service_with_mocks):
        """Test handling database errors in browse_products."""
        service = ecommerce_service_with_mocks
        service.products_table.scan.side_effect = Exception("Database connection error")
        
        request = ProductBrowseRequest(max_results=10)
        
        with pytest.raises(Exception, match="Database connection error"):
            await service.browse_products(request)


class TestGetCategoryCounts:
    """Test get_category_counts functionality."""
    
    @pytest.mark.asyncio
    async def test_get_category_counts_success(self, ecommerce_service_with_mocks, mock_multiple_products):
        """Test successful category counts retrieval."""
        service = ecommerce_service_with_mocks
        service.products_table.scan.return_value = mock_multiple_products
        
        request = CategoryCountsRequest()
        result = await service.get_category_counts(request)
        
        assert isinstance(result, CategoryCountsResult)
        assert len(result.categories) >= 2  # At least fruits and vegetables
        assert result.total_products == 3
        assert isinstance(result.timestamp, datetime)
        
        # Check specific category counts
        category_names = [cat.name for cat in result.categories]
        assert 'Fruits' in category_names
        assert 'Vegetables' in category_names
        
        # Check percentages add up correctly
        total_percentage = sum(cat.percentage for cat in result.categories)
        assert abs(total_percentage - 100.0) < 0.1  # Allow small floating point errors
    
    @pytest.mark.asyncio
    async def test_get_category_counts_with_inactive_products(self, ecommerce_service_with_mocks, mock_multiple_products):
        """Test category counts excluding inactive products."""
        service = ecommerce_service_with_mocks
        
        # Add inactive product to mock data
        modified_data = dict(mock_multiple_products)
        modified_data['Items'] = list(mock_multiple_products['Items']) + [{
            'productID': 'product-inactive-001',
            'name': 'Inactive Product',
            'category': 'fruits',
            'isActive': False,  # Inactive
            'status': 'discontinued',
            'pricing': {'sellingPrice': Decimal('100.00')},
        }]
        
        service.products_table.scan.return_value = modified_data
        
        request = CategoryCountsRequest()
        result = await service.get_category_counts(request)
        
        # Should only count active products
        assert result.total_products == 3  # Should not include inactive product
        
        # Verify filter was applied
        service.products_table.scan.assert_called_once()
        call_args = service.products_table.scan.call_args
        assert 'FilterExpression' in call_args[1]
    
    @pytest.mark.asyncio
    async def test_get_category_counts_empty_database(self, ecommerce_service_with_mocks):
        """Test category counts with empty database."""
        service = ecommerce_service_with_mocks
        service.products_table.scan.return_value = {'Items': []}
        
        request = CategoryCountsRequest()
        result = await service.get_category_counts(request)
        
        assert len(result.categories) == 0
        assert result.total_products == 0
        assert isinstance(result.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_get_category_counts_single_category(self, ecommerce_service_with_mocks):
        """Test category counts with only one category."""
        service = ecommerce_service_with_mocks
        single_category_data = {
            'Items': [
                {
                    'productID': 'product-fruits-001',
                    'name': 'Apples',
                    'category': 'fruits',
                    'isActive': True,
                    'status': 'active',
                    'pricing': {'sellingPrice': Decimal('150.00')}
                },
                {
                    'productID': 'product-fruits-002',
                    'name': 'Bananas',
                    'category': 'fruits',
                    'isActive': True,
                    'status': 'active',
                    'pricing': {'sellingPrice': Decimal('80.00')}
                }
            ]
        }
        service.products_table.scan.return_value = single_category_data
        
        request = CategoryCountsRequest()
        result = await service.get_category_counts(request)
        
        assert len(result.categories) == 1
        assert result.categories[0].name == 'Fruits'
        assert result.categories[0].count == 2
        assert result.categories[0].percentage == 100.0
        assert result.total_products == 2


class TestPrivateMethods:
    """Test private helper methods."""
    
    def test_get_product_price(self, ecommerce_service_with_mocks, sample_product_data):
        """Test _get_product_price method."""
        service = ecommerce_service_with_mocks
        
        price = service._get_product_price(sample_product_data)
        assert price == 150.50  # From pricing.sellingPrice
    
    def test_get_product_price_missing_pricing(self, ecommerce_service_with_mocks):
        """Test _get_product_price with missing pricing data."""
        service = ecommerce_service_with_mocks
        
        # Product without pricing
        product_data = {
            'productID': 'test-001',
            'name': 'Test Product'
        }
        
        price = service._get_product_price(product_data)
        assert price == 0.0
    
    def test_get_product_price_from_variant(self, ecommerce_service_with_mocks):
        """Test _get_product_price falling back to variant pricing."""
        service = ecommerce_service_with_mocks
        
        product_data = {
            'productID': 'test-001',
            'name': 'Test Product',
            'hasVariants': True,
            'variants': [
                {
                    'variantID': 'var-001',
                    'pricing': {'sellingPrice': Decimal('200.00')}
                }
            ]
        }
        
        price = service._get_product_price(product_data)
        assert price == 200.00
    
    def test_get_simulated_stock(self, ecommerce_service_with_mocks):
        """Test _get_simulated_stock method."""
        service = ecommerce_service_with_mocks
        
        # Test with inventory tracking enabled
        inventory_data = {
            'trackInventory': True,
            'maxStock': Decimal('100'),
            'minStock': Decimal('10')
        }
        
        stock = service._get_simulated_stock(inventory_data)
        assert stock == 70  # 70% of 100
    
    def test_get_simulated_stock_no_tracking(self, ecommerce_service_with_mocks):
        """Test _get_simulated_stock with tracking disabled."""
        service = ecommerce_service_with_mocks
        
        inventory_data = {
            'trackInventory': False,
            'maxStock': Decimal('100')
        }
        
        stock = service._get_simulated_stock(inventory_data)
        assert stock == 0
    
    def test_get_simulated_stock_no_max_stock(self, ecommerce_service_with_mocks):
        """Test _get_simulated_stock without maxStock."""
        service = ecommerce_service_with_mocks
        
        inventory_data = {
            'trackInventory': True,
            'minStock': Decimal('10')
            # No maxStock
        }
        
        stock = service._get_simulated_stock(inventory_data)
        assert stock == 0
    
    def test_convert_raw_product_to_model(self, ecommerce_service_with_mocks, sample_product_data):
        """Test _convert_raw_product_to_model method."""
        service = ecommerce_service_with_mocks
        
        product_info = service._convert_raw_product_to_model(sample_product_data)
        
        assert isinstance(product_info, ProductInfo)
        assert product_info.product_id == 'product-fruits-001'
        assert product_info.name == 'Apples'
        assert product_info.category == 'Fruits'  # Title case
        assert product_info.price == 150.50
        assert product_info.has_variants is True
        assert len(product_info.variants) == 1
        assert product_info.stock.available == 350  # 70% of 500
        assert product_info.attributes.organic is False
    
    @pytest.mark.asyncio
    async def test_get_all_categories(self, ecommerce_service_with_mocks, mock_multiple_products):
        """Test _get_all_categories method."""
        service = ecommerce_service_with_mocks
        service.products_table.scan.return_value = mock_multiple_products
        
        categories = await service._get_all_categories()
        
        assert isinstance(categories, list)
        assert 'Fruits' in categories
        assert 'Vegetables' in categories
        assert len(categories) >= 2
