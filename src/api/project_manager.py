"""
Project management module for the Automated QuantConnect Pipeline.

This module provides functionality to manage QuantConnect projects,
including creating projects, uploading files, and compiling projects.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from src.utils.logger import get_logger
from src.utils.api_client import QuantConnectAPIClient
from src.utils.api_error_handler import APIErrorHandler, APIError, ErrorCategory, ErrorSeverity


class ProjectManagerError(Exception):
    """Custom exception for project manager operations."""
    pass


class ProjectManager:
    """
    Manages QuantConnect projects.
    
    Provides functionality to:
    - Create new projects
    - Upload algorithm files
    - Compile projects
    - Read project details
    - Update project information
    - Delete projects
    """
    
    def __init__(self, api_client: Optional[QuantConnectAPIClient] = None):
        """
        Initialize the project manager.
        
        Args:
            api_client: QuantConnect API client instance
        """
        self.logger = get_logger(__name__)
        self.api_client = api_client
        self.error_handler = APIErrorHandler()
        
        if self.api_client is None:
            self.logger.warning("No API client provided - some operations may fail")
    
    def create_project(self, name: str, language: str = "Py", 
                      description: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new QuantConnect project.
        
        Args:
            name: Project name (must be unique within organization)
            language: Programming language ("Py" or "C#")
            description: Optional project description
            
        Returns:
            Project creation response with project details
            
        Raises:
            ProjectManagerError: If project creation fails
        """
        try:
            self.logger.info(f"Creating project '{name}' with language {language}")
            
            if not self.api_client:
                raise ProjectManagerError("API client not available")
            
            # Validate language
            if language not in ["Py", "C#"]:
                raise ProjectManagerError(f"Invalid language '{language}'. Must be 'Py' or 'C#'")
            
            # Validate project name
            if not name or not name.strip():
                raise ProjectManagerError("Project name cannot be empty")
            
            # Create project via API
            response = self.api_client.create_project(name, language)
            
            if not response or "projects" not in response:
                raise ProjectManagerError("Invalid response from project creation API")
            
            project_data = response["projects"][0] if response["projects"] else response
            
            # Add description if provided
            if description:
                self.logger.info(f"Adding description to project {project_data.get('id', 'unknown')}")
                try:
                    self.update_project(project_data["id"], description=description)
                except Exception as e:
                    self.logger.warning(f"Failed to add project description: {e}")
            
            result = {
                "success": True,
                "project_id": project_data.get("id"),
                "name": project_data.get("name"),
                "language": project_data.get("language"),
                "description": description,
                "created_at": datetime.now().isoformat(),
                "organization_id": project_data.get("organizationId"),
                "url": f"https://www.quantconnect.com/project/{project_data.get('id')}"
            }
            
            self.logger.info(f"Project created successfully: {result['name']} (ID: {result['project_id']})")
            return result
            
        except ProjectManagerError:
            raise
        except Exception as e:
            error_msg = f"Failed to create project '{name}': {str(e)}"
            self.logger.error(error_msg)
            raise ProjectManagerError(error_msg)
    
    def read_project(self, project_id: int) -> Dict[str, Any]:
        """
        Read project details.
        
        Args:
            project_id: Project ID to read
            
        Returns:
            Project details
            
        Raises:
            ProjectManagerError: If project read fails
        """
        try:
            self.logger.info(f"Reading project details for project {project_id}")
            
            if not self.api_client:
                raise ProjectManagerError("API client not available")
            
            response = self.api_client.read_project(project_id)
            
            if not response or "projects" not in response or not response["projects"]:
                raise ProjectManagerError(f"Project {project_id} not found")
            
            project_data = response["projects"][0]
            
            result = {
                "success": True,
                "project_id": project_data.get("id"),
                "name": project_data.get("name"),
                "language": project_data.get("language"),
                "description": project_data.get("description"),
                "created": project_data.get("created"),
                "modified": project_data.get("modified"),
                "organization_id": project_data.get("organizationId"),
                "owner": project_data.get("owner"),
                "collaborators": project_data.get("collaborators", []),
                "url": f"https://www.quantconnect.com/project/{project_data.get('id')}"
            }
            
            self.logger.info(f"Project details retrieved successfully for project {project_id}")
            return result
            
        except ProjectManagerError:
            raise
        except Exception as e:
            error_msg = f"Failed to read project {project_id}: {str(e)}"
            self.logger.error(error_msg)
            raise ProjectManagerError(error_msg)
    
    def update_project(self, project_id: int, name: Optional[str] = None, 
                      description: Optional[str] = None) -> Dict[str, Any]:
        """
        Update project information.
        
        Args:
            project_id: Project ID to update
            name: New project name (optional)
            description: New project description (optional)
            
        Returns:
            Update response
            
        Raises:
            ProjectManagerError: If project update fails
        """
        try:
            self.logger.info(f"Updating project {project_id}")
            
            if not self.api_client:
                raise ProjectManagerError("API client not available")
            
            if not name and not description:
                raise ProjectManagerError("No updates specified - provide name or description")
            
            response = self.api_client.update_project(project_id, name, description)
            
            if not response:
                raise ProjectManagerError("Invalid response from project update API")
            
            result = {
                "success": True,
                "project_id": project_id,
                "updated_fields": []
            }
            
            if name:
                result["updated_fields"].append("name")
                result["name"] = name
            
            if description:
                result["updated_fields"].append("description")
                result["description"] = description
            
            result["updated_at"] = datetime.now().isoformat()
            
            self.logger.info(f"Project {project_id} updated successfully: {result['updated_fields']}")
            return result
            
        except ProjectManagerError:
            raise
        except Exception as e:
            error_msg = f"Failed to update project {project_id}: {str(e)}"
            self.logger.error(error_msg)
            raise ProjectManagerError(error_msg)
    
    def delete_project(self, project_id: int) -> Dict[str, Any]:
        """
        Delete a project.
        
        Args:
            project_id: Project ID to delete
            
        Returns:
            Deletion response
            
        Raises:
            ProjectManagerError: If project deletion fails
        """
        try:
            self.logger.info(f"Deleting project {project_id}")
            
            if not self.api_client:
                raise ProjectManagerError("API client not available")
            
            # First get project details for logging
            try:
                project_details = self.read_project(project_id)
                project_name = project_details.get("name", "Unknown")
            except:
                project_name = "Unknown"
            
            response = self.api_client.delete_project(project_id)
            
            if not response:
                raise ProjectManagerError("Invalid response from project deletion API")
            
            result = {
                "success": True,
                "project_id": project_id,
                "project_name": project_name,
                "deleted_at": datetime.now().isoformat()
            }
            
            self.logger.info(f"Project '{project_name}' (ID: {project_id}) deleted successfully")
            return result
            
        except ProjectManagerError:
            raise
        except Exception as e:
            error_msg = f"Failed to delete project {project_id}: {str(e)}"
            self.logger.error(error_msg)
            raise ProjectManagerError(error_msg)
    
    def list_projects(self, organization_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List all projects (mock implementation - QuantConnect API doesn't have a list endpoint).
        
        Args:
            organization_id: Optional organization ID to filter projects
            
        Returns:
            List of project summaries
            
        Raises:
            ProjectManagerError: If listing fails
        """
        try:
            self.logger.info(f"Listing projects for organization {organization_id or 'all'}")
            
            # Note: QuantConnect API doesn't have a direct list projects endpoint
            # This is a mock implementation for development
            # In production, you might need to maintain a local registry
            
            mock_projects = [
                {
                    "project_id": 12345,
                    "name": "Sample Trading Algorithm",
                    "language": "Py",
                    "description": "Sample algorithm for testing",
                    "created": "2024-01-15T10:30:00Z",
                    "modified": "2024-01-20T15:45:00Z",
                    "organization_id": organization_id or 67890
                },
                {
                    "project_id": 12346,
                    "name": "Market Maker Strategy",
                    "language": "C#",
                    "description": "Advanced market making algorithm",
                    "created": "2024-01-10T08:15:00Z",
                    "modified": "2024-01-18T12:30:00Z",
                    "organization_id": organization_id or 67890
                }
            ]
            
            # Filter by organization if specified
            if organization_id:
                mock_projects = [p for p in mock_projects if p["organization_id"] == organization_id]
            
            self.logger.info(f"Found {len(mock_projects)} projects")
            return mock_projects
            
        except Exception as e:
            error_msg = f"Failed to list projects: {str(e)}"
            self.logger.error(error_msg)
            raise ProjectManagerError(error_msg)
    
    def upload_file(self, project_id: int, file_path: str, 
                   content: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a file to a project.
        
        Args:
            project_id: Project ID to upload file to
            file_path: File path within the project (e.g., "main.py")
            content: File content (if None, reads from local file)
            
        Returns:
            File upload response
            
        Raises:
            ProjectManagerError: If file upload fails
        """
        try:
            self.logger.info(f"Uploading file '{file_path}' to project {project_id}")
            
            if not self.api_client:
                raise ProjectManagerError("API client not available")
            
            # Get file content if not provided
            if content is None:
                # Try to read from local file
                local_path = Path(file_path)
                if local_path.exists():
                    content = local_path.read_text(encoding='utf-8')
                else:
                    raise ProjectManagerError(f"Local file '{file_path}' not found and no content provided")
            
            # Upload file via API
            response = self.api_client.create_file(project_id, file_path, content)
            
            if not response:
                raise ProjectManagerError("Invalid response from file upload API")
            
            result = {
                "success": True,
                "project_id": project_id,
                "file_path": file_path,
                "file_size": len(content.encode('utf-8')),
                "uploaded_at": datetime.now().isoformat()
            }
            
            self.logger.info(f"File '{file_path}' uploaded successfully to project {project_id}")
            return result
            
        except ProjectManagerError:
            raise
        except Exception as e:
            error_msg = f"Failed to upload file '{file_path}' to project {project_id}: {str(e)}"
            self.logger.error(error_msg)
            raise ProjectManagerError(error_msg)
    
    def compile_project(self, project_id: int) -> Dict[str, Any]:
        """
        Compile a project.
        
        Args:
            project_id: Project ID to compile
            
        Returns:
            Compilation response with compile ID
            
        Raises:
            ProjectManagerError: If compilation fails
        """
        try:
            self.logger.info(f"Compiling project {project_id}")
            
            if not self.api_client:
                raise ProjectManagerError("API client not available")
            
            response = self.api_client.compile_project(project_id)
            
            if not response or "compileId" not in response:
                raise ProjectManagerError("Invalid response from project compilation API")
            
            compile_id = response["compileId"]
            
            result = {
                "success": True,
                "project_id": project_id,
                "compile_id": compile_id,
                "status": "in_progress",
                "started_at": datetime.now().isoformat()
            }
            
            self.logger.info(f"Project {project_id} compilation started (Compile ID: {compile_id})")
            return result
            
        except ProjectManagerError:
            raise
        except Exception as e:
            error_msg = f"Failed to compile project {project_id}: {str(e)}"
            self.logger.error(error_msg)
            raise ProjectManagerError(error_msg)
    
    def get_compilation_status(self, project_id: int, compile_id: str) -> Dict[str, Any]:
        """
        Get compilation status.
        
        Args:
            project_id: Project ID
            compile_id: Compilation ID
            
        Returns:
            Compilation status
            
        Raises:
            ProjectManagerError: If status check fails
        """
        try:
            self.logger.info(f"Checking compilation status for project {project_id}, compile {compile_id}")
            
            if not self.api_client:
                raise ProjectManagerError("API client not available")
            
            response = self.api_client.read_compilation_result(project_id, compile_id)
            
            if not response:
                raise ProjectManagerError("Invalid response from compilation status API")
            
            result = {
                "success": True,
                "project_id": project_id,
                "compile_id": compile_id,
                "status": response.get("status", "unknown"),
                "errors": response.get("errors", []),
                "warnings": response.get("warnings", []),
                "compile_time": response.get("compileTime"),
                "checked_at": datetime.now().isoformat()
            }
            
            self.logger.info(f"Compilation status for project {project_id}: {result['status']}")
            return result
            
        except ProjectManagerError:
            raise
        except Exception as e:
            error_msg = f"Failed to get compilation status for project {project_id}: {str(e)}"
            self.logger.error(error_msg)
            raise ProjectManagerError(error_msg)


# Convenience function for creating project manager
def get_project_manager(api_client: Optional[QuantConnectAPIClient] = None) -> ProjectManager:
    """
    Get a configured project manager instance.
    
    Args:
        api_client: Optional API client instance
        
    Returns:
        Configured ProjectManager instance
    """
    return ProjectManager(api_client)