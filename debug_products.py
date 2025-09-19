#!/usr/bin/env python3

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.services.ecommerce_service import EcommerceService
from src.models.ecommerce_models import ProductBrowseRequest

async def debug_products():
    print("🔍 Debug: Testing product structure...")
    
    service = EcommerceService()
    request = ProductBrowseRequest(max_results=3, category="vegetables")
    
    try:
        result = await service.browse_products(request)
        
        print(f"✅ Got {len(result.products)} products")
        
        for i, product in enumerate(result.products[:2]):
            print(f"\n📦 Product {i+1}:")
            print(f"  - ID: {product.product_id}")
            print(f"  - Name: {product.name}")
            print(f"  - Category: {product.category}")
            print(f"  - Price: ${product.price}")
            print(f"  - Unit: {product.unit}")
            print(f"  - Stock: {product.stock}")
            print(f"    - Available: {product.stock.available}")
            print(f"    - Status: {product.stock.status}")
            print(f"  - Attributes: {product.attributes}")
            print(f"  - Availability: {product.availability}")
            
            # Check if attributes exist
            attrs = dir(product)
            problematic_attrs = [attr for attr in attrs if 'stock_quantity' in attr or 'in_stock' in attr]
            if problematic_attrs:
                print(f"  ⚠️  Found problematic attributes: {problematic_attrs}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_products())
