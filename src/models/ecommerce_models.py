"""
Data models for e-commerce functionality.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime


@dataclass
class ProductBrowseRequest:
    """Request parameters for product browsing."""
    category: Optional[str] = None
    search_term: Optional[str] = None
    max_results: int = 20
    include_out_of_stock: bool = True
    min_price: Optional[float] = None
    max_price: Optional[float] = None


@dataclass
class CategoryCountsRequest:
    """Request parameters for category counts (no parameters needed currently)."""
    pass


@dataclass
class ProductVariant:
    """Product variant information."""
    variant_id: str
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    price: float = 0.0
    stock_available: int = 0


@dataclass
class ProductStock:
    """Product stock information."""
    available: int
    status: str
    track_inventory: bool = False


@dataclass
class ProductAttributes:
    """Product attributes and characteristics."""
    perishable: bool = False
    shelf_life_days: Optional[int] = None
    quality_grade: Optional[str] = None
    organic: bool = False
    brand: Optional[str] = None


@dataclass
class ProductAvailability:
    """Product availability information."""
    is_active: bool = True
    status: str = "active"
    b2c_available: bool = True


@dataclass
class ProductInfo:
    """Complete product information."""
    product_id: str
    product_code: str
    name: str
    description: str = ""
    category: str = "uncategorized"
    price: float = 0.0
    unit: str = "piece"
    stock: ProductStock = field(default_factory=ProductStock)
    variants: List[ProductVariant] = field(default_factory=list)
    has_variants: bool = False
    attributes: ProductAttributes = field(default_factory=ProductAttributes)
    availability: ProductAvailability = field(default_factory=ProductAvailability)


@dataclass
class CategoryInfo:
    """Category information with counts."""
    name: str
    count: int
    percentage: float = 0.0


@dataclass
class SearchMetadata:
    """Metadata about the search/browse operation."""
    category_filter: Optional[str] = None
    search_term: Optional[str] = None
    price_range: Dict[str, Optional[float]] = field(default_factory=dict)
    include_out_of_stock: bool = True
    max_results: int = 20


@dataclass
class ProductBrowseResult:
    """Result of product browsing operation."""
    status: str
    products: List[ProductInfo]
    total_found: int
    returned_count: int
    categories: Dict[str, List[str]]
    search_metadata: SearchMetadata
    timestamp: datetime
    error_message: Optional[str] = None


@dataclass
class CategoryCountsResult:
    """Result of category counts operation."""
    status: str
    categories: List[CategoryInfo]
    total_products: int
    total_categories: int
    timestamp: datetime
    error_message: Optional[str] = None
