#!/usr/bin/env python3
"""Test script to verify Bambuddy MCP Server installation."""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from bambuddy_mcpserver import __version__
        print(f"✓ bambuddy_mcpserver version {__version__}")
    except ImportError as e:
        print(f"✗ Failed to import bambuddy_mcpserver: {e}")
        return False
    
    try:
        from bambuddy_mcpserver.client import (
            BambuConnectClient,
            PrinterInfo,
            PrinterStatus,
            PrintJob
        )
        print("✓ Client classes imported")
    except ImportError as e:
        print(f"✗ Failed to import client classes: {e}")
        return False
    
    try:
        from bambuddy_mcpserver.server import BambuddyMCPServer
        print("✓ MCP Server class imported")
    except ImportError as e:
        print(f"✗ Failed to import MCP Server: {e}")
        return False
    
    return True


def test_client():
    """Test client initialization."""
    print("\nTesting client initialization...")
    
    try:
        from bambuddy_mcpserver.client import BambuConnectClient
        
        client = BambuConnectClient("http://localhost:8080")
        print("✓ BambuConnect client created")
        return True
    except Exception as e:
        print(f"✗ Failed to create client: {e}")
        return False


def test_models():
    """Test model creation."""
    print("\nTesting data models...")
    
    try:
        from bambuddy_mcpserver.client import PrinterInfo, PrinterStatus, PrintJob
        
        # Test PrinterInfo
        printer = PrinterInfo(
            device_id="test123",
            name="Test Printer",
            model="X1C",
            online=True
        )
        print(f"✓ PrinterInfo: {printer.name}")
        
        # Test PrinterStatus
        status = PrinterStatus(
            device_id="test123",
            state="idle",
            progress=0
        )
        print(f"✓ PrinterStatus: {status.state}")
        
        # Test PrintJob
        job = PrintJob(
            job_id="job123",
            filename="test.gcode",
            status="completed",
            progress=100
        )
        print(f"✓ PrintJob: {job.filename}")
        
        return True
    except Exception as e:
        print(f"✗ Failed to create models: {e}")
        return False


def test_server():
    """Test MCP server initialization."""
    print("\nTesting MCP server...")
    
    try:
        from bambuddy_mcpserver.server import BambuddyMCPServer
        
        server = BambuddyMCPServer()
        print("✓ MCP Server created")
        
        server.initialize_client("http://localhost:8080")
        print("✓ MCP Server client initialized")
        
        return True
    except Exception as e:
        print(f"✗ Failed to initialize server: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Bambuddy MCP Server - Installation Test")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Client", test_client),
        ("Models", test_models),
        ("Server", test_server),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"\n✗ Test '{name}' failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    if all(results):
        print("✅ All tests passed!")
        print("\nThe Bambuddy MCP Server is installed correctly.")
        print("\nTo run the server:")
        print("  python -m bambuddy_mcpserver.server")
        print("\nOr with environment variables:")
        print("  BAMBU_CONNECT_URL=http://your-server:8080 \\")
        print("  BAMBU_CONNECT_TOKEN=your-token \\")
        print("  python -m bambuddy_mcpserver.server")
        return 0
    else:
        print("❌ Some tests failed!")
        print("\nPlease check:")
        print("  1. All dependencies are installed: pip install -r requirements.txt")
        print("  2. Python version is 3.10 or higher")
        return 1


if __name__ == "__main__":
    sys.exit(main())
