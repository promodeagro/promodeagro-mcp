"""
Pytest configuration and fixtures for E-commerce MCP server tests.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, List

# Add the src directory to the path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.ecommerce_service import EcommerceService
from src.models.ecommerce_models import (
    ProductBrowseRequest, CategoryCountsRequest, ProductBrowseResult,
    CategoryCountsResult, ProductInfo, CategoryInfo, ProductStock,
    ProductAttributes, ProductAvailability, ProductVariant, SearchMetadata
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_dynamodb_resource():
    """Mock boto3 DynamoDB resource."""
    with patch('boto3.resource') as mock_resource:
        mock_dynamodb = Mock()
        mock_resource.return_value = mock_dynamodb
        
        # Mock products table
        mock_products_table = Mock()
        mock_inventory_table = Mock()
        
        mock_dynamodb.Table.side_effect = lambda name: {
            'EcommerceApp-Products': mock_products_table,
            'EcommerceApp-Inventory': mock_inventory_table
        }.get(name, Mock())
        
        yield {
            'dynamodb': mock_dynamodb,
            'products_table': mock_products_table,
            'inventory_table': mock_inventory_table
        }


@pytest.fixture
def sample_product_data():
    """Sample product data for testing."""
    return {
        'productID': 'product-fruits-001',
        'productCode': 'APL-FRU-001',
        'name': 'Apples',
        'description': 'Fresh Red Apples',
        'category': 'fruits',
        'unit': 'kg',
        'isActive': True,
        'status': 'active',
        'hasVariants': True,
        'pricing': {
            'sellingPrice': Decimal('150.50'),
            'basePrice': Decimal('120.00'),
            'discountPrice': Decimal('140.00'),
            'costPrice': Decimal('100.00')
        },
        'inventory': {
            'trackInventory': True,
            'minStock': Decimal('10'),
            'maxStock': Decimal('500'),
            'sku': 'APL-FRU-001-SKU'
        },
        'variants': [
            {
                'variantID': 'product-fruits-001-variant-1',
                'variantName': 'Red Apples',
                'variantCode': 'APL-FRU-001-RED',
                'isActive': True,
                'pricing': {
                    'sellingPrice': Decimal('150.50'),
                    'basePrice': Decimal('120.00')
                },
                'inventory': {
                    'trackInventory': True,
                    'sku': 'APL-FRU-001-RED-SKU'
                },
                'attributes': {
                    'color': 'Red',
                    'size': 'Medium'
                }
            }
        ],
        'attributes': {
            'organic': False,
            'brand': 'FreshFarm'
        },
        'tags': ['fruits', 'fresh', 'healthy']
    }


@pytest.fixture
def sample_inventory_data():
    """Sample inventory data for testing."""
    return [
        {
            'productID': 'product-fruits-001',
            'productName': 'Apples',
            'category': 'fruits',
            'availableStock': Decimal('100'),
            'currentStock': Decimal('120'),
            'reservedStock': Decimal('20'),
            'storageLocation': 'warehouse-A',
            'batchNumber': 'BATCH-001',
            'expiryDate': '2024-12-01T00:00:00Z',
            'unitCost': Decimal('100.00')
        },
        {
            'productID': 'product-fruits-001',
            'productName': 'Apples',
            'category': 'fruits',
            'availableStock': Decimal('200'),
            'currentStock': Decimal('220'),
            'reservedStock': Decimal('20'),
            'storageLocation': 'warehouse-B',
            'batchNumber': 'BATCH-002',
            'expiryDate': '2024-11-15T00:00:00Z',
            'unitCost': Decimal('95.00')
        }
    ]


@pytest.fixture
def sample_browse_request():
    """Sample product browse request."""
    return ProductBrowseRequest(
        category='fruits',
        search_term=None,
        max_results=10,
        include_out_of_stock=True,
        min_price=None,
        max_price=None
    )


@pytest.fixture
def sample_category_counts_request():
    """Sample category counts request."""
    return CategoryCountsRequest()


@pytest.fixture
def sample_product_info():
    """Sample ProductInfo object."""
    return ProductInfo(
        product_id='product-fruits-001',
        product_code='APL-FRU-001',
        name='Apples',
        description='Fresh Red Apples',
        category='Fruits',
        price=150.50,
        unit='kg',
        stock=ProductStock(
            available=350,
            status='In Stock',
            track_inventory=True
        ),
        variants=[
            ProductVariant(
                variant_id='product-fruits-001-variant-1',
                name='Red Apples',
                attributes={'color': 'Red', 'size': 'Medium'},
                price=150.50,
                stock_available=50
            )
        ],
        has_variants=True,
        attributes=ProductAttributes(
            organic=False,
            brand='FreshFarm',
            perishable=True
        ),
        availability=ProductAvailability(
            is_active=True,
            status='active',
            b2c_available=True
        )
    )


@pytest.fixture
def sample_category_info():
    """Sample CategoryInfo objects."""
    return [
        CategoryInfo(name='Fruits', count=10, percentage=40.0),
        CategoryInfo(name='Vegetables', count=8, percentage=32.0),
        CategoryInfo(name='Dairy', count=5, percentage=20.0),
        CategoryInfo(name='Grains', count=2, percentage=8.0)
    ]


@pytest.fixture
def ecommerce_service_with_mocks(mock_dynamodb_resource):
    """EcommerceService with mocked DynamoDB."""
    with patch('src.services.ecommerce_service.boto3.resource') as mock_boto3:
        mock_boto3.return_value = mock_dynamodb_resource['dynamodb']
        service = EcommerceService()
        service.products_table = mock_dynamodb_resource['products_table']
        service.inventory_table = mock_dynamodb_resource['inventory_table']
        yield service


@pytest.fixture
def mock_scan_products_response(sample_product_data):
    """Mock scan response for products table."""
    return {
        'Items': [sample_product_data],
        'Count': 1,
        'ScannedCount': 1
    }


@pytest.fixture
def mock_scan_inventory_response(sample_inventory_data):
    """Mock scan response for inventory table."""
    return {
        'Items': sample_inventory_data,
        'Count': len(sample_inventory_data),
        'ScannedCount': len(sample_inventory_data)
    }


@pytest.fixture
def mock_multiple_products():
    """Mock data for multiple products."""
    return {
        'Items': [
            {
                'productID': 'product-fruits-001',
                'name': 'Apples',
                'category': 'fruits',
                'pricing': {'sellingPrice': Decimal('150.50')},
                'unit': 'kg',
                'isActive': True,
                'status': 'active',
                'inventory': {'trackInventory': True, 'maxStock': Decimal('500')}
            },
            {
                'productID': 'product-fruits-002',
                'name': 'Bananas',
                'category': 'fruits',
                'pricing': {'sellingPrice': Decimal('80.00')},
                'unit': 'dozen',
                'isActive': True,
                'status': 'active',
                'inventory': {'trackInventory': True, 'maxStock': Decimal('300')}
            },
            {
                'productID': 'product-vegetables-001',
                'name': 'Carrots',
                'category': 'vegetables',
                'pricing': {'sellingPrice': Decimal('120.00')},
                'unit': 'kg',
                'isActive': True,
                'status': 'active',
                'inventory': {'trackInventory': True, 'maxStock': Decimal('200')}
            }
        ]
    }
