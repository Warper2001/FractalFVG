#!/usr/bin/env python3

import requests
import hashlib
import time
import hmac
import base64
import os
from datetime import datetime

class QuantConnectAPIClient:
    def __init__(self):
        self.base_url = "https://www.quantconnect.com/api/v2"
        self.user_id = os.getenv('QUANTCONNECT_USER_ID')
        self.api_token = os.getenv('QUANTCONNECT_API_TOKEN')
        
        if not self.user_id or not self.api_token:
            raise ValueError("QUANTCONNECT_USER_ID and QUANTCONNECT_API_TOKEN environment variables must be set")
    
    def _get_auth_headers(self):
        """Generate authentication headers using correct QuantConnect method"""
        timestamp = str(int(time.time()))
        
        # Create time-stamped token
        time_stamped_token = f"{self.api_token}:{timestamp}".encode('utf-8')
        hashed_token = hashlib.sha256(time_stamped_token).hexdigest()
        
        # Create authentication string
        auth_string = f"{self.user_id}:{hashed_token}".encode('utf-8')
        authentication = base64.b64encode(auth_string).decode('ascii')
        
        return {
            'Authorization': authentication,
            'Timestamp': timestamp
        }
    
    def _make_request(self, endpoint, method='GET', data=None):
        """Make authenticated request to QuantConnect API"""
        headers = self._get_auth_headers()
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                headers['Content-Type'] = 'application/json'
                response = requests.post(url, headers=headers, json=data)
            
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def create_project(self, name, language="Py"):
        """Create a new project"""
        data = {
            'name': name,
            'language': language,
            'organizationId': os.getenv('QUANTCONNECT_ORGANIZATION_ID', '')
        }
        
        response = self._make_request('projects/create', method='POST', data=data)
        
        if response.get('success'):
            return {
                'success': True,
                'projectId': response.get('projects', {}).get('id'),
                'message': 'Project created successfully'
            }
        else:
            return {
                'success': False,
                'error': response.get('errors', ['Unknown error'])[0] if response.get('errors') else 'Unknown error'
            }
    
    def create_file(self, project_id, name, content):
        """Create a file in the project"""
        data = {
            'name': name,
            'content': content,
            'projectId': project_id
        }
        
        response = self._make_request('files/create', method='POST', data=data)
        
        if response.get('success'):
            return {
                'success': True,
                'message': 'File created successfully'
            }
        else:
            return {
                'success': False,
                'error': response.get('errors', ['Unknown error'])[0] if response.get('errors') else 'Unknown error'
            }
    
    def compile_project(self, project_id):
        """Compile a project"""
        data = {'projectId': project_id}
        
        response = self._make_request('compile/create', method='POST', data=data)
        
        if response.get('success'):
            return {
                'success': True,
                'compileId': response.get('compileId'),
                'message': 'Compilation started'
            }
        else:
            return {
                'success': False,
                'error': response.get('errors', ['Unknown error'])[0] if response.get('errors') else 'Unknown error'
            }
    
    def read_compilation_result(self, project_id, compile_id):
        """Read compilation result"""
        response = self._make_request(f'compile/read?projectId={project_id}&compileId={compile_id}')
        
        return response

def test_deployment():
    """Test deployment with minimal futures algorithm"""
    
    # Initialize client
    client = QuantConnectAPIClient()
    
    # Read the algorithm file
    with open("minimal_futures_test.py", "r") as f:
        algorithm_content = f.read()
    
    print("Testing QuantConnect deployment...")
    
    # Step 1: Create project
    print("1. Creating project...")
    project_result = client.create_project(
        name="Test Futures Algorithm",
        language="Py"
    )
    
    if project_result["success"]:
        project_id = project_result["projectId"]
        print(f"   ✅ Project created successfully! ID: {project_id}")
    else:
        print(f"   ❌ Project creation failed: {project_result.get('error', 'Unknown error')}")
        return
    
    # Step 2: Upload algorithm file
    print("2. Uploading algorithm file...")
    upload_result = client.create_file(
        project_id=project_id,
        name="Main.py",
        content=algorithm_content
    )
    
    if upload_result["success"]:
        print(f"   ✅ File uploaded successfully!")
    else:
        print(f"   ❌ File upload failed: {upload_result.get('error', 'Unknown error')}")
        return
    
    # Step 3: Compile project
    print("3. Compiling project...")
    compile_result = client.compile_project(project_id)
    
    if compile_result["success"]:
        compile_id = compile_result["compileId"]
        print(f"   ✅ Compilation started! ID: {compile_id}")
        
        # Step 4: Check compilation result
        print("4. Checking compilation result...")
        time.sleep(10)  # Wait for compilation
        
        result_result = client.read_compilation_result(project_id, compile_id)
        print(f"   Compilation state: {result_result.get('state', 'Unknown')}")
        
        if result_result.get("state") == "BuildSuccess":
            print("   ✅ Compilation successful!")
            print("   🎉 Full deployment pipeline working!")
        else:
            print(f"   ❌ Compilation failed")
            errors = result_result.get('errors', [])
            if errors:
                print(f"   Errors: {errors}")
    else:
        print(f"   ❌ Compilation failed to start: {compile_result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    test_deployment()