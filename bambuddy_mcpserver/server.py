"""MCP server for Bambu Lab printers."""

import asyncio
import json
import logging
import os
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .client import BambuConnectClient


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BambuddyMCPServer:
    """MCP Server for Bambu Lab printers."""
    
    def __init__(self):
        """Initialize the MCP server."""
        self.server = Server("bambuddy-mcpserver")
        self.client: Optional[BambuConnectClient] = None
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register MCP server handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="get_printers",
                    description="Get list of available Bambu Lab printers",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                Tool(
                    name="get_printer_status",
                    description="Get current status of a specific Bambu Lab printer",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Unique device ID of the printer",
                            },
                        },
                        "required": ["device_id"],
                    },
                ),
                Tool(
                    name="get_print_jobs",
                    description="Get list of print jobs",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Optional device ID to filter jobs for a specific printer",
                            },
                        },
                    },
                ),
                Tool(
                    name="get_job_details",
                    description="Get detailed information about a specific print job",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "job_id": {
                                "type": "string",
                                "description": "Job ID",
                            },
                        },
                        "required": ["job_id"],
                    },
                ),
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """Handle tool calls."""
            if not self.client:
                return [TextContent(
                    type="text",
                    text="Error: BambuConnect client not initialized. Please check configuration."
                )]
            
            try:
                if name == "get_printers":
                    printers = self.client.get_printers()
                    result = {
                        "printers": [
                            {
                                "device_id": p.device_id,
                                "name": p.name,
                                "model": p.model,
                                "online": p.online,
                            }
                            for p in printers
                        ]
                    }
                    return [TextContent(
                        type="text",
                        text=json.dumps(result, indent=2)
                    )]
                
                elif name == "get_printer_status":
                    device_id = arguments.get("device_id")
                    if not device_id:
                        return [TextContent(
                            type="text",
                            text="Error: device_id is required"
                        )]
                    
                    status = self.client.get_printer_status(device_id)
                    if not status:
                        return [TextContent(
                            type="text",
                            text=f"Error: Could not get status for device {device_id}"
                        )]
                    
                    result = {
                        "device_id": status.device_id,
                        "state": status.state,
                        "progress": status.progress,
                        "current_file": status.current_file,
                        "bed_temp": status.bed_temp,
                        "nozzle_temp": status.nozzle_temp,
                    }
                    return [TextContent(
                        type="text",
                        text=json.dumps(result, indent=2)
                    )]
                
                elif name == "get_print_jobs":
                    device_id = arguments.get("device_id")
                    jobs = self.client.get_print_jobs(device_id)
                    result = {
                        "jobs": [
                            {
                                "job_id": j.job_id,
                                "filename": j.filename,
                                "status": j.status,
                                "progress": j.progress,
                                "start_time": j.start_time,
                                "end_time": j.end_time,
                            }
                            for j in jobs
                        ]
                    }
                    return [TextContent(
                        type="text",
                        text=json.dumps(result, indent=2)
                    )]
                
                elif name == "get_job_details":
                    job_id = arguments.get("job_id")
                    if not job_id:
                        return [TextContent(
                            type="text",
                            text="Error: job_id is required"
                        )]
                    
                    details = self.client.get_job_details(job_id)
                    if not details:
                        return [TextContent(
                            type="text",
                            text=f"Error: Could not get details for job {job_id}"
                        )]
                    
                    return [TextContent(
                        type="text",
                        text=json.dumps(details, indent=2)
                    )]
                
                else:
                    return [TextContent(
                        type="text",
                        text=f"Error: Unknown tool {name}"
                    )]
            
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                return [TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
    
    def initialize_client(self, base_url: str, access_token: Optional[str] = None):
        """Initialize the BambuConnect client.
        
        Args:
            base_url: Base URL for BambuConnect API
            access_token: Optional access token for authentication
        """
        self.client = BambuConnectClient(base_url, access_token)
        logger.info(f"Initialized BambuConnect client with base URL: {base_url}")
    
    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point for the MCP server."""
    # Load configuration from environment variables
    base_url = os.environ.get("BAMBU_CONNECT_URL", "http://localhost:8080")
    access_token = os.environ.get("BAMBU_CONNECT_TOKEN")
    
    # Create and initialize server
    server = BambuddyMCPServer()
    server.initialize_client(base_url, access_token)
    
    logger.info("Starting Bambuddy MCP Server...")
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
