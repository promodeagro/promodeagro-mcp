#!/usr/bin/env python3
"""
Test runner script for E-commerce MCP server tests.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and return the result."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print('='*60)
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False

def main():
    """Main test runner function."""
    print("🚀 E-commerce MCP Server - Test Suite Runner")
    print("=" * 60)
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Test commands to run
    tests = [
        {
            "command": "python -m pytest tests/test_ecommerce_models.py -v",
            "description": "Testing Data Models"
        },
        {
            "command": "python -m pytest tests/test_ecommerce_service.py -v", 
            "description": "Testing Service Layer"
        },
        {
            "command": "python -m pytest tests/test_ecommerce_tools.py -v",
            "description": "Testing MCP Tools"
        },
        {
            "command": "python -m pytest tests/test_mcp_integration.py -v",
            "description": "Testing MCP Integration"
        },
        {
            "command": "python -m pytest tests/test_http_server.py -v",
            "description": "Testing HTTP Server"
        },
        {
            "command": "python -m pytest tests/ -v --tb=short",
            "description": "Running All Tests (Summary)"
        },
        {
            "command": "python -m pytest tests/ --cov=src --cov-report=term-missing",
            "description": "Running Tests with Coverage"
        }
    ]
    
    # Run tests
    results = []
    for test in tests:
        success = run_command(test["command"], test["description"])
        results.append((test["description"], success))
        
        if not success:
            print(f"❌ {test['description']} FAILED")
        else:
            print(f"✅ {test['description']} PASSED")
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print('='*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for description, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{description:<40} {status}")
    
    print(f"\n🎯 Overall Result: {passed}/{total} test suites passed")
    
    if passed == total:
        print("🎉 All tests passed! MCP server is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
