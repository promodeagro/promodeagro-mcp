#!/usr/bin/env python3

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.services.ecommerce_service import EcommerceService
from src.models.ecommerce_models import ProductBrowseRequest, CategoryCountsRequest

async def show_catalog():
    service = EcommerceService()
    
    print('🏪 Aurora Spark E-commerce Product Catalog')
    print('=' * 50)
    
    # Get category counts
    print('\n📊 Product Categories:')
    cat_request = CategoryCountsRequest()
    categories = await service.get_category_counts(cat_request)
    
    for cat in categories.categories:
        print(f'  • {cat.name}: {cat.count} products ({cat.percentage:.1f}%)')
    print(f'  Total Products: {categories.total_products}')
    
    # Sample products from each category
    print('\n🛒 Sample Products by Category:')
    
    for cat in categories.categories[:3]:  # Show first 3 categories
        print(f'\n--- {cat.name} ---')
        browse_req = ProductBrowseRequest(category=cat.name.lower(), max_results=3)
        products = await service.browse_products(browse_req)
        
        for product in products.products:
            stock_status = '✅ In Stock' if product.stock.status == 'In Stock' else '❌ Out of Stock'
            organic_label = '🌱 Organic' if product.attributes.organic else ''
            print(f'  📦 {product.name}')
            print(f'     💰 ${product.price:.2f}/{product.unit} | {stock_status} ({product.stock.available} available) {organic_label}')
            if product.description:
                print(f'     📝 {product.description[:80]}...')

if __name__ == "__main__":
    asyncio.run(show_catalog())
