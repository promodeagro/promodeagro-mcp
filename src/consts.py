# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Constants for E-commerce MCP Server."""

import os
from dotenv import load_dotenv

load_dotenv()

# Application name
ECOMMERCE_MCP_SERVER_APPLICATION_NAME = "E-commerce MCP Server"

# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")

# E-commerce Configuration
ECOMMERCE_DEFAULT_MAX_RESULTS = 20
ECOMMERCE_MAX_RESULTS_LIMIT = 100
ECOMMERCE_DEFAULT_REGION = AWS_REGION

# E-commerce DynamoDB Tables
ECOMMERCE_TABLES = {
    'users': 'EcommerceApp-Users',
    'products': 'EcommerceApp-Products',
    'inventory': 'EcommerceApp-Inventory',
    'orders': 'EcommerceApp-Orders',
    'delivery': 'EcommerceApp-Delivery',
    'system': 'EcommerceApp-System'
}

# Product Categories (commonly used in e-commerce)
COMMON_PRODUCT_CATEGORIES = [
    'vegetables',
    'fruits',
    'dairy',
    'grains',
    'spices',
    'beverages',
    'snacks',
    'frozen',
    'organic',
    'household'
]

# Default values for product browsing
DEFAULT_PRODUCT_SEARCH_PARAMS = {
    'max_results': ECOMMERCE_DEFAULT_MAX_RESULTS,
    'include_out_of_stock': True,
    'min_price': None,
    'max_price': None
}
