"""BambuConnect API client for interacting with Bambu Lab printers."""

import json
import logging
from typing import Any, Dict, List, Optional

import requests
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class PrinterInfo(BaseModel):
    """Information about a Bambu Lab printer."""
    
    device_id: str = Field(..., description="Unique device ID")
    name: str = Field(..., description="Printer name")
    model: str = Field(..., description="Printer model")
    online: bool = Field(default=False, description="Whether printer is online")


class PrinterStatus(BaseModel):
    """Current status of a Bambu Lab printer."""
    
    device_id: str = Field(..., description="Unique device ID")
    state: str = Field(..., description="Current printer state")
    progress: int = Field(default=0, description="Print progress percentage")
    current_file: Optional[str] = Field(default=None, description="Currently printing file")
    bed_temp: Optional[float] = Field(default=None, description="Bed temperature")
    nozzle_temp: Optional[float] = Field(default=None, description="Nozzle temperature")


class PrintJob(BaseModel):
    """Information about a print job."""
    
    job_id: str = Field(..., description="Job ID")
    filename: str = Field(..., description="File name")
    status: str = Field(..., description="Job status")
    progress: int = Field(default=0, description="Progress percentage")
    start_time: Optional[str] = Field(default=None, description="Start time")
    end_time: Optional[str] = Field(default=None, description="End time")


class BambuConnectClient:
    """Client for interacting with BambuConnect API."""
    
    def __init__(self, base_url: str, access_token: Optional[str] = None):
        """Initialize the BambuConnect client.
        
        Args:
            base_url: Base URL for BambuConnect API
            access_token: Optional access token for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.access_token = access_token
        self.session = requests.Session()
        
        if access_token:
            self.session.headers.update({
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            })
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make an API request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional arguments for requests
            
        Returns:
            Response data as dictionary
            
        Raises:
            requests.RequestException: If request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        logger.debug(f"Making {method} request to {url}")
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def get_printers(self) -> List[PrinterInfo]:
        """Get list of available printers.
        
        Returns:
            List of printer information
        """
        try:
            data = self._make_request('GET', '/api/printers')
            printers = []
            
            for printer_data in data.get('printers', []):
                printers.append(PrinterInfo(
                    device_id=printer_data.get('device_id', ''),
                    name=printer_data.get('name', 'Unknown'),
                    model=printer_data.get('model', 'Unknown'),
                    online=printer_data.get('online', False)
                ))
            
            return printers
        except Exception as e:
            logger.error(f"Failed to get printers: {e}")
            return []
    
    def get_printer_status(self, device_id: str) -> Optional[PrinterStatus]:
        """Get current status of a specific printer.
        
        Args:
            device_id: Unique device ID of the printer
            
        Returns:
            Printer status or None if not found
        """
        try:
            data = self._make_request('GET', f'/api/printers/{device_id}/status')
            
            return PrinterStatus(
                device_id=device_id,
                state=data.get('state', 'unknown'),
                progress=data.get('progress', 0),
                current_file=data.get('current_file'),
                bed_temp=data.get('bed_temp'),
                nozzle_temp=data.get('nozzle_temp')
            )
        except Exception as e:
            logger.error(f"Failed to get printer status: {e}")
            return None
    
    def get_print_jobs(self, device_id: Optional[str] = None) -> List[PrintJob]:
        """Get list of print jobs.
        
        Args:
            device_id: Optional device ID to filter jobs
            
        Returns:
            List of print jobs
        """
        try:
            endpoint = '/api/jobs'
            params = {}
            
            if device_id:
                params['device_id'] = device_id
            
            data = self._make_request('GET', endpoint, params=params)
            jobs = []
            
            for job_data in data.get('jobs', []):
                jobs.append(PrintJob(
                    job_id=job_data.get('job_id', ''),
                    filename=job_data.get('filename', 'Unknown'),
                    status=job_data.get('status', 'unknown'),
                    progress=job_data.get('progress', 0),
                    start_time=job_data.get('start_time'),
                    end_time=job_data.get('end_time')
                ))
            
            return jobs
        except Exception as e:
            logger.error(f"Failed to get print jobs: {e}")
            return []
    
    def get_job_details(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific print job.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job details or None if not found
        """
        try:
            data = self._make_request('GET', f'/api/jobs/{job_id}')
            return data
        except Exception as e:
            logger.error(f"Failed to get job details: {e}")
            return None
