#!/usr/bin/env python3
"""
Products CLI - Manage Products in DynamoDB
Connects to AWS DynamoDB Products table and manages product data
"""

import boto3
import sys
import json
import uuid
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional


class ProductsCLI:
    """CLI for managing Products in DynamoDB"""
    
    def __init__(self, region_name: str = 'ap-south-1'):
        """
        Initialize Products CLI
        
        Args:
            region_name: AWS region (default: ap-south-1)
        """
        self.region_name = region_name
        self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
        
        # Connect to tables
        self.table_name = 'Products'
        self.products_table = self.dynamodb.Table(self.table_name)
        self.categories_table = self.dynamodb.Table('Category_management')
        self.units_table = self.dynamodb.Table('Unit_management')
        self.adjustments_table = self.dynamodb.Table('Stock_adjustment')
        self.pincodes_table = self.dynamodb.Table('Pincode_management')
        self.delivery_types_table = self.dynamodb.Table('Delivery_types')
        self.delivery_slots_table = self.dynamodb.Table('Delivery_slots')
        self.customers_table = self.dynamodb.Table('Customers')
        self.orders_table = self.dynamodb.Table('Orders')
    
    def test_connection(self) -> bool:
        """Test connection to DynamoDB table"""
        try:
            # Try to describe the table
            response = self.products_table.meta.client.describe_table(TableName=self.table_name)
            table_status = response['Table']['TableStatus']
            
            print(f"\n📊 Table Status: {table_status}")
            print(f"📊 Table ARN: {response['Table']['TableArn']}")
            print(f"📊 Item Count: {response['Table'].get('ItemCount', 'N/A')}")
            
            if table_status == 'ACTIVE':
                print("✅ Connection successful! Table is active and ready.")
                return True
            else:
                print(f"⚠️  WARNING: Table status is '{table_status}', not ACTIVE")
                return False
                
        except ClientError as e:
            print(f"❌ ERROR: {e}")
            return False
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return False
    
    def get_table_info(self):
        """Get detailed information about the Products table"""
        try:
            response = self.products_table.meta.client.describe_table(TableName=self.table_name)
            table = response['Table']
            
            print("\n" + "=" * 80)
            print("📋 PRODUCTS TABLE INFORMATION")
            print("=" * 80)
            print(f"Table Name: {table['TableName']}")
            print(f"Table Status: {table['TableStatus']}")
            print(f"Table ARN: {table['TableArn']}")
            print(f"Creation Date: {table['CreationDateTime']}")
            print(f"Item Count: {table.get('ItemCount', 0)}")
            
            # Key Schema
            print(f"\n🔑 Primary Key:")
            for key in table['KeySchema']:
                print(f"   - {key['AttributeName']} ({key['KeyType']})")
            
            # Attribute Definitions
            print(f"\n📝 Attributes:")
            for attr in table.get('AttributeDefinitions', []):
                print(f"   - {attr['AttributeName']}: {attr['AttributeType']}")
            
            # Capacity Mode
            billing_mode = table.get('BillingModeSummary', {}).get('BillingMode', 'PROVISIONED')
            print(f"\n💰 Billing Mode: {billing_mode}")
            
            if billing_mode == 'PROVISIONED':
                provisioned = table.get('ProvisionedThroughput', {})
                print(f"   Read Capacity: {provisioned.get('ReadCapacityUnits', 'N/A')}")
                print(f"   Write Capacity: {provisioned.get('WriteCapacityUnits', 'N/A')}")
            else:
                print("   On-Demand (pay per request)")
            
            print("=" * 80)
            
        except ClientError as e:
            print(f"❌ ERROR: {e}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    def calculate_product_status(self, stock: int, low_stock_alert: int) -> str:
        """Calculate product status based on stock"""
        if stock == 0:
            return 'out-of-stock'
        elif low_stock_alert > 0 and stock <= low_stock_alert:
            return 'low-stock'
        else:
            return 'in-stock'

    def convert_variant_qty_to_parent_unit(self, qty_str: str, variant_unit: str, parent_unit: str) -> float:
        """Convert variant sell quantity into parent unit quantity.
        Supports common weight and volume units; defaults to 1:1 if unknown.
        """
        try:
            qty = float(qty_str or '0')
        except ValueError:
            qty = 0.0

        if qty <= 0:
            return 0.0

        v = (variant_unit or '').strip().lower()
        p = (parent_unit or '').strip().lower()

        # Weight conversions to kg
        weight_to_kg = {
            'kg': 1.0,
            'kilogram': 1.0,
            'g': 0.001,
            'gram': 0.001,
            'grams': 0.001,
            'gms': 0.001,  # Common abbreviation for grams
        }

        # Volume conversions to liter
        volume_to_l = {
            'l': 1.0,
            'liter': 1.0,
            'litre': 1.0,
            'ml': 0.001,
            'milliliter': 0.001,
            'millilitre': 0.001,
        }

        if v in weight_to_kg and p in weight_to_kg:
            qty_in_kg = qty * weight_to_kg[v]
            return qty_in_kg / weight_to_kg[p]

        if v in volume_to_l and p in volume_to_l:
            qty_in_l = qty * volume_to_l[v]
            return qty_in_l / volume_to_l[p]

        # Fallback: treat as same unit
        return qty
    
    def create_product(self):
        """Create a new product with variants (interactive)"""
        print("\n" + "=" * 80)
        print("➕ CREATE NEW PRODUCT")
        print("=" * 80)
        
        try:
            # Get parent product data
            print("\n📦 PARENT PRODUCT INFORMATION:")
            print("-" * 80)
            
            # Required fields
            name = input("Product Name *: ").strip()
            if not name:
                print("❌ ERROR: Product Name is required!")
                return False
            
            # Get categories from DynamoDB
            categories = self.get_categories()
            if not categories:
                print("❌ ERROR: No categories found! Please create a category first.")
                return False
            
            # Show categories for selection
            print("\n📋 Available Categories:")
            active_categories = [cat for cat in categories if cat.get('isActive', True)]
            for idx, cat in enumerate(active_categories, 1):
                print(f"   {idx}. {cat.get('name', 'N/A')}")
            
            category_choice = input("\nSelect Category (enter number) *: ").strip()
            try:
                category_index = int(category_choice) - 1
                if 0 <= category_index < len(active_categories):
                    selected_category = active_categories[category_index]
                    category = selected_category.get('name', '')
                else:
                    print("❌ ERROR: Invalid category selection!")
                    return False
            except ValueError:
                print("❌ ERROR: Please enter a valid number!")
                return False
            
            # Get subcategories for selected category
            subcategories = selected_category.get('subcategories', [])
            if not subcategories:
                print("❌ ERROR: No subcategories found for this category!")
                return False
            
            # Show subcategories for selection
            print("\n📋 Available Sub Categories:")
            for idx, sub in enumerate(subcategories, 1):
                print(f"   {idx}. {sub}")
            
            subcategory_choice = input("\nSelect Sub Category (enter number) *: ").strip()
            try:
                subcategory_index = int(subcategory_choice) - 1
                if 0 <= subcategory_index < len(subcategories):
                    sub_category = subcategories[subcategory_index]
                else:
                    print("❌ ERROR: Invalid subcategory selection!")
                    return False
            except ValueError:
                print("❌ ERROR: Please enter a valid number!")
                return False
            
            print("\nStock Mode options: 'parent' or 'variant'")
            stock_mode = input("Stock Mode * (parent/variant): ").strip().lower()
            if stock_mode not in ['parent', 'variant']:
                print("❌ ERROR: Stock Mode must be 'parent' or 'variant'!")
                return False
            
            # Optional fields with defaults
            description = input("Description (optional): ").strip() or ""
            tags_input = input("Tags (comma-separated, optional): ").strip()
            tags = [tag.strip() for tag in tags_input.split(',')] if tags_input else []
            
            # Get units from DynamoDB (needed for product and variants)
            units = self.get_units()
            active_units = [u for u in units if u.get('isActive', True)] if units else []
            
            if not active_units:
                print("⚠️  WARNING: No active units found! Using default 'kg'")
                # Create a default unit entry for later use
                active_units = [{'name': 'Kilogram', 'symbol': 'kg'}]
            else:
                default_unit = active_units[0].get('symbol', 'kg')
            
            if stock_mode == 'parent':
                print("\nOpening Stock Quantity:")
                stock_input = input("  Quantity (default: 0): ").strip()
                stock = int(stock_input) if stock_input else 0
                
                print("\nOpening Stock Quantity Unit:")
                for idx, u in enumerate(active_units, 1):
                    print(f"   {idx}. {u.get('name', 'N/A')} ({u.get('symbol', 'N/A')})")
                unit_choice = input("\nSelect Unit (enter number, default: 1) *: ").strip()
                try:
                    if unit_choice:
                        unit_index = int(unit_choice) - 1
                        if 0 <= unit_index < len(active_units):
                            unit = active_units[unit_index].get('symbol', 'kg')
                        else:
                            print("⚠️  WARNING: Invalid selection, using first unit")
                            unit = active_units[0].get('symbol', 'kg')
                    else:
                        unit = active_units[0].get('symbol', 'kg')
                except ValueError:
                    print("⚠️  WARNING: Invalid input, using first unit")
                    unit = active_units[0].get('symbol', 'kg')
            else:
                stock = 0
                unit = ""
            
            # B2C Sell Unit (required) - Use units from DynamoDB
            b2c_qty = input("Sell Unit in B2C - Quantity *: ").strip()
            if not b2c_qty:
                print("❌ ERROR: Sell Unit in B2C (Quantity) is required!")
                return False
            
            # Show units for B2C selection
            print("\n📋 Available Units for B2C:")
            for idx, u in enumerate(active_units, 1):
                print(f"   {idx}. {u.get('name', 'N/A')} ({u.get('symbol', 'N/A')})")
            
            b2c_unit_choice = input("\nSelect B2C Unit (enter number, default: 1) *: ").strip()
            try:
                if b2c_unit_choice:
                    b2c_unit_index = int(b2c_unit_choice) - 1
                    if 0 <= b2c_unit_index < len(active_units):
                        b2c_unit = active_units[b2c_unit_index].get('symbol', 'kg')
                    else:
                        print("⚠️  WARNING: Invalid selection, using first unit")
                        b2c_unit = active_units[0].get('symbol', 'kg')
                else:
                    b2c_unit = active_units[0].get('symbol', 'kg')
            except ValueError:
                print("⚠️  WARNING: Invalid input, using first unit")
                b2c_unit = active_units[0].get('symbol', 'kg')
            
            # Pricing
            purchase_price = input("Purchase Price (₹, default: 0): ").strip() or "0"
            sale_price = input("Sale Price (₹, default: 0): ").strip() or "0"
            compare_price = input("Compare Price (₹, default: 0): ").strip() or "0"
            
            # Stock alerts
            low_stock_alert = input("Low Stock Alert (default: 0): ").strip() or "0"
            expiry_date = input("Expiry Date (YYYY-MM-DD, optional): ").strip() or ""
            
            # B2C Status
            on_b2c_input = input("Publish to B2C Portal? (y/n, default: y): ").strip().lower()
            on_b2c = on_b2c_input != 'n'
            
            # Images (optional)
            images_input = input("Product Images URLs (comma-separated, optional): ").strip()
            images = [img.strip() for img in images_input.split(',')] if images_input else []
            
            # Generate product ID
            product_id = self.generate_product_id()
            
            # Calculate status
            status = self.calculate_product_status(int(stock), int(low_stock_alert))
            
            # Get variants
            variants = []
            print("\n" + "-" * 80)
            add_variants = input("Add variants? (y/n, default: n): ").strip().lower()
            
            if add_variants == 'y':
                variant_count = 1
                while True:
                    print(f"\n📦 VARIANT {variant_count}:")
                    # Prefill variant name with parent name; allow edit or Enter to accept
                    variant_name_input = input(f"  Variant Name (default: {name}) (or 'done' to finish): ").strip()
                    if variant_name_input.lower() == 'done':
                        break
                    variant_name = variant_name_input or name

                    
                    # Variant stock (only if stock_mode is 'variant')
                    if stock_mode == 'variant':
                        variant_qty = input(f"  Opening Stock (default: 0): ").strip() or "0"
                        # Show units for variant selection
                        print("\n  Opening Stock Quantity Unit:")
                        for idx, u in enumerate(active_units, 1):
                            print(f"     {idx}. {u.get('name', 'N/A')} ({u.get('symbol', 'N/A')})")
                        variant_unit_choice = input("\n  Select Unit (enter number, default: 1): ").strip()
                        try:
                            if variant_unit_choice:
                                variant_unit_index = int(variant_unit_choice) - 1
                                if 0 <= variant_unit_index < len(active_units):
                                    variant_unit = active_units[variant_unit_index].get('symbol', 'kg')
                                else:
                                    variant_unit = active_units[0].get('symbol', 'kg')
                            else:
                                variant_unit = active_units[0].get('symbol', 'kg')
                        except ValueError:
                            variant_unit = active_units[0].get('symbol', 'kg')
                    else:
                        variant_qty = "0"
                        variant_unit = None
                    
                    # Variant B2C Sell Unit
                    variant_b2c_qty = input(f"  Sell Unit in B2C - Quantity *: ").strip()
                    if not variant_b2c_qty:
                        print("  ❌ ERROR: Sell Unit in B2C (Quantity) is required!")
                        continue
                    
                    # Show units for variant B2C selection
                    print("\n  📋 Available Units for B2C:")
                    for idx, u in enumerate(active_units, 1):
                        print(f"     {idx}. {u.get('name', 'N/A')} ({u.get('symbol', 'N/A')})")
                    variant_b2c_unit_choice = input(f"\n  Select B2C Unit (enter number, default: {b2c_unit}): ").strip()
                    try:
                        if variant_b2c_unit_choice:
                            variant_b2c_unit_index = int(variant_b2c_unit_choice) - 1
                            if 0 <= variant_b2c_unit_index < len(active_units):
                                variant_b2c_unit = active_units[variant_b2c_unit_index].get('symbol', b2c_unit)
                            else:
                                variant_b2c_unit = b2c_unit
                        else:
                            variant_b2c_unit = b2c_unit
                    except ValueError:
                        variant_b2c_unit = b2c_unit
                    
                    # Variant pricing
                    if stock_mode == 'parent':
                        # Auto-calc using parent purchase/sale price and unit conversion
                        # Convert variant B2C quantity to parent B2C unit, then multiply by parent price
                        qty_in_parent_b2c_unit = self.convert_variant_qty_to_parent_unit(
                            variant_b2c_qty, variant_b2c_unit, b2c_unit or 'kg'
                        )
                        # Calculate price: (variant qty in parent B2C unit) * (parent price per parent B2C unit)
                        suggested_purchase = Decimal(purchase_price) * Decimal(str(qty_in_parent_b2c_unit))
                        suggested_sale = Decimal(sale_price) * Decimal(str(qty_in_parent_b2c_unit))
                        print(f"  → Suggested Purchase Price: ₹{suggested_purchase:.2f} (auto) ")
                        print(f"  → Suggested Sale Price: ₹{suggested_sale:.2f} (auto) ")
                        # Allow override; Enter keeps suggested
                        vpp_in = input(f"  Purchase Price (₹, default: {suggested_purchase:.2f}): ").strip()
                        vsp_in = input(f"  Sale Price (₹, default: {suggested_sale:.2f}): ").strip()
                        variant_purchase_price = vpp_in or f"{suggested_purchase:.2f}"
                        variant_sale_price = vsp_in or f"{suggested_sale:.2f}"
                        variant_compare_price = input(f"  Compare Price (₹, default: 0): ").strip() or "0"
                    else:
                        variant_purchase_price = input(f"  Purchase Price (₹, default: 0): ").strip() or "0"
                        variant_sale_price = input(f"  Sale Price (₹, default: 0): ").strip() or "0"
                        variant_compare_price = input(f"  Compare Price (₹, default: 0): ").strip() or "0"
                    
                    # Variant stock alerts (only if stock_mode is 'variant')
                    if stock_mode == 'variant':
                        variant_low_stock_alert = input(f"  Low Stock Alert (default: 0): ").strip() or "0"
                        variant_expiry_date = input(f"  Expiry Date (YYYY-MM-DD, optional): ").strip() or ""
                    else:
                        variant_low_stock_alert = "0"
                        variant_expiry_date = ""
                    
                    # Variant B2C Status (default inherits from parent)
                    parent_default = 'y' if on_b2c else 'n'
                    variant_on_b2c_input = input(f"  Publish to B2C Portal? (y/n, default: {parent_default}): ").strip().lower()
                    if variant_on_b2c_input == '':
                        variant_on_b2c = on_b2c
                    else:
                        variant_on_b2c = (variant_on_b2c_input == 'y')
                    
                    # Variant images
                    variant_images_input = input(f"  Variant Images URLs (comma-separated, optional): ").strip()
                    variant_images = [img.strip() for img in variant_images_input.split(',')] if variant_images_input else []
                    
                    # Create variant object (organized in logical order)
                    variant = {
                        # ID and Basic Information
                        'id': self.generate_variant_id(product_id, variant_count),
                        'name': variant_name,
                        'category': category,
                        'subCategory': sub_category,
                        'isVariant': True,
                        
                        # Stock Information
                        'stock': int(variant_qty),
                        'b2cQty': variant_b2c_qty,
                        'b2cUnit': variant_b2c_unit,
                        'lowStockAlert': int(variant_low_stock_alert),
                        
                        # Pricing
                        'purchasePrice': Decimal(variant_purchase_price),
                        'salePrice': Decimal(variant_sale_price),
                        'comparePrice': Decimal(variant_compare_price),
                        
                        # Status
                        'onB2C': variant_on_b2c
                    }
                    
                    # Only add optional fields if they have values
                    if stock_mode == 'variant':
                        variant['lowStockAlert'] = int(variant_low_stock_alert)
                        if variant_unit:
                            variant['unit'] = variant_unit
                        if variant_expiry_date:
                            variant['expiryDate'] = variant_expiry_date
                        if variant_images:
                            variant['images'] = variant_images
                        if tags:
                            variant['tags'] = tags
                    if variant_expiry_date:
                        variant['expiryDate'] = variant_expiry_date
                    if variant_images:
                        variant['images'] = variant_images
                    if tags:
                        variant['tags'] = tags
                    
                    variants.append(variant)
                    variant_count += 1
            
            # Create parent product object (DynamoDB format - single item with variants array)
            # Organized in logical order: ID, Basic Info, Stock Info, Pricing, Status, Optional, Variants
            product_data = {
                # ID and Basic Information
                'productID': product_id,
                'name': name,
                'category': category,
                'subCategory': sub_category,
                'isVariant': False,
                
                # Stock Information
                'stockMode': stock_mode,
                'stock': int(stock),
                **({'unit': unit} if unit else {}),
                'b2cQty': b2c_qty,
                'b2cUnit': b2c_unit,
                'lowStockAlert': int(low_stock_alert),
                
                # Pricing
                'purchasePrice': Decimal(purchase_price),
                'salePrice': Decimal(sale_price),
                'comparePrice': Decimal(compare_price),
                
                # Status and Metadata
                'onB2C': on_b2c,
                'status': status,
                'lastUpdated': datetime.now(timezone.utc).isoformat().split('T')[0],
                'createdAt': datetime.now(timezone.utc).isoformat(),
                
                # Variants
                'variants': variants  # Variants array in DynamoDB format
            }
            
            # Only add optional fields if they have values (added at the end)
            if expiry_date:
                product_data['expiryDate'] = expiry_date
            if description:
                product_data['description'] = description
            if tags:
                product_data['tags'] = tags
            if images:
                product_data['images'] = images
            
            # Store in DynamoDB
            print("\n" + "-" * 80)
            print("💾 Saving to DynamoDB...")
            print("-" * 80)
            
            self.products_table.put_item(Item=product_data)
            
            print(f"\n✅ Product '{name}' created successfully!")
            print(f"🔑 Product ID: {product_id}")
            print(f"📦 Variants: {len(variants)}")
            print(f"📊 Status: {status}")
            
            return True
            
        except ValueError as e:
            print(f"❌ ERROR: Invalid input - {e}")
            return False
        except ClientError as e:
            print(f"❌ ERROR: DynamoDB error - {e}")
            return False
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def main_menu(self):
        """Display main menu and handle user selection"""
        while True:
            print("\n" + "=" * 80)
            print("🏭 PRODUCTS CLI - Main Menu")
            print("=" * 80)
            print("\n📋 AVAILABLE OPTIONS:")
            print("-" * 80)
            print("1. 📦 Product Management")
            print("2. 🏷️  Category Management")
            print("3. 📏 Unit Management")
            print("4. 📊 Stock Adjustment Management")
            print("5. 📍 Pincode Management")
            print("6. 🛒 Order Management")
            print("0. ⬅️  Exit")
            print("-" * 80)
            
            choice = input("\nSelect an option (0-6): ").strip()
            
            if choice == '0':
                print("\n👋 Thank you for using Products CLI!")
                print("Goodbye!")
                break
            elif choice == '1':
                self.product_management_menu()
            elif choice == '2':
                self.category_management_menu()
            elif choice == '3':
                self.unit_management_menu()
            elif choice == '4':
                self.stock_adjustment_menu()
            elif choice == '5':
                self.pincode_management_menu()
            elif choice == '6':
                self.order_management_menu()
            else:
                print("❌ ERROR: Invalid choice. Please select a number between 0-6.")
                input("\nPress Enter to continue...")
    
    def product_management_menu(self):
        """Product management menu"""
        while True:
            print("\n" + "=" * 80)
            print("📦 PRODUCT MANAGEMENT")
            print("=" * 80)
            print("\n📋 AVAILABLE OPTIONS:")
            print("-" * 80)
            print("1. ➕ Create Product (with variants)")
            print("2. 📋 List All Products")
            print("3. 🔍 Search Products")
            print("4. 🔎 Get Product by ID")
            print("5. ✏️  Update Product")
            print("6. 🗑️  Delete Product")
            print("7. 📊 View Table Information")
            print("0. ⬅️  Back to Main Menu")
            print("-" * 80)
            
            choice = input("\nSelect an option (0-7): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.create_product()
                input("\nPress Enter to continue...")
            elif choice == '2':
                self.list_products()
                input("\nPress Enter to continue...")
            elif choice == '3':
                self.search_products()
                input("\nPress Enter to continue...")
            elif choice == '4':
                product_id = input("\nEnter Product ID: ").strip()
                if product_id:
                    self.get_product_by_id(product_id)
                else:
                    print("❌ ERROR: Product ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '5':
                product_id = input("\nEnter Product ID to update: ").strip()
                if product_id:
                    self.update_product(product_id)
                else:
                    print("❌ ERROR: Product ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '6':
                product_id = input("\nEnter Product ID to delete: ").strip()
                if product_id:
                    self.delete_product(product_id)
                else:
                    print("❌ ERROR: Product ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '7':
                self.get_table_info()
                input("\nPress Enter to continue...")
            else:
                print("❌ ERROR: Invalid choice. Please select a number between 0-7.")
                input("\nPress Enter to continue...")

    def list_products(self):
        """List all products"""
        print("\n" + "=" * 80)
        print("📋 LIST ALL PRODUCTS")
        print("=" * 80)
        
        try:
            # Scan all items from DynamoDB
            response = self.products_table.scan()
            products = response.get('Items', [])
            
            if not products:
                print("\n📦 No products found in the database.")
                return
            
            print(f"\n📊 Total Products: {len(products)}")
            print("-" * 80)
            
            for idx, product in enumerate(products, 1):
                product_id = product.get('productID', 'N/A')
                name = product.get('name', 'N/A')
                category = product.get('category', 'N/A')
                sub_category = product.get('subCategory', 'N/A')
                stock_mode = product.get('stockMode', 'N/A')
                stock = product.get('stock', 0)
                unit = product.get('unit', '')
                b2c_qty = product.get('b2cQty', 'N/A')
                b2c_unit = product.get('b2cUnit', 'N/A')
                purchase_price = product.get('purchasePrice', 0)
                sale_price = product.get('salePrice', 0)
                compare_price = product.get('comparePrice', 0)
                low_stock_alert = product.get('lowStockAlert', 0)
                status = product.get('status', 'N/A')
                on_b2c = 'Yes' if product.get('onB2C', False) else 'No'
                last_updated = product.get('lastUpdated', 'N/A')
                created_at = product.get('createdAt', 'N/A')
                expiry_date = product.get('expiryDate')
                description = product.get('description')
                tags = product.get('tags', [])
                images = product.get('images', [])
                variants = product.get('variants', [])
                
                print(f"\n{idx}. Product ID: {product_id}")
                print(f"   Name: {name}")
                print(f"   Category: {category} > {sub_category}")
                print(f"   Stock Mode: {stock_mode}")
                print(f"   Opening Stock: {stock} {unit}")
                print(f"   Sell Unit (B2C): {b2c_qty} {b2c_unit}")
                print(f"   Purchase Price: ₹{Decimal(purchase_price)}")
                print(f"   Sale Price: ₹{Decimal(sale_price)}")
                print(f"   Compare Price: ₹{Decimal(compare_price)}")
                print(f"   Low Stock Alert: {low_stock_alert}")
                print(f"   Status: {status}")
                print(f"   Published to B2C: {on_b2c}")
                print(f"   Last Updated: {last_updated}")
                print(f"   Created At: {created_at}")
                if expiry_date:
                    print(f"   Expiry Date: {expiry_date}")
                if description:
                    print(f"   Description: {description}")
                if tags:
                    print(f"   Tags: {', '.join(tags)}")
                if images:
                    print(f"   Images ({len(images)}):")
                    for img_idx, img in enumerate(images, 1):
                        print(f"      {img_idx}. {img}")
                print(f"   Variants: {len(variants)}")
                
                if variants:
                    for v_idx, variant in enumerate(variants, 1):
                        print(f"      → Variant {v_idx}:")
                        print(f"         ID: {variant.get('id', 'N/A')}")
                        print(f"         Name: {variant.get('name', 'N/A')}")
                        if 'stock' in variant:
                            print(f"         Opening Stock: {variant.get('stock', 0)} {variant.get('unit', '')}")
                        else:
                            print(f"         Opening Stock: --")
                        print(f"         B2C Sell Unit: {variant.get('b2cQty', 'N/A')} {variant.get('b2cUnit', 'N/A')}")
                        print(f"         Purchase Price: ₹{Decimal(variant.get('purchasePrice', 0))}")
                        print(f"         Sale Price: ₹{Decimal(variant.get('salePrice', 0))}")
                        print(f"         Compare Price: ₹{Decimal(variant.get('comparePrice', 0))}")
                        if 'lowStockAlert' in variant:
                            print(f"         Low Stock Alert: {variant.get('lowStockAlert', 0)}")
                        else:
                            print(f"         Low Stock Alert: --")
                        print(f"         Published to B2C: {'Yes' if variant.get('onB2C', False) else 'No'}")
                        v_expiry = variant.get('expiryDate')
                        if v_expiry:
                            print(f"         Expiry Date: {v_expiry}")
                        v_images = variant.get('images', [])
                        if v_images:
                            print(f"         Images ({len(v_images)}):")
                            for img_idx, img in enumerate(v_images, 1):
                                print(f"            {img_idx}. {img}")
            
            print("\n" + "-" * 80)
            
        except ClientError as e:
            print(f"❌ ERROR: DynamoDB error - {e}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def search_products(self):
        """Search products by various criteria"""
        print("\n" + "=" * 80)
        print("🔍 SEARCH PRODUCTS")
        print("=" * 80)
        
        try:
            # Get search query
            print("\n📝 Search Options:")
            print("-" * 80)
            print("1. Search by Product Name")
            print("2. Search by Category")
            print("3. Search by Subcategory")
            print("4. Search by Tags")
            print("5. Search by Product ID")
            print("6. Search by Variant Name")
            print("0. Cancel")
            print("-" * 80)
            
            search_type = input("\nSelect search type (0-6): ").strip()
            
            if search_type == '0':
                return
            
            search_term = input("\nEnter search term: ").strip().lower()
            
            if not search_term:
                print("❌ ERROR: Search term cannot be empty!")
                return
            
            # Scan all products
            response = self.products_table.scan()
            all_products = response.get('Items', [])
            
            # Handle pagination if needed
            while 'LastEvaluatedKey' in response:
                response = self.products_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                all_products.extend(response.get('Items', []))
            
            matched_products = []
            
            if search_type == '1':
                # Search by product name
                for product in all_products:
                    name = product.get('name', '').lower()
                    if search_term in name:
                        matched_products.append(product)
            
            elif search_type == '2':
                # Search by category
                for product in all_products:
                    category = product.get('category', '').lower()
                    if search_term in category:
                        matched_products.append(product)
            
            elif search_type == '3':
                # Search by subcategory
                for product in all_products:
                    subcategory = product.get('subCategory', '').lower()
                    if search_term in subcategory:
                        matched_products.append(product)
            
            elif search_type == '4':
                # Search by tags
                for product in all_products:
                    tags = product.get('tags', [])
                    variant_tags = []
                    for variant in product.get('variants', []):
                        variant_tags.extend(variant.get('tags', []))
                    all_tags = tags + variant_tags
                    if any(search_term in tag.lower() for tag in all_tags):
                        matched_products.append(product)
            
            elif search_type == '5':
                # Search by product ID
                for product in all_products:
                    product_id = product.get('productID', '').lower()
                    if search_term in product_id:
                        matched_products.append(product)
            
            elif search_type == '6':
                # Search by variant name
                for product in all_products:
                    variants = product.get('variants', [])
                    for variant in variants:
                        variant_name = variant.get('name', '').lower()
                        if search_term in variant_name:
                            matched_products.append(product)
                            break  # Add parent once if any variant matches
            
            else:
                print("❌ ERROR: Invalid search type selected!")
                return
            
            # Display results
            if not matched_products:
                print(f"\n❌ No products found matching '{search_term}'")
                return
            
            print(f"\n✅ Found {len(matched_products)} product(s):")
            print("-" * 80)
            
            # Display results in similar format to list_products
            for idx, product in enumerate(matched_products, 1):
                product_id = product.get('productID', 'N/A')
                name = product.get('name', 'N/A')
                category = product.get('category', 'N/A')
                sub_category = product.get('subCategory', 'N/A')
                stock_mode = product.get('stockMode', 'N/A')
                stock = product.get('stock', 0)
                unit = product.get('unit', '')
                b2c_qty = product.get('b2cQty', 'N/A')
                b2c_unit = product.get('b2cUnit', 'N/A')
                purchase_price = product.get('purchasePrice', 0)
                sale_price = product.get('salePrice', 0)
                compare_price = product.get('comparePrice', 0)
                low_stock_alert = product.get('lowStockAlert', 0)
                status = product.get('status', 'N/A')
                on_b2c = 'Yes' if product.get('onB2C', False) else 'No'
                last_updated = product.get('lastUpdated', 'N/A')
                created_at = product.get('createdAt', 'N/A')
                expiry_date = product.get('expiryDate')
                description = product.get('description')
                tags = product.get('tags', [])
                images = product.get('images', [])
                variants = product.get('variants', [])
                
                print(f"\n{idx}. Product ID: {product_id}")
                print(f"   Name: {name}")
                print(f"   Category: {category} > {sub_category}")
                print(f"   Stock Mode: {stock_mode}")
                if unit:
                    print(f"   Opening Stock: {stock} {unit}")
                else:
                    print(f"   Opening Stock: {stock}")
                print(f"   Sell Unit (B2C): {b2c_qty} {b2c_unit}")
                print(f"   Purchase Price: ₹{Decimal(purchase_price)}")
                print(f"   Sale Price: ₹{Decimal(sale_price)}")
                print(f"   Compare Price: ₹{Decimal(compare_price)}")
                print(f"   Low Stock Alert: {low_stock_alert}")
                print(f"   Status: {status}")
                print(f"   Published to B2C: {on_b2c}")
                print(f"   Last Updated: {last_updated}")
                print(f"   Created At: {created_at}")
                if expiry_date:
                    print(f"   Expiry Date: {expiry_date}")
                if description:
                    print(f"   Description: {description}")
                if tags:
                    print(f"   Tags: {', '.join(tags)}")
                if images:
                    print(f"   Images ({len(images)}):")
                    for img_idx, img in enumerate(images, 1):
                        print(f"      {img_idx}. {img}")
                print(f"   Variants: {len(variants)}")
                
                if variants:
                    for v_idx, variant in enumerate(variants, 1):
                        print(f"      → Variant {v_idx}:")
                        print(f"         ID: {variant.get('id', 'N/A')}")
                        print(f"         Name: {variant.get('name', 'N/A')}")
                        if 'stock' in variant:
                            print(f"         Opening Stock: {variant.get('stock', 0)} {variant.get('unit', '')}")
                        else:
                            print(f"         Opening Stock: --")
                        print(f"         B2C Sell Unit: {variant.get('b2cQty', 'N/A')} {variant.get('b2cUnit', 'N/A')}")
                        print(f"         Purchase Price: ₹{Decimal(variant.get('purchasePrice', 0))}")
                        print(f"         Sale Price: ₹{Decimal(variant.get('salePrice', 0))}")
                        print(f"         Compare Price: ₹{Decimal(variant.get('comparePrice', 0))}")
                        if 'lowStockAlert' in variant:
                            print(f"         Low Stock Alert: {variant.get('lowStockAlert', 0)}")
                        else:
                            print(f"         Low Stock Alert: --")
                        print(f"         Published to B2C: {'Yes' if variant.get('onB2C', False) else 'No'}")
            
            print("\n" + "-" * 80)
            
        except ClientError as e:
            print(f"❌ ERROR: DynamoDB error - {e}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def get_product_by_id(self, product_id: str):
        """Get product details by ID"""
        print("\n" + "=" * 80)
        print(f"🔍 PRODUCT DETAILS - {product_id}")
        print("=" * 80)
        
        try:
            response = self.products_table.get_item(
                Key={'productID': product_id}
            )
            
            if 'Item' not in response:
                print(f"\n❌ Product with ID '{product_id}' not found!")
                return
            
            product = response['Item']
            
            print("\n📦 PARENT PRODUCT:")
            print("-" * 80)
            print(f"Product ID: {product.get('productID', 'N/A')}")
            print(f"Name: {product.get('name', 'N/A')}")
            print(f"Category: {product.get('category', 'N/A')}")
            print(f"Sub Category: {product.get('subCategory', 'N/A')}")
            print(f"Stock Mode: {product.get('stockMode', 'N/A')}")
            print(f"Stock: {product.get('stock', 0)} {product.get('unit', '')}")
            print(f"B2C Sell Unit: {product.get('b2cQty', 'N/A')} {product.get('b2cUnit', 'N/A')}")
            print(f"Purchase Price: ₹{Decimal(product.get('purchasePrice', 0))}")
            print(f"Sale Price: ₹{Decimal(product.get('salePrice', 0))}")
            print(f"Compare Price: ₹{Decimal(product.get('comparePrice', 0))}")
            print(f"Low Stock Alert: {product.get('lowStockAlert', 0)}")
            print(f"Status: {product.get('status', 'N/A')}")
            print(f"B2C Status: {'Active' if product.get('onB2C', False) else 'Inactive'}")
            print(f"Last Updated: {product.get('lastUpdated', 'N/A')}")
            print(f"Created At: {product.get('createdAt', 'N/A')}")
            if product.get('expiryDate'):
                print(f"Expiry Date: {product.get('expiryDate')}")
            if product.get('description'):
                print(f"Description: {product.get('description')}")
            if product.get('tags'):
                print(f"Tags: {', '.join(product.get('tags', []))}")
            if product.get('images'):
                print(f"Images ({len(product.get('images', []))}):")
                for img_idx, img in enumerate(product.get('images', []), 1):
                    print(f"  {img_idx}. {img}")
            
            variants = product.get('variants', [])
            if variants:
                print(f"\n📦 VARIANTS ({len(variants)}):")
                print("-" * 80)
                for idx, variant in enumerate(variants, 1):
                    print(f"\n  Variant {idx}:")
                    print(f"    ID: {variant.get('id', 'N/A')}")
                    print(f"    Name: {variant.get('name', 'N/A')}")
                    if 'stock' in variant:
                        print(f"    Stock: {variant.get('stock', 0)} {variant.get('unit', '')}")
                    else:
                        print(f"    Stock: --")
                    print(f"    B2C Sell Unit: {variant.get('b2cQty', 'N/A')} {variant.get('b2cUnit', 'N/A')}")
                    print(f"    Purchase Price: ₹{Decimal(variant.get('purchasePrice', 0))}")
                    print(f"    Sale Price: ₹{Decimal(variant.get('salePrice', 0))}")
                    print(f"    Compare Price: ₹{Decimal(variant.get('comparePrice', 0))}")
                    if 'lowStockAlert' in variant:
                        print(f"    Low Stock Alert: {variant.get('lowStockAlert', 0)}")
                    else:
                        print(f"    Low Stock Alert: --")
                    print(f"    B2C Status: {'Active' if variant.get('onB2C', False) else 'Inactive'}")
                    v_expiry = variant.get('expiryDate')
                    if v_expiry:
                        print(f"    Expiry Date: {v_expiry}")
                    v_images = variant.get('images', [])
                    if v_images:
                        print(f"    Images ({len(v_images)}):")
                        for img_idx, img in enumerate(v_images, 1):
                            print(f"      {img_idx}. {img}")
            else:
                print("\n📦 No variants found for this product.")
            
        except ClientError as e:
            print(f"❌ ERROR: DynamoDB error - {e}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def update_product(self, product_id: str):
        """Update an existing product"""
        print("\n" + "=" * 80)
        print(f"✏️  UPDATE PRODUCT - {product_id}")
        print("=" * 80)
        
        try:
            response = self.products_table.get_item(Key={'productID': product_id})
            if 'Item' not in response:
                print(f"\n❌ Product with ID '{product_id}' not found!")
                return False
            
            product = response['Item']
            print("\nℹ️  Leave any prompt empty to keep the current value.")
            
            # Current values
            name = product.get('name', '')
            category = product.get('category', '')
            sub_category = product.get('subCategory', '')
            stock_mode = product.get('stockMode', 'parent')
            stock = str(product.get('stock', 0))
            unit = product.get('unit', '')
            b2c_qty = str(product.get('b2cQty', ''))
            b2c_unit = product.get('b2cUnit', '')
            purchase_price = str(product.get('purchasePrice', '0'))
            sale_price = str(product.get('salePrice', '0'))
            compare_price = str(product.get('comparePrice', '0'))
            low_stock_alert = str(product.get('lowStockAlert', 0))
            on_b2c = product.get('onB2C', False)
            status = product.get('status', 'in-stock')
            description = product.get('description', '')
            expiry_date = product.get('expiryDate', '')
            tags = product.get('tags', [])
            images = product.get('images', [])
            variants = product.get('variants', [])
            
            name_input = input(f"Product Name ({name}): ").strip()
            if name_input:
                name = name_input
            
            # Category update
            categories = self.get_categories()
            active_categories = [cat for cat in categories if cat.get('isActive', True)]
            if active_categories:
                print(f"\nCurrent Category: {category} > {sub_category}")
                change_category = input("Change category? (y/n, default: n): ").strip().lower() or 'n'
                if change_category == 'y':
                    for idx, cat in enumerate(active_categories, 1):
                        print(f"   {idx}. {cat.get('name', 'N/A')}")
                    category_choice = input("Select Category (enter number): ").strip()
                    try:
                        category_index = int(category_choice) - 1
                        if 0 <= category_index < len(active_categories):
                            selected_category = active_categories[category_index]
                            category = selected_category.get('name', '')
                            subcategories = selected_category.get('subcategories', [])
                            if subcategories:
                                for idx, sub in enumerate(subcategories, 1):
                                    print(f"   {idx}. {sub}")
                                sub_choice = input("Select Sub Category (enter number): ").strip()
                                sub_index = int(sub_choice) - 1
                                if 0 <= sub_index < len(subcategories):
                                    sub_category = subcategories[sub_index]
                                else:
                                    print("⚠️  Invalid subcategory selection. Keeping previous value.")
                            else:
                                print("⚠️  Selected category has no subcategories. Keeping previous value.")
                        else:
                            print("⚠️  Invalid category selection. Keeping previous value.")
                    except ValueError:
                        print("⚠️  Invalid input. Keeping previous category.")
            
            stock_mode_input = input(f"Stock Mode (parent/variant) [{stock_mode}]: ").strip().lower()
            if stock_mode_input in ['parent', 'variant']:
                stock_mode = stock_mode_input
            
            # Units
            units = self.get_units()
            active_units = [u for u in units if u.get('isActive', True)] if units else []
            if not active_units:
                active_units = [{'name': 'Kilogram', 'symbol': 'kg'}]
            
            if stock_mode == 'parent':
                stock_input = input(f"Opening Stock Quantity [{stock}]: ").strip()
                if stock_input:
                    stock = stock_input
                
                print("\nOpening Stock Quantity Unit:")
                for idx, u in enumerate(active_units, 1):
                    indicator = " (current)" if u.get('symbol') == unit else ""
                    print(f"   {idx}. {u.get('name', 'N/A')} ({u.get('symbol', 'N/A')}){indicator}")
                unit_choice = input("Select Unit (enter number, blank to keep current): ").strip()
                if unit_choice:
                    try:
                        unit_index = int(unit_choice) - 1
                        if 0 <= unit_index < len(active_units):
                            unit = active_units[unit_index].get('symbol', 'kg')
                    except ValueError:
                        print("⚠️  Invalid input. Keeping current unit.")
                elif not unit:
                    unit = active_units[0].get('symbol', 'kg')
            else:
                stock = '0'
                unit = ''
            
            b2c_qty_input = input(f"Sell Unit in B2C - Quantity [{b2c_qty}]: ").strip()
            if b2c_qty_input:
                b2c_qty = b2c_qty_input
            
            print("\nSell Unit in B2C - Unit:")
            for idx, u in enumerate(active_units, 1):
                indicator = " (current)" if u.get('symbol') == b2c_unit else ""
                print(f"   {idx}. {u.get('name', 'N/A')} ({u.get('symbol', 'N/A')}){indicator}")
            b2c_unit_choice = input("Select B2C Unit (enter number, blank to keep current): ").strip()
            if b2c_unit_choice:
                try:
                    b2c_unit_index = int(b2c_unit_choice) - 1
                    if 0 <= b2c_unit_index < len(active_units):
                        b2c_unit = active_units[b2c_unit_index].get('symbol', 'kg')
                except ValueError:
                    print("⚠️  Invalid input. Keeping current B2C unit.")
            elif not b2c_unit:
                b2c_unit = active_units[0].get('symbol', 'kg')
            
            purchase_input = input(f"Purchase Price (₹) [{purchase_price}]: ").strip()
            if purchase_input:
                purchase_price = purchase_input
            sale_input = input(f"Sale Price (₹) [{sale_price}]: ").strip()
            if sale_input:
                sale_price = sale_input
            compare_input = input(f"Compare Price (₹) [{compare_price}]: ").strip()
            if compare_input:
                compare_price = compare_input
            low_stock_input = input(f"Low Stock Alert [{low_stock_alert}]: ").strip()
            if low_stock_input:
                low_stock_alert = low_stock_input
            
            on_b2c_input = input(f"Publish to B2C (y/n) [{'y' if on_b2c else 'n'}]: ").strip().lower()
            if on_b2c_input in ['y', 'n']:
                on_b2c = on_b2c_input == 'y'
            
            description_input = input(f"Description [{description or 'none'}]: ").strip()
            if description_input:
                description = description_input
            tags_input = input(f"Tags (comma separated) [{', '.join(tags) if tags else 'none'}]: ").strip()
            if tags_input:
                tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
            expiry_input = input(f"Expiry Date ({expiry_date or 'YYYY-MM-DD'}) (leave blank to keep): ").strip()
            if expiry_input:
                expiry_date = expiry_input
            images_input = input(f"Images URLs (comma separated) [{len(images)} current]: ").strip()
            if images_input:
                images = [img.strip() for img in images_input.split(',') if img.strip()]
            
            update_variants = input("Update variants? (y/n, default: n): ").strip().lower() or 'n'
            if update_variants == 'y':
                variants = []
                variant_count = 1
                while True:
                    print(f"\n📦 VARIANT {variant_count} (type 'done' to finish)")
                    variant_name_input = input(f"  Variant Name (default: {name}) (or 'done'): ").strip()
                    if variant_name_input.lower() == 'done':
                        break
                    variant_name = variant_name_input or name
                    
                    if stock_mode == 'variant':
                        variant_qty = input("  Opening Stock (default: 0): ").strip() or "0"
                        print("\n  Opening Stock Quantity Unit:")
                        for idx, u in enumerate(active_units, 1):
                            print(f"     {idx}. {u.get('name', 'N/A')} ({u.get('symbol', 'N/A')})")
                        variant_unit_choice = input("  Select Unit (enter number, default: 1): ").strip()
                        try:
                            if variant_unit_choice:
                                variant_unit_index = int(variant_unit_choice) - 1
                                if 0 <= variant_unit_index < len(active_units):
                                    variant_unit = active_units[variant_unit_index].get('symbol', 'kg')
                                else:
                                    variant_unit = active_units[0].get('symbol', 'kg')
                            else:
                                variant_unit = active_units[0].get('symbol', 'kg')
                        except ValueError:
                            variant_unit = active_units[0].get('symbol', 'kg')
                    else:
                        variant_qty = "0"
                        variant_unit = None
                    
                    variant_b2c_qty = input("  Sell Unit in B2C - Quantity *: ").strip()
                    if not variant_b2c_qty:
                        print("  ❌ ERROR: Sell Unit quantity required!")
                        continue
                    print("\n  Sell Unit in B2C - Unit:")
                    for idx, u in enumerate(active_units, 1):
                        print(f"     {idx}. {u.get('name', 'N/A')} ({u.get('symbol', 'N/A')})")
                    variant_b2c_unit_choice = input(f"  Select B2C Unit (enter number, default: {b2c_unit or '1'}): ").strip()
                    try:
                        if variant_b2c_unit_choice:
                            variant_b2c_unit_index = int(variant_b2c_unit_choice) - 1
                            if 0 <= variant_b2c_unit_index < len(active_units):
                                variant_b2c_unit = active_units[variant_b2c_unit_index].get('symbol', b2c_unit or 'kg')
                            else:
                                variant_b2c_unit = b2c_unit or active_units[0].get('symbol', 'kg')
                        else:
                            variant_b2c_unit = b2c_unit or active_units[0].get('symbol', 'kg')
                    except ValueError:
                        variant_b2c_unit = b2c_unit or active_units[0].get('symbol', 'kg')
                    
                    if stock_mode == 'parent':
                        # Convert variant B2C quantity to parent B2C unit, then multiply by parent price
                        qty_in_parent_b2c_unit = self.convert_variant_qty_to_parent_unit(
                            variant_b2c_qty, variant_b2c_unit, b2c_unit or 'kg'
                        )
                        # Calculate price: (variant qty in parent B2C unit) * (parent price per parent B2C unit)
                        suggested_purchase = Decimal(purchase_price) * Decimal(str(qty_in_parent_b2c_unit))
                        suggested_sale = Decimal(sale_price) * Decimal(str(qty_in_parent_b2c_unit))
                        print(f"  → Suggested Purchase Price: ₹{suggested_purchase:.2f}")
                        print(f"  → Suggested Sale Price: ₹{suggested_sale:.2f}")
                        variant_purchase_price = input(
                            f"  Purchase Price (₹, default: {suggested_purchase:.2f}): "
                        ).strip() or f"{suggested_purchase:.2f}"
                        variant_sale_price = input(
                            f"  Sale Price (₹, default: {suggested_sale:.2f}): "
                        ).strip() or f"{suggested_sale:.2f}"
                    else:
                        variant_purchase_price = input("  Purchase Price (₹, default: 0): ").strip() or "0"
                        variant_sale_price = input("  Sale Price (₹, default: 0): ").strip() or "0"
                    variant_compare_price = input("  Compare Price (₹, default: 0): ").strip() or "0"
                    variant_low_stock_alert = input("  Low Stock Alert (default: 0): ").strip() or "0"
                    variant_on_b2c_input = input(
                        f"  Publish to B2C (y/n, default: {'y' if on_b2c else 'n'}): "
                    ).strip().lower()
                    variant_on_b2c = variant_on_b2c_input == 'y' if variant_on_b2c_input in ['y', 'n'] else on_b2c
                    variant_expiry_date = input("  Expiry Date (optional): ").strip()
                    variant_images_input = input("  Images URLs (comma separated, optional): ").strip()
                    variant_images = [img.strip() for img in variant_images_input.split(',') if img.strip()] if variant_images_input else []
                    
                    variant = {
                        'id': self.generate_variant_id(product_id, variant_count),
                        'name': variant_name,
                        'category': category,
                        'subCategory': sub_category,
                        'isVariant': True,
                        'b2cQty': variant_b2c_qty,
                        'b2cUnit': variant_b2c_unit,
                        'purchasePrice': Decimal(variant_purchase_price),
                        'salePrice': Decimal(variant_sale_price),
                        'comparePrice': Decimal(variant_compare_price),
                        'onB2C': variant_on_b2c
                    }
                    if stock_mode == 'variant':
                        variant['stock'] = int(variant_qty)
                        variant['lowStockAlert'] = int(variant_low_stock_alert)
                        if variant_unit:
                            variant['unit'] = variant_unit
                    if variant_expiry_date:
                        variant['expiryDate'] = variant_expiry_date
                    if variant_images:
                        variant['images'] = variant_images
                    if tags:
                        variant['tags'] = tags
                    variants.append(variant)
                    variant_count += 1
            else:
                cleaned_variants = []
                for idx, variant in enumerate(variants, 1):
                    next_variant = dict(variant)
                    next_variant['isVariant'] = True
                    next_variant['id'] = self.generate_variant_id(product_id, idx)
                    if stock_mode != 'variant':
                        next_variant.pop('stock', None)
                        next_variant.pop('lowStockAlert', None)
                        next_variant.pop('unit', None)
                    else:
                        # Ensure numeric types are consistent
                        if 'stock' in next_variant:
                            next_variant['stock'] = int(next_variant.get('stock', 0))
                        if 'lowStockAlert' in next_variant:
                            next_variant['lowStockAlert'] = int(next_variant.get('lowStockAlert', 0))
                    cleaned_variants.append(next_variant)
                variants = cleaned_variants
            
            stock_int = int(stock)
            low_stock_int = int(low_stock_alert)
            status = self.calculate_product_status(stock_int, low_stock_int)
            
            product_data = {
                'productID': product_id,
                'name': name,
                'category': category,
                'subCategory': sub_category,
                'isVariant': False,
                'stockMode': stock_mode,
                'stock': stock_int,
                **({'unit': unit} if unit else {}),
                'b2cQty': b2c_qty,
                'b2cUnit': b2c_unit,
                'lowStockAlert': low_stock_int,
                'purchasePrice': Decimal(purchase_price),
                'salePrice': Decimal(sale_price),
                'comparePrice': Decimal(compare_price),
                'onB2C': on_b2c,
                'status': status,
                'lastUpdated': datetime.now(timezone.utc).isoformat().split('T')[0],
                'createdAt': datetime.now(timezone.utc).isoformat(),
                'variants': variants
            }
            if description:
                product_data['description'] = description
            if tags:
                product_data['tags'] = tags
            if images:
                product_data['images'] = images
            if expiry_date:
                product_data['expiryDate'] = expiry_date
            
            self.products_table.put_item(Item=product_data)
            print("\n✅ Product updated successfully!")
            return True
        except ValueError as e:
            print(f"❌ ERROR: Invalid input - {e}")
            return False
        except ClientError as e:
            print(f"❌ ERROR: DynamoDB error - {e}")
            return False
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_categories(self):
        """Get all categories from DynamoDB"""
        try:
            response = self.categories_table.scan()
            return response.get('Items', [])
        except ClientError as e:
            print(f"❌ ERROR: Failed to fetch categories - {e}")
            return []
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return []
    
    def get_units(self):
        """Get all units from DynamoDB"""
        try:
            response = self.units_table.scan()
            return response.get('Items', [])
        except ClientError as e:
            print(f"❌ ERROR: Failed to fetch units - {e}")
            return []
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return []
    
    def category_management_menu(self):
        """Category management menu"""
        while True:
            print("\n" + "=" * 80)
            print("🏷️  CATEGORY MANAGEMENT")
            print("=" * 80)
            print("\n📋 AVAILABLE OPTIONS:")
            print("-" * 80)
            print("1. ➕ Create Category")
            print("2. 📋 List All Categories")
            print("3. 🔍 Get Category by ID")
            print("4. ✏️  Update Category")
            print("5. 🗑️  Delete Category")
            print("6. 🔄 Toggle Active/Inactive Status")
            print("0. ⬅️  Back to Main Menu")
            print("-" * 80)
            
            choice = input("\nSelect an option (0-6): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.create_category()
                input("\nPress Enter to continue...")
            elif choice == '2':
                self.list_categories()
                input("\nPress Enter to continue...")
            elif choice == '3':
                category_id = input("\nEnter Category ID: ").strip()
                if category_id:
                    self.get_category_by_id(category_id)
                else:
                    print("❌ ERROR: Category ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '4':
                category_id = input("\nEnter Category ID to update: ").strip()
                if category_id:
                    self.update_category(category_id)
                else:
                    print("❌ ERROR: Category ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '5':
                category_id = input("\nEnter Category ID to delete: ").strip()
                if category_id:
                    self.delete_category(category_id)
                else:
                    print("❌ ERROR: Category ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '6':
                category_id = input("\nEnter Category ID to toggle status: ").strip()
                if category_id:
                    self.toggle_category_status(category_id)
                else:
                    print("❌ ERROR: Category ID is required!")
                input("\nPress Enter to continue...")
            else:
                print("❌ ERROR: Invalid choice. Please select a number between 0-6.")
                input("\nPress Enter to continue...")
    
    def unit_management_menu(self):
        """Unit management menu"""
        while True:
            print("\n" + "=" * 80)
            print("📏 UNIT MANAGEMENT")
            print("=" * 80)
            print("\n📋 AVAILABLE OPTIONS:")
            print("-" * 80)
            print("1. ➕ Create Unit")
            print("2. 📋 List All Units")
            print("3. 🔍 Get Unit by ID")
            print("4. ✏️  Update Unit")
            print("5. 🗑️  Delete Unit")
            print("0. ⬅️  Back to Main Menu")
            print("-" * 80)
            
            choice = input("\nSelect an option (0-5): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.create_unit()
                input("\nPress Enter to continue...")
            elif choice == '2':
                self.list_units()
                input("\nPress Enter to continue...")
            elif choice == '3':
                unit_id = input("\nEnter Unit ID: ").strip()
                if unit_id:
                    self.get_unit_by_id(unit_id)
                else:
                    print("❌ ERROR: Unit ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '4':
                unit_id = input("\nEnter Unit ID to update: ").strip()
                if unit_id:
                    self.update_unit(unit_id)
                else:
                    print("❌ ERROR: Unit ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '5':
                unit_id = input("\nEnter Unit ID to delete: ").strip()
                if unit_id:
                    self.delete_unit(unit_id)
                else:
                    print("❌ ERROR: Unit ID is required!")
                input("\nPress Enter to continue...")
            else:
                print("❌ ERROR: Invalid choice. Please select a number between 0-5.")
                input("\nPress Enter to continue...")
    
    def create_category(self):
        """Create a new category"""
        print("\n" + "=" * 80)
        print("➕ CREATE CATEGORY")
        print("=" * 80)
        
        try:
            name = input("\nCategory Name *: ").strip()
            if not name:
                print("❌ ERROR: Category Name is required!")
                return False
            
            description = input("Description (optional): ").strip() or ""
            
            # Subcategories
            subcategories = []
            print("\nSub Categories (press Enter with empty value to finish):")
            while True:
                sub = input(f"  Sub Category {len(subcategories) + 1}: ").strip()
                if not sub:
                    break
                subcategories.append(sub)
            
            # Color selection
            color_options = ['green', 'orange', 'red', 'purple', 'blue', 'yellow']
            print("\nColor options:")
            for idx, col in enumerate(color_options, 1):
                print(f"   {idx}. {col}")
            color_choice = input("Select Color (enter number, default: 1): ").strip()
            try:
                if color_choice:
                    color_index = int(color_choice) - 1
                    if 0 <= color_index < len(color_options):
                        color = color_options[color_index]
                    else:
                        color = color_options[0]
                else:
                    color = color_options[0]
            except ValueError:
                color = color_options[0]
            
            # Generate category ID
            category_id = f"CAT-{str(uuid.uuid4())[:8].upper()}"
            
            # Create category data
            category_data = {
                'categoryID': category_id,
                'name': name,
                'description': description,
                'subcategories': subcategories,
                'color': color,
                'isActive': True,  # Default to active
                'createdAt': datetime.now(timezone.utc).isoformat(),
                'updatedAt': datetime.now(timezone.utc).isoformat()
            }
            
            self.categories_table.put_item(Item=category_data)
            
            print(f"\n✅ Category '{name}' created successfully!")
            print(f"🔑 Category ID: {category_id}")
            return True
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def list_categories(self):
        """List all categories"""
        print("\n" + "=" * 80)
        print("📋 LIST ALL CATEGORIES")
        print("=" * 80)
        
        try:
            categories = self.get_categories()
            
            if not categories:
                print("\n📦 No categories found in the database.")
                return
            
            print(f"\n📊 Total Categories: {len(categories)}")
            print("-" * 80)
            
            for idx, category in enumerate(categories, 1):
                category_id = category.get('categoryID', 'N/A')
                name = category.get('name', 'N/A')
                subcategories = category.get('subcategories', [])
                subcategories_count = len(subcategories)
                is_active = category.get('isActive', True)
                status = "Active" if is_active else "Inactive"
                color = category.get('color', 'N/A')
                
                print(f"\n{idx}. Category ID: {category_id}")
                print(f"   Name: {name}")
                print(f"   Color: {color}")
                print(f"   Status: {status}")
                print(f"   Sub Categories ({subcategories_count}):")
                if subcategories:
                    for sub_idx, sub in enumerate(subcategories, 1):
                        print(f"      {sub_idx}. {sub}")
                else:
                    print(f"      (No subcategories)")
            
            print("\n" + "-" * 80)
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def get_category_by_id(self, category_id: str):
        """Get category details by ID"""
        print("\n" + "=" * 80)
        print(f"🔍 CATEGORY DETAILS - {category_id}")
        print("=" * 80)
        
        try:
            response = self.categories_table.get_item(
                Key={'categoryID': category_id}
            )
            
            if 'Item' not in response:
                print(f"\n❌ Category with ID '{category_id}' not found!")
                return
            
            category = response['Item']
            
            print("\n📦 CATEGORY:")
            print("-" * 80)
            print(f"Category ID: {category.get('categoryID', 'N/A')}")
            print(f"Name: {category.get('name', 'N/A')}")
            print(f"Description: {category.get('description', 'N/A')}")
            print(f"Color: {category.get('color', 'N/A')}")
            print(f"Status: {'Active' if category.get('isActive', True) else 'Inactive'}")
            print(f"Created At: {category.get('createdAt', 'N/A')}")
            print(f"Updated At: {category.get('updatedAt', 'N/A')}")
            
            subcategories = category.get('subcategories', [])
            if subcategories:
                print(f"\n📦 SUB CATEGORIES ({len(subcategories)}):")
                print("-" * 80)
                for idx, sub in enumerate(subcategories, 1):
                    print(f"  {idx}. {sub}")
            else:
                print("\n📦 No subcategories found.")
            
        except ClientError as e:
            print(f"❌ ERROR: DynamoDB error - {e}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def update_category(self, category_id: str):
        """Update an existing category"""
        print("\n" + "=" * 80)
        print(f"✏️  UPDATE CATEGORY - {category_id}")
        print("=" * 80)
        
        try:
            response = self.categories_table.get_item(
                Key={'categoryID': category_id}
            )
            
            if 'Item' not in response:
                print(f"\n❌ Category with ID '{category_id}' not found!")
                return False
            
            category = response['Item']
            current_name = category.get('name', '')
            current_description = category.get('description', '')
            current_color = category.get('color', 'green')
            current_subcategories = category.get('subcategories', [])
            
            print("\nCurrent details:")
            print(f"  Name: {current_name}")
            print(f"  Description: {current_description or '(none)'}")
            print(f"  Color: {current_color}")
            if current_subcategories:
                print("  Sub Categories:")
                for idx, sub in enumerate(current_subcategories, 1):
                    print(f"    {idx}. {sub}")
            else:
                print("  Sub Categories: (none)")
            
            print("\nEnter new values (leave blank to keep current value)")
            name = input(f"New Name (current: {current_name}): ").strip() or current_name
            description = input(f"New Description (current: {current_description or '(none)'}): ").strip()
            if description == "":
                description = current_description
            
            # Subcategories update
            print("\nUpdate Sub Categories:")
            print(" - Enter comma-separated names to replace the list")
            print(" - Leave blank to keep existing sub categories")
            subcategories_input = input("New Sub Categories: ").strip()
            if subcategories_input:
                subcategories = [sub.strip() for sub in subcategories_input.split(',') if sub.strip()]
            else:
                subcategories = current_subcategories
            
            # Color update
            color_options = ['green', 'orange', 'red', 'purple', 'blue', 'yellow']
            print("\nColor options:")
            for idx, col in enumerate(color_options, 1):
                selected_marker = " (current)" if col == current_color else ""
                print(f"   {idx}. {col}{selected_marker}")
            color_choice = input(f"Select Color (enter number, current: {current_color}): ").strip()
            if color_choice:
                try:
                    color_index = int(color_choice) - 1
                    if 0 <= color_index < len(color_options):
                        color = color_options[color_index]
                    else:
                        print("⚠️  Invalid color selection. Keeping current color.")
                        color = current_color
                except ValueError:
                    print("⚠️  Invalid input. Keeping current color.")
                    color = current_color
            else:
                color = current_color
            
            # Perform update
            self.categories_table.update_item(
                Key={'categoryID': category_id},
                UpdateExpression="""
                    SET #name = :name,
                        description = :description,
                        subcategories = :subcategories,
                        color = :color,
                        updatedAt = :updatedAt
                """,
                ExpressionAttributeNames={
                    '#name': 'name',  # 'name' is a reserved word in DynamoDB
                },
                ExpressionAttributeValues={
                    ':name': name,
                    ':description': description,
                    ':subcategories': subcategories,
                    ':color': color,
                    ':updatedAt': datetime.now(timezone.utc).isoformat()
                }
            )
            
            print("\n✅ Category updated successfully!")
            return True
        
        except ClientError as e:
            print(f"❌ ERROR: DynamoDB error - {e}")
            return False
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def delete_category(self, category_id: str):
        """Delete category by ID"""
        print("\n" + "=" * 80)
        print(f"🗑️  DELETE CATEGORY - {category_id}")
        print("=" * 80)
        
        try:
            confirm = input(f"\n⚠️  Are you sure you want to delete category '{category_id}'? (yes/no): ").strip().lower()
            
            if confirm != 'yes':
                print("❌ Deletion cancelled.")
                return
            
            self.categories_table.delete_item(
                Key={'categoryID': category_id}
            )
            
            print(f"\n✅ Category '{category_id}' deleted successfully!")
            
        except ClientError as e:
            print(f"❌ ERROR: DynamoDB error - {e}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def toggle_category_status(self, category_id: str):
        """Toggle category active/inactive status"""
        print("\n" + "=" * 80)
        print(f"🔄 TOGGLE CATEGORY STATUS - {category_id}")
        print("=" * 80)
        
        try:
            response = self.categories_table.get_item(
                Key={'categoryID': category_id}
            )
            
            if 'Item' not in response:
                print(f"\n❌ Category with ID '{category_id}' not found!")
                return
            
            category = response['Item']
            current_status = category.get('isActive', True)
            new_status = not current_status
            
            self.categories_table.update_item(
                Key={'categoryID': category_id},
                UpdateExpression='SET isActive = :status, updatedAt = :updatedAt',
                ExpressionAttributeValues={
                    ':status': new_status,
                    ':updatedAt': datetime.now(timezone.utc).isoformat()
                }
            )
            
            status_text = "Active" if new_status else "Inactive"
            print(f"\n✅ Category status updated to: {status_text}")
            
        except ClientError as e:
            print(f"❌ ERROR: DynamoDB error - {e}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def create_unit(self):
        """Create a new unit"""
        print("\n" + "=" * 80)
        print("➕ CREATE UNIT")
        print("=" * 80)
        
        try:
            name = input("\nUnit Name * (e.g., Kilogram): ").strip()
            if not name:
                print("❌ ERROR: Unit Name is required!")
                return False
            
            symbol = input("Unit Symbol * (e.g., kg): ").strip()
            if not symbol:
                print("❌ ERROR: Unit Symbol is required!")
                return False
            
            # Generate unit ID
            unit_id = f"UNIT-{str(uuid.uuid4())[:8].upper()}"
            
            # Create unit data
            unit_data = {
                'unitID': unit_id,
                'name': name,
                'symbol': symbol,
                'isActive': True,  # Default to active
                'createdAt': datetime.now(timezone.utc).isoformat(),
                'updatedAt': datetime.now(timezone.utc).isoformat()
            }
            
            self.units_table.put_item(Item=unit_data)
            
            print(f"\n✅ Unit '{name}' ({symbol}) created successfully!")
            print(f"🔑 Unit ID: {unit_id}")
            return True
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def list_units(self):
        """List all units"""
        print("\n" + "=" * 80)
        print("📋 LIST ALL UNITS")
        print("=" * 80)
        
        try:
            units = self.get_units()
            
            if not units:
                print("\n📦 No units found in the database.")
                return
            
            print(f"\n📊 Total Units: {len(units)}")
            print("-" * 80)
            
            for idx, unit in enumerate(units, 1):
                unit_id = unit.get('unitID', 'N/A')
                name = unit.get('name', 'N/A')
                symbol = unit.get('symbol', 'N/A')
                is_active = unit.get('isActive', True)
                status = "Active" if is_active else "Inactive"
                
                print(f"\n{idx}. Unit ID: {unit_id}")
                print(f"   Name: {name}")
                print(f"   Symbol: {symbol}")
                print(f"   Status: {status}")
            
            print("\n" + "-" * 80)
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def get_unit_by_id(self, unit_id: str):
        """Get unit details by ID"""
        print("\n" + "=" * 80)
        print(f"🔍 UNIT DETAILS - {unit_id}")
        print("=" * 80)
        
        try:
            response = self.units_table.get_item(
                Key={'unitID': unit_id}
            )
            
            if 'Item' not in response:
                print(f"\n❌ Unit with ID '{unit_id}' not found!")
                return
            
            unit = response['Item']
            
            print("\n📦 UNIT:")
            print("-" * 80)
            print(f"Unit ID: {unit.get('unitID', 'N/A')}")
            print(f"Name: {unit.get('name', 'N/A')}")
            print(f"Symbol: {unit.get('symbol', 'N/A')}")
            print(f"Status: {'Active' if unit.get('isActive', True) else 'Inactive'}")
            print(f"Created At: {unit.get('createdAt', 'N/A')}")
            print(f"Updated At: {unit.get('updatedAt', 'N/A')}")
            
        except ClientError as e:
            print(f"❌ ERROR: DynamoDB error - {e}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def update_unit(self, unit_id: str):
        """Update an existing unit"""
        print("\n" + "=" * 80)
        print(f"✏️  UPDATE UNIT - {unit_id}")
        print("=" * 80)
        
        try:
            response = self.units_table.get_item(
                Key={'unitID': unit_id}
            )
            
            if 'Item' not in response:
                print(f"\n❌ Unit with ID '{unit_id}' not found!")
                return False
            
            unit = response['Item']
            current_name = unit.get('name', '')
            current_symbol = unit.get('symbol', '')
            current_status = 'Active' if unit.get('isActive', True) else 'Inactive'
            
            print("\nCurrent details:")
            print(f"  Name: {current_name}")
            print(f"  Symbol: {current_symbol}")
            print(f"  Status: {current_status}")
            
            print("\nEnter new values (leave blank to keep current value)")
            name = input(f"New Name (current: {current_name}): ").strip() or current_name
            symbol = input(f"New Symbol (current: {current_symbol}): ").strip() or current_symbol
            
            if not name or not symbol:
                print("❌ ERROR: Unit name and symbol cannot be empty!")
                return False
            
            self.units_table.update_item(
                Key={'unitID': unit_id},
                UpdateExpression="""
                    SET #name = :name,
                        symbol = :symbol,
                        updatedAt = :updatedAt
                """,
                ExpressionAttributeNames={
                    '#name': 'name',
                },
                ExpressionAttributeValues={
                    ':name': name,
                    ':symbol': symbol,
                    ':updatedAt': datetime.now(timezone.utc).isoformat()
                }
            )
            
            print("\n✅ Unit updated successfully!")
            return True
        
        except ClientError as e:
            print(f"❌ ERROR: DynamoDB error - {e}")
            return False
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def delete_unit(self, unit_id: str):
        """Delete unit by ID"""
        print("\n" + "=" * 80)
        print(f"🗑️  DELETE UNIT - {unit_id}")
        print("=" * 80)
        
        try:
            confirm = input(f"\n⚠️  Are you sure you want to delete unit '{unit_id}'? (yes/no): ").strip().lower()
            
            if confirm != 'yes':
                print("❌ Deletion cancelled.")
                return
            
            self.units_table.delete_item(
                Key={'unitID': unit_id}
            )
            
            print(f"\n✅ Unit '{unit_id}' deleted successfully!")
            
        except ClientError as e:
            print(f"❌ ERROR: DynamoDB error - {e}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def toggle_unit_status(self, unit_id: str):
        """Toggle unit active/inactive status"""
        print("\n" + "=" * 80)
        print(f"🔄 TOGGLE UNIT STATUS - {unit_id}")
        print("=" * 80)
        
        try:
            response = self.units_table.get_item(
                Key={'unitID': unit_id}
            )
            
            if 'Item' not in response:
                print(f"\n❌ Unit with ID '{unit_id}' not found!")
                return
            
            unit = response['Item']
            current_status = unit.get('isActive', True)
            new_status = not current_status
            
            self.units_table.update_item(
                Key={'unitID': unit_id},
                UpdateExpression='SET isActive = :status, updatedAt = :updatedAt',
                ExpressionAttributeValues={
                    ':status': new_status,
                    ':updatedAt': datetime.now(timezone.utc).isoformat()
                }
            )
            
            status_text = "Active" if new_status else "Inactive"
            print(f"\n✅ Unit status updated to: {status_text}")
            
        except ClientError as e:
            print(f"❌ ERROR: DynamoDB error - {e}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def delete_product(self, product_id: str):
        """Delete product by ID"""
        print("\n" + "=" * 80)
        print(f"🗑️  DELETE PRODUCT - {product_id}")
        print("=" * 80)
        
        try:
            # Confirm deletion
            confirm = input(f"\n⚠️  Are you sure you want to delete product '{product_id}'? (yes/no): ").strip().lower()
            
            if confirm != 'yes':
                print("❌ Deletion cancelled.")
                return
            
            # Delete the product
            self.products_table.delete_item(
                Key={'productID': product_id}
            )
            
            print(f"\n✅ Product '{product_id}' deleted successfully!")
            
        except ClientError as e:
            print(f"❌ ERROR: DynamoDB error - {e}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def convert_base_to_unit(self, qty: float, base_unit: str, target_unit: str) -> float:
        """Convert quantity from base unit to target unit"""
        base_unit = base_unit.lower()
        target_unit = target_unit.lower()
        
        if base_unit == target_unit:
            return qty
        
        if base_unit == 'kg' and target_unit == 'g':
            return qty * 1000
        if base_unit == 'g' and target_unit == 'kg':
            return qty / 1000
        if base_unit == 'l' and target_unit == 'ml':
            return qty * 1000
        if base_unit == 'ml' and target_unit == 'l':
            return qty / 1000
        
        return qty

    def generate_product_id(self) -> str:
        """Generate the next sequential product ID (PRD-0001, etc.)"""
        try:
            max_number = 0
            scan_kwargs = {'ProjectionExpression': 'productID'}
            while True:
                response = self.products_table.scan(**scan_kwargs)
                for item in response.get('Items', []):
                    product_id = item.get('productID', '')
                    match = re.match(r'^PRD-(\d{4})$', product_id)
                    if match:
                        number = int(match.group(1))
                        if number > max_number:
                            max_number = number
                last_key = response.get('LastEvaluatedKey')
                if not last_key:
                    break
                scan_kwargs['ExclusiveStartKey'] = last_key
            next_number = max_number + 1
            return f"PRD-{next_number:04d}"
        except Exception:
            # Fallback to UUID-based if scan fails
            return f"PRD-{str(uuid.uuid4())[:4].upper()}"

    def generate_variant_id(self, product_id: str, index: int) -> str:
        """Generate a variant ID based on the product ID"""
        return f"{product_id}-v{index:02d}"

    def generate_adjustment_id(self) -> str:
        """Generate the next sequential adjustment ID (ADJ-0001, etc.)"""
        try:
            max_number = 0
            scan_kwargs = {'ProjectionExpression': 'adjustmentID'}
            while True:
                response = self.adjustments_table.scan(**scan_kwargs)
                for item in response.get('Items', []):
                    adj_id = item.get('adjustmentID', '')
                    match = re.match(r'^ADJ-(\d{4})$', adj_id)
                    if match:
                        number = int(match.group(1))
                        if number > max_number:
                            max_number = number
                last_key = response.get('LastEvaluatedKey')
                if not last_key:
                    break
                scan_kwargs['ExclusiveStartKey'] = last_key
            next_number = max_number + 1
            return f"ADJ-{next_number:04d}"
        except Exception:
            # Fallback to UUID-based if scan fails
            return f"ADJ-{str(uuid.uuid4())[:4].upper()}"

    def stock_adjustment_menu(self):
        """Stock adjustment management menu"""
        if self.adjustments_table is None:
            print("\n❌ ERROR: Stock_adjustment table not found!")
            print("   Please create the 'Stock_adjustment' table in DynamoDB first.")
            print("   Table requirements:")
            print("   - Table Name: Stock_adjustment")
            print("   - Partition Key: adjustmentID (String)")
            print("   - Sort Key: date (String)")
            input("\nPress Enter to continue...")
            return
        
        while True:
            print("\n" + "=" * 80)
            print("📊 STOCK ADJUSTMENT MANAGEMENT")
            print("=" * 80)
            print("\n📋 AVAILABLE OPTIONS:")
            print("-" * 80)
            print("1. ➕ Create New Adjustment")
            print("2. 📋 List All Adjustments")
            print("3. 🔍 Get Adjustment by ID")
            print("4. 🔎 View Adjustments by Type")
            print("5. 📅 View Adjustments by Date Range")
            print("0. ⬅️  Back to Main Menu")
            print("-" * 80)
            
            choice = input("\nSelect an option (0-5): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.create_stock_adjustment()
                input("\nPress Enter to continue...")
            elif choice == '2':
                self.list_adjustments()
                input("\nPress Enter to continue...")
            elif choice == '3':
                adjustment_id = input("\nEnter Adjustment ID: ").strip()
                if adjustment_id:
                    self.get_adjustment_by_id(adjustment_id)
                else:
                    print("❌ ERROR: Adjustment ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '4':
                self.list_adjustments_by_type()
                input("\nPress Enter to continue...")
            elif choice == '5':
                self.list_adjustments_by_date_range()
                input("\nPress Enter to continue...")
            else:
                print("❌ ERROR: Invalid choice. Please select a number between 0-5.")
                input("\nPress Enter to continue...")

    def get_products_for_adjustment(self):
        """Get products list filtered by stockMode for adjustment selection"""
        try:
            response = self.products_table.scan()
            all_products = response.get('Items', [])
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.products_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                all_products.extend(response.get('Items', []))
            
            items_list = []
            
            for product in all_products:
                stock_mode = product.get('stockMode', 'parent')
                product_id = product.get('productID', 'N/A')
                name = product.get('name', 'N/A')
                category = product.get('category', 'N/A')
                sub_category = product.get('subCategory', 'N/A')
                stock = product.get('stock', 0)
                unit = product.get('unit', '')
                purchase_price = product.get('purchasePrice', 0)
                sale_price = product.get('salePrice', 0)
                in_cart_qty = product.get('inCartQuantity', 0)
                variants = product.get('variants', [])
                
                if stock_mode == 'parent':
                    # Show only parent product
                    available_stock = stock - in_cart_qty
                    items_list.append({
                        'type': 'parent',
                        'productID': product_id,
                        'variantID': None,
                        'name': name,
                        'category': category,
                        'subCategory': sub_category,
                        'stock': stock,
                        'availableStock': available_stock,
                        'unit': unit,
                        'purchasePrice': purchase_price,
                        'salePrice': sale_price,
                        'inCartQuantity': in_cart_qty
                    })
                else:  # stock_mode == 'variant'
                    # Show parent product
                    available_stock = stock - in_cart_qty
                    items_list.append({
                        'type': 'parent',
                        'productID': product_id,
                        'variantID': None,
                        'name': name,
                        'category': category,
                        'subCategory': sub_category,
                        'stock': stock,
                        'availableStock': available_stock,
                        'unit': unit,
                        'purchasePrice': purchase_price,
                        'salePrice': sale_price,
                        'inCartQuantity': in_cart_qty
                    })
                    
                    # Show all variants
                    for variant in variants:
                        variant_id = variant.get('id', 'N/A')
                        variant_name = variant.get('name', 'N/A')
                        variant_stock = variant.get('stock', 0)
                        variant_unit = variant.get('unit', '')
                        variant_purchase_price = variant.get('purchasePrice', 0)
                        variant_sale_price = variant.get('salePrice', 0)
                        variant_in_cart = variant.get('inCartQuantity', 0)
                        variant_available = variant_stock - variant_in_cart
                        
                        items_list.append({
                            'type': 'variant',
                            'productID': product_id,
                            'variantID': variant_id,
                            'name': variant_name,
                            'category': category,
                            'subCategory': sub_category,
                            'stock': variant_stock,
                            'availableStock': variant_available,
                            'unit': variant_unit,
                            'purchasePrice': variant_purchase_price,
                            'salePrice': variant_sale_price,
                            'inCartQuantity': variant_in_cart
                        })
            
            return items_list
            
        except Exception as e:
            print(f"❌ ERROR: Failed to fetch products - {e}")
            return []

    def create_stock_adjustment(self):
        """Create a new stock adjustment"""
        print("\n" + "=" * 80)
        print("➕ CREATE NEW STOCK ADJUSTMENT")
        print("=" * 80)
        
        try:
            # Generate adjustment ID
            adjustment_id = self.generate_adjustment_id()
            
            # Adjustment details
            print("\n📝 ADJUSTMENT DETAILS:")
            print("-" * 80)
            print(f"Adjustment No: {adjustment_id}")
            
            # Date
            date_input = input("Date (YYYY-MM-DD, default: today): ").strip()
            if date_input:
                adjustment_date = date_input
            else:
                adjustment_date = datetime.now(timezone.utc).isoformat().split('T')[0]
            
            # Adjustment Type
            print("\n📋 Adjustment Types:")
            print("1. Cart Stock (Stock moved to cart)")
            print("2. Return (Returned stock from cart)")
            print("3. Damage (Damaged/spoiled stock)")
            print("4. Internal Consumption (Used internally)")
            print("5. Extra Given (Extra weight given to customers)")
            
            type_choice = input("\nSelect Adjustment Type (1-5): ").strip()
            type_map = {
                '1': 'cart_stock',
                '2': 'return',
                '3': 'damage',
                '4': 'internal_consumption',
                '5': 'extra_given'
            }
            
            if type_choice not in type_map:
                print("❌ ERROR: Invalid adjustment type!")
                return False
            
            adjustment_type = type_map[type_choice]
            
            # Notes
            notes = input("Notes (optional): ").strip() or ""
            
            # Get products for selection
            print("\n📦 SELECTING ITEMS:")
            print("-" * 80)
            items_list = self.get_products_for_adjustment()
            
            if not items_list:
                print("❌ ERROR: No products found!")
                return False
            
            # Display items for selection
            print(f"\n📋 Available Items ({len(items_list)}):")
            print("-" * 80)
            print(f"{'#':<5} {'Name':<30} {'Category':<20} {'Stock':<15} {'Available':<15} {'Purchase Price':<15}")
            print("-" * 80)
            
            for idx, item in enumerate(items_list, 1):
                item_type = "Parent" if item['type'] == 'parent' else "Variant"
                name_display = f"{item['name']} ({item_type})"
                stock_display = f"{item['stock']} {item['unit']}" if item['unit'] else f"{item['stock']}"
                available_display = f"{item['availableStock']} {item['unit']}" if item['unit'] else f"{item['availableStock']}"
                price_display = f"₹{Decimal(item['purchasePrice'])}"
                
                print(f"{idx:<5} {name_display:<30} {item['category']:<20} {stock_display:<15} {available_display:<15} {price_display:<15}")
            
            # Select items
            selected_items = []
            print("\n📝 Select items (enter numbers separated by commas, e.g., 1,3,5):")
            selection = input("Item numbers: ").strip()
            
            if not selection:
                print("❌ ERROR: At least one item must be selected!")
                return False
            
            try:
                selected_indices = [int(x.strip()) - 1 for x in selection.split(',')]
                selected_indices = [idx for idx in selected_indices if 0 <= idx < len(items_list)]
                
                if not selected_indices:
                    print("❌ ERROR: Invalid selection!")
                    return False
                
                # Get selected items
                selected_items_data = [items_list[idx] for idx in selected_indices]
                
                # Enter quantities for selected items
                print("\n📝 ENTER ADJUSTMENT QUANTITIES:")
                print("-" * 80)
                adjustment_items = []
                total_price = Decimal('0')
                
                for item in selected_items_data:
                    print(f"\n{item['name']} ({'Parent' if item['type'] == 'parent' else 'Variant'})")
                    print(f"  Available Stock: {item['availableStock']} {item['unit']}")
                    print(f"  Purchase Price: ₹{Decimal(item['purchasePrice'])} per {item['unit']}")
                    
                    qty_input = input(f"  Adjustment Quantity ({item['unit']}): ").strip()
                    
                    if not qty_input:
                        print("  ⚠️  Skipping this item (no quantity entered)")
                        continue
                    
                    try:
                        qty = Decimal(qty_input)
                        
                        # Validate quantity based on adjustment type
                        if adjustment_type == 'return':
                            # For returns, check if we can return this much
                            if item['type'] == 'parent':
                                max_return = Decimal(str(item.get('inCartQuantity', 0)))
                            else:
                                max_return = Decimal(str(item.get('inCartQuantity', 0)))
                            
                            if qty > max_return:
                                print(f"  ❌ ERROR: Cannot return more than {max_return} {item['unit']} (currently in cart)")
                                continue
                        else:
                            # For other types, check available stock
                            available = Decimal(str(item['availableStock']))
                            if qty > available:
                                print(f"  ❌ ERROR: Insufficient stock! Available: {available} {item['unit']}")
                                continue
                        
                        if qty <= 0:
                            print("  ❌ ERROR: Quantity must be greater than 0")
                            continue
                        
                        item_price = Decimal(item['purchasePrice']) * qty
                        total_price += item_price
                        
                        adjustment_items.append({
                            'productID': item['productID'],
                            'variantID': item['variantID'],
                            'name': item['name'],
                            'quantity': qty,  # Decimal type
                            'unit': item['unit'],
                            'purchasePrice': Decimal(item['purchasePrice']),
                            'totalPrice': item_price  # Decimal type
                        })
                        
                        print(f"  ✅ Added: {qty} {item['unit']} (Price: ₹{item_price:.2f})")
                        
                    except ValueError:
                        print("  ❌ ERROR: Invalid quantity!")
                        continue
                
                if not adjustment_items:
                    print("\n❌ ERROR: No items added to adjustment!")
                    return False
                
                # Create adjustment record
                adjustment_data = {
                    'adjustmentID': adjustment_id,
                    'date': adjustment_date,
                    'adjustmentType': adjustment_type,
                    'items': adjustment_items,
                    'totalPrice': total_price,  # Decimal type
                    'notes': notes,
                    'createdAt': datetime.now(timezone.utc).isoformat()
                }
                
                # Save adjustment
                try:
                    self.adjustments_table.put_item(Item=adjustment_data)
                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                    if error_code == 'ResourceNotFoundException':
                        print(f"\n❌ ERROR: Stock_adjustment table not found!")
                        print(f"   Please create the 'Stock_adjustment' table in DynamoDB first.")
                        print(f"   Table requirements:")
                        print(f"   - Table Name: Stock_adjustment")
                        print(f"   - Partition Key: adjustmentID (String)")
                        print(f"   - Sort Key: date (String)")
                        print(f"   - Capacity Mode: On-demand (recommended)")
                        return False
                    else:
                        raise
                
                # Update product stock based on adjustment type
                for item in adjustment_items:
                    self.update_product_stock_for_adjustment(
                        item['productID'],
                        item.get('variantID'),
                        item['quantity'],
                        item['unit'],
                        adjustment_type
                    )
                
                print(f"\n✅ Stock adjustment '{adjustment_id}' created successfully!")
                print(f"📊 Total Price: ₹{total_price:.2f}")
                return True
                
            except ValueError:
                print("❌ ERROR: Invalid item selection format!")
                return False
                
        except ClientError as e:
            print(f"❌ ERROR: DynamoDB error - {e}")
            return False
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_product_stock_for_adjustment(self, product_id: str, variant_id: Optional[str], quantity: Decimal, unit: str, adjustment_type: str):
        """Update product stock based on adjustment type"""
        try:
            # Convert Decimal quantity to float for calculations
            qty_float = float(quantity)
            
            # Helper function to safely convert to float (handles both Decimal and numeric types)
            def to_float(value):
                if isinstance(value, Decimal):
                    return float(value)
                elif value is None:
                    return 0.0
                else:
                    return float(value)
            
            # Get product
            response = self.products_table.get_item(Key={'productID': product_id})
            if 'Item' not in response:
                print(f"⚠️  WARNING: Product {product_id} not found, skipping stock update")
                return
            
            product = response['Item']
            
            if variant_id:
                # Update variant stock
                variants = product.get('variants', [])
                variant_found = False
                
                for variant in variants:
                    if variant.get('id') == variant_id:
                        variant_found = True
                        current_stock = to_float(variant.get('stock', 0))
                        current_in_cart = to_float(variant.get('inCartQuantity', 0))
                        
                        if adjustment_type == 'cart_stock':
                            new_stock = current_stock - qty_float
                            new_in_cart = current_in_cart + qty_float
                            variant['stock'] = int(new_stock)
                            variant['inCartQuantity'] = int(new_in_cart)
                        elif adjustment_type == 'return':
                            new_stock = current_stock + qty_float
                            new_in_cart = max(0, current_in_cart - qty_float)
                            variant['stock'] = int(new_stock)
                            variant['inCartQuantity'] = int(new_in_cart)
                        else:  # damage, internal_consumption, extra_given
                            new_stock = current_stock - qty_float
                            variant['stock'] = int(new_stock)
                            # Don't change inCartQuantity for these types
                        
                        break
                
                if not variant_found:
                    print(f"⚠️  WARNING: Variant {variant_id} not found, skipping stock update")
                    return
                
                # Update product with modified variants
                self.products_table.put_item(Item=product)
                
            else:
                # Update parent product stock
                current_stock = to_float(product.get('stock', 0))
                current_in_cart = to_float(product.get('inCartQuantity', 0))  # Defaults to 0 if not present
                
                if adjustment_type == 'cart_stock':
                    new_stock = current_stock - qty_float
                    new_in_cart = current_in_cart + qty_float
                    product['stock'] = int(new_stock)
                    product['inCartQuantity'] = int(new_in_cart)
                elif adjustment_type == 'return':
                    new_stock = current_stock + qty_float
                    new_in_cart = max(0, current_in_cart - qty_float)
                    product['stock'] = int(new_stock)
                    product['inCartQuantity'] = int(new_in_cart)
                else:  # damage, internal_consumption, extra_given
                    new_stock = current_stock - qty_float
                    product['stock'] = int(new_stock)
                
                # Recalculate status
                low_stock_alert = to_float(product.get('lowStockAlert', 0))
                product['status'] = self.calculate_product_status(int(new_stock), int(low_stock_alert))
                
                # Update B2C availability
                available_stock = new_stock - to_float(product.get('inCartQuantity', 0))
                if available_stock <= 0:
                    product['onB2C'] = False
                else:
                    # Check if it was previously unavailable
                    if not product.get('onB2C', False) and available_stock > 0:
                        product['onB2C'] = True
                
                # Update product
                self.products_table.put_item(Item=product)
                
        except Exception as e:
            print(f"⚠️  WARNING: Failed to update stock for {product_id}: {e}")

    def list_adjustments(self):
        """List all stock adjustments"""
        print("\n" + "=" * 80)
        print("📋 LIST ALL STOCK ADJUSTMENTS")
        print("=" * 80)
        
        try:
            response = self.adjustments_table.scan()
            adjustments = response.get('Items', [])
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.adjustments_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                adjustments.extend(response.get('Items', []))
            
            if not adjustments:
                print("\n📦 No adjustments found.")
                return
            
            # Sort by date (newest first)
            adjustments.sort(key=lambda x: x.get('date', ''), reverse=True)
            
            print(f"\n📊 Total Adjustments: {len(adjustments)}")
            print("-" * 80)
            
            for idx, adj in enumerate(adjustments, 1):
                adj_id = adj.get('adjustmentID', 'N/A')
                date = adj.get('date', 'N/A')
                adj_type = adj.get('adjustmentType', 'N/A')
                total_price = adj.get('totalPrice', 0)
                notes = adj.get('notes', '')
                items = adj.get('items', [])
                
                # Convert to Decimal for display
                total_decimal = Decimal(str(total_price)) if not isinstance(total_price, Decimal) else total_price
                
                print(f"\n{idx}. Adjustment ID: {adj_id}")
                print(f"   Date: {date}")
                print(f"   Type: {adj_type.replace('_', ' ').title()}")
                print(f"   Total Price: ₹{total_decimal:.2f}")
                print(f"   Items: {len(items)}")
                if notes:
                    print(f"   Notes: {notes}")
                
                # Display items details
                if items:
                    print(f"\n   📦 Items Details:")
                    print(f"   {'─' * 76}")
                    print(f"   {'Name':<25} {'Quantity':<12} {'Unit':<8} {'Price/Unit':<12} {'Total':<12}")
                    print(f"   {'─' * 76}")
                    for item in items:
                        name = item.get('name', 'N/A')
                        qty = item.get('quantity', 0)
                        unit = item.get('unit', '')
                        price_per_unit = item.get('purchasePrice', 0)
                        total = item.get('totalPrice', 0)
                        
                        # Convert to Decimal if not already
                        qty_decimal = Decimal(str(qty)) if not isinstance(qty, Decimal) else qty
                        price_decimal = Decimal(str(price_per_unit)) if not isinstance(price_per_unit, Decimal) else Decimal(price_per_unit)
                        total_decimal_item = Decimal(str(total)) if not isinstance(total, Decimal) else Decimal(total)
                        
                        print(f"   {name:<25} {qty_decimal:<12} {unit:<8} ₹{price_decimal:<11} ₹{total_decimal_item:<11}")
                    print(f"   {'─' * 76}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def get_adjustment_by_id(self, adjustment_id: str):
        """Get adjustment details by ID"""
        print("\n" + "=" * 80)
        print(f"🔍 ADJUSTMENT DETAILS - {adjustment_id}")
        print("=" * 80)
        
        try:
            # Scan to find adjustment (since date is sort key, we need to scan)
            response = self.adjustments_table.scan(
                FilterExpression="adjustmentID = :id",
                ExpressionAttributeValues={":id": adjustment_id}
            )
            
            adjustments = response.get('Items', [])
            
            if not adjustments:
                print(f"\n❌ Adjustment with ID '{adjustment_id}' not found!")
                return
            
            adj = adjustments[0]  # Should be unique
            
            print("\n📝 ADJUSTMENT DETAILS:")
            print("-" * 80)
            total_price = adj.get('totalPrice', 0)
            total_decimal = Decimal(str(total_price)) if not isinstance(total_price, Decimal) else total_price
            
            print(f"Adjustment ID: {adj.get('adjustmentID', 'N/A')}")
            print(f"Date: {adj.get('date', 'N/A')}")
            print(f"Type: {adj.get('adjustmentType', 'N/A').replace('_', ' ').title()}")
            print(f"Total Price: ₹{total_decimal:.2f}")
            print(f"Created At: {adj.get('createdAt', 'N/A')}")
            if adj.get('notes'):
                print(f"Notes: {adj.get('notes')}")
            
            items = adj.get('items', [])
            print(f"\n📦 ITEMS ({len(items)}):")
            print("-" * 80)
            print(f"{'Name':<30} {'Quantity':<15} {'Unit':<10} {'Price/Unit':<15} {'Total Price':<15}")
            print("-" * 80)
            
            for item in items:
                name = item.get('name', 'N/A')
                qty = item.get('quantity', 0)
                unit = item.get('unit', '')
                price_per_unit = item.get('purchasePrice', 0)
                total = item.get('totalPrice', 0)
                
                # Convert to Decimal if not already
                qty_decimal = Decimal(str(qty)) if not isinstance(qty, Decimal) else qty
                price_decimal = Decimal(str(price_per_unit)) if not isinstance(price_per_unit, Decimal) else Decimal(price_per_unit)
                total_decimal = Decimal(str(total)) if not isinstance(total, Decimal) else Decimal(total)
                
                print(f"{name:<30} {qty_decimal:<15} {unit:<10} ₹{price_decimal:<14} ₹{total_decimal:<14}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def list_adjustments_by_type(self):
        """List adjustments filtered by type"""
        print("\n" + "=" * 80)
        print("🔎 ADJUSTMENTS BY TYPE")
        print("=" * 80)
        
        print("\n📋 Adjustment Types:")
        print("1. Cart Stock")
        print("2. Return")
        print("3. Damage")
        print("4. Internal Consumption")
        print("5. Extra Given")
        
        type_choice = input("\nSelect Type (1-5): ").strip()
        type_map = {
            '1': 'cart_stock',
            '2': 'return',
            '3': 'damage',
            '4': 'internal_consumption',
            '5': 'extra_given'
        }
        
        if type_choice not in type_map:
            print("❌ ERROR: Invalid type selection!")
            return
        
        adj_type = type_map[type_choice]
        
        try:
            response = self.adjustments_table.scan(
                FilterExpression="adjustmentType = :type",
                ExpressionAttributeValues={":type": adj_type}
            )
            
            adjustments = response.get('Items', [])
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.adjustments_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey'],
                    FilterExpression="adjustmentType = :type",
                    ExpressionAttributeValues={":type": adj_type}
                )
                adjustments.extend(response.get('Items', []))
            
            if not adjustments:
                print(f"\n📦 No {adj_type.replace('_', ' ')} adjustments found.")
                return
            
            adjustments.sort(key=lambda x: x.get('date', ''), reverse=True)
            
            print(f"\n📊 Total {adj_type.replace('_', ' ').title()} Adjustments: {len(adjustments)}")
            print("-" * 80)
            
            for idx, adj in enumerate(adjustments, 1):
                adj_id = adj.get('adjustmentID', 'N/A')
                date = adj.get('date', 'N/A')
                total_price = adj.get('totalPrice', 0)
                items = adj.get('items', [])
                
                # Convert to Decimal for display
                total_decimal = Decimal(str(total_price)) if not isinstance(total_price, Decimal) else total_price
                
                print(f"\n{idx}. {adj_id} - {date}")
                print(f"   Total Price: ₹{total_decimal:.2f}")
                print(f"   Items: {len(items)}")
                
                # Display items details
                if items:
                    print(f"\n   📦 Items Details:")
                    print(f"   {'─' * 76}")
                    print(f"   {'Name':<25} {'Quantity':<12} {'Unit':<8} {'Price/Unit':<12} {'Total':<12}")
                    print(f"   {'─' * 76}")
                    for item in items:
                        name = item.get('name', 'N/A')
                        qty = item.get('quantity', 0)
                        unit = item.get('unit', '')
                        price_per_unit = item.get('purchasePrice', 0)
                        total = item.get('totalPrice', 0)
                        
                        # Convert to Decimal if not already
                        qty_decimal = Decimal(str(qty)) if not isinstance(qty, Decimal) else qty
                        price_decimal = Decimal(str(price_per_unit)) if not isinstance(price_per_unit, Decimal) else Decimal(price_per_unit)
                        total_decimal_item = Decimal(str(total)) if not isinstance(total, Decimal) else Decimal(total)
                        
                        print(f"   {name:<25} {qty_decimal:<12} {unit:<8} ₹{price_decimal:<11} ₹{total_decimal_item:<11}")
                    print(f"   {'─' * 76}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def list_adjustments_by_date_range(self):
        """List adjustments filtered by date range"""
        print("\n" + "=" * 80)
        print("📅 ADJUSTMENTS BY DATE RANGE")
        print("=" * 80)
        
        start_date = input("\nStart Date (YYYY-MM-DD): ").strip()
        end_date = input("End Date (YYYY-MM-DD): ").strip()
        
        if not start_date or not end_date:
            print("❌ ERROR: Both start and end dates are required!")
            return
        
        try:
            # Scan all and filter by date range
            response = self.adjustments_table.scan()
            all_adjustments = response.get('Items', [])
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.adjustments_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                all_adjustments.extend(response.get('Items', []))
            
            # Filter by date range
            filtered = [
                adj for adj in all_adjustments
                if start_date <= adj.get('date', '') <= end_date
            ]
            
            if not filtered:
                print(f"\n📦 No adjustments found between {start_date} and {end_date}.")
                return
            
            filtered.sort(key=lambda x: x.get('date', ''), reverse=True)
            
            print(f"\n📊 Total Adjustments: {len(filtered)}")
            print("-" * 80)
            
            for idx, adj in enumerate(filtered, 1):
                adj_id = adj.get('adjustmentID', 'N/A')
                date = adj.get('date', 'N/A')
                adj_type = adj.get('adjustmentType', 'N/A')
                total_price = adj.get('totalPrice', 0)
                items = adj.get('items', [])
                
                # Convert to Decimal for display
                total_decimal = Decimal(str(total_price)) if not isinstance(total_price, Decimal) else total_price
                
                print(f"\n{idx}. {adj_id} - {date}")
                print(f"   Type: {adj_type.replace('_', ' ').title()}")
                print(f"   Total Price: ₹{total_decimal:.2f}")
                print(f"   Items: {len(items)}")
                
                # Display items details
                if items:
                    print(f"\n   📦 Items Details:")
                    print(f"   {'─' * 76}")
                    print(f"   {'Name':<25} {'Quantity':<12} {'Unit':<8} {'Price/Unit':<12} {'Total':<12}")
                    print(f"   {'─' * 76}")
                    for item in items:
                        name = item.get('name', 'N/A')
                        qty = item.get('quantity', 0)
                        unit = item.get('unit', '')
                        price_per_unit = item.get('purchasePrice', 0)
                        total = item.get('totalPrice', 0)
                        
                        # Convert to Decimal if not already
                        qty_decimal = Decimal(str(qty)) if not isinstance(qty, Decimal) else qty
                        price_decimal = Decimal(str(price_per_unit)) if not isinstance(price_per_unit, Decimal) else Decimal(price_per_unit)
                        total_decimal_item = Decimal(str(total)) if not isinstance(total, Decimal) else Decimal(total)
                        
                        print(f"   {name:<25} {qty_decimal:<12} {unit:<8} ₹{price_decimal:<11} ₹{total_decimal_item:<11}")
                    print(f"   {'─' * 76}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def pincode_management_menu(self):
        """Display pincode management menu"""
        if not self.pincodes_table:
            print("\n⚠️  WARNING: Pincode_management table not found!")
            print("Please create the 'Pincode_management' table in DynamoDB first.")
            input("\nPress Enter to continue...")
            return
        
        while True:
            print("\n" + "=" * 80)
            print("📍 PINCODE MANAGEMENT")
            print("=" * 80)
            print("\n📋 AVAILABLE OPTIONS:")
            print("-" * 80)
            print("1. ➕ Create Pincode")
            print("2. 📋 List All Pincodes")
            print("3. 🔍 Search Pincodes")
            print("4. 🔎 Get Pincode by ID")
            print("5. ✏️  Update Pincode")
            print("6. 🗑️  Delete Pincode")
            print("7. 🔄 Toggle Status")
            print("8. 🚚 Manage Delivery Types")
            print("9. 💰 Manage Delivery Charges")
            print("10. ℹ️  View Table Information")
            print("0. ⬅️  Back to Main Menu")
            print("-" * 80)
            
            choice = input("\nSelect an option (0-10): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.create_pincode()
                input("\nPress Enter to continue...")
            elif choice == '2':
                self.list_pincodes()
                input("\nPress Enter to continue...")
            elif choice == '3':
                self.search_pincodes()
                input("\nPress Enter to continue...")
            elif choice == '4':
                pincode_id = input("\nEnter Pincode ID: ").strip()
                if pincode_id:
                    self.get_pincode_by_id(pincode_id)
                else:
                    print("❌ ERROR: Pincode ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '5':
                pincode_id = input("\nEnter Pincode ID to update: ").strip()
                if pincode_id:
                    self.update_pincode(pincode_id)
                else:
                    print("❌ ERROR: Pincode ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '6':
                pincode_id = input("\nEnter Pincode ID to delete: ").strip()
                if pincode_id:
                    self.delete_pincode(pincode_id)
                else:
                    print("❌ ERROR: Pincode ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '7':
                pincode_id = input("\nEnter Pincode ID to toggle status: ").strip()
                if pincode_id:
                    self.toggle_pincode_status(pincode_id)
                else:
                    print("❌ ERROR: Pincode ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '8':
                self.delivery_types_management_menu()
            elif choice == '9':
                self.delivery_charges_management_menu()
            elif choice == '10':
                self.view_pincode_table_info()
                input("\nPress Enter to continue...")
            else:
                print("❌ ERROR: Invalid choice. Please select a number between 0-10.")
                input("\nPress Enter to continue...")

    def generate_pincode_id(self):
        """Generate sequential pincode ID (PIN-0001)"""
        try:
            response = self.pincodes_table.scan(
                ProjectionExpression='pincodeID'
            )
            
            existing_ids = []
            for item in response.get('Items', []):
                pid = item.get('pincodeID', '')
                if pid.startswith('PIN-'):
                    try:
                        num = int(pid.split('-')[1])
                        existing_ids.append(num)
                    except:
                        pass
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.pincodes_table.scan(
                    ProjectionExpression='pincodeID',
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                for item in response.get('Items', []):
                    pid = item.get('pincodeID', '')
                    if pid.startswith('PIN-'):
                        try:
                            num = int(pid.split('-')[1])
                            existing_ids.append(num)
                        except:
                            pass
            
            if existing_ids:
                next_num = max(existing_ids) + 1
            else:
                next_num = 1
            
            return f"PIN-{next_num:04d}"
        except Exception as e:
            # Fallback to timestamp-based ID
            return f"PIN-{int(datetime.now(timezone.utc).timestamp())}"

    def create_pincode(self):
        """Create a new pincode"""
        print("\n" + "=" * 80)
        print("➕ CREATE NEW PINCODE")
        print("=" * 80)
        
        try:
            # Pincode Number
            pincode_number = input("\n📍 Pincode Number (e.g., 560001): ").strip()
            if not pincode_number:
                print("❌ ERROR: Pincode number is required!")
                return
            
            # Check if pincode number already exists
            response = self.pincodes_table.scan(
                FilterExpression="pincodeNumber = :pn",
                ExpressionAttributeValues={":pn": pincode_number}
            )
            if response.get('Items'):
                print(f"❌ ERROR: Pincode {pincode_number} already exists!")
                return
            
            # Areas
            areas = []
            print("\n📍 Areas / Localities:")
            print("(Enter area names one by one, press Enter with empty input to finish)")
            while True:
                area_name = input("  Area name (or press Enter to finish): ").strip()
                if not area_name:
                    break
                area_id = f"area-{uuid.uuid4().hex[:8]}"
                areas.append({
                    'id': area_id,
                    'name': area_name,
                    'pincodeId': '',  # Will be set after pincode ID is generated
                    'createdAt': datetime.now(timezone.utc).isoformat()
                })
            
            if not areas:
                print("⚠️  WARNING: No areas added. Adding at least one area is recommended.")
                add_anyway = input("Continue without areas? (y/n): ").strip().lower()
                if add_anyway != 'y':
                    return
            
            # Delivery Types (optional)
            delivery_types = []
            if self.delivery_types_table:
                try:
                    shifts_response = self.delivery_types_table.scan()
                    available_shifts = shifts_response.get('Items', [])
                    
                    if available_shifts:
                        print("\n🚚 Available Delivery Types:")
                        for idx, shift in enumerate(available_shifts, 1):
                            shift_type = shift.get('deliveryType', 'N/A')
                            is_active = shift.get('isActive', True)
                            status = "Active" if is_active else "Inactive"
                            print(f"  {idx}. {shift_type} ({status})")
                        
                        shift_choice = input("\nSelect Delivery Type (number, or press Enter to skip): ").strip()
                        if shift_choice:
                            try:
                                idx = int(shift_choice) - 1
                                if 0 <= idx < len(available_shifts):
                                    selected_shift = available_shifts[idx]
                                    delivery_types = [selected_shift.get('deliveryType', '')]
                            except:
                                print("⚠️  Invalid selection, skipping delivery type.")
                except Exception as e:
                    print(f"⚠️  Could not load delivery types: {e}")
            
            # Minimum Order Value and Delivery Charges
            min_order_value = None
            delivery_charge = None
            
            print("\n💰 Delivery Charges Configuration:")
            min_order_input = input("  Minimum Order Value (₹) [optional]: ").strip()
            if min_order_input:
                try:
                    min_order_value = Decimal(min_order_input)
                except:
                    print("⚠️  Invalid minimum order value, skipping.")
            
            charge_input = input("  Delivery Charges (₹) [optional]: ").strip()
            if charge_input:
                try:
                    delivery_charge = Decimal(charge_input)
                    if min_order_value and delivery_charge >= min_order_value:
                        print("❌ ERROR: Delivery charges must be less than minimum order value!")
                        return
                except:
                    print("⚠️  Invalid delivery charge, skipping.")
            
            # Status
            print("\n📊 Status:")
            print("  1. Active")
            print("  2. Inactive")
            status_choice = input("Select status (1-2, default: 1): ").strip() or '1'
            status = 'Active' if status_choice == '1' else 'Inactive'
            
            # Generate IDs
            pincode_id = self.generate_pincode_id()
            current_time = datetime.now(timezone.utc).isoformat()
            
            # Prepare areas with pincode ID
            areas_with_id = []
            for area in areas:
                area['pincodeId'] = pincode_id
                areas_with_id.append(area)
            
            # Prepare charges
            charges = []
            if min_order_value and delivery_charge:
                charge_id = f"charge-{uuid.uuid4().hex[:8]}"
                charges.append({
                    'id': charge_id,
                    'pincodeId': pincode_id,
                    'minOrderValue': min_order_value,
                    'charge': delivery_charge,
                    'isActive': True,
                    'createdAt': current_time,
                    'updatedAt': current_time
                })
            
            # Create pincode item
            pincode_item = {
                'pincodeID': pincode_id,
                'pincodeNumber': pincode_number,
                'status': status,
                'deliveryTypes': delivery_types,
                'areas': areas_with_id,
                'charges': charges,
                'createdAt': current_time,
                'updatedAt': current_time
            }
            
            # Save to DynamoDB
            self.pincodes_table.put_item(Item=pincode_item)
            
            print(f"\n✅ SUCCESS: Pincode created successfully!")
            print(f"   Pincode ID: {pincode_id}")
            print(f"   Pincode Number: {pincode_number}")
            print(f"   Status: {status}")
            print(f"   Areas: {len(areas_with_id)}")
            if charges:
                print(f"   Min Order: ₹{min_order_value}, Charge: ₹{delivery_charge}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def list_pincodes(self):
        """List all pincodes"""
        print("\n" + "=" * 80)
        print("📋 ALL PINCODES")
        print("=" * 80)
        
        try:
            response = self.pincodes_table.scan()
            pincodes = response.get('Items', [])
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.pincodes_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                pincodes.extend(response.get('Items', []))
            
            if not pincodes:
                print("\n📦 No pincodes found.")
                return
            
            # Sort by pincode number
            pincodes.sort(key=lambda x: x.get('pincodeNumber', ''))
            
            print(f"\n📊 Total Pincodes: {len(pincodes)}")
            print("-" * 80)
            print(f"{'Pincode':<12} {'Number':<12} {'Status':<10} {'Areas':<5} {'Delivery Types':<20} {'Min Order':<12} {'Charge':<10}")
            print("-" * 80)
            
            for pincode in pincodes:
                pincode_id = pincode.get('pincodeID', 'N/A')
                pincode_num = pincode.get('pincodeNumber', 'N/A')
                status = pincode.get('status', 'N/A')
                areas = pincode.get('areas', [])
                delivery_types = pincode.get('deliveryTypes', [])
                charges = pincode.get('charges', [])
                
                areas_count = len(areas)
                dt_str = ', '.join(delivery_types[:2]) if delivery_types else 'None'
                if len(delivery_types) > 2:
                    dt_str += '...'
                
                min_order = 'N/A'
                charge = 'N/A'
                if charges:
                    latest_charge = charges[-1]
                    min_order_val = latest_charge.get('minOrderValue', 0)
                    charge_val = latest_charge.get('charge', 0)
                    if isinstance(min_order_val, Decimal):
                        min_order = f"₹{min_order_val}"
                    else:
                        min_order = f"₹{min_order_val}"
                    if isinstance(charge_val, Decimal):
                        charge = f"₹{charge_val}"
                    else:
                        charge = f"₹{charge_val}"
                
                print(f"{pincode_id:<12} {pincode_num:<12} {status:<10} {areas_count:<5} {dt_str:<20} {min_order:<12} {charge:<10}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def get_pincode_by_id(self, pincode_id: str):
        """Get pincode details by ID"""
        print("\n" + "=" * 80)
        print(f"🔎 PINCODE DETAILS: {pincode_id}")
        print("=" * 80)
        
        try:
            response = self.pincodes_table.get_item(Key={'pincodeID': pincode_id})
            
            if 'Item' not in response:
                print(f"\n❌ ERROR: Pincode {pincode_id} not found!")
                return
            
            pincode = response['Item']
            
            print(f"\n📍 PINCODE INFORMATION:")
            print("-" * 80)
            print(f"Pincode ID: {pincode.get('pincodeID', 'N/A')}")
            print(f"Pincode Number: {pincode.get('pincodeNumber', 'N/A')}")
            print(f"Status: {pincode.get('status', 'N/A')}")
            print(f"Created At: {pincode.get('createdAt', 'N/A')}")
            print(f"Updated At: {pincode.get('updatedAt', 'N/A')}")
            
            # Delivery Types
            delivery_types = pincode.get('deliveryTypes', [])
            if delivery_types:
                print(f"\n🚚 Delivery Types: {', '.join(delivery_types)}")
            else:
                print(f"\n🚚 Delivery Types: None")
            
            # Areas
            areas = pincode.get('areas', [])
            if areas:
                print(f"\n📍 Areas ({len(areas)}):")
                for idx, area in enumerate(areas, 1):
                    print(f"  {idx}. {area.get('name', 'N/A')}")
            else:
                print(f"\n📍 Areas: None")
            
            # Charges
            charges = pincode.get('charges', [])
            if charges:
                print(f"\n💰 Delivery Charges ({len(charges)}):")
                for idx, charge in enumerate(charges, 1):
                    min_val = charge.get('minOrderValue', 0)
                    charge_val = charge.get('charge', 0)
                    is_active = charge.get('isActive', True)
                    
                    if isinstance(min_val, Decimal):
                        min_str = f"₹{min_val}"
                    else:
                        min_str = f"₹{min_val}"
                    
                    if isinstance(charge_val, Decimal):
                        charge_str = f"₹{charge_val}"
                    else:
                        charge_str = f"₹{charge_val}"
                    
                    status_str = "Active" if is_active else "Inactive"
                    print(f"  {idx}. Min Order: {min_str}, Charge: {charge_str} ({status_str})")
            else:
                print(f"\n💰 Delivery Charges: Not configured")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def search_pincodes(self):
        """Search pincodes by various criteria"""
        print("\n" + "=" * 80)
        print("🔍 SEARCH PINCODES")
        print("=" * 80)
        
        print("\n📋 Search Options:")
        print("1. By Pincode Number")
        print("2. By Area Name")
        print("3. By Status")
        print("4. By Delivery Type")
        print("0. Cancel")
        
        choice = input("\nSelect search option (0-4): ").strip()
        
        if choice == '0':
            return
        
        try:
            if choice == '1':
                search_term = input("\nEnter pincode number: ").strip()
                if not search_term:
                    print("❌ ERROR: Search term is required!")
                    return
                
                response = self.pincodes_table.scan(
                    FilterExpression="contains(pincodeNumber, :term)",
                    ExpressionAttributeValues={":term": search_term}
                )
                
            elif choice == '2':
                search_term = input("\nEnter area name: ").strip()
                if not search_term:
                    print("❌ ERROR: Search term is required!")
                    return
                
                # Scan all and filter by area name
                response = self.pincodes_table.scan()
                all_pincodes = response.get('Items', [])
                
                # Handle pagination
                while 'LastEvaluatedKey' in response:
                    response = self.pincodes_table.scan(
                        ExclusiveStartKey=response['LastEvaluatedKey']
                    )
                    all_pincodes.extend(response.get('Items', []))
                
                # Filter by area name
                filtered = []
                for pincode in all_pincodes:
                    areas = pincode.get('areas', [])
                    for area in areas:
                        if search_term.lower() in area.get('name', '').lower():
                            filtered.append(pincode)
                            break
                
                # Convert to scan-like response
                response = {'Items': filtered}
                
            elif choice == '3':
                print("\nStatus Options:")
                print("1. Active")
                print("2. Inactive")
                status_choice = input("Select status (1-2): ").strip()
                status = 'Active' if status_choice == '1' else 'Inactive'
                
                response = self.pincodes_table.scan(
                    FilterExpression="status = :status",
                    ExpressionAttributeValues={":status": status}
                )
                
            elif choice == '4':
                if not self.delivery_types_table:
                    print("❌ ERROR: Delivery types table not available!")
                    return
                
                delivery_type = input("\nEnter delivery type: ").strip()
                if not delivery_type:
                    print("❌ ERROR: Delivery type is required!")
                    return
                
                # Scan all and filter by delivery type
                response = self.pincodes_table.scan()
                all_pincodes = response.get('Items', [])
                
                # Handle pagination
                while 'LastEvaluatedKey' in response:
                    response = self.pincodes_table.scan(
                        ExclusiveStartKey=response['LastEvaluatedKey']
                    )
                    all_pincodes.extend(response.get('Items', []))
                
                # Filter by delivery type
                filtered = []
                for pincode in all_pincodes:
                    delivery_types = pincode.get('deliveryTypes', [])
                    if delivery_type in delivery_types:
                        filtered.append(pincode)
                
                # Convert to scan-like response
                response = {'Items': filtered}
                
            else:
                print("❌ ERROR: Invalid choice!")
                return
            
            pincodes = response.get('Items', [])
            
            if not pincodes:
                print("\n📦 No pincodes found matching the search criteria.")
                return
            
            print(f"\n📊 Found {len(pincodes)} pincode(s):")
            print("-" * 80)
            
            for idx, pincode in enumerate(pincodes, 1):
                pincode_id = pincode.get('pincodeID', 'N/A')
                pincode_num = pincode.get('pincodeNumber', 'N/A')
                status = pincode.get('status', 'N/A')
                areas = pincode.get('areas', [])
                areas_str = ', '.join([a.get('name', '') for a in areas[:3]])
                if len(areas) > 3:
                    areas_str += f" (+{len(areas) - 3} more)"
                
                print(f"\n{idx}. {pincode_id} - {pincode_num} ({status})")
                print(f"   Areas: {areas_str if areas_str else 'None'}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def update_pincode(self, pincode_id: str):
        """Update an existing pincode"""
        print("\n" + "=" * 80)
        print(f"✏️  UPDATE PINCODE: {pincode_id}")
        print("=" * 80)
        
        try:
            # Get existing pincode
            response = self.pincodes_table.get_item(Key={'pincodeID': pincode_id})
            
            if 'Item' not in response:
                print(f"\n❌ ERROR: Pincode {pincode_id} not found!")
                return
            
            pincode = response['Item']
            
            print("\n📝 Enter new values (press Enter to keep current value):")
            
            # Pincode Number
            current_pincode_num = pincode.get('pincodeNumber', '')
            new_pincode_num = input(f"\n📍 Pincode Number [{current_pincode_num}]: ").strip()
            if not new_pincode_num:
                new_pincode_num = current_pincode_num
            else:
                # Check if new pincode number already exists (if changed)
                if new_pincode_num != current_pincode_num:
                    check_response = self.pincodes_table.scan(
                        FilterExpression="pincodeNumber = :pn AND pincodeID <> :id",
                        ExpressionAttributeValues={
                            ":pn": new_pincode_num,
                            ":id": pincode_id
                        }
                    )
                    if check_response.get('Items'):
                        print(f"❌ ERROR: Pincode number {new_pincode_num} already exists!")
                        return
            
            # Areas
            current_areas = pincode.get('areas', [])
            print(f"\n📍 Current Areas ({len(current_areas)}):")
            for idx, area in enumerate(current_areas, 1):
                print(f"  {idx}. {area.get('name', 'N/A')}")
            
            update_areas = input("\nUpdate areas? (y/n, default: n): ").strip().lower()
            new_areas = current_areas
            if update_areas == 'y':
                new_areas = []
                print("Enter area names one by one (press Enter with empty input to finish):")
                while True:
                    area_name = input("  Area name: ").strip()
                    if not area_name:
                        break
                    area_id = f"area-{uuid.uuid4().hex[:8]}"
                    new_areas.append({
                        'id': area_id,
                        'name': area_name,
                        'pincodeId': pincode_id,
                        'createdAt': datetime.now(timezone.utc).isoformat()
                    })
            
            # Delivery Types
            current_delivery_types = pincode.get('deliveryTypes', [])
            new_delivery_types = current_delivery_types
            if self.delivery_types_table:
                try:
                    shifts_response = self.delivery_types_table.scan()
                    available_shifts = shifts_response.get('Items', [])
                    
                    if available_shifts:
                        print(f"\n🚚 Current Delivery Types: {', '.join(current_delivery_types) if current_delivery_types else 'None'}")
                        print("Available Delivery Types:")
                        for idx, shift in enumerate(available_shifts, 1):
                            shift_type = shift.get('deliveryType', 'N/A')
                            is_active = shift.get('isActive', True)
                            status = "Active" if is_active else "Inactive"
                            print(f"  {idx}. {shift_type} ({status})")
                        
                        update_dt = input("\nUpdate delivery types? (y/n, default: n): ").strip().lower()
                        if update_dt == 'y':
                            shift_choice = input("Select Delivery Type (number, or press Enter to clear): ").strip()
                            if shift_choice:
                                try:
                                    idx = int(shift_choice) - 1
                                    if 0 <= idx < len(available_shifts):
                                        selected_shift = available_shifts[idx]
                                        new_delivery_types = [selected_shift.get('deliveryType', '')]
                                except:
                                    print("⚠️  Invalid selection, keeping current.")
                            else:
                                new_delivery_types = []
                except:
                    pass
            
            # Charges
            current_charges = pincode.get('charges', [])
            update_charges = input("\nUpdate delivery charges? (y/n, default: n): ").strip().lower()
            new_charges = current_charges
            if update_charges == 'y':
                min_order_input = input("  Minimum Order Value (₹) [optional]: ").strip()
                charge_input = input("  Delivery Charges (₹) [optional]: ").strip()
                
                if min_order_input and charge_input:
                    try:
                        min_order_value = Decimal(min_order_input)
                        delivery_charge = Decimal(charge_input)
                        
                        charge_id = f"charge-{uuid.uuid4().hex[:8]}"
                        new_charges = [{
                            'id': charge_id,
                            'pincodeId': pincode_id,
                            'minOrderValue': min_order_value,
                            'charge': delivery_charge,
                            'isActive': True,
                            'createdAt': datetime.now(timezone.utc).isoformat(),
                            'updatedAt': datetime.now(timezone.utc).isoformat()
                        }]
                    except Exception as e:
                        print(f"⚠️  Invalid values: {e}, keeping current charges.")
            
            # Status
            current_status = pincode.get('status', 'Active')
            print(f"\n📊 Current Status: {current_status}")
            print("1. Active")
            print("2. Inactive")
            status_choice = input(f"Select status (1-2, default: {current_status}): ").strip()
            new_status = current_status
            if status_choice == '1':
                new_status = 'Active'
            elif status_choice == '2':
                new_status = 'Inactive'
            
            # Update pincode
            updated_time = datetime.now(timezone.utc).isoformat()
            pincode['pincodeNumber'] = new_pincode_num
            pincode['areas'] = new_areas
            pincode['deliveryTypes'] = new_delivery_types
            pincode['charges'] = new_charges
            pincode['status'] = new_status
            pincode['updatedAt'] = updated_time
            
            self.pincodes_table.put_item(Item=pincode)
            
            print(f"\n✅ SUCCESS: Pincode {pincode_id} updated successfully!")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def delete_pincode(self, pincode_id: str):
        """Delete a pincode"""
        print("\n" + "=" * 80)
        print(f"🗑️  DELETE PINCODE: {pincode_id}")
        print("=" * 80)
        
        try:
            # Get pincode first to show details
            response = self.pincodes_table.get_item(Key={'pincodeID': pincode_id})
            
            if 'Item' not in response:
                print(f"\n❌ ERROR: Pincode {pincode_id} not found!")
                return
            
            pincode = response['Item']
            pincode_num = pincode.get('pincodeNumber', 'N/A')
            
            print(f"\n⚠️  WARNING: You are about to delete:")
            print(f"   Pincode ID: {pincode_id}")
            print(f"   Pincode Number: {pincode_num}")
            
            confirm = input("\nAre you sure you want to delete this pincode? (yes/no): ").strip().lower()
            
            if confirm == 'yes':
                self.pincodes_table.delete_item(Key={'pincodeID': pincode_id})
                print(f"\n✅ SUCCESS: Pincode {pincode_id} deleted successfully!")
            else:
                print("\n❌ Deletion cancelled.")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def toggle_pincode_status(self, pincode_id: str):
        """Toggle pincode status between Active and Inactive"""
        print("\n" + "=" * 80)
        print(f"🔄 TOGGLE PINCODE STATUS: {pincode_id}")
        print("=" * 80)
        
        try:
            response = self.pincodes_table.get_item(Key={'pincodeID': pincode_id})
            
            if 'Item' not in response:
                print(f"\n❌ ERROR: Pincode {pincode_id} not found!")
                return
            
            pincode = response['Item']
            current_status = pincode.get('status', 'Active')
            new_status = 'Inactive' if current_status == 'Active' else 'Active'
            
            pincode['status'] = new_status
            pincode['updatedAt'] = datetime.now(timezone.utc).isoformat()
            
            self.pincodes_table.put_item(Item=pincode)
            
            print(f"\n✅ SUCCESS: Pincode status changed from {current_status} to {new_status}!")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def delivery_types_management_menu(self):
        """Manage Delivery Types (Shifts)"""
        if not self.delivery_types_table:
            print("\n⚠️  WARNING: Delivery_types table not found!")
            print("Please create the 'Delivery_types' table in DynamoDB first.")
            input("\nPress Enter to continue...")
            return
        
        while True:
            print("\n" + "=" * 80)
            print("🚚 DELIVERY TYPES MANAGEMENT")
            print("=" * 80)
            print("\n📋 AVAILABLE OPTIONS:")
            print("-" * 80)
            print("1. ➕ Create Delivery Type")
            print("2. 📋 List All Delivery Types")
            print("3. 🔎 Get Delivery Type by ID")
            print("4. ✏️  Update Delivery Type")
            print("5. 🗑️  Delete Delivery Type")
            print("6. 🕐 Manage Time Slots")
            print("7. 📍 Assign Delivery Type to Pincode")
            print("0. ⬅️  Back to Pincode Management")
            print("-" * 80)
            
            choice = input("\nSelect an option (0-7): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.create_delivery_type()
                input("\nPress Enter to continue...")
            elif choice == '2':
                self.list_delivery_types()
                input("\nPress Enter to continue...")
            elif choice == '3':
                dt_id = input("\nEnter Delivery Type ID: ").strip()
                if dt_id:
                    self.get_delivery_type_by_id(dt_id)
                else:
                    print("❌ ERROR: Delivery Type ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '4':
                dt_id = input("\nEnter Delivery Type ID to update: ").strip()
                if dt_id:
                    self.update_delivery_type(dt_id)
                else:
                    print("❌ ERROR: Delivery Type ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '5':
                dt_id = input("\nEnter Delivery Type ID to delete: ").strip()
                if dt_id:
                    self.delete_delivery_type(dt_id)
                else:
                    print("❌ ERROR: Delivery Type ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '6':
                self.time_slots_management_menu()
            elif choice == '7':
                self.assign_delivery_type_to_pincode()
                input("\nPress Enter to continue...")
            else:
                print("❌ ERROR: Invalid choice. Please select a number between 0-7.")
                input("\nPress Enter to continue...")

    def time_slots_management_menu(self):
        """Manage Time Slots"""
        if not self.delivery_types_table:
            print("\n⚠️  WARNING: Delivery_types table not found!")
            print("Please create the 'Delivery_types' table first (slots are stored within delivery types).")
            input("\nPress Enter to continue...")
            return
        
        while True:
            print("\n" + "=" * 80)
            print("🕐 TIME SLOTS MANAGEMENT")
            print("=" * 80)
            print("\n📋 AVAILABLE OPTIONS:")
            print("-" * 80)
            print("1. ➕ Create Time Slot")
            print("2. 📋 List All Time Slots")
            print("3. 🔎 Get Time Slot by ID")
            print("4. ✏️  Update Time Slot")
            print("5. 🗑️  Delete Time Slot")
            print("0. ⬅️  Back to Delivery Types Management")
            print("-" * 80)
            
            choice = input("\nSelect an option (0-5): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.create_time_slot()
                input("\nPress Enter to continue...")
            elif choice == '2':
                self.list_time_slots()
                input("\nPress Enter to continue...")
            elif choice == '3':
                slot_id = input("\nEnter Time Slot ID: ").strip()
                if slot_id:
                    self.get_time_slot_by_id(slot_id)
                else:
                    print("❌ ERROR: Time Slot ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '4':
                slot_id = input("\nEnter Time Slot ID to update: ").strip()
                if slot_id:
                    self.update_time_slot(slot_id)
                else:
                    print("❌ ERROR: Time Slot ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '5':
                slot_id = input("\nEnter Time Slot ID to delete: ").strip()
                if slot_id:
                    self.delete_time_slot(slot_id)
                else:
                    print("❌ ERROR: Time Slot ID is required!")
                input("\nPress Enter to continue...")
            else:
                print("❌ ERROR: Invalid choice. Please select a number between 0-5.")
                input("\nPress Enter to continue...")

    def delivery_charges_management_menu(self):
        """Manage Delivery Charges"""
        if not self.pincodes_table:
            print("\n⚠️  WARNING: Pincode_management table not found!")
            print("Please create the 'Pincode_management' table in DynamoDB first.")
            input("\nPress Enter to continue...")
            return
        
        while True:
            print("\n" + "=" * 80)
            print("💰 DELIVERY CHARGES MANAGEMENT")
            print("=" * 80)
            print("\n📋 AVAILABLE OPTIONS:")
            print("-" * 80)
            print("1. ➕ Add Delivery Charge to Pincode")
            print("2. 📋 List All Delivery Charges")
            print("3. 🔎 Get Charges by Pincode ID")
            print("4. ✏️  Update Delivery Charge")
            print("5. 🗑️  Delete Delivery Charge")
            print("0. ⬅️  Back to Pincode Management")
            print("-" * 80)
            
            choice = input("\nSelect an option (0-5): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                pincode_id = input("\nEnter Pincode ID: ").strip()
                if pincode_id:
                    self.add_delivery_charge(pincode_id)
                else:
                    print("❌ ERROR: Pincode ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '2':
                self.list_all_delivery_charges()
                input("\nPress Enter to continue...")
            elif choice == '3':
                pincode_id = input("\nEnter Pincode ID: ").strip()
                if pincode_id:
                    self.get_charges_by_pincode(pincode_id)
                else:
                    print("❌ ERROR: Pincode ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '4':
                pincode_id = input("\nEnter Pincode ID: ").strip()
                charge_id = input("Enter Charge ID: ").strip()
                if pincode_id and charge_id:
                    self.update_delivery_charge(pincode_id, charge_id)
                else:
                    print("❌ ERROR: Both Pincode ID and Charge ID are required!")
                input("\nPress Enter to continue...")
            elif choice == '5':
                pincode_id = input("\nEnter Pincode ID: ").strip()
                charge_id = input("Enter Charge ID: ").strip()
                if pincode_id and charge_id:
                    self.delete_delivery_charge(pincode_id, charge_id)
                else:
                    print("❌ ERROR: Both Pincode ID and Charge ID are required!")
                input("\nPress Enter to continue...")
            else:
                print("❌ ERROR: Invalid choice. Please select a number between 0-5.")
                input("\nPress Enter to continue...")

    def view_pincode_table_info(self):
        """View pincode table information"""
        print("\n" + "=" * 80)
        print("ℹ️  PINCODE TABLE INFORMATION")
        print("=" * 80)
        
        try:
            table = self.pincodes_table
            table_desc = table.meta.client.describe_table(TableName='Pincode_management')
            
            print(f"\n📊 Table Name: Pincode_management")
            print(f"📊 Table Status: {table_desc['Table']['TableStatus']}")
            print(f"📊 Item Count: {table_desc['Table'].get('ItemCount', 'N/A')}")
            print(f"📊 Table Size: {table_desc['Table'].get('TableSizeBytes', 0)} bytes")
            
            # Get key schema
            key_schema = table_desc['Table'].get('KeySchema', [])
            if key_schema:
                print(f"\n🔑 Key Schema:")
                for key in key_schema:
                    print(f"   {key['AttributeName']}: {key['KeyType']}")
            
            # Get attribute definitions
            attr_defs = table_desc['Table'].get('AttributeDefinitions', [])
            if attr_defs:
                print(f"\n📋 Attribute Definitions:")
                for attr in attr_defs:
                    print(f"   {attr['AttributeName']}: {attr['AttributeType']}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    # ==================== DELIVERY TYPES MANAGEMENT FUNCTIONS ====================
    
    def generate_delivery_type_id(self):
        """Generate sequential delivery type ID (DT-0001)"""
        try:
            response = self.delivery_types_table.scan(ProjectionExpression='Delivery_type_id')
            existing_ids = []
            for item in response.get('Items', []):
                dt_id = item.get('Delivery_type_id', '')
                if dt_id.startswith('DT-'):
                    try:
                        num = int(dt_id.split('-')[1])
                        existing_ids.append(num)
                    except:
                        pass
            
            while 'LastEvaluatedKey' in response:
                response = self.delivery_types_table.scan(
                    ProjectionExpression='Delivery_type_id',
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                for item in response.get('Items', []):
                    dt_id = item.get('Delivery_type_id', '')
                    if dt_id.startswith('DT-'):
                        try:
                            num = int(dt_id.split('-')[1])
                            existing_ids.append(num)
                        except:
                            pass
            
            if existing_ids:
                next_num = max(existing_ids) + 1
            else:
                next_num = 1
            
            return f"DT-{next_num:04d}"
        except Exception:
            return f"DT-{int(datetime.now(timezone.utc).timestamp())}"

    def create_delivery_type(self):
        """Create a new delivery type"""
        print("\n" + "=" * 80)
        print("➕ CREATE NEW DELIVERY TYPE")
        print("=" * 80)
        
        try:
            delivery_type_name = input("\n🚚 Delivery Type Name (e.g., Same Day Delivery): ").strip()
            if not delivery_type_name:
                print("❌ ERROR: Delivery type name is required!")
                return
            
            # Check if delivery type already exists
            response = self.delivery_types_table.scan(
                FilterExpression="deliveryType = :dt",
                ExpressionAttributeValues={":dt": delivery_type_name}
            )
            if response.get('Items'):
                print(f"❌ ERROR: Delivery type '{delivery_type_name}' already exists!")
                return
            
            print("\n📊 Status:")
            print("  1. Active")
            print("  2. Inactive")
            status_choice = input("Select status (1-2, default: 1): ").strip() or '1'
            is_active = status_choice == '1'
            
            dt_id = self.generate_delivery_type_id()
            current_time = datetime.now(timezone.utc).isoformat()
            
            delivery_type_item = {
                'Delivery_type_id': dt_id,
                'deliveryType': delivery_type_name,
                'isActive': is_active,
                'slots': [],  # Empty slots array initially
                'createdAt': current_time,
                'updatedAt': current_time
            }
            
            self.delivery_types_table.put_item(Item=delivery_type_item)
            
            print(f"\n✅ SUCCESS: Delivery type created successfully!")
            print(f"   ID: {dt_id}")
            print(f"   Name: {delivery_type_name}")
            print(f"   Status: {'Active' if is_active else 'Inactive'}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def list_delivery_types(self):
        """List all delivery types"""
        print("\n" + "=" * 80)
        print("📋 ALL DELIVERY TYPES")
        print("=" * 80)
        
        try:
            response = self.delivery_types_table.scan()
            delivery_types = response.get('Items', [])
            
            while 'LastEvaluatedKey' in response:
                response = self.delivery_types_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                delivery_types.extend(response.get('Items', []))
            
            if not delivery_types:
                print("\n📦 No delivery types found.")
                return
            
            delivery_types.sort(key=lambda x: x.get('deliveryType', ''))
            
            print(f"\n📊 Total Delivery Types: {len(delivery_types)}")
            print("-" * 80)
            print(f"{'ID':<12} {'Delivery Type':<30} {'Status':<10} {'Slots':<10}")
            print("-" * 80)
            
            for dt in delivery_types:
                dt_id = dt.get('Delivery_type_id', 'N/A')
                dt_name = dt.get('deliveryType', 'N/A')
                is_active = dt.get('isActive', True)
                slots = dt.get('slots', [])
                status = 'Active' if is_active else 'Inactive'
                
                print(f"{dt_id:<12} {dt_name:<30} {status:<10} {len(slots):<10}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def get_delivery_type_by_id(self, dt_id: str):
        """Get delivery type details by ID"""
        print("\n" + "=" * 80)
        print(f"🔎 DELIVERY TYPE DETAILS: {dt_id}")
        print("=" * 80)
        
        try:
            response = self.delivery_types_table.get_item(Key={'Delivery_type_id': dt_id})
            
            if 'Item' not in response:
                print(f"\n❌ ERROR: Delivery type {dt_id} not found!")
                return
            
            dt = response['Item']
            
            print(f"\n🚚 DELIVERY TYPE INFORMATION:")
            print("-" * 80)
            print(f"ID: {dt.get('Delivery_type_id', 'N/A')}")
            print(f"Delivery Type: {dt.get('deliveryType', 'N/A')}")
            print(f"Status: {'Active' if dt.get('isActive', True) else 'Inactive'}")
            print(f"Created At: {dt.get('createdAt', 'N/A')}")
            print(f"Updated At: {dt.get('updatedAt', 'N/A')}")
            
            slots = dt.get('slots', [])
            if slots:
                print(f"\n🕐 Time Slots ({len(slots)}):")
                for idx, slot in enumerate(slots, 1):
                    slot_name = slot.get('name', 'N/A')
                    start_time = slot.get('startTime', 'N/A')
                    end_time = slot.get('endTime', 'N/A')
                    is_active = slot.get('isActive', True)
                    print(f"  {idx}. {slot_name} ({start_time} - {end_time}) - {'Active' if is_active else 'Inactive'}")
            else:
                print(f"\n🕐 Time Slots: None")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def update_delivery_type(self, dt_id: str):
        """Update an existing delivery type"""
        print("\n" + "=" * 80)
        print(f"✏️  UPDATE DELIVERY TYPE: {dt_id}")
        print("=" * 80)
        
        try:
            response = self.delivery_types_table.get_item(Key={'Delivery_type_id': dt_id})
            
            if 'Item' not in response:
                print(f"\n❌ ERROR: Delivery type {dt_id} not found!")
                return
            
            dt = response['Item']
            
            print("\n📝 Enter new values (press Enter to keep current value):")
            
            current_name = dt.get('deliveryType', '')
            new_name = input(f"\n🚚 Delivery Type Name [{current_name}]: ").strip()
            if not new_name:
                new_name = current_name
            else:
                # Check if new name already exists (if changed)
                if new_name != current_name:
                    check_response = self.delivery_types_table.scan(
                        FilterExpression="deliveryType = :dt AND Delivery_type_id <> :id",
                        ExpressionAttributeValues={
                            ":dt": new_name,
                            ":id": dt_id
                        }
                    )
                    if check_response.get('Items'):
                        print(f"❌ ERROR: Delivery type '{new_name}' already exists!")
                        return
            
            current_status = dt.get('isActive', True)
            print(f"\n📊 Current Status: {'Active' if current_status else 'Inactive'}")
            print("1. Active")
            print("2. Inactive")
            status_choice = input(f"Select status (1-2, default: {'1' if current_status else '2'}): ").strip()
            new_is_active = current_status
            if status_choice == '1':
                new_is_active = True
            elif status_choice == '2':
                new_is_active = False
            
            dt['deliveryType'] = new_name
            dt['isActive'] = new_is_active
            dt['updatedAt'] = datetime.now(timezone.utc).isoformat()
            
            self.delivery_types_table.put_item(Item=dt)
            
            print(f"\n✅ SUCCESS: Delivery type {dt_id} updated successfully!")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def delete_delivery_type(self, dt_id: str):
        """Delete a delivery type"""
        print("\n" + "=" * 80)
        print(f"🗑️  DELETE DELIVERY TYPE: {dt_id}")
        print("=" * 80)
        
        try:
            response = self.delivery_types_table.get_item(Key={'Delivery_type_id': dt_id})
            
            if 'Item' not in response:
                print(f"\n❌ ERROR: Delivery type {dt_id} not found!")
                return
            
            dt = response['Item']
            dt_name = dt.get('deliveryType', 'N/A')
            
            print(f"\n⚠️  WARNING: You are about to delete:")
            print(f"   ID: {dt_id}")
            print(f"   Name: {dt_name}")
            
            confirm = input("\nAre you sure you want to delete this delivery type? (yes/no): ").strip().lower()
            
            if confirm == 'yes':
                self.delivery_types_table.delete_item(Key={'Delivery_type_id': dt_id})
                print(f"\n✅ SUCCESS: Delivery type {dt_id} deleted successfully!")
            else:
                print("\n❌ Deletion cancelled.")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def toggle_delivery_type_status(self, dt_id: str):
        """Toggle delivery type status"""
        try:
            response = self.delivery_types_table.get_item(Key={'Delivery_type_id': dt_id})
            
            if 'Item' not in response:
                print(f"\n❌ ERROR: Delivery type {dt_id} not found!")
                return
            
            dt = response['Item']
            current_status = dt.get('isActive', True)
            new_status = not current_status
            
            dt['isActive'] = new_status
            dt['updatedAt'] = datetime.now(timezone.utc).isoformat()
            
            self.delivery_types_table.put_item(Item=dt)
            
            print(f"\n✅ SUCCESS: Delivery type status changed to {'Active' if new_status else 'Inactive'}!")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    # ==================== TIME SLOTS MANAGEMENT FUNCTIONS ====================
    # Note: Time slots are stored nested inside Delivery_types table
    
    def create_time_slot(self):
        """Create a new time slot for a delivery type"""
        print("\n" + "=" * 80)
        print("➕ CREATE NEW TIME SLOT")
        print("=" * 80)
        
        try:
            # First, list available delivery types
            response = self.delivery_types_table.scan()
            delivery_types = response.get('Items', [])
            
            while 'LastEvaluatedKey' in response:
                response = self.delivery_types_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                delivery_types.extend(response.get('Items', []))
            
            if not delivery_types:
                print("\n❌ ERROR: No delivery types found!")
                print("Please create a delivery type first.")
                return
            
            # Filter only active delivery types
            active_delivery_types = [dt for dt in delivery_types if dt.get('isActive', True)]
            
            if not active_delivery_types:
                print("\n❌ ERROR: No active delivery types found!")
                print("Please create or activate a delivery type first.")
                return
            
            print("\n📋 Available Delivery Types:")
            print("-" * 80)
            for idx, dt in enumerate(active_delivery_types, 1):
                dt_id = dt.get('Delivery_type_id', 'N/A')
                dt_name = dt.get('deliveryType', 'N/A')
                print(f"{idx}. {dt_name} (ID: {dt_id})")
            
            dt_choice = input(f"\nSelect Delivery Type (1-{len(active_delivery_types)}): ").strip()
            try:
                dt_index = int(dt_choice) - 1
                if dt_index < 0 or dt_index >= len(active_delivery_types):
                    print("❌ ERROR: Invalid selection!")
                    return
                selected_dt = active_delivery_types[dt_index]
            except ValueError:
                print("❌ ERROR: Invalid input! Please enter a number.")
                return
            
            dt_id = selected_dt.get('Delivery_type_id')
            dt_name = selected_dt.get('deliveryType', 'N/A')
            
            print(f"\n✅ Selected: {dt_name}")
            
            # Get slot details
            slot_name = input("\n🕐 Slot Name (e.g., Morning Slot, Afternoon Slot): ").strip()
            if not slot_name:
                print("❌ ERROR: Slot name is required!")
                return
            
            start_time = input("⏰ Start Time (12-hour format, e.g., 9:00 AM): ").strip()
            if not start_time:
                print("❌ ERROR: Start time is required!")
                return
            
            end_time = input("⏰ End Time (12-hour format, e.g., 5:00 PM): ").strip()
            if not end_time:
                print("❌ ERROR: End time is required!")
                return
            
            print("\n📊 Status:")
            print("  1. Active")
            print("  2. Inactive")
            status_choice = input("Select status (1-2, default: 1): ").strip() or '1'
            is_active = status_choice == '1'
            
            # Generate slot ID
            slot_id = f"slot-{uuid.uuid4().hex[:8]}"
            current_time = datetime.now(timezone.utc).isoformat()
            
            new_slot = {
                'id': slot_id,
                'name': slot_name,
                'startTime': start_time,
                'endTime': end_time,
                'isActive': is_active,
                'createdAt': current_time,
                'updatedAt': current_time
            }
            
            # Add slot to delivery type's slots array
            slots = selected_dt.get('slots', [])
            slots.append(new_slot)
            selected_dt['slots'] = slots
            selected_dt['updatedAt'] = current_time
            
            self.delivery_types_table.put_item(Item=selected_dt)
            
            print(f"\n✅ SUCCESS: Time slot created successfully!")
            print(f"   Slot ID: {slot_id}")
            print(f"   Name: {slot_name}")
            print(f"   Delivery Type: {dt_name}")
            print(f"   Time: {start_time} - {end_time}")
            print(f"   Status: {'Active' if is_active else 'Inactive'}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
        
    def list_time_slots(self):
        """List all time slots across all delivery types"""
        print("\n" + "=" * 80)
        print("📋 ALL TIME SLOTS")
        print("=" * 80)
        
        try:
            response = self.delivery_types_table.scan()
            delivery_types = response.get('Items', [])
            
            while 'LastEvaluatedKey' in response:
                response = self.delivery_types_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                delivery_types.extend(response.get('Items', []))
            
            all_slots = []
            for dt in delivery_types:
                dt_id = dt.get('Delivery_type_id', 'N/A')
                dt_name = dt.get('deliveryType', 'N/A')
                slots = dt.get('slots', [])
                for slot in slots:
                    slot['_deliveryTypeId'] = dt_id
                    slot['_deliveryTypeName'] = dt_name
                    all_slots.append(slot)
            
            if not all_slots:
                print("\n📦 No time slots found.")
                return
            
            print(f"\n📊 Total Time Slots: {len(all_slots)}")
            print("-" * 80)
            print(f"{'Slot ID':<15} {'Name':<20} {'Delivery Type':<25} {'Time':<20} {'Status':<10}")
            print("-" * 80)
            
            for slot in all_slots:
                slot_id = slot.get('id', 'N/A')
                slot_name = slot.get('name', 'N/A')
                dt_name = slot.get('_deliveryTypeName', 'N/A')
                start_time = slot.get('startTime', 'N/A')
                end_time = slot.get('endTime', 'N/A')
                is_active = slot.get('isActive', True)
                
                time_str = f"{start_time} - {end_time}"
                status = 'Active' if is_active else 'Inactive'
                
                print(f"{slot_id:<15} {slot_name:<20} {dt_name:<25} {time_str:<20} {status:<10}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
        
    def get_time_slot_by_id(self, slot_id: str):
        """Get time slot details by ID"""
        print("\n" + "=" * 80)
        print(f"🔎 TIME SLOT DETAILS: {slot_id}")
        print("=" * 80)
        
        try:
            response = self.delivery_types_table.scan()
            delivery_types = response.get('Items', [])
            
            while 'LastEvaluatedKey' in response:
                response = self.delivery_types_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                delivery_types.extend(response.get('Items', []))
            
            found_slot = None
            found_dt = None
            
            for dt in delivery_types:
                slots = dt.get('slots', [])
                for slot in slots:
                    if slot.get('id') == slot_id:
                        found_slot = slot
                        found_dt = dt
                        break
                if found_slot:
                    break
            
            if not found_slot:
                print(f"\n❌ ERROR: Time slot {slot_id} not found!")
                return
            
            dt_id = found_dt.get('Delivery_type_id', 'N/A')
            dt_name = found_dt.get('deliveryType', 'N/A')
            
            print(f"\n🕐 TIME SLOT INFORMATION:")
            print("-" * 80)
            print(f"Slot ID: {found_slot.get('id', 'N/A')}")
            print(f"Name: {found_slot.get('name', 'N/A')}")
            print(f"Delivery Type: {dt_name} (ID: {dt_id})")
            print(f"Start Time: {found_slot.get('startTime', 'N/A')}")
            print(f"End Time: {found_slot.get('endTime', 'N/A')}")
            print(f"Status: {'Active' if found_slot.get('isActive', True) else 'Inactive'}")
            print(f"Created At: {found_slot.get('createdAt', 'N/A')}")
            print(f"Updated At: {found_slot.get('updatedAt', 'N/A')}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
        
    def update_time_slot(self, slot_id: str):
        """Update a time slot"""
        print("\n" + "=" * 80)
        print(f"✏️  UPDATE TIME SLOT: {slot_id}")
        print("=" * 80)
        
        try:
            # Find the slot
            response = self.delivery_types_table.scan()
            delivery_types = response.get('Items', [])
            
            while 'LastEvaluatedKey' in response:
                response = self.delivery_types_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                delivery_types.extend(response.get('Items', []))
            
            found_slot = None
            found_dt = None
            slot_index = None
            
            for dt in delivery_types:
                slots = dt.get('slots', [])
                for idx, slot in enumerate(slots):
                    if slot.get('id') == slot_id:
                        found_slot = slot
                        found_dt = dt
                        slot_index = idx
                        break
                if found_slot:
                    break
            
            if not found_slot:
                print(f"\n❌ ERROR: Time slot {slot_id} not found!")
                return
            
            print("\n📝 Enter new values (press Enter to keep current value):")
            
            current_name = found_slot.get('name', '')
            current_start = found_slot.get('startTime', '')
            current_end = found_slot.get('endTime', '')
            current_status = found_slot.get('isActive', True)
            
            new_name = input(f"\n🕐 Slot Name [{current_name}]: ").strip()
            if not new_name:
                new_name = current_name
            
            new_start = input(f"⏰ Start Time [{current_start}]: ").strip()
            if not new_start:
                new_start = current_start
            
            new_end = input(f"⏰ End Time [{current_end}]: ").strip()
            if not new_end:
                new_end = current_end
            
            print(f"\n📊 Current Status: {'Active' if current_status else 'Inactive'}")
            print("1. Active")
            print("2. Inactive")
            status_choice = input(f"Select status (1-2, default: {'1' if current_status else '2'}): ").strip()
            new_is_active = current_status
            if status_choice == '1':
                new_is_active = True
            elif status_choice == '2':
                new_is_active = False
            
            # Update the slot
            found_slot['name'] = new_name
            found_slot['startTime'] = new_start
            found_slot['endTime'] = new_end
            found_slot['isActive'] = new_is_active
            found_slot['updatedAt'] = datetime.now(timezone.utc).isoformat()
            
            # Update the delivery type's slots array
            slots = found_dt.get('slots', [])
            slots[slot_index] = found_slot
            found_dt['slots'] = slots
            found_dt['updatedAt'] = datetime.now(timezone.utc).isoformat()
            
            self.delivery_types_table.put_item(Item=found_dt)
            
            print(f"\n✅ SUCCESS: Time slot {slot_id} updated successfully!")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
        
    def delete_time_slot(self, slot_id: str):
        """Delete a time slot"""
        print("\n" + "=" * 80)
        print(f"🗑️  DELETE TIME SLOT: {slot_id}")
        print("=" * 80)
        
        try:
            # Find the slot
            response = self.delivery_types_table.scan()
            delivery_types = response.get('Items', [])
            
            while 'LastEvaluatedKey' in response:
                response = self.delivery_types_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                delivery_types.extend(response.get('Items', []))
            
            found_slot = None
            found_dt = None
            
            for dt in delivery_types:
                slots = dt.get('slots', [])
                for slot in slots:
                    if slot.get('id') == slot_id:
                        found_slot = slot
                        found_dt = dt
                        break
                if found_slot:
                    break
            
            if not found_slot:
                print(f"\n❌ ERROR: Time slot {slot_id} not found!")
                return
            
            slot_name = found_slot.get('name', 'N/A')
            dt_name = found_dt.get('deliveryType', 'N/A')
            
            print(f"\n⚠️  WARNING: You are about to delete:")
            print(f"   Slot ID: {slot_id}")
            print(f"   Name: {slot_name}")
            print(f"   Delivery Type: {dt_name}")
            print(f"   Time: {found_slot.get('startTime', 'N/A')} - {found_slot.get('endTime', 'N/A')}")
            
            confirm = input("\nAre you sure you want to delete this time slot? (yes/no): ").strip().lower()
            
            if confirm == 'yes':
                # Remove slot from delivery type's slots array
                slots = found_dt.get('slots', [])
                slots = [s for s in slots if s.get('id') != slot_id]
                found_dt['slots'] = slots
                found_dt['updatedAt'] = datetime.now(timezone.utc).isoformat()
                
                self.delivery_types_table.put_item(Item=found_dt)
                
                print(f"\n✅ SUCCESS: Time slot {slot_id} deleted successfully!")
            else:
                print("\n❌ Deletion cancelled.")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
        
    def toggle_time_slot_status(self, slot_id: str):
        """Toggle time slot status"""
        print("\n⚠️  NOTE: Time slot status toggle will be implemented.")
        # TODO: Implement
    
    def assign_delivery_type_to_pincode(self):
        """Assign delivery type(s) to a pincode"""
        print("\n" + "=" * 80)
        print("📍 ASSIGN DELIVERY TYPE TO PINCODE")
        print("=" * 80)
        
        try:
            if not self.pincodes_table:
                print("\n❌ ERROR: Pincode_management table not found!")
                return
            
            if not self.delivery_types_table:
                print("\n❌ ERROR: Delivery_types table not found!")
                return
            
            # Step 1: List and select pincode
            print("\n📋 Available Pincodes:")
            response = self.pincodes_table.scan()
            pincodes = response.get('Items', [])
            
            while 'LastEvaluatedKey' in response:
                response = self.pincodes_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                pincodes.extend(response.get('Items', []))
            
            if not pincodes:
                print("\n❌ ERROR: No pincodes found!")
                return
            
            # Filter active pincodes
            active_pincodes = [p for p in pincodes if p.get('status') == 'Active']
            
            if not active_pincodes:
                print("\n❌ ERROR: No active pincodes found!")
                return
            
            print("-" * 80)
            for idx, pincode in enumerate(active_pincodes, 1):
                pincode_id = pincode.get('pincodeID', 'N/A')
                pincode_num = pincode.get('pincodeNumber', 'N/A')
                current_dts = pincode.get('deliveryTypes', [])
                dt_str = ', '.join(current_dts) if current_dts else 'None'
                print(f"{idx}. {pincode_num} (ID: {pincode_id}) - Current Delivery Types: {dt_str}")
            
            pincode_choice = input(f"\nSelect Pincode (1-{len(active_pincodes)}): ").strip()
            try:
                pincode_idx = int(pincode_choice) - 1
                if pincode_idx < 0 or pincode_idx >= len(active_pincodes):
                    print("❌ ERROR: Invalid selection!")
                    return
                selected_pincode = active_pincodes[pincode_idx]
            except ValueError:
                print("❌ ERROR: Invalid input! Please enter a number.")
                return
            
            pincode_id = selected_pincode.get('pincodeID')
            pincode_num = selected_pincode.get('pincodeNumber', 'N/A')
            current_delivery_types = selected_pincode.get('deliveryTypes', [])
            
            print(f"\n✅ Selected: {pincode_num} (ID: {pincode_id})")
            if current_delivery_types:
                print(f"   Current Delivery Types: {', '.join(current_delivery_types)}")
            else:
                print(f"   Current Delivery Types: None")
            
            # Step 2: List and select delivery types
            print("\n🚚 Available Delivery Types:")
            dt_response = self.delivery_types_table.scan()
            delivery_types = dt_response.get('Items', [])
            
            while 'LastEvaluatedKey' in dt_response:
                dt_response = self.delivery_types_table.scan(
                    ExclusiveStartKey=dt_response['LastEvaluatedKey']
                )
                delivery_types.extend(dt_response.get('Items', []))
            
            # Filter active delivery types
            active_delivery_types = [dt for dt in delivery_types if dt.get('isActive', True)]
            
            if not active_delivery_types:
                print("\n❌ ERROR: No active delivery types found!")
                return
            
            print("-" * 80)
            for idx, dt in enumerate(active_delivery_types, 1):
                dt_id = dt.get('Delivery_type_id', 'N/A')
                dt_name = dt.get('deliveryType', 'N/A')
                slots = dt.get('slots', [])
                active_slots = [s for s in slots if s.get('isActive', True)]
                is_assigned = dt_name in current_delivery_types
                assigned_mark = " ✓ (Already Assigned)" if is_assigned else ""
                print(f"{idx}. {dt_name} (ID: {dt_id}) - Slots: {len(active_slots)}{assigned_mark}")
            
            print("\n💡 You can select multiple delivery types by entering numbers separated by commas (e.g., 1,2,3)")
            dt_choices = input(f"\nSelect Delivery Type(s) (1-{len(active_delivery_types)}): ").strip()
            
            if not dt_choices:
                print("❌ ERROR: At least one delivery type must be selected!")
                return
            
            # Parse multiple selections
            selected_indices = []
            for choice in dt_choices.split(','):
                try:
                    idx = int(choice.strip()) - 1
                    if 0 <= idx < len(active_delivery_types):
                        selected_indices.append(idx)
                except ValueError:
                    pass
            
            if not selected_indices:
                print("❌ ERROR: Invalid selection!")
                return
            
            # Get selected delivery types
            selected_delivery_types = []
            selected_dt_names = []
            for idx in selected_indices:
                dt = active_delivery_types[idx]
                dt_name = dt.get('deliveryType', '')
                if dt_name:
                    selected_delivery_types.append(dt)
                    selected_dt_names.append(dt_name)
            
            if not selected_delivery_types:
                print("❌ ERROR: No valid delivery types selected!")
                return
            
            # Step 3: Update pincode
            print(f"\n📝 Assigning delivery types to pincode {pincode_num}:")
            for dt_name in selected_dt_names:
                print(f"   - {dt_name}")
            
            confirm = input("\n✅ Confirm assignment? (y/n): ").strip().lower()
            if confirm != 'y':
                print("❌ Assignment cancelled.")
                return
            
            # Update pincode's deliveryTypes array
            selected_pincode['deliveryTypes'] = selected_dt_names
            selected_pincode['updatedAt'] = datetime.now(timezone.utc).isoformat()
            
            self.pincodes_table.put_item(Item=selected_pincode)
            
            print(f"\n✅ SUCCESS: Delivery types assigned successfully!")
            print(f"   Pincode: {pincode_num} (ID: {pincode_id})")
            print(f"   Assigned Delivery Types: {', '.join(selected_dt_names)}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    # ==================== DELIVERY CHARGES MANAGEMENT FUNCTIONS ====================
    # Note: Delivery charges are stored nested inside Pincode_management table
    
    def add_delivery_charge(self, pincode_id: str):
        """Add delivery charge to a pincode"""
        print("\n" + "=" * 80)
        print(f"➕ ADD DELIVERY CHARGE TO PINCODE: {pincode_id}")
        print("=" * 80)
        
        try:
            response = self.pincodes_table.get_item(Key={'pincodeID': pincode_id})
            
            if 'Item' not in response:
                print(f"\n❌ ERROR: Pincode {pincode_id} not found!")
                return
            
            pincode = response['Item']
            
            min_order_input = input("\n💰 Minimum Order Value (₹): ").strip()
            charge_input = input("💰 Delivery Charge (₹): ").strip()
            
            if not min_order_input or not charge_input:
                print("❌ ERROR: Minimum order value and delivery charge are required!")
                return
            
            try:
                min_order_value = Decimal(min_order_input)
                delivery_charge = Decimal(charge_input)
                
                charge_id = f"charge-{uuid.uuid4().hex[:8]}"
                current_time = datetime.now(timezone.utc).isoformat()
                
                new_charge = {
                    'id': charge_id,
                    'pincodeId': pincode_id,
                    'minOrderValue': min_order_value,
                    'charge': delivery_charge,
                    'isActive': True,
                    'createdAt': current_time,
                    'updatedAt': current_time
                }
                
                charges = pincode.get('charges', [])
                if charges:
                    print("\n⚠️  INFO: Existing delivery charges found. Replacing with the new values.")
                    charges = [new_charge]
                else:
                    charges = [new_charge]
                
                pincode['charges'] = charges
                pincode['updatedAt'] = current_time
                
                self.pincodes_table.put_item(Item=pincode)
                
                print(f"\n✅ SUCCESS: Delivery charge added successfully!")
                print(f"   Charge ID: {charge_id}")
                
            except ValueError:
                print("❌ ERROR: Invalid numeric values!")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def list_all_delivery_charges(self):
        """List all delivery charges across all pincodes"""
        print("\n" + "=" * 80)
        print("📋 ALL DELIVERY CHARGES")
        print("=" * 80)
        
        try:
            response = self.pincodes_table.scan()
            pincodes = response.get('Items', [])
            
            while 'LastEvaluatedKey' in response:
                response = self.pincodes_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                pincodes.extend(response.get('Items', []))
            
            all_charges = []
            for pincode in pincodes:
                pincode_id = pincode.get('pincodeID', 'N/A')
                pincode_num = pincode.get('pincodeNumber', 'N/A')
                charges = pincode.get('charges', [])
                for charge in charges:
                    charge['_pincodeID'] = pincode_id
                    charge['_pincodeNumber'] = pincode_num
                    all_charges.append(charge)
            
            if not all_charges:
                print("\n📦 No delivery charges found.")
                return
            
            print(f"\n📊 Total Delivery Charges: {len(all_charges)}")
            print("-" * 80)
            print(f"{'Pincode':<12} {'Pincode #':<12} {'Min Order':<15} {'Charge':<12} {'Status':<10}")
            print("-" * 80)
            
            for charge in all_charges:
                pincode_id = charge.get('_pincodeID', 'N/A')
                pincode_num = charge.get('_pincodeNumber', 'N/A')
                min_val = charge.get('minOrderValue', 0)
                charge_val = charge.get('charge', 0)
                is_active = charge.get('isActive', True)
                
                if isinstance(min_val, Decimal):
                    min_str = f"₹{min_val}"
                else:
                    min_str = f"₹{min_val}"
                
                if isinstance(charge_val, Decimal):
                    charge_str = f"₹{charge_val}"
                else:
                    charge_str = f"₹{charge_val}"
                
                status = 'Active' if is_active else 'Inactive'
                
                print(f"{pincode_id:<12} {pincode_num:<12} {min_str:<15} {charge_str:<12} {status:<10}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def get_charges_by_pincode(self, pincode_id: str):
        """Get all charges for a specific pincode"""
        try:
            response = self.pincodes_table.get_item(Key={'pincodeID': pincode_id})
            
            if 'Item' not in response:
                print(f"\n❌ ERROR: Pincode {pincode_id} not found!")
                return
            
            pincode = response['Item']
            charges = pincode.get('charges', [])
            
            if not charges:
                print(f"\n📦 No delivery charges found for pincode {pincode_id}.")
                return
            
            print(f"\n💰 Delivery Charges for Pincode {pincode_id}:")
            print("-" * 80)
            
            for idx, charge in enumerate(charges, 1):
                min_val = charge.get('minOrderValue', 0)
                charge_val = charge.get('charge', 0)
                is_active = charge.get('isActive', True)
                charge_id = charge.get('id', 'N/A')
                
                print(f"\n{idx}. Charge ID: {charge_id}")
                print(f"   Minimum Order Value: ₹{min_val}")
                print(f"   Charge: ₹{charge_val}")
                print(f"   Status: {'Active' if is_active else 'Inactive'}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def update_delivery_charge(self, pincode_id: str, charge_id: str):
        """Update a delivery charge"""
        try:
            response = self.pincodes_table.get_item(Key={'pincodeID': pincode_id})
            
            if 'Item' not in response:
                print(f"\n❌ ERROR: Pincode {pincode_id} not found!")
                return
            
            pincode = response['Item']
            charges = pincode.get('charges', [])
            
            charge_to_update = None
            charge_index = None
            for idx, charge in enumerate(charges):
                if charge.get('id') == charge_id:
                    charge_to_update = charge
                    charge_index = idx
                    break
            
            if not charge_to_update:
                print(f"\n❌ ERROR: Charge {charge_id} not found in pincode {pincode_id}!")
                return
            
            print("\n📝 Enter new values (press Enter to keep current value):")
            
            current_min = charge_to_update.get('minOrderValue', 0)
            current_charge = charge_to_update.get('charge', 0)
            
            min_input = input(f"Minimum Order Value (₹) [{current_min}]: ").strip()
            charge_input = input(f"Delivery Charge (₹) [{current_charge}]: ").strip()
            
            try:
                min_order_value = Decimal(min_input) if min_input else current_min
                delivery_charge = Decimal(charge_input) if charge_input else current_charge
                
                charge_to_update['minOrderValue'] = min_order_value
                charge_to_update['charge'] = delivery_charge
                charge_to_update['updatedAt'] = datetime.now(timezone.utc).isoformat()
                
                charges[charge_index] = charge_to_update
                pincode['charges'] = charges
                pincode['updatedAt'] = datetime.now(timezone.utc).isoformat()
                
                self.pincodes_table.put_item(Item=pincode)
                
                print(f"\n✅ SUCCESS: Delivery charge updated successfully!")
                
            except ValueError:
                print("❌ ERROR: Invalid numeric values!")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def delete_delivery_charge(self, pincode_id: str, charge_id: str):
        """Delete a delivery charge"""
        try:
            response = self.pincodes_table.get_item(Key={'pincodeID': pincode_id})
            
            if 'Item' not in response:
                print(f"\n❌ ERROR: Pincode {pincode_id} not found!")
                return
            
            pincode = response['Item']
            charges = pincode.get('charges', [])
            
            charge_to_delete = None
            for charge in charges:
                if charge.get('id') == charge_id:
                    charge_to_delete = charge
                    break
            
            if not charge_to_delete:
                print(f"\n❌ ERROR: Charge {charge_id} not found in pincode {pincode_id}!")
                return
            
            min_val = charge_to_delete.get('minOrderValue', 0)
            charge_val = charge_to_delete.get('charge', 0)
            
            print(f"\n⚠️  WARNING: You are about to delete:")
            print(f"   Charge ID: {charge_id}")
            print(f"   Order Range: ₹{min_val} and above")
            print(f"   Charge: ₹{charge_val}")
            
            confirm = input("\nAre you sure you want to delete this charge? (yes/no): ").strip().lower()
            
            if confirm == 'yes':
                charges = [c for c in charges if c.get('id') != charge_id]
                pincode['charges'] = charges
                pincode['updatedAt'] = datetime.now(timezone.utc).isoformat()
                
                self.pincodes_table.put_item(Item=pincode)
                
                print(f"\n✅ SUCCESS: Delivery charge deleted successfully!")
            else:
                print("\n❌ Deletion cancelled.")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    # ============================================================================
    # ORDER MANAGEMENT FUNCTIONS
    # ============================================================================
    
    def generate_customer_id(self) -> str:
        """Generate sequential customer ID (CUST-0001, CUST-0002, ...)"""
        try:
            if not self.customers_table:
                return f"CUST-{uuid.uuid4().hex[:8].upper()}"
            
            # Scan all customers to find the highest number
            response = self.customers_table.scan(
                ProjectionExpression='customer_id'
            )
            customers = response.get('Items', [])
            
            while 'LastEvaluatedKey' in response:
                response = self.customers_table.scan(
                    ProjectionExpression='customer_id',
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                customers.extend(response.get('Items', []))
            
            max_num = 0
            for customer in customers:
                customer_id = customer.get('customer_id', '')
                if customer_id.startswith('CUST-'):
                    try:
                        num = int(customer_id.split('-')[1])
                        max_num = max(max_num, num)
                    except (ValueError, IndexError):
                        pass
            
            next_num = max_num + 1
            return f"CUST-{next_num:04d}"
        except Exception:
            return f"CUST-{uuid.uuid4().hex[:8].upper()}"
    
    def generate_order_id(self) -> str:
        """Generate sequential order ID (ORD-YYYYMMDD-0001, ORD-YYYYMMDD-0002, ...)"""
        try:
            if not self.orders_table:
                today = datetime.now(timezone.utc).strftime('%Y%m%d')
                return f"ORD-{today}-0001"
            
            today = datetime.now(timezone.utc).strftime('%Y%m%d')
            date_prefix = f"ORD-{today}-"
            
            # Scan orders with today's date prefix
            response = self.orders_table.scan(
                FilterExpression='begins_with(order_id, :prefix)',
                ExpressionAttributeValues={':prefix': date_prefix},
                ProjectionExpression='order_id'
            )
            orders = response.get('Items', [])
            
            while 'LastEvaluatedKey' in response:
                response = self.orders_table.scan(
                    FilterExpression='begins_with(order_id, :prefix)',
                    ExpressionAttributeValues={':prefix': date_prefix},
                    ProjectionExpression='order_id',
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                orders.extend(response.get('Items', []))
            
            max_num = 0
            for order in orders:
                order_id = order.get('order_id', '')
                if order_id.startswith(date_prefix):
                    try:
                        num = int(order_id.split('-')[2])
                        max_num = max(max_num, num)
                    except (ValueError, IndexError):
                        pass
            
            next_num = max_num + 1
            return f"{date_prefix}{next_num:04d}"
        except Exception:
            today = datetime.now(timezone.utc).strftime('%Y%m%d')
            return f"ORD-{today}-{uuid.uuid4().hex[:4].upper()}"
    
    def lookup_customer_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Lookup customer by phone number"""
        try:
            if not self.customers_table:
                return None
            
            response = self.customers_table.get_item(Key={'phone': phone})
            if 'Item' in response:
                return response['Item']
            return None
        except Exception as e:
            print(f"⚠️  Error looking up customer: {e}")
            return None
    
    def get_delivery_charge_for_pincode(self, pincode: str, order_value: Decimal) -> Decimal:
        """Get delivery charge for a pincode based on order value"""
        try:
            if not self.pincodes_table:
                return Decimal('0')
            
            # Find pincode
            response = self.pincodes_table.scan(
                FilterExpression='pincodeNumber = :pincode',
                ExpressionAttributeValues={':pincode': pincode}
            )
            pincodes = response.get('Items', [])
            
            if not pincodes:
                return Decimal('0')
            
            pincode_data = pincodes[0]
            charges = pincode_data.get('charges', [])
            
            if not charges:
                return Decimal('0')
            
            # Find the applicable charge based on minOrderValue
            applicable_charge = Decimal('0')
            for charge in charges:
                if not charge.get('isActive', True):
                    continue
                min_order = Decimal(str(charge.get('minOrderValue', 0)))
                if order_value >= min_order:
                    charge_amount = Decimal(str(charge.get('charge', 0)))
                    if charge_amount > applicable_charge:
                        applicable_charge = charge_amount
            
            return applicable_charge
        except Exception as e:
            print(f"⚠️  Error getting delivery charge: {e}")
            return Decimal('0')
    
    def get_pincode_by_number(self, pincode_number: str) -> Optional[Dict[str, Any]]:
        """Fetch pincode record by pincode number"""
        try:
            if not self.pincodes_table:
                return None
            
            response = self.pincodes_table.scan(
                FilterExpression='pincodeNumber = :pincode',
                ExpressionAttributeValues={':pincode': pincode_number}
            )
            pincodes = response.get('Items', [])
            
            while 'LastEvaluatedKey' in response:
                response = self.pincodes_table.scan(
                    FilterExpression='pincodeNumber = :pincode',
                    ExpressionAttributeValues={':pincode': pincode_number},
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                pincodes.extend(response.get('Items', []))
            
            return pincodes[0] if pincodes else None
        except Exception as e:
            print(f"⚠️  Error finding pincode: {e}")
            return None
    
    def get_available_slots_for_pincode(self, pincode_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Return list of active slots assigned to a pincode"""
        slots: List[Dict[str, str]] = []
        seen = set()
        
        def add_slots_from_source(source: Dict[str, Any], source_name: str):
            for slot in source.get('slots', []):
                if not slot.get('isActive', True):
                    continue
                slot_name = slot.get('name', 'N/A')
                start_time = slot.get('startTime', 'N/A')
                end_time = slot.get('endTime', 'N/A')
                slot_time = f"{start_time} - {end_time}"
                key = (slot_name, slot_time, source_name)
                if key in seen:
                    continue
                seen.add(key)
                slots.append({
                    'name': slot_name,
                    'time': slot_time,
                    'full_string': f"{slot_time} ({slot_name})",
                    'delivery_type': source_name
                })
        
        # Get slots from delivery type names list
        if not slots:
            delivery_type_names = pincode_data.get('deliveryTypes', [])
            if delivery_type_names and self.delivery_types_table:
                delivery_type_set = set(delivery_type_names)
                try:
                    response = self.delivery_types_table.scan()
                    delivery_types = response.get('Items', [])
                    
                    while 'LastEvaluatedKey' in response:
                        response = self.delivery_types_table.scan(
                            ExclusiveStartKey=response['LastEvaluatedKey']
                        )
                        delivery_types.extend(response.get('Items', []))
                    
                    for dt in delivery_types:
                        dt_name = dt.get('deliveryType', '')
                        if dt_name in delivery_type_set and dt.get('isActive', True):
                            add_slots_from_source(dt, dt_name)
                except Exception as e:
                    print(f"⚠️  Error loading delivery slots: {e}")
        
        return slots
    
    def order_management_menu(self):
        """Display order management menu"""
        if not self.orders_table:
            print("\n⚠️  WARNING: Orders table not found!")
            print("Please create the 'Orders' table in DynamoDB first.")
            input("\nPress Enter to continue...")
            return
        
        while True:
            print("\n" + "=" * 80)
            print("🛒 ORDER MANAGEMENT")
            print("=" * 80)
            print("\n📋 AVAILABLE OPTIONS:")
            print("-" * 80)
            print("1. ➕ Create Order")
            print("2. 📋 List All Orders")
            print("3. 🔍 Search Orders")
            print("4. 🔎 Get Order by ID")
            print("5. ✏️  Update Order")
            print("6. 🔄 Update Order Status")
            print("7. ❌ Cancel Order")
            print("8. 👤 Customer Management")
            print("9. ℹ️  View Table Information")
            print("0. ⬅️  Back to Main Menu")
            print("-" * 80)
            
            choice = input("\nSelect an option (0-9): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.create_order()
                input("\nPress Enter to continue...")
            elif choice == '2':
                self.list_orders()
                input("\nPress Enter to continue...")
            elif choice == '3':
                self.search_orders()
                input("\nPress Enter to continue...")
            elif choice == '4':
                order_id = input("\nEnter Order ID: ").strip()
                if order_id:
                    self.get_order_by_id(order_id)
                else:
                    print("❌ ERROR: Order ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '5':
                order_id = input("\nEnter Order ID to update: ").strip()
                if order_id:
                    self.update_order(order_id)
                else:
                    print("❌ ERROR: Order ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '6':
                order_id = input("\nEnter Order ID to update status: ").strip()
                if order_id:
                    self.update_order_status(order_id)
                else:
                    print("❌ ERROR: Order ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '7':
                order_id = input("\nEnter Order ID to cancel: ").strip()
                if order_id:
                    self.cancel_order(order_id)
                else:
                    print("❌ ERROR: Order ID is required!")
                input("\nPress Enter to continue...")
            elif choice == '8':
                self.customer_management_menu()
            elif choice == '9':
                self.view_orders_table_info()
                input("\nPress Enter to continue...")
            else:
                print("❌ ERROR: Invalid choice. Please select a number between 0-9.")
                input("\nPress Enter to continue...")
    
    def customer_management_menu(self):
        """Display customer management menu"""
        if not self.customers_table:
            print("\n⚠️  WARNING: Customers table not found!")
            print("Please create the 'Customers' table in DynamoDB first.")
            input("\nPress Enter to continue...")
            return
        
        while True:
            print("\n" + "=" * 80)
            print("👤 CUSTOMER MANAGEMENT")
            print("=" * 80)
            print("\n📋 AVAILABLE OPTIONS:")
            print("-" * 80)
            print("1. 🔍 Lookup Customer by Phone")
            print("2. ➕ Create Customer")
            print("3. 📋 List All Customers")
            print("4. 🔎 Get Customer by Phone")
            print("5. ✏️  Update Customer")
            print("6. 📍 Add Customer Address")
            print("7. 📋 List Customer Addresses")
            print("8. ⭐ Set Default Address")
            print("0. ⬅️  Back to Order Management")
            print("-" * 80)
            
            choice = input("\nSelect an option (0-8): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                phone = input("\nEnter Phone Number: ").strip()
                if phone:
                    customer = self.lookup_customer_by_phone(phone)
                    if customer:
                        self.display_customer_details(customer)
                    else:
                        print(f"\n❌ Customer with phone {phone} not found!")
                else:
                    print("❌ ERROR: Phone number is required!")
                input("\nPress Enter to continue...")
            elif choice == '2':
                self.create_customer()
                input("\nPress Enter to continue...")
            elif choice == '3':
                self.list_customers()
                input("\nPress Enter to continue...")
            elif choice == '4':
                phone = input("\nEnter Phone Number: ").strip()
                if phone:
                    customer = self.lookup_customer_by_phone(phone)
                    if customer:
                        self.display_customer_details(customer)
                    else:
                        print(f"\n❌ Customer with phone {phone} not found!")
                else:
                    print("❌ ERROR: Phone number is required!")
                input("\nPress Enter to continue...")
            elif choice == '5':
                phone = input("\nEnter Phone Number to update: ").strip()
                if phone:
                    self.update_customer(phone)
                else:
                    print("❌ ERROR: Phone number is required!")
                input("\nPress Enter to continue...")
            elif choice == '6':
                phone = input("\nEnter Phone Number: ").strip()
                if phone:
                    self.add_customer_address(phone)
                else:
                    print("❌ ERROR: Phone number is required!")
                input("\nPress Enter to continue...")
            elif choice == '7':
                phone = input("\nEnter Phone Number: ").strip()
                if phone:
                    self.list_customer_addresses(phone)
                else:
                    print("❌ ERROR: Phone number is required!")
                input("\nPress Enter to continue...")
            elif choice == '8':
                phone = input("\nEnter Phone Number: ").strip()
                if phone:
                    self.set_default_address(phone)
                else:
                    print("❌ ERROR: Phone number is required!")
                input("\nPress Enter to continue...")
            else:
                print("❌ ERROR: Invalid choice. Please select a number between 0-8.")
                input("\nPress Enter to continue...")
    
    def create_customer(self):
        """Create a new customer"""
        print("\n" + "=" * 80)
        print("➕ CREATE NEW CUSTOMER")
        print("=" * 80)
        
        try:
            phone = input("\n📱 Phone Number *: ").strip()
            if not phone:
                print("❌ ERROR: Phone number is required!")
                return
            
            # Check if customer already exists
            existing = self.lookup_customer_by_phone(phone)
            if existing:
                print(f"\n⚠️  Customer with phone {phone} already exists!")
                print("Use 'Update Customer' to modify existing customer.")
                return
            
            name = input("👤 Customer Name *: ").strip()
            if not name:
                print("❌ ERROR: Customer name is required!")
                return
            
            # Get first address
            print("\n📍 Address Details:")
            flat_no = input("  Flat/House/Building No *: ").strip()
            area = input("  Area/Locality *: ").strip()
            landmark = input("  Landmark *: ").strip()
            pincode = input("  Pincode *: ").strip()
            
            if not all([flat_no, area, landmark, pincode]):
                print("❌ ERROR: All address fields are required!")
                return
            
            if not self.pincodes_table:
                print("\n⚠️  WARNING: Pincode management table not connected!")
                print("Please create the 'Pincode_management' table and configure pincodes before creating orders.")
                return
            
            # Validate pincode availability
            pincode_record = self.get_pincode_by_number(pincode)
            if not pincode_record:
                print(f"\n❌ ERROR: Pincode {pincode} is not serviceable. Please add it in Pincode Management before creating orders.")
                return
            
            status = pincode_record.get('status', 'Inactive')
            if status.lower() != 'active':
                print(f"\n❌ ERROR: Pincode {pincode} is currently '{status}'. Please activate it before creating orders.")
                return
            
            available_slots = self.get_available_slots_for_pincode(pincode_record)
            if not available_slots:
                print(f"\n❌ ERROR: No delivery slots configured for pincode {pincode}.")
                print("Please assign delivery types and slots in Pincode Management before creating orders.")
                return
            
            customer_id = self.generate_customer_id()
            address_id = f"addr-{uuid.uuid4().hex[:8]}"
            current_time = datetime.now(timezone.utc).isoformat()
            
            address = {
                'id': address_id,
                'flatNo': flat_no,
                'area': area,
                'landmark': landmark,
                'pincode': pincode,
                'isDefault': True,
                'createdAt': current_time,
                'updatedAt': current_time
            }
            
            customer = {
                'phone': phone,
                'customer_id': customer_id,
                'name': name,
                'addresses': [address],
                'createdAt': current_time,
                'updatedAt': current_time
            }
            
            self.customers_table.put_item(Item=customer)
            
            print(f"\n✅ SUCCESS: Customer created successfully!")
            print(f"   Customer ID: {customer_id}")
            print(f"   Phone: {phone}")
            print(f"   Name: {name}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def list_customers(self):
        """List all customers"""
        print("\n" + "=" * 80)
        print("📋 ALL CUSTOMERS")
        print("=" * 80)
        
        try:
            response = self.customers_table.scan()
            customers = response.get('Items', [])
            
            while 'LastEvaluatedKey' in response:
                response = self.customers_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                customers.extend(response.get('Items', []))
            
            if not customers:
                print("\n📦 No customers found.")
                return
            
            print(f"\n📊 Total Customers: {len(customers)}")
            print("-" * 80)
            print(f"{'Customer ID':<15} {'Phone':<15} {'Name':<30} {'Addresses':<10}")
            print("-" * 80)
            
            for customer in customers:
                customer_id = customer.get('customer_id', 'N/A')
                phone = customer.get('phone', 'N/A')
                name = customer.get('name', 'N/A')
                addresses_count = len(customer.get('addresses', []))
                
                print(f"{customer_id:<15} {phone:<15} {name:<30} {addresses_count:<10}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def display_customer_details(self, customer: Dict[str, Any]):
        """Display customer details"""
        print("\n" + "=" * 80)
        print(f"👤 CUSTOMER DETAILS")
        print("=" * 80)
        
        print(f"\n📱 Phone: {customer.get('phone', 'N/A')}")
        print(f"🆔 Customer ID: {customer.get('customer_id', 'N/A')}")
        print(f"👤 Name: {customer.get('name', 'N/A')}")
        print(f"📅 Created At: {customer.get('createdAt', 'N/A')}")
        print(f"🔄 Updated At: {customer.get('updatedAt', 'N/A')}")
        
        addresses = customer.get('addresses', [])
        if addresses:
            print(f"\n📍 Addresses ({len(addresses)}):")
            for idx, addr in enumerate(addresses, 1):
                is_default = addr.get('isDefault', False)
                default_mark = " ⭐ (Default)" if is_default else ""
                print(f"\n  {idx}. Address ID: {addr.get('id', 'N/A')}{default_mark}")
                print(f"     Flat/House: {addr.get('flatNo', 'N/A')}")
                print(f"     Area: {addr.get('area', 'N/A')}")
                print(f"     Landmark: {addr.get('landmark', 'N/A')}")
                print(f"     Pincode: {addr.get('pincode', 'N/A')}")
        else:
            print("\n📍 No addresses found.")
    
    def update_customer(self, phone: str):
        """Update customer details"""
        print("\n" + "=" * 80)
        print(f"✏️  UPDATE CUSTOMER: {phone}")
        print("=" * 80)
        
        try:
            customer = self.lookup_customer_by_phone(phone)
            if not customer:
                print(f"\n❌ ERROR: Customer with phone {phone} not found!")
                return
            
            print("\n📝 Enter new values (press Enter to keep current value):")
            
            current_name = customer.get('name', '')
            new_name = input(f"\n👤 Customer Name [{current_name}]: ").strip()
            if not new_name:
                new_name = current_name
            
            customer['name'] = new_name
            customer['updatedAt'] = datetime.now(timezone.utc).isoformat()
            
            self.customers_table.put_item(Item=customer)
            
            print(f"\n✅ SUCCESS: Customer updated successfully!")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def add_customer_address(self, phone: str):
        """Add a new address to customer"""
        print("\n" + "=" * 80)
        print(f"📍 ADD ADDRESS TO CUSTOMER: {phone}")
        print("=" * 80)
        
        try:
            customer = self.lookup_customer_by_phone(phone)
            if not customer:
                print(f"\n❌ ERROR: Customer with phone {phone} not found!")
                return
            
            print("\n📍 Address Details:")
            flat_no = input("  Flat/House/Building No *: ").strip()
            area = input("  Area/Locality *: ").strip()
            landmark = input("  Landmark *: ").strip()
            pincode = input("  Pincode *: ").strip()
            
            if not all([flat_no, area, landmark, pincode]):
                print("❌ ERROR: All address fields are required!")
                return
            
            set_default = input("\nSet as default address? (y/n, default: n): ").strip().lower() == 'y'
            
            address_id = f"addr-{uuid.uuid4().hex[:8]}"
            current_time = datetime.now(timezone.utc).isoformat()
            
            new_address = {
                'id': address_id,
                'flatNo': flat_no,
                'area': area,
                'landmark': landmark,
                'pincode': pincode,
                'isDefault': set_default,
                'createdAt': current_time,
                'updatedAt': current_time
            }
            
            addresses = customer.get('addresses', [])
            
            # If setting as default, unset other defaults
            if set_default:
                for addr in addresses:
                    addr['isDefault'] = False
            
            addresses.append(new_address)
            customer['addresses'] = addresses
            customer['updatedAt'] = current_time
            
            self.customers_table.put_item(Item=customer)
            
            print(f"\n✅ SUCCESS: Address added successfully!")
            print(f"   Address ID: {address_id}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def list_customer_addresses(self, phone: str):
        """List all addresses for a customer"""
        print("\n" + "=" * 80)
        print(f"📍 CUSTOMER ADDRESSES: {phone}")
        print("=" * 80)
        
        try:
            customer = self.lookup_customer_by_phone(phone)
            if not customer:
                print(f"\n❌ ERROR: Customer with phone {phone} not found!")
                return
            
            addresses = customer.get('addresses', [])
            if not addresses:
                print("\n📦 No addresses found.")
                return
            
            print(f"\n📊 Total Addresses: {len(addresses)}")
            print("-" * 80)
            
            for idx, addr in enumerate(addresses, 1):
                is_default = addr.get('isDefault', False)
                default_mark = " ⭐ (Default)" if is_default else ""
                print(f"\n{idx}. Address ID: {addr.get('id', 'N/A')}{default_mark}")
                print(f"   Flat/House: {addr.get('flatNo', 'N/A')}")
                print(f"   Area: {addr.get('area', 'N/A')}")
                print(f"   Landmark: {addr.get('landmark', 'N/A')}")
                print(f"   Pincode: {addr.get('pincode', 'N/A')}")
                print(f"   Created: {addr.get('createdAt', 'N/A')}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def set_default_address(self, phone: str):
        """Set default address for customer"""
        print("\n" + "=" * 80)
        print(f"⭐ SET DEFAULT ADDRESS: {phone}")
        print("=" * 80)
        
        try:
            customer = self.lookup_customer_by_phone(phone)
            if not customer:
                print(f"\n❌ ERROR: Customer with phone {phone} not found!")
                return
            
            addresses = customer.get('addresses', [])
            if not addresses:
                print("\n❌ ERROR: No addresses found for this customer!")
                return
            
            print("\n📍 Available Addresses:")
            for idx, addr in enumerate(addresses, 1):
                is_default = addr.get('isDefault', False)
                default_mark = " ⭐ (Current Default)" if is_default else ""
                print(f"{idx}. {addr.get('flatNo', 'N/A')}, {addr.get('area', 'N/A')} - {addr.get('pincode', 'N/A')}{default_mark}")
            
            choice = input(f"\nSelect address (1-{len(addresses)}): ").strip()
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(addresses):
                    print("❌ ERROR: Invalid selection!")
                    return
                
                # Unset all defaults
                for addr in addresses:
                    addr['isDefault'] = False
                
                # Set selected as default
                addresses[idx]['isDefault'] = True
                addresses[idx]['updatedAt'] = datetime.now(timezone.utc).isoformat()
                
                customer['addresses'] = addresses
                customer['updatedAt'] = datetime.now(timezone.utc).isoformat()
                
                self.customers_table.put_item(Item=customer)
                
                print(f"\n✅ SUCCESS: Default address updated successfully!")
                
            except ValueError:
                print("❌ ERROR: Invalid input! Please enter a number.")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    # ==================== ORDER CRUD FUNCTIONS ====================
    
    def create_order(self):
        """Create a new order with phone lookup functionality"""
        print("\n" + "=" * 80)
        print("➕ CREATE NEW ORDER")
        print("=" * 80)
        
        try:
            # Step 1: Customer Information with Phone Lookup
            print("\n" + "-" * 80)
            print("👤 CUSTOMER INFORMATION")
            print("-" * 80)
            
            phone = input("\n📱 Phone Number *: ").strip()
            if not phone:
                print("❌ ERROR: Phone number is required!")
                return
            
            customer = None
            customer_id = None
            customer_name = ""
            flat_no = ""
            area = ""
            landmark = ""
            pincode = ""
            selected_address = None
            
            # Auto-lookup customer
            if len(phone) >= 10:
                print("\n🔍 Looking up customer...")
                customer = self.lookup_customer_by_phone(phone)
                
                if customer:
                    print("✅ Customer found! Details loaded from database.")
                    customer_id = customer.get('customer_id')
                    customer_name = customer.get('name', '')
                    
                    # Get addresses
                    addresses = customer.get('addresses', [])
                    if addresses:
                        # Find default address or use first
                        default_addr = next((a for a in addresses if a.get('isDefault', False)), addresses[0])
                        selected_address = default_addr
                        flat_no = default_addr.get('flatNo', '')
                        area = default_addr.get('area', '')
                        landmark = default_addr.get('landmark', '')
                        pincode = default_addr.get('pincode', '')
                        
                        # If multiple addresses, let user choose
                        if len(addresses) > 1:
                            print(f"\n📍 Found {len(addresses)} addresses:")
                            for idx, addr in enumerate(addresses, 1):
                                is_default = addr.get('isDefault', False)
                                default_mark = " ⭐ (Default)" if is_default else ""
                                print(f"{idx}. {addr.get('flatNo', 'N/A')}, {addr.get('area', 'N/A')} - {addr.get('pincode', 'N/A')}{default_mark}")
                            
                            choice = input(f"\nSelect address (1-{len(addresses)}, default: 1): ").strip()
                            if choice:
                                try:
                                    idx = int(choice) - 1
                                    if 0 <= idx < len(addresses):
                                        selected_address = addresses[idx]
                                        flat_no = selected_address.get('flatNo', '')
                                        area = selected_address.get('area', '')
                                        landmark = selected_address.get('landmark', '')
                                        pincode = selected_address.get('pincode', '')
                                except ValueError:
                                    pass
                else:
                    print("❌ Customer not found. Please enter details manually.")
            
            # Get customer details (pre-filled if found)
            if not customer_name:
                customer_name = input("👤 Customer Name *: ").strip()
                if not customer_name:
                    print("❌ ERROR: Customer name is required!")
                    return
            
            if not flat_no:
                print("\n📍 Address Details:")
                flat_no = input("  Flat/House/Building No *: ").strip()
                area = input("  Area/Locality *: ").strip()
                landmark = input("  Landmark *: ").strip()
                pincode = input("  Pincode *: ").strip()
            
            if not all([flat_no, area, landmark, pincode]):
                print("❌ ERROR: All address fields are required!")
                return
            
            # Validate pincode and get available slots
            available_slots = []
            if not self.pincodes_table:
                print("\n⚠️  WARNING: Pincode management table not connected!")
                print("Please create the 'Pincode_management' table and configure pincodes before creating orders.")
                return
            
            # Validate pincode availability
            pincode_record = self.get_pincode_by_number(pincode)
            if not pincode_record:
                print(f"\n❌ ERROR: Pincode {pincode} is not serviceable.")
                print("Please add this pincode in Pincode Management before creating orders.")
                return
            
            status = pincode_record.get('status', 'Inactive')
            if status.lower() != 'active':
                print(f"\n❌ ERROR: Pincode {pincode} is currently '{status}'.")
                print("Please activate it in Pincode Management before creating orders.")
                return
            
            available_slots = self.get_available_slots_for_pincode(pincode_record)
            if not available_slots:
                print(f"\n❌ ERROR: No delivery slots configured for pincode {pincode}.")
                print("Please assign delivery types and create time slots in Pincode Management before creating orders.")
                return
            
            # If customer not found, ask if they want to save as new customer
            if not customer:
                save_customer = input("\n💾 Save as new customer? (y/n, default: n): ").strip().lower() == 'y'
                if save_customer:
                    # Create customer
                    customer_id = self.generate_customer_id()
                    address_id = f"addr-{uuid.uuid4().hex[:8]}"
                    current_time = datetime.now(timezone.utc).isoformat()
                    
                    address = {
                        'id': address_id,
                        'flatNo': flat_no,
                        'area': area,
                        'landmark': landmark,
                        'pincode': pincode,
                        'isDefault': True,
                        'createdAt': current_time,
                        'updatedAt': current_time
                    }
                    
                    new_customer = {
                        'phone': phone,
                        'customer_id': customer_id,
                        'name': customer_name,
                        'addresses': [address],
                        'createdAt': current_time,
                        'updatedAt': current_time
                    }
                    
                    self.customers_table.put_item(Item=new_customer)
                    print(f"✅ Customer saved! Customer ID: {customer_id}")
            
            # Step 2: Add Order Items
            print("\n" + "-" * 80)
            print("📦 ORDER ITEMS")
            print("-" * 80)
            
            order_items = []
            while True:
                print("\n📋 Current Items in Order:")
                if order_items:
                    total_items = sum(item['quantity'] for item in order_items)
                    print(f"   Total Items: {total_items}")
                    for idx, item in enumerate(order_items, 1):
                        print(f"   {idx}. {item['product_name']} - Qty: {item['quantity']} {item.get('unit', '')} - ₹{item['subtotal']}")
                else:
                    print("   No items added yet.")
                
                add_more = input("\n➕ Add item? (y/n, default: n): ").strip().lower()
                if add_more != 'y':
                    break
                
                # List available products
                print("\n📦 Available Products:")
                response = self.products_table.scan()
                products = response.get('Items', [])
                
                while 'LastEvaluatedKey' in response:
                    response = self.products_table.scan(
                        ExclusiveStartKey=response['LastEvaluatedKey']
                    )
                    products.extend(response.get('Items', []))
                
                # Filter active products
                active_products = [p for p in products if p.get('status') != 'inactive']
                
                if not active_products:
                    print("❌ No active products found!")
                    break
                
                # Display products (parent and variants based on stockMode)
                display_products = []
                for product in active_products:
                    product_id = product.get('productID', '')
                    name = product.get('name', 'N/A')
                    stock_mode = product.get('stockMode', 'parent')
                    stock = product.get('stock', 0)
                    unit = product.get('unit', '')
                    sale_price = Decimal(str(product.get('salePrice', 0)))
                    
                    if stock_mode == 'parent':
                        # Show only parent
                        display_products.append({
                            'id': product_id,
                            'name': name,
                            'stock': stock,
                            'unit': unit,
                            'price': sale_price,
                            'is_variant': False
                        })
                    else:
                        # Show parent and variants
                        display_products.append({
                            'id': product_id,
                            'name': name,
                            'stock': stock,
                            'unit': unit,
                            'price': sale_price,
                            'is_variant': False
                        })
                        
                        variants = product.get('variants', [])
                        for variant in variants:
                            variant_id = variant.get('variantID', '')
                            variant_name = variant.get('name', name)
                            variant_stock = variant.get('stock', 0)
                            variant_unit = variant.get('unit', unit)
                            variant_price = Decimal(str(variant.get('salePrice', sale_price)))
                            
                            display_products.append({
                                'id': variant_id,
                                'name': f"{variant_name} ({variant.get('gram', 'N/A')})",
                                'stock': variant_stock,
                                'unit': variant_unit,
                                'price': variant_price,
                                'is_variant': True,
                                'parent_id': product_id
                            })
                
                # Display products for selection
                print("\n" + "-" * 80)
                print(f"{'#':<5} {'Product ID':<20} {'Name':<30} {'Stock':<15} {'Price':<15}")
                print("-" * 80)
                for idx, prod in enumerate(display_products[:50], 1):  # Limit to 50 for display
                    stock_str = f"{prod['stock']} {prod['unit']}" if prod['stock'] > 0 else "Out of Stock"
                    print(f"{idx:<5} {prod['id']:<20} {prod['name']:<30} {stock_str:<15} ₹{prod['price']:<14}")
                
                if len(display_products) > 50:
                    print(f"... and {len(display_products) - 50} more products")
                
                choice = input(f"\nSelect product (1-{min(len(display_products), 50)}): ").strip()
                try:
                    idx = int(choice) - 1
                    if idx < 0 or idx >= len(display_products):
                        print("❌ ERROR: Invalid selection!")
                        continue
                    
                    selected_product = display_products[idx]
                    
                    # Check stock
                    if selected_product['stock'] <= 0:
                        print("⚠️  WARNING: This product is out of stock!")
                        continue_anyway = input("Continue anyway? (y/n): ").strip().lower() == 'y'
                        if not continue_anyway:
                            continue
                    
                    # Get quantity
                    quantity_input = input(f"Enter quantity (available: {selected_product['stock']} {selected_product['unit']}): ").strip()
                    try:
                        quantity = Decimal(quantity_input)
                        if quantity <= 0:
                            print("❌ ERROR: Quantity must be greater than 0!")
                            continue
                        
                        if quantity > selected_product['stock']:
                            print(f"⚠️  WARNING: Requested quantity ({quantity}) exceeds available stock ({selected_product['stock']})!")
                            continue_anyway = input("Continue anyway? (y/n): ").strip().lower() == 'y'
                            if not continue_anyway:
                                continue
                    except ValueError:
                        print("❌ ERROR: Invalid quantity!")
                        continue
                    
                    # Calculate subtotal
                    subtotal = selected_product['price'] * quantity
                    
                    # Add to order items
                    order_items.append({
                        'id': f"OI-{uuid.uuid4().hex[:8]}",
                        'product_id': selected_product['id'],
                        'product_name': selected_product['name'],
                        'quantity': quantity,
                        'price': selected_product['price'],
                        'subtotal': subtotal,
                        'unit': selected_product['unit']
                    })
                    
                    print(f"✅ Added: {selected_product['name']} - Qty: {quantity} {selected_product['unit']} - ₹{subtotal}")
                    
                except ValueError:
                    print("❌ ERROR: Invalid input! Please enter a number.")
                    continue
            
            if not order_items:
                print("❌ ERROR: At least one item is required to create an order!")
                return
            
            # Step 3: Delivery Information
            print("\n" + "-" * 80)
            print("🚚 DELIVERY INFORMATION")
            print("-" * 80)
            
            # Delivery Date
            today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            delivery_date = input(f"📅 Delivery Date (YYYY-MM-DD, default: {today}): ").strip() or today
            
            # Delivery Time Slot (must come from pincode configuration)
            delivery_slot = ""
            if available_slots:
                print("\n🕐 Available Time Slots for this pincode:")
                for idx, slot in enumerate(available_slots, 1):
                    print(f"{idx}. {slot['full_string']} - {slot['delivery_type']}")
                
                choice = input(f"\nSelect time slot (1-{len(available_slots)}): ").strip()
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(available_slots):
                        selected_slot = available_slots[idx]
                        delivery_slot = selected_slot['full_string']
                    else:
                        print("⚠️  Invalid selection, using first available slot.")
                        delivery_slot = available_slots[0]['full_string']
                except ValueError:
                    print("⚠️  Invalid input, using first available slot.")
                    delivery_slot = available_slots[0]['full_string']
            else:
                # This should not happen because we enforce slots above,
                # but keep a fallback to avoid crashing.
                delivery_slot = "11:00 AM - 1:00 PM (Afternoon)"
            
            # Payment Mode
            print("\n💳 Payment Mode:")
            print("1. Cash on Delivery (COD)")
            print("2. Online (Prepaid)")
            payment_choice = input("Select payment mode (1-2, default: 1): ").strip() or '1'
            payment_mode = 'COD' if payment_choice == '1' else 'Online'
            
            # Step 4: Calculate Totals
            print("\n" + "-" * 80)
            print("💰 ORDER SUMMARY")
            print("-" * 80)
            
            subtotal = sum(Decimal(str(item['subtotal'])) for item in order_items)
            
            # Discount
            discount_input = input(f"\n💸 Discount (₹, default: 0): ").strip() or '0'
            try:
                discount = Decimal(discount_input)
            except ValueError:
                discount = Decimal('0')
            
            # Shipping Charges (from pincode)
            shipping_charges = self.get_delivery_charge_for_pincode(pincode, subtotal)
            print(f"🚚 Shipping Charges: ₹{shipping_charges} (based on pincode {pincode})")
            
            # Grand Total
            grand_total = subtotal - discount + shipping_charges
            
            print(f"\n📊 Order Summary:")
            print(f"   Subtotal: ₹{subtotal}")
            print(f"   Discount: ₹{discount}")
            print(f"   Shipping: ₹{shipping_charges}")
            print(f"   Grand Total: ₹{grand_total}")
            
            # Order Notes
            notes = input("\n📝 Order Notes (optional): ").strip()
            
            # Confirm
            confirm = input("\n✅ Create this order? (y/n): ").strip().lower()
            if confirm != 'y':
                print("❌ Order creation cancelled.")
                return
            
            # Step 5: Create Order
            order_id = self.generate_order_id()
            current_time = datetime.now(timezone.utc).isoformat()
            
            # Build full address string
            full_address = f"{flat_no}, {area}, {landmark}, {pincode}"
            
            order = {
                'order_id': order_id,
                'customer_id': customer_id or f"CUST-{uuid.uuid4().hex[:8]}",
                'customer_name': customer_name,
                'customer_phone': phone,
                'address': full_address,
                'pincode': pincode,
                'subtotal': subtotal,
                'discount': discount,
                'shipping_charges': shipping_charges,
                'total_amount': grand_total,
                'payment_mode': payment_mode,
                'status': 'Placed',
                'items': order_items,
                'delivery_slot': delivery_slot,
                'delivery_date': delivery_date,
                'notes': notes if notes else None,
                'created_at': current_time,
                'updated_at': current_time
            }
            
            # Convert Decimal values for DynamoDB
            order['subtotal'] = subtotal
            order['discount'] = discount
            order['shipping_charges'] = shipping_charges
            order['total_amount'] = grand_total
            
            # Convert items to proper format
            formatted_items = []
            for item in order_items:
                formatted_items.append({
                    'id': item['id'],
                    'product_id': item['product_id'],
                    'product_name': item['product_name'],
                    'quantity': Decimal(str(item['quantity'])),
                    'price': Decimal(str(item['price'])),
                    'subtotal': Decimal(str(item['subtotal'])),
                    'unit': item.get('unit', '')
                })
            order['items'] = formatted_items
            
            self.orders_table.put_item(Item=order)
            
            print(f"\n✅ SUCCESS: Order created successfully!")
            print(f"   Order ID: {order_id}")
            print(f"   Customer: {customer_name} ({phone})")
            print(f"   Subtotal: ₹{subtotal}")
            print(f"   Discount: ₹{discount}")
            print(f"   Shipping Charges: ₹{shipping_charges}")
            print(f"   Total Amount: ₹{grand_total}")
            print(f"   Status: Placed")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def list_orders(self):
        """List all orders"""
        print("\n" + "=" * 80)
        print("📋 ALL ORDERS")
        print("=" * 80)
        
        try:
            response = self.orders_table.scan()
            orders = response.get('Items', [])
            
            while 'LastEvaluatedKey' in response:
                response = self.orders_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                orders.extend(response.get('Items', []))
            
            if not orders:
                print("\n📦 No orders found.")
                return
            
            # Sort by created_at (newest first)
            orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            print(f"\n📊 Total Orders: {len(orders)}")
            print("-" * 80)
            print(f"{'Order ID':<20} {'Customer':<25} {'Phone':<15} {'Amount':<15} {'Status':<15} {'Payment':<10}")
            print("-" * 80)
            
            for order in orders:
                order_id = order.get('order_id', 'N/A')
                customer_name = order.get('customer_name', 'N/A')[:24]
                phone = order.get('customer_phone', 'N/A')[:14]
                total = Decimal(str(order.get('total_amount', 0)))
                status = order.get('status', 'N/A')
                payment_mode = order.get('payment_mode', 'N/A')
                
                print(f"{order_id:<20} {customer_name:<25} {phone:<15} ₹{total:<14} {status:<15} {payment_mode:<10}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def search_orders(self):
        """Search orders by order number, customer name, or phone"""
        print("\n" + "=" * 80)
        print("🔍 SEARCH ORDERS")
        print("=" * 80)
        
        try:
            search_term = input("\nEnter search term (Order ID, Customer Name, or Phone): ").strip().lower()
            if not search_term:
                print("❌ ERROR: Search term is required!")
                return
            
            response = self.orders_table.scan()
            orders = response.get('Items', [])
            
            while 'LastEvaluatedKey' in response:
                response = self.orders_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                orders.extend(response.get('Items', []))
            
            # Filter orders
            filtered_orders = []
            for order in orders:
                order_id = order.get('order_id', '').lower()
                customer_name = order.get('customer_name', '').lower()
                phone = order.get('customer_phone', '').lower()
                
                if search_term in order_id or search_term in customer_name or search_term in phone:
                    filtered_orders.append(order)
            
            if not filtered_orders:
                print(f"\n📦 No orders found matching '{search_term}'")
                return
            
            print(f"\n📊 Found {len(filtered_orders)} order(s):")
            print("-" * 80)
            print(f"{'Order ID':<20} {'Customer':<25} {'Phone':<15} {'Amount':<15} {'Status':<15}")
            print("-" * 80)
            
            for order in filtered_orders:
                order_id = order.get('order_id', 'N/A')
                customer_name = order.get('customer_name', 'N/A')[:24]
                phone = order.get('customer_phone', 'N/A')[:14]
                total = Decimal(str(order.get('total_amount', 0)))
                status = order.get('status', 'N/A')
                
                print(f"{order_id:<20} {customer_name:<25} {phone:<15} ₹{total:<14} {status:<15}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def get_order_by_id(self, order_id: str):
        """Get order details by ID"""
        print("\n" + "=" * 80)
        print(f"🔎 ORDER DETAILS: {order_id}")
        print("=" * 80)
        
        try:
            response = self.orders_table.get_item(Key={'order_id': order_id})
            
            if 'Item' not in response:
                print(f"\n❌ Order {order_id} not found!")
                return
            
            order = response['Item']
            
            print("\n📦 ORDER INFORMATION:")
            print("-" * 80)
            print(f"Order ID: {order.get('order_id', 'N/A')}")
            print(f"Status: {order.get('status', 'N/A')}")
            print(f"Payment Mode: {order.get('payment_mode', 'N/A')}")
            print(f"Created At: {order.get('created_at', 'N/A')}")
            print(f"Updated At: {order.get('updated_at', 'N/A')}")
            
            print("\n👤 CUSTOMER INFORMATION:")
            print("-" * 80)
            print(f"Customer ID: {order.get('customer_id', 'N/A')}")
            print(f"Name: {order.get('customer_name', 'N/A')}")
            print(f"Phone: {order.get('customer_phone', 'N/A')}")
            print(f"Address: {order.get('address', 'N/A')}")
            print(f"Pincode: {order.get('pincode', 'N/A')}")
            
            print("\n🚚 DELIVERY INFORMATION:")
            print("-" * 80)
            print(f"Delivery Date: {order.get('delivery_date', 'N/A')}")
            print(f"Delivery Slot: {order.get('delivery_slot', 'N/A')}")
            
            items = order.get('items', [])
            if items:
                print(f"\n📦 ORDER ITEMS ({len(items)}):")
                print("-" * 80)
                print(f"{'#':<5} {'Product Name':<30} {'Qty':<10} {'Price':<15} {'Subtotal':<15}")
                print("-" * 80)
                for idx, item in enumerate(items, 1):
                    product_name = item.get('product_name', 'N/A')[:29]
                    quantity = Decimal(str(item.get('quantity', 0)))
                    unit = item.get('unit', '')
                    price = Decimal(str(item.get('price', 0)))
                    subtotal = Decimal(str(item.get('subtotal', 0)))
                    
                    print(f"{idx:<5} {product_name:<30} {quantity} {unit:<7} ₹{price:<14} ₹{subtotal:<14}")
            
            print("\n💰 ORDER SUMMARY:")
            print("-" * 80)
            subtotal = sum(Decimal(str(item.get('subtotal', 0))) for item in items)
            discount = Decimal(str(order.get('discount', 0)))
            shipping = Decimal(str(order.get('shipping_charges', 0)))
            total = Decimal(str(order.get('total_amount', 0)))
            
            print(f"Subtotal: ₹{subtotal}")
            print(f"Discount: ₹{discount}")
            print(f"Shipping Charges: ₹{shipping}")
            print(f"Grand Total: ₹{total}")
            
            if order.get('notes'):
                print(f"\n📝 Notes: {order.get('notes')}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def update_order(self, order_id: str):
        """Update order details"""
        print("\n" + "=" * 80)
        print(f"✏️  UPDATE ORDER: {order_id}")
        print("=" * 80)
        
        try:
            response = self.orders_table.get_item(Key={'order_id': order_id})
            
            if 'Item' not in response:
                print(f"\n❌ Order {order_id} not found!")
                return
            
            order = response['Item']
            
            print("\n📝 Enter new values (press Enter to keep current value):")
            
            # Update notes
            current_notes = order.get('notes', '')
            new_notes = input(f"\n📝 Order Notes [{current_notes}]: ").strip()
            if new_notes:
                order['notes'] = new_notes
            
            # Update delivery date
            current_delivery_date = order.get('delivery_date', '')
            new_delivery_date = input(f"📅 Delivery Date (YYYY-MM-DD) [{current_delivery_date}]: ").strip()
            if new_delivery_date:
                order['delivery_date'] = new_delivery_date
            
            # Update delivery slot
            current_slot = order.get('delivery_slot', '')
            new_slot = input(f"🕐 Delivery Slot [{current_slot}]: ").strip()
            if new_slot:
                order['delivery_slot'] = new_slot
            
            order['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            self.orders_table.put_item(Item=order)
            
            print(f"\n✅ SUCCESS: Order updated successfully!")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def update_order_status(self, order_id: str):
        """Update order status"""
        print("\n" + "=" * 80)
        print(f"🔄 UPDATE ORDER STATUS: {order_id}")
        print("=" * 80)
        
        try:
            response = self.orders_table.get_item(Key={'order_id': order_id})
            
            if 'Item' not in response:
                print(f"\n❌ Order {order_id} not found!")
                return
            
            order = response['Item']
            current_status = order.get('status', 'N/A')
            
            print(f"\n📊 Current Status: {current_status}")
            print("\nAvailable Statuses:")
            statuses = ['Placed', 'Accepted', 'Packed', 'Dispatched', 'Delivered', 'Cancelled', 'Returned']
            for idx, status in enumerate(statuses, 1):
                marker = " ← Current" if status == current_status else ""
                print(f"{idx}. {status}{marker}")
            
            choice = input(f"\nSelect new status (1-{len(statuses)}): ").strip()
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(statuses):
                    print("❌ ERROR: Invalid selection!")
                    return
                
                new_status = statuses[idx]
                order['status'] = new_status
                order['updated_at'] = datetime.now(timezone.utc).isoformat()
                
                self.orders_table.put_item(Item=order)
                
                print(f"\n✅ SUCCESS: Order status updated to '{new_status}'!")
                
            except ValueError:
                print("❌ ERROR: Invalid input! Please enter a number.")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def cancel_order(self, order_id: str):
        """Cancel an order"""
        print("\n" + "=" * 80)
        print(f"❌ CANCEL ORDER: {order_id}")
        print("=" * 80)
        
        try:
            response = self.orders_table.get_item(Key={'order_id': order_id})
            
            if 'Item' not in response:
                print(f"\n❌ Order {order_id} not found!")
                return
            
            order = response['Item']
            current_status = order.get('status', 'N/A')
            
            if current_status == 'Cancelled':
                print(f"\n⚠️  Order is already cancelled!")
                return
            
            if current_status == 'Delivered':
                print(f"\n⚠️  Cannot cancel a delivered order!")
                return
            
            print(f"\n⚠️  WARNING: You are about to cancel order {order_id}")
            print(f"   Current Status: {current_status}")
            print(f"   Customer: {order.get('customer_name', 'N/A')}")
            print(f"   Total Amount: ₹{Decimal(str(order.get('total_amount', 0)))}")
            
            confirm = input("\nAre you sure you want to cancel this order? (yes/no): ").strip().lower()
            
            if confirm == 'yes':
                order['status'] = 'Cancelled'
                order['updated_at'] = datetime.now(timezone.utc).isoformat()
                
                self.orders_table.put_item(Item=order)
                
                print(f"\n✅ SUCCESS: Order {order_id} cancelled successfully!")
            else:
                print("\n❌ Cancellation cancelled.")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def view_orders_table_info(self):
        """View Orders table information"""
        try:
            response = self.orders_table.meta.client.describe_table(TableName='Orders')
            table = response['Table']
            
            print("\n" + "=" * 80)
            print("📋 ORDERS TABLE INFORMATION")
            print("=" * 80)
            print(f"Table Name: {table['TableName']}")
            print(f"Table Status: {table['TableStatus']}")
            print(f"Table ARN: {table['TableArn']}")
            print(f"Creation Date: {table['CreationDateTime']}")
            print(f"Item Count: {table.get('ItemCount', 0)}")
            
            # Key Schema
            print(f"\n🔑 Primary Key:")
            for key in table['KeySchema']:
                print(f"   - {key['AttributeName']} ({key['KeyType']})")
            
            # Attribute Definitions
            print(f"\n📝 Attributes:")
            for attr in table.get('AttributeDefinitions', []):
                print(f"   - {attr['AttributeName']}: {attr['AttributeType']}")
            
            # Capacity Mode
            billing_mode = table.get('BillingModeSummary', {}).get('BillingMode', 'PROVISIONED')
            print(f"\n💰 Billing Mode: {billing_mode}")
            
            if billing_mode == 'PROVISIONED':
                provisioned = table.get('ProvisionedThroughput', {})
                print(f"   Read Capacity: {provisioned.get('ReadCapacityUnits', 'N/A')}")
                print(f"   Write Capacity: {provisioned.get('WriteCapacityUnits', 'N/A')}")
            else:
                print("   On-Demand (pay per request)")
            
            print("=" * 80)
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main entry point"""
    print("=" * 80)
    print("🏭 PRODUCTS CLI - DynamoDB Management")
    print("=" * 80)
    
    # Initialize CLI
    try:
        cli = ProductsCLI(region_name='ap-south-1')
        
        # Test connection first
        print("\n" + "-" * 80)
        print("🔌 Testing Connection...")
        print("-" * 80)
        
        if not cli.test_connection():
            print("\n❌ Connection test failed. Please check your AWS configuration.")
            sys.exit(1)
        
        # Check for direct command (for backward compatibility)
        command = None
        if len(sys.argv) > 1:
            if sys.argv[1].startswith('-'):
                command = sys.argv[1]
            elif len(sys.argv) > 2:
                command = sys.argv[2]
        
        if command == '--create' or command == '-c':
            # Direct create command (backward compatibility)
            cli.create_product()
        else:
            # Show main menu
            cli.main_menu()
            
    except KeyboardInterrupt:
        print("\n\n👋 CLI terminated by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

