#!/usr/bin/env python3
"""
Quick test to check QuantConnect node status
"""

import os
import requests
import base64

# Set credentials
user_id = "421529"
api_token = "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"
base_url = "https://www.quantconnect.com/api/v2"

# Create session with auth
session = requests.Session()
credentials = f"{user_id}:{api_token}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()
session.headers.update({
    'Authorization': f'Basic {encoded_credentials}',
    'Content-Type': 'application/json'
})

# Test authentication and get projects
print("🔍 Testing authentication...")
response = session.get(f"{base_url}/projects")
print(f"Auth response: {response.status_code}")

if response.status_code == 200:
    print("✅ Authentication successful")
    
    # Check project 25780050
    project_id = 25780050
    print(f"\n🔍 Checking project {project_id}...")
    response = session.get(f"{base_url}/projects/read/{project_id}")
    print(f"Project response: {response.status_code}")
    
    if response.status_code == 200:
        project_data = response.json()
        print("✅ Project data retrieved")
        
        # Check nodes
        if 'projects' in project_data:
            projects = project_data.get('projects', [])
            our_project = None
            for project in projects:
                if project.get('projectId') == project_id:
                    our_project = project
                    break
            
            if our_project:
                nodes = our_project.get('nodes', {})
            else:
                print(f"❌ Project {project_id} not found")
                nodes = {}
        else:
            nodes = project_data.get('nodes', {})
        
        backtest_nodes = nodes.get('backtest', [])
        print(f"\n📊 Backtest nodes: {len(backtest_nodes)}")
        
        for node in backtest_nodes:
            busy = node.get('busy', False)
            used_by = node.get('usedBy', 'None')
            name = node.get('name', 'Unknown')
            print(f"   • {name}: Busy={busy}, UsedBy={used_by}")
            
        # Check running backtests
        print(f"\n🔍 Checking backtests...")
        response = session.get(f"{base_url}/backtests/read/{project_id}")
        if response.status_code == 200:
            result = response.json()
            backtests = result.get('backtests', [])
            print(f"📋 Total backtests: {len(backtests)}")
            
            running_count = 0
            for bt in backtests:
                status = bt.get('status', '')
                name = bt.get('name', 'Unknown')
                if status in ['Running', 'In Progress', 'inprogress']:
                    running_count += 1
                    print(f"   🏃 RUNNING: {name} ({status})")
            
            if running_count == 0:
                print("✅ No running backtests - nodes should be available")
            else:
                print(f"⚠️ {running_count} running backtest(s) found")
        else:
            print(f"❌ Failed to get backtests: {response.status_code}")
    else:
        print(f"❌ Failed to get project: {response.status_code}")
        print(f"Response: {response.text}")
else:
    print(f"❌ Authentication failed: {response.status_code}")
    print(f"Response: {response.text}")