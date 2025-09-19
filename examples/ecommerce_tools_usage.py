#!/usr/bin/env python3
"""
Example usage of the new E-commerce MCP Tools (Standardized Implementation)

This demonstrates the standardized Tool and Service composition pattern:
- Tools: browse-products, get-category-counts  
- Models: ProductBrowseRequest, CategoryCountsRequest, ProductBrowseResult, CategoryCountsResult
- Service: EcommerceService with business logic
- Architecture: Same pattern as site_analysis_tools.py

Available via:
1. FastMCP server (src/server.py) - MCP Protocol  
2. HTTP transport server (mcp_http_server.py) - REST API + MCP over HTTP
"""

import asyncio
import json
import httpx
from datetime import datetime


async def test_browse_products_http():
    """Test the browse-products tool via HTTP transport."""
    print("=" * 60)
    print("🛒 Testing browse-products via HTTP Transport")
    print("=" * 60)
    
    # Example 1: Browse all products
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/tools/browse-products",
                json={
                    "max_results": 10,
                    "include_out_of_stock": True
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Browse all products (first 10):")
                print(f"   Total found: {result['result']['total_found']}")
                print(f"   Categories: {result['result']['categories']['available_categories']}")
                
                for product in result['result']['products'][:3]:  # Show first 3
                    print(f"   • {product['name']} - ₹{product['price']}/{product['unit']}")
                    print(f"     Stock: {product['stock']['available']} ({product['stock']['status']})")
                    if product['variants']:
                        print(f"     Variants: {len(product['variants'])} available")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ HTTP Error: {str(e)}")
    
    print()
    
    # Example 2: Search for specific products
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/tools/browse-products",
                json={
                    "search_term": "rice",
                    "max_results": 5,
                    "include_out_of_stock": False
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print("🔍 Search results for 'rice' (in stock only):")
                print(f"   Found: {result['result']['total_found']} products")
                
                for product in result['result']['products']:
                    print(f"   • {product['name']} - ₹{product['price']}/{product['unit']}")
                    print(f"     Category: {product['category']}")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ HTTP Error: {str(e)}")


async def test_category_counts_http():
    """Test the get-category-counts tool via HTTP transport."""
    print("\n" + "=" * 60)
    print("📊 Testing get-category-counts via HTTP Transport")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/tools/get-category-counts",
                json={},
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print("📈 Category Distribution:")
                print(f"   Total Products: {result['result']['total_products']}")
                print(f"   Total Categories: {result['result']['total_categories']}")
                print()
                
                for category in result['result']['categories'][:5]:  # Show top 5
                    print(f"   📂 {category['name']}: {category['count']} products ({category['percentage']}%)")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ HTTP Error: {str(e)}")


async def test_mcp_protocol():
    """Test the tools via MCP protocol."""
    print("\n" + "=" * 60)
    print("🔧 Testing via MCP Protocol")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        try:
            # List available tools
            response = await client.post(
                "http://localhost:8000/mcp/request",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list"
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                tools = result['result']['tools']
                ecommerce_tools = [t for t in tools if 'product' in t['name'].lower() or 'category' in t['name'].lower()]
                
                print("🛠️  Available E-commerce MCP Tools:")
                for tool in ecommerce_tools:
                    print(f"   • {tool['name']}: {tool['description']}")
                    
            # Test browse-products via MCP
            response = await client.post(
                "http://localhost:8000/mcp/request",
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "browse-products",
                        "arguments": {
                            "category": "vegetables",
                            "max_results": 3,
                            "include_out_of_stock": True
                        }
                    }
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n🥬 MCP Call Result (vegetables category):")
                # The result is wrapped in MCP format, extract the actual data
                content = result['result']['content'][0]['text']
                data = json.loads(content)
                print(f"   Found {data['total_found']} vegetables")
                for product in data['products'][:2]:  # Show first 2
                    print(f"   • {product['name']} - ₹{product['price']}")
            else:
                print(f"❌ MCP Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ MCP Error: {str(e)}")


async def main():
    """Main function to run all tests."""
    print("🚀 E-commerce MCP Tools Testing")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("📋 Prerequisites:")
    print("   1. MCP HTTP server running on http://localhost:8000")
    print("   2. AWS credentials configured for DynamoDB access")
    print("   3. AuroraSparkTheme-Products table populated")
    print()
    print("🏗️  Standardized Architecture:")
    print("   📁 src/models/ecommerce_models.py - Request/Response models")
    print("   ⚙️  src/services/ecommerce_service.py - Business logic service")
    print("   🔧 src/tools/ecommerce_tools.py - MCP tool implementations")
    print("   📡 mcp_http_server.py - HTTP transport wrappers")
    print()
    
    try:
        # Test health endpoint first
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health", timeout=10.0)
            if response.status_code == 200:
                health = response.json()
                print(f"✅ Server Status: {health['status']}")
                print(f"   Tools Available: {health['tools_available']}")
                print()
            else:
                print("❌ Server not responding. Please start the MCP server first:")
                print("   python3 mcp_http_server.py")
                return
        
        # Run all tests
        await test_browse_products_http()
        await test_category_counts_http() 
        await test_mcp_protocol()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
