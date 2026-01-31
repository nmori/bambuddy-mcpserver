"""Example usage of Bambuddy MCP Server."""

import asyncio
import os
import sys

# Add parent directory to path for local development
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bambuddy_mcpserver.server import BambuddyMCPServer


async def main():
    """Example of running the MCP server."""
    # Configure server (can also use environment variables)
    base_url = os.getenv("BAMBU_CONNECT_URL", "http://localhost:8080")
    access_token = os.getenv("BAMBU_CONNECT_TOKEN")
    
    # Create and initialize server
    server = BambuddyMCPServer()
    server.initialize_client(base_url, access_token)
    
    print(f"Starting Bambuddy MCP Server")
    print(f"BambuConnect URL: {base_url}")
    print(f"Ready to accept connections...")
    
    # Run the server
    await server.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
