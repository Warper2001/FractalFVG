"""
Unit tests for the ProjectManager module.

This module tests the functionality of the ProjectManager class,
including project creation, file upload, compilation, and error handling.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.project_manager import ProjectManager, ProjectManagerError
from src.utils.api_client import QuantConnectAPIClient


class TestProjectManager(unittest.TestCase):
    """Test cases for ProjectManager class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_api_client = Mock(spec=QuantConnectAPIClient)
        self.project_manager = ProjectManager(self.mock_api_client)
    
    def test_init_with_api_client(self):
        """Test ProjectManager initialization with API client."""
        self.assertEqual(self.project_manager.api_client, self.mock_api_client)
        self.assertIsNotNone(self.project_manager.logger)
        self.assertIsNotNone(self.project_manager.error_handler)
    
    def test_init_without_api_client(self):
        """Test ProjectManager initialization without API client."""
        manager = ProjectManager()
        self.assertIsNone(manager.api_client)
        # Should log warning but not raise exception
    
    def test_create_project_success_python(self):
        """Test successful creation of Python project."""
        name = "Test Python Project"
        language = "Py"
        description = "Test description"
        
        # Mock API response
        mock_response = {
            "projects": [{
                "id": 12345,
                "name": name,
                "language": language,
                "organizationId": 67890
            }]
        }
        self.mock_api_client.create_project.return_value = mock_response
        self.mock_api_client.update_project.return_value = {"success": True}
        
        result = self.project_manager.create_project(name, language, description)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["project_id"], 12345)
        self.assertEqual(result["name"], name)
        self.assertEqual(result["language"], language)
        self.assertEqual(result["description"], description)
        self.assertIn("created_at", result)
        self.assertIn("url", result)
        
        # Verify API calls
        self.mock_api_client.create_project.assert_called_once_with(name, language)
        self.mock_api_client.update_project.assert_called_once_with(12345, None, description)
    
    def test_create_project_success_csharp(self):
        """Test successful creation of C# project."""
        name = "Test C# Project"
        language = "C#"
        
        mock_response = {
            "projects": [{
                "id": 12346,
                "name": name,
                "language": language,
                "organizationId": 67890
            }]
        }
        self.mock_api_client.create_project.return_value = mock_response
        
        result = self.project_manager.create_project(name, language)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["project_id"], 12346)
        self.assertEqual(result["language"], language)
    
    def test_create_project_invalid_language(self):
        """Test project creation with invalid language."""
        with self.assertRaises(ProjectManagerError) as cm:
            self.project_manager.create_project("Test", "Invalid")
        self.assertIn("Invalid language", str(cm.exception))
    
    def test_create_project_empty_name(self):
        """Test project creation with empty name."""
        with self.assertRaises(ProjectManagerError) as cm:
            self.project_manager.create_project("", "Py")
        self.assertIn("Project name cannot be empty", str(cm.exception))
    
    def test_create_project_no_api_client(self):
        """Test project creation without API client."""
        manager = ProjectManager()
        
        with self.assertRaises(ProjectManagerError) as cm:
            manager.create_project("Test", "Py")
        self.assertIn("API client not available", str(cm.exception))
    
    def test_create_project_api_error(self):
        """Test project creation with API error."""
        self.mock_api_client.create_project.side_effect = Exception("API Error")
        
        with self.assertRaises(ProjectManagerError) as cm:
            self.project_manager.create_project("Test", "Py")
        self.assertIn("Failed to create project", str(cm.exception))
    
    def test_read_project_success(self):
        """Test successful project read."""
        project_id = 12345
        mock_response = {
            "projects": [{
                "id": project_id,
                "name": "Test Project",
                "language": "Py",
                "description": "Test description",
                "created": "2024-01-15T10:30:00Z",
                "modified": "2024-01-20T15:45:00Z",
                "organizationId": 67890,
                "owner": "test_user",
                "collaborators": ["user1", "user2"]
            }]
        }
        self.mock_api_client.read_project.return_value = mock_response
        
        result = self.project_manager.read_project(project_id)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["project_id"], project_id)
        self.assertEqual(result["name"], "Test Project")
        self.assertEqual(result["language"], "Py")
        self.assertEqual(result["description"], "Test description")
        self.assertIn("url", result)
        
        self.mock_api_client.read_project.assert_called_once_with(project_id)
    
    def test_read_project_not_found(self):
        """Test reading non-existent project."""
        self.mock_api_client.read_project.return_value = {"projects": []}
        
        with self.assertRaises(ProjectManagerError) as cm:
            self.project_manager.read_project(99999)
        self.assertIn("not found", str(cm.exception))
    
    def test_read_project_no_api_client(self):
        """Test reading project without API client."""
        manager = ProjectManager()
        
        with self.assertRaises(ProjectManagerError) as cm:
            manager.read_project(12345)
        self.assertIn("API client not available", str(cm.exception))
    
    def test_update_project_success(self):
        """Test successful project update."""
        project_id = 12345
        new_name = "Updated Project"
        new_description = "Updated description"
        
        self.mock_api_client.update_project.return_value = {"success": True}
        
        result = self.project_manager.update_project(project_id, new_name, new_description)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["project_id"], project_id)
        self.assertEqual(result["name"], new_name)
        self.assertEqual(result["description"], new_description)
        self.assertEqual(set(result["updated_fields"]), {"name", "description"})
        self.assertIn("updated_at", result)
        
        self.mock_api_client.update_project.assert_called_once_with(project_id, new_name, new_description)
    
    def test_update_project_no_changes(self):
        """Test project update with no changes specified."""
        with self.assertRaises(ProjectManagerError) as cm:
            self.project_manager.update_project(12345)
        self.assertIn("No updates specified", str(cm.exception))
    
    def test_update_project_no_api_client(self):
        """Test updating project without API client."""
        manager = ProjectManager()
        
        with self.assertRaises(ProjectManagerError) as cm:
            manager.update_project(12345, name="New Name")
        self.assertIn("API client not available", str(cm.exception))
    
    def test_delete_project_success(self):
        """Test successful project deletion."""
        project_id = 12345
        
        # Mock read_project for getting project name
        mock_project_response = {
            "projects": [{
                "id": project_id,
                "name": "Test Project"
            }]
        }
        self.mock_api_client.read_project.return_value = mock_project_response
        self.mock_api_client.delete_project.return_value = {"success": True}
        
        result = self.project_manager.delete_project(project_id)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["project_id"], project_id)
        self.assertEqual(result["project_name"], "Test Project")
        self.assertIn("deleted_at", result)
        
        self.mock_api_client.read_project.assert_called_once_with(project_id)
        self.mock_api_client.delete_project.assert_called_once_with(project_id)
    
    def test_delete_project_no_api_client(self):
        """Test deleting project without API client."""
        manager = ProjectManager()
        
        with self.assertRaises(ProjectManagerError) as cm:
            manager.delete_project(12345)
        self.assertIn("API client not available", str(cm.exception))
    
    def test_list_projects_success(self):
        """Test successful project listing."""
        organization_id = 67890
        
        result = self.project_manager.list_projects(organization_id)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)  # Mock returns 2 projects
        
        for project in result:
            self.assertIn("project_id", project)
            self.assertIn("name", project)
            self.assertIn("language", project)
            self.assertIn("description", project)
            self.assertIn("created", project)
            self.assertIn("modified", project)
            self.assertEqual(project["organization_id"], organization_id)
    
    def test_list_projects_all_organizations(self):
        """Test listing projects without organization filter."""
        result = self.project_manager.list_projects()
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
    
    def test_upload_file_success_with_content(self):
        """Test successful file upload with provided content."""
        project_id = 12345
        file_path = "main.py"
        content = "print('Hello, World!')"
        
        self.mock_api_client.create_file.return_value = {"success": True}
        
        result = self.project_manager.upload_file(project_id, file_path, content)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["project_id"], project_id)
        self.assertEqual(result["file_path"], file_path)
        self.assertEqual(result["file_size"], len(content.encode('utf-8')))
        self.assertIn("uploaded_at", result)
        
        self.mock_api_client.create_file.assert_called_once_with(project_id, file_path, content)
    
    def test_upload_file_success_from_local(self):
        """Test successful file upload from local file."""
        project_id = 12345
        file_path = "test_file.py"
        content = "print('Local file content')"
        
        # Create temporary file
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=content):
            
            self.mock_api_client.create_file.return_value = {"success": True}
            
            result = self.project_manager.upload_file(project_id, file_path)
            
            self.assertTrue(result["success"])
            self.assertEqual(result["file_path"], file_path)
            self.assertEqual(result["file_size"], len(content.encode('utf-8')))
    
    def test_upload_file_local_file_not_found(self):
        """Test file upload when local file doesn't exist."""
        project_id = 12345
        file_path = "nonexistent.py"
        
        with patch('pathlib.Path.exists', return_value=False):
            with self.assertRaises(ProjectManagerError) as cm:
                self.project_manager.upload_file(project_id, file_path)
            self.assertIn("not found", str(cm.exception))
    
    def test_upload_file_no_api_client(self):
        """Test uploading file without API client."""
        manager = ProjectManager()
        
        with self.assertRaises(ProjectManagerError) as cm:
            manager.upload_file(12345, "main.py", "content")
        self.assertIn("API client not available", str(cm.exception))
    
    def test_compile_project_success(self):
        """Test successful project compilation."""
        project_id = 12345
        compile_id = "compile_12345"
        
        mock_response = {"compileId": compile_id}
        self.mock_api_client.compile_project.return_value = mock_response
        
        result = self.project_manager.compile_project(project_id)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["project_id"], project_id)
        self.assertEqual(result["compile_id"], compile_id)
        self.assertEqual(result["status"], "in_progress")
        self.assertIn("started_at", result)
        
        self.mock_api_client.compile_project.assert_called_once_with(project_id)
    
    def test_compile_project_no_api_client(self):
        """Test compiling project without API client."""
        manager = ProjectManager()
        
        with self.assertRaises(ProjectManagerError) as cm:
            manager.compile_project(12345)
        self.assertIn("API client not available", str(cm.exception))
    
    def test_get_compilation_status_success(self):
        """Test successful compilation status check."""
        project_id = 12345
        compile_id = "compile_12345"
        
        mock_response = {
            "status": "success",
            "errors": [],
            "warnings": ["Minor warning"],
            "compileTime": 2.5
        }
        self.mock_api_client.read_compilation_result.return_value = mock_response
        
        result = self.project_manager.get_compilation_status(project_id, compile_id)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["project_id"], project_id)
        self.assertEqual(result["compile_id"], compile_id)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["warnings"], ["Minor warning"])
        self.assertEqual(result["compile_time"], 2.5)
        self.assertIn("checked_at", result)
        
        self.mock_api_client.read_compilation_result.assert_called_once_with(project_id, compile_id)
    
    def test_get_compilation_status_no_api_client(self):
        """Test getting compilation status without API client."""
        manager = ProjectManager()
        
        with self.assertRaises(ProjectManagerError) as cm:
            manager.get_compilation_status(12345, "compile_123")
        self.assertIn("API client not available", str(cm.exception))


class TestProjectManagerError(unittest.TestCase):
    """Test cases for ProjectManagerError exception."""
    
    def test_project_manager_error_creation(self):
        """Test ProjectManagerError exception creation."""
        error = ProjectManagerError("Test error message")
        
        self.assertEqual(str(error), "Test error message")
        self.assertIsInstance(error, Exception)
    
    def test_project_manager_error_inheritance(self):
        """Test ProjectManagerError inherits from Exception."""
        self.assertTrue(issubclass(ProjectManagerError, Exception))


class TestGetProjectManager(unittest.TestCase):
    """Test cases for get_project_manager convenience function."""
    
    def test_get_project_manager_with_client(self):
        """Test getting project manager with API client."""
        mock_client = Mock(spec=QuantConnectAPIClient)
        
        from src.api.project_manager import get_project_manager
        manager = get_project_manager(mock_client)
        
        self.assertIsInstance(manager, ProjectManager)
        self.assertEqual(manager.api_client, mock_client)
    
    def test_get_project_manager_without_client(self):
        """Test getting project manager without API client."""
        from src.api.project_manager import get_project_manager
        manager = get_project_manager()
        
        self.assertIsInstance(manager, ProjectManager)
        self.assertIsNone(manager.api_client)


if __name__ == "__main__":
    unittest.main()