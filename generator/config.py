"""
Configuration settings for the Call Data Generator

Author: AI Assistant
Date: 2025
"""

# S3 Configuration
DEFAULT_S3_BUCKET = "starhub-totogi-poc"
S3_PREFIX = "call-analysis"

# Generation Settings
DEFAULT_NUM_CALLS = 10
DEFAULT_DAYS_BACK = 7

# Local Output Settings
LOCAL_OUTPUT_DIR = "output"

# AWS Settings
AWS_REGION = "ap-southeast-1"  # Singapore region for Starhub

# Data Generation Settings
GRADING_PASS_THRESHOLD = 70.0

# Call Types and their weights for random selection
CALL_TYPE_WEIGHTS = {
    "Internet Service Upgrade": 0.3,
    "New Service Inquiry": 0.25, 
    "Service Renewal": 0.2,
    "Technical Support": 0.15,
    "Billing Inquiry": 0.1
}

# Agent Performance Ranges
AGENT_PERFORMANCE_RANGES = {
    "excellent": {"min_score": 85, "probability": 0.2},
    "good": {"min_score": 70, "probability": 0.5},  
    "needs_improvement": {"min_score": 50, "probability": 0.3}
}

# Sample customer segments distribution
CUSTOMER_SEGMENT_WEIGHTS = {
    "Existing Customer": 0.6,
    "New Customer": 0.25,
    "VIP Customer": 0.15
}
