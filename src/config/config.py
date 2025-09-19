from typing import Dict
import os
import yaml
from dotenv import load_dotenv

class EcommerceConfig:
    """Configuration class for E-commerce MCP Server."""
    
    def __init__(self, config_path: str = None):
        load_dotenv()  # Load environment variables
        
        self.config = {
            'aws': {
                'region': os.getenv('AWS_REGION', 'ap-south-1'),
                'dynamodb': {
                    'tables': {
                        'users': 'EcommerceApp-Users',
                        'products': 'EcommerceApp-Products',
                        'inventory': 'EcommerceApp-Inventory',
                        'orders': 'EcommerceApp-Orders',
                        'delivery': 'EcommerceApp-Delivery',
                        'system': 'EcommerceApp-System'
                    }
                }
            },
            'ecommerce': {
                'product_search': {
                    'default_max_results': 20,
                    'max_results_limit': 100,
                    'default_include_out_of_stock': True
                },
                'categories': [
                    'vegetables', 'fruits', 'dairy', 'grains', 'spices',
                    'beverages', 'snacks', 'frozen', 'organic', 'household'
                ]
            },
            'server': {
                'name': 'E-commerce MCP Server',
                'version': '1.0.0',
                'description': 'MCP server for e-commerce product catalog operations'
            },
            'logging': {
                'level': os.getenv('LOG_LEVEL', 'INFO'),
                'file': './logs/ecommerce_mcp.log'
            }
        }
        
        # Override with config file if provided
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f)
                self._deep_update(self.config, file_config)
    
    def get(self, key: str, default=None):
        """Get configuration value using dot notation (e.g., 'aws.region')"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value
    
    def get_aws_region(self) -> str:
        """Get AWS region configuration."""
        return self.get('aws.region', 'ap-south-1')
    
    def get_dynamodb_tables(self) -> Dict[str, str]:
        """Get DynamoDB table names."""
        return self.get('aws.dynamodb.tables', {})
    
    def get_product_search_config(self) -> Dict:
        """Get product search configuration."""
        return self.get('ecommerce.product_search', {})
    
    def get_common_categories(self) -> list:
        """Get list of common product categories."""
        return self.get('ecommerce.categories', [])
    
    def update(self, updates: Dict):
        """Update configuration"""
        self._deep_update(self.config, updates)
    
    def _deep_update(self, d: Dict, u: Dict):
        """Recursively update dictionary d with values from dictionary u"""
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._deep_update(d[k], v)
            else:
                d[k] = v

# Backward compatibility alias
Config = EcommerceConfig
