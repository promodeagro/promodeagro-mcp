"""
Tests for E-commerce data models.
"""

import pytest
from datetime import datetime
from dataclasses import FrozenInstanceError

from src.models.ecommerce_models import (
    ProductBrowseRequest, CategoryCountsRequest, ProductBrowseResult,
    CategoryCountsResult, ProductInfo, CategoryInfo, ProductStock,
    ProductAttributes, ProductAvailability, ProductVariant, SearchMetadata
)


class TestProductBrowseRequest:
    """Test ProductBrowseRequest model."""
    
    def test_default_values(self):
        """Test default values are set correctly."""
        request = ProductBrowseRequest()
        
        assert request.category is None
        assert request.search_term is None
        assert request.max_results == 20
        assert request.include_out_of_stock is True
        assert request.min_price is None
        assert request.max_price is None
    
    def test_custom_values(self):
        """Test custom values are set correctly."""
        request = ProductBrowseRequest(
            category='fruits',
            search_term='apple',
            max_results=50,
            include_out_of_stock=False,
            min_price=10.0,
            max_price=100.0
        )
        
        assert request.category == 'fruits'
        assert request.search_term == 'apple'
        assert request.max_results == 50
        assert request.include_out_of_stock is False
        assert request.min_price == 10.0
        assert request.max_price == 100.0
    
    def test_price_filtering_logic(self):
        """Test price filtering scenarios."""
        # Only min price
        request1 = ProductBrowseRequest(min_price=50.0)
        assert request1.min_price == 50.0
        assert request1.max_price is None
        
        # Only max price  
        request2 = ProductBrowseRequest(max_price=200.0)
        assert request2.min_price is None
        assert request2.max_price == 200.0
        
        # Both prices
        request3 = ProductBrowseRequest(min_price=50.0, max_price=200.0)
        assert request3.min_price == 50.0
        assert request3.max_price == 200.0


class TestCategoryCountsRequest:
    """Test CategoryCountsRequest model."""
    
    def test_empty_request(self):
        """Test that CategoryCountsRequest can be created without parameters."""
        request = CategoryCountsRequest()
        assert request is not None
        # Since it's an empty dataclass with pass, no attributes to test


class TestProductStock:
    """Test ProductStock model."""
    
    def test_default_values(self):
        """Test default values."""
        stock = ProductStock(available=100, status='In Stock')
        
        assert stock.available == 100
        assert stock.status == 'In Stock'
        assert stock.track_inventory is False
    
    def test_custom_values(self):
        """Test custom values."""
        stock = ProductStock(
            available=100,
            status='In Stock',
            track_inventory=True
        )
        
        assert stock.available == 100
        assert stock.status == 'In Stock'
        assert stock.track_inventory is True
    
    def test_stock_status_scenarios(self):
        """Test different stock status scenarios."""
        # In stock
        stock1 = ProductStock(available=50, status='In Stock')
        assert stock1.available > 0
        assert stock1.status == 'In Stock'
        
        # Out of stock
        stock2 = ProductStock(available=0, status='Out of Stock')
        assert stock2.available == 0
        assert stock2.status == 'Out of Stock'
        
        # Low stock
        stock3 = ProductStock(available=5, status='Low Stock')
        assert stock3.available == 5
        assert stock3.status == 'Low Stock'


class TestProductVariant:
    """Test ProductVariant model."""
    
    def test_default_values(self):
        """Test default values."""
        variant = ProductVariant(
            variant_id='var-001',
            name='Test Variant'
        )
        
        assert variant.variant_id == 'var-001'
        assert variant.name == 'Test Variant'
        assert variant.attributes == {}
        assert variant.price == 0.0
        assert variant.stock_available == 0
    
    def test_custom_values(self):
        """Test custom values."""
        variant = ProductVariant(
            variant_id='var-001',
            name='Red Apple',
            attributes={'color': 'red', 'size': 'large'},
            price=150.50,
            stock_available=25
        )
        
        assert variant.variant_id == 'var-001'
        assert variant.name == 'Red Apple'
        assert variant.attributes == {'color': 'red', 'size': 'large'}
        assert variant.price == 150.50
        assert variant.stock_available == 25


class TestProductAttributes:
    """Test ProductAttributes model."""
    
    def test_default_values(self):
        """Test default values."""
        attrs = ProductAttributes()
        
        assert attrs.perishable is False
        assert attrs.shelf_life_days is None
        assert attrs.quality_grade is None
        assert attrs.organic is False
        assert attrs.brand is None
    
    def test_organic_product(self):
        """Test organic product attributes."""
        attrs = ProductAttributes(
            perishable=True,
            shelf_life_days=7,
            quality_grade='Premium',
            organic=True,
            brand='OrganicFarms'
        )
        
        assert attrs.perishable is True
        assert attrs.shelf_life_days == 7
        assert attrs.quality_grade == 'Premium'
        assert attrs.organic is True
        assert attrs.brand == 'OrganicFarms'


class TestProductAvailability:
    """Test ProductAvailability model."""
    
    def test_default_values(self):
        """Test default values."""
        availability = ProductAvailability()
        
        assert availability.is_active is True
        assert availability.status == 'active'
        assert availability.b2c_available is True
    
    def test_inactive_product(self):
        """Test inactive product availability."""
        availability = ProductAvailability(
            is_active=False,
            status='discontinued',
            b2c_available=False
        )
        
        assert availability.is_active is False
        assert availability.status == 'discontinued'
        assert availability.b2c_available is False


class TestProductInfo:
    """Test ProductInfo model."""
    
    def test_minimal_product(self):
        """Test minimal product creation."""
        product = ProductInfo(
            product_id='prod-001',
            product_code='CODE-001',
            name='Test Product',
            stock=ProductStock(available=0, status='Out of Stock')
        )
        
        assert product.product_id == 'prod-001'
        assert product.product_code == 'CODE-001'
        assert product.name == 'Test Product'
        assert product.description == ''
        assert product.category == 'uncategorized'
        assert product.price == 0.0
        assert product.unit == 'piece'
        assert isinstance(product.stock, ProductStock)
        assert isinstance(product.attributes, ProductAttributes)
        assert isinstance(product.availability, ProductAvailability)
        assert product.variants == []
        assert product.has_variants is False
    
    def test_full_product(self, sample_product_info):
        """Test fully populated product."""
        product = sample_product_info
        
        assert product.product_id == 'product-fruits-001'
        assert product.name == 'Apples'
        assert product.category == 'Fruits'
        assert product.price == 150.50
        assert product.has_variants is True
        assert len(product.variants) == 1
        assert product.variants[0].name == 'Red Apples'
        assert product.stock.available == 350
        assert product.attributes.brand == 'FreshFarm'


class TestCategoryInfo:
    """Test CategoryInfo model."""
    
    def test_category_creation(self):
        """Test category info creation."""
        category = CategoryInfo(
            name='Fruits',
            count=15,
            percentage=60.0
        )
        
        assert category.name == 'Fruits'
        assert category.count == 15
        assert category.percentage == 60.0
    
    def test_zero_category(self):
        """Test category with zero products."""
        category = CategoryInfo(
            name='Empty Category',
            count=0,
            percentage=0.0
        )
        
        assert category.name == 'Empty Category'
        assert category.count == 0
        assert category.percentage == 0.0


class TestSearchMetadata:
    """Test SearchMetadata model."""
    
    def test_default_metadata(self):
        """Test default search metadata."""
        metadata = SearchMetadata()
        
        assert metadata.category_filter is None
        assert metadata.search_term is None
        assert metadata.price_range == {}
        assert metadata.include_out_of_stock is True
        assert metadata.max_results == 20
    
    def test_populated_metadata(self):
        """Test populated search metadata."""
        metadata = SearchMetadata(
            category_filter='fruits',
            search_term='apple',
            price_range={'min': 10.0, 'max': 100.0},
            include_out_of_stock=False,
            max_results=50
        )
        
        assert metadata.category_filter == 'fruits'
        assert metadata.search_term == 'apple'
        assert metadata.price_range == {'min': 10.0, 'max': 100.0}
        assert metadata.include_out_of_stock is False
        assert metadata.max_results == 50


class TestProductBrowseResult:
    """Test ProductBrowseResult model."""
    
    def test_empty_result(self):
        """Test empty browse result."""
        result = ProductBrowseResult(
            status='success',
            products=[],
            total_found=0,
            returned_count=0,
            categories={},
            search_metadata=SearchMetadata(),
            timestamp=datetime.now()
        )
        
        assert result.products == []
        assert isinstance(result.search_metadata, SearchMetadata)
        assert result.status == 'success'
        assert result.total_found == 0
    
    def test_result_with_products(self, sample_product_info):
        """Test result with products."""
        metadata = SearchMetadata(
            category_filter='fruits',
            max_results=10
        )
        
        result = ProductBrowseResult(
            status='success',
            products=[sample_product_info],
            total_found=1,
            returned_count=1,
            categories={'fruits': ['Apples']},
            search_metadata=metadata,
            timestamp=datetime.now()
        )
        
        assert len(result.products) == 1
        assert result.products[0].name == 'Apples'
        assert result.search_metadata.category_filter == 'fruits'
        assert result.total_found == 1


class TestCategoryCountsResult:
    """Test CategoryCountsResult model."""
    
    def test_category_counts_result(self, sample_category_info):
        """Test category counts result."""
        result = CategoryCountsResult(
            status='success',
            categories=sample_category_info,
            total_products=25,
            total_categories=4,
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        assert len(result.categories) == 4
        assert result.total_products == 25
        assert result.total_categories == 4
        assert result.timestamp == datetime(2024, 1, 1, 12, 0, 0)
        
        # Check category details
        fruits_category = next(c for c in result.categories if c.name == 'Fruits')
        assert fruits_category.count == 10
        assert fruits_category.percentage == 40.0
    
    def test_empty_categories(self):
        """Test result with no categories."""
        result = CategoryCountsResult(
            status='success',
            categories=[],
            total_products=0,
            total_categories=0,
            timestamp=datetime.now()
        )
        
        assert result.categories == []
        assert result.total_products == 0
        assert result.total_categories == 0
        assert isinstance(result.timestamp, datetime)
