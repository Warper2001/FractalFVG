#!/usr/bin/env python3
"""Debug script to test project creation API response."""

import sys
import json
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.deployment.config import load_credentials
from src.api.quantconnect_client import QuantConnectAPIClient

def main():
    """Test project creation and debug response."""
    try:
        # Load credentials
        credentials = load_credentials()
        
        # Create API client
        client = QuantConnectAPIClient(credentials)
        
        # Test project creation
        print("Creating test project...")
        response = client.create_project(
            name="Debug-Test-Project",
            language="Py",
            description="Debug test project"
        )
        
        print("API Response:")
        print(json.dumps(response, indent=2))
        
        # Try to extract project ID
        projects = response.get('projects', {})
        print(f"\nProjects field: {projects}")
        print(f"Type of projects: {type(projects)}")
        
        if isinstance(projects, dict):
            print(f"Dict keys: {list(projects.keys())}")
            if 'id' in projects:
                print(f"Project ID from dict: {projects['id']}")
        elif isinstance(projects, list):
            print(f"List length: {len(projects)}")
            if projects:
                print(f"First item: {projects[0]}")
                if 'id' in projects[0]:
                    print(f"Project ID from list: {projects[0]['id']}")
        
        # Check other possible locations
        if 'id' in response:
            print(f"Project ID from root: {response['id']}")
        
        if 'projectId' in response:
            print(f"Project ID from projectId: {response['projectId']}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()