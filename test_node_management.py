#!/usr/bin/env python3
"""
Simple test for QuantConnect API authentication and node checking
"""

import requests
import base64
import json

def test_authentication():
    """Test QuantConnect API authentication"""
    
    user_id = "421529"
    api_token = "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"
    
    # Use Basic authentication with base64 encoding
    credentials = f"{user_id}:{api_token}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Test authentication by getting projects
        response = requests.get("https://www.quantconnect.com/api/v2/projects", headers=headers)
        
        print(f"Projects API Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            projects = result.get('projects', [])
            print(f"✅ Authentication successful! Found {len(projects)} projects")
            
            # Find our project
            target_project_id = 25780050
            our_project = None
            for project in projects:
                if project.get('projectId') == target_project_id:
                    our_project = project
                    break
            
            if our_project:
                print(f"✅ Found target project: {our_project.get('name')}")
                
                # Check nodes
                nodes = our_project.get('nodes', {})
                backtest_nodes = nodes.get('backtest', [])
                
                print(f"📊 Backtest Nodes: {len(backtest_nodes)}")
                for node in backtest_nodes:
                    busy = node.get('busy', False)
                    used_by = node.get('usedBy', 'None')
                    name = node.get('name', 'Unknown')
                    print(f"   • {name} - Busy: {busy} - Used by: {used_by}")
                
                return True
            else:
                print(f"❌ Project {target_project_id} not found")
                return False
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_stop_backtest():
    """Test stopping a running backtest"""
    
    user_id = "421529"
    api_token = "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"
    
    credentials = f"{user_id}:{api_token}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/json'
    }
    
    project_id = 25780050
    
    try:
        # Get backtests for the project
        response = requests.get(f"https://www.quantconnect.com/api/v2/backtests/read/{project_id}", headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            backtests = result.get('backtests', [])
            
            print(f"📋 Found {len(backtests)} backtests")
            
            # Find running backtests
            running_backtests = []
            for bt in backtests:
                status = bt.get('status', '')
                if status in ['Running', 'In Progress', 'inprogress']:
                    running_backtests.append(bt)
            
            if running_backtests:
                print(f"🔄 Found {len(running_backtests)} running backtest(s):")
                for bt in running_backtests:
                    name = bt.get('name', 'Unknown')
                    bt_id = bt.get('backtestId', 'Unknown')
                    print(f"   • {name} ({bt_id})")
                
                # Try to stop the first running backtest
                target_bt = running_backtests[0]
                bt_id = target_bt.get('backtestId')
                
                print(f"🛑 Attempting to stop backtest: {bt_id}")
                
                stop_response = requests.delete(f"https://www.quantconnect.com/api/v2/backtests/delete/{project_id}/{bt_id}", headers=headers)
                
                print(f"Stop response status: {stop_response.status_code}")
                if stop_response.status_code == 200:
                    print("✅ Backtest stop request sent successfully")
                    return True
                else:
                    print(f"❌ Failed to stop backtest: {stop_response.text}")
                    return False
            else:
                print("ℹ️ No running backtests found")
                return True
        else:
            print(f"❌ Failed to get backtests: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error stopping backtest: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing QuantConnect API Authentication and Node Management")
    print("=" * 60)
    
    # Test authentication
    if test_authentication():
        print("\n✅ Authentication test passed")
        
        # Test stopping backtest
        print("\n🛑 Testing backtest stop functionality...")
        if test_stop_backtest():
            print("✅ Node management test passed")
        else:
            print("❌ Node management test failed")
    else:
        print("❌ Authentication test failed")