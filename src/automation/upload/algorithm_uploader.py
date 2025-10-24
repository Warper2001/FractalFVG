"""
Algorithm uploader for the Automated QuantConnect Pipeline.

Handles uploading validated algorithms to QuantConnect.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import uuid
from datetime import datetime

from ..models.algorithm import Algorithm, AlgorithmFile, AlgorithmStatus
from ..models.pipeline_execution import PipelineExecution, PipelineStage, PipelineStatus
from ...utils.logger import get_logger
from ...utils.api_client import QuantConnectAPIClient
from ...utils.credential_manager import get_quantconnect_credential_manager
from .validation import AlgorithmValidator, ValidationResult


class AlgorithmUploader:
    """Uploads algorithms to QuantConnect with comprehensive error handling."""
    
    def __init__(self, pipeline_execution: Optional[PipelineExecution] = None):
        """
        Initialize algorithm uploader.
        
        Args:
            pipeline_execution: Optional pipeline execution for tracking
        """
        self.logger = get_logger()
        self.pipeline_execution = pipeline_execution
        self.validator = AlgorithmValidator()
        self.api_client: Optional[QuantConnectAPIClient] = None
        
        # Initialize credentials
        self._initialize_credentials()
    
    def _initialize_credentials(self):
        """Initialize QuantConnect API credentials."""
        try:
            cred_manager = get_quantconnect_credential_manager()
            user_id, api_token, organization_id = cred_manager.get_quantconnect_credentials()
            
            if not user_id or not api_token:
                raise ValueError("QuantConnect credentials not found")
            
            self.api_client = QuantConnectAPIClient(
                user_id=user_id,
                api_token=api_token,
                organization_id=organization_id
            )
            
            self.logger.info("QuantConnect credentials initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize credentials: {e}")
            raise
    
    def upload_algorithm(self, algorithm: Algorithm) -> Dict[str, Any]:
        """
        Upload algorithm to QuantConnect.
        
        Args:
            algorithm: Algorithm to upload
            
        Returns:
            Upload result with project details
        """
        if not self.api_client:
            raise RuntimeError("API client not initialized")
        
        self.logger.info(f"Starting upload for algorithm: {algorithm.name}")
        
        try:
            # Validate algorithm first
            validation_result = self.validator.validate_algorithm(algorithm)
            
            if not validation_result.is_valid:
                error_msg = f"Algorithm validation failed: {validation_result.errors}"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'validation_errors': validation_result.errors,
                    'validation_warnings': validation_result.warnings
                }
            
            # Log validation warnings
            if validation_result.warnings:
                self.logger.warning(f"Validation warnings: {validation_result.warnings}")
            
            # Create project
            project_result = self._create_project(algorithm)
            
            if not project_result['success']:
                return project_result
            
            project_id = project_result['project_id']
            
            # Upload files
            upload_result = self._upload_files(project_id, algorithm.files)
            
            if not upload_result['success']:
                # Clean up failed project
                self._cleanup_project(project_id)
                return upload_result
            
            # Compile project
            compile_result = self._compile_project(project_id)
            
            if not compile_result['success']:
                # Clean up failed project
                self._cleanup_project(project_id)
                return compile_result
            
            # Update algorithm status
            algorithm.status = AlgorithmStatus.UPLOADED
            algorithm.project_id = project_id
            
            result = {
                'success': True,
                'project_id': project_id,
                'compile_id': compile_result['compile_id'],
                'validation_warnings': validation_result.warnings,
                'uploaded_files': len(algorithm.files),
                'upload_time': datetime.utcnow().isoformat()
            }
            
            self.logger.info(f"Algorithm uploaded successfully: {algorithm.name} (Project ID: {project_id})")
            return result
            
        except Exception as e:
            error_msg = f"Upload failed: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _create_project(self, algorithm: Algorithm) -> Dict[str, Any]:
        """Create QuantConnect project."""
        try:
            self.logger.info(f"Creating project: {algorithm.name}")
            
            response = self.api_client.create_project(
                name=algorithm.name,
                language=algorithm.language
            )
            
            if 'projects' in response and response['projects']:
                project_id = response['projects'][0]['id']
                self.logger.info(f"Project created successfully: {project_id}")
                
                return {
                    'success': True,
                    'project_id': project_id,
                    'project_name': algorithm.name
                }
            else:
                error_msg = "Failed to create project - no project ID in response"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'response': response
                }
                
        except Exception as e:
            error_msg = f"Project creation failed: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _upload_files(self, project_id: int, files: List[AlgorithmFile]) -> Dict[str, Any]:
        """Upload files to project."""
        try:
            self.logger.info(f"Uploading {len(files)} files to project {project_id}")
            
            uploaded_files = []
            errors = []
            
            for file in files:
                try:
                    response = self.api_client.create_file(
                        project_id=project_id,
                        name=file.name,
                        content=file.content
                    )
                    
                    if response.get('success'):
                        uploaded_files.append(file.name)
                        self.logger.debug(f"File uploaded: {file.name}")
                    else:
                        error_msg = f"Failed to upload file {file.name}: {response}"
                        errors.append(error_msg)
                        self.logger.error(error_msg)
                        
                except Exception as e:
                    error_msg = f"Exception uploading file {file.name}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            if errors:
                return {
                    'success': False,
                    'error': f"Failed to upload {len(errors)} files",
                    'upload_errors': errors,
                    'uploaded_files': uploaded_files
                }
            
            self.logger.info(f"All files uploaded successfully: {len(uploaded_files)} files")
            return {
                'success': True,
                'uploaded_files': uploaded_files
            }
            
        except Exception as e:
            error_msg = f"File upload failed: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _compile_project(self, project_id: int) -> Dict[str, Any]:
        """Compile project."""
        try:
            self.logger.info(f"Compiling project {project_id}")
            
            response = self.api_client.compile_project(project_id)
            
            if 'compileId' in response:
                compile_id = response['compileId']
                self.logger.info(f"Compilation started: {compile_id}")
                
                # Wait for compilation to complete
                compilation_result = self._wait_for_compilation(project_id, compile_id)
                
                return compilation_result
            else:
                error_msg = "Failed to start compilation - no compile ID in response"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'response': response
                }
                
        except Exception as e:
            error_msg = f"Compilation failed: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _wait_for_compilation(self, project_id: int, compile_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for compilation to complete."""
        import time
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = self.api_client.read_compilation_result(project_id, compile_id)
                
                if response.get('state') == 'BuildSuccess':
                    self.logger.info(f"Compilation successful: {compile_id}")
                    return {
                        'success': True,
                        'compile_id': compile_id,
                        'compilation_time': time.time() - start_time
                    }
                elif response.get('state') in ['BuildError', 'RuntimeError']:
                    error_msg = f"Compilation failed: {response.get('error', 'Unknown error')}"
                    self.logger.error(error_msg)
                    return {
                        'success': False,
                        'error': error_msg,
                        'compile_id': compile_id,
                        'compilation_time': time.time() - start_time
                    }
                elif response.get('state') in ['Build', 'Runtime']:
                    # Still compiling, wait and retry
                    time.sleep(5)
                    continue
                else:
                    # Unknown state, wait and retry
                    self.logger.warning(f"Unknown compilation state: {response.get('state')}")
                    time.sleep(5)
                    continue
                    
            except Exception as e:
                self.logger.error(f"Error checking compilation status: {e}")
                time.sleep(5)
                continue
        
        # Timeout
        error_msg = f"Compilation timeout after {timeout} seconds"
        self.logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'compile_id': compile_id,
            'compilation_time': timeout
        }
    
    def _cleanup_project(self, project_id: int):
        """Clean up failed project."""
        try:
            self.logger.info(f"Cleaning up failed project {project_id}")
            response = self.api_client.delete_project(project_id)
            
            if response.get('success'):
                self.logger.info(f"Project {project_id} cleaned up successfully")
            else:
                self.logger.warning(f"Failed to clean up project {project_id}")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up project {project_id}: {e}")
    
    def update_algorithm(self, algorithm: Algorithm) -> Dict[str, Any]:
        """Update existing algorithm."""
        if not algorithm.project_id:
            return {
                'success': False,
                'error': 'No project ID specified for update'
            }
        
        try:
            # Validate algorithm
            validation_result = self.validator.validate_algorithm(algorithm)
            
            if not validation_result.is_valid:
                return {
                    'success': False,
                    'error': 'Algorithm validation failed',
                    'validation_errors': validation_result.errors
                }
            
            # Update files
            upload_result = self._upload_files(algorithm.project_id, algorithm.files)
            
            if not upload_result['success']:
                return upload_result
            
            # Compile project
            compile_result = self._compile_project(algorithm.project_id)
            
            if not compile_result['success']:
                return compile_result
            
            return {
                'success': True,
                'project_id': algorithm.project_id,
                'compile_id': compile_result['compile_id'],
                'updated_files': len(algorithm.files)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Update failed: {str(e)}"
            }
    
    def close(self):
        """Clean up resources."""
        if self.api_client:
            self.api_client.close()