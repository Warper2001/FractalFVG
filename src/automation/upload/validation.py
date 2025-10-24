"""
Algorithm validation logic for the Automated QuantConnect Pipeline.

Validates trading algorithms before upload to QuantConnect.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from ..models.algorithm import Algorithm, AlgorithmFile, AlgorithmStatus
from ...utils.logger import get_logger


@dataclass
class ValidationResult:
    """Result of algorithm validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


class AlgorithmValidator:
    """Validates trading algorithms for QuantConnect compatibility."""
    
    def __init__(self):
        self.logger = get_logger()
        
        # QuantConnect required imports and patterns
        self.required_imports = {
            'QuantConnect.Algorithm': ['QCAlgorithm'],
            'QuantConnect.Data': ['Slice', 'TradeBars', 'Tick'],
            'QuantConnect.Indicators': ['Indicator', 'IndicatorBase'],
        }
        
        # Required algorithm structure
        self.required_methods = ['Initialize', 'OnData']
        
        # File size limits (in bytes)
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.max_total_size = 50 * 1024 * 1024  # 50MB
        
        # Supported file extensions
        self.supported_extensions = {'.cs', '.py', '.py'}
    
    def validate_algorithm(self, algorithm: Algorithm) -> ValidationResult:
        """
        Validate complete algorithm.
        
        Args:
            algorithm: Algorithm to validate
            
        Returns:
            ValidationResult with validation details
        """
        errors = []
        warnings = []
        metadata = {}
        
        self.logger.info(f"Validating algorithm: {algorithm.name}")
        
        # Validate basic algorithm properties
        basic_errors, basic_warnings, basic_metadata = self._validate_basic_properties(algorithm)
        errors.extend(basic_errors)
        warnings.extend(basic_warnings)
        metadata.update(basic_metadata)
        
        # Validate files
        file_errors, file_warnings, file_metadata = self._validate_files(algorithm.files)
        errors.extend(file_errors)
        warnings.extend(file_warnings)
        metadata.update(file_metadata)
        
        # Validate main algorithm file
        if algorithm.main_file:
            main_errors, main_warnings, main_metadata = self._validate_main_file(algorithm.main_file, algorithm.language)
            errors.extend(main_errors)
            warnings.extend(main_warnings)
            metadata.update(main_metadata)
        
        # Validate algorithm structure
        if algorithm.files:
            structure_errors, structure_warnings, structure_metadata = self._validate_algorithm_structure(algorithm.files, algorithm.language)
            errors.extend(structure_errors)
            warnings.extend(structure_warnings)
            metadata.update(structure_metadata)
        
        is_valid = len(errors) == 0
        
        result = ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )
        
        if is_valid:
            self.logger.info(f"Algorithm validation passed: {algorithm.name}")
        else:
            self.logger.warning(f"Algorithm validation failed: {algorithm.name} - {len(errors)} errors")
        
        return result
    
    def _validate_basic_properties(self, algorithm: Algorithm) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """Validate basic algorithm properties."""
        errors = []
        warnings = []
        metadata = {}
        
        # Check name
        if not algorithm.name or not algorithm.name.strip():
            errors.append("Algorithm name is required")
        elif len(algorithm.name) > 100:
            errors.append("Algorithm name must be less than 100 characters")
        elif not re.match(r'^[a-zA-Z0-9_\-\s]+$', algorithm.name):
            warnings.append("Algorithm name contains special characters")
        
        # Check description
        if not algorithm.description or not algorithm.description.strip():
            warnings.append("Algorithm description is recommended")
        elif len(algorithm.description) > 1000:
            errors.append("Algorithm description must be less than 1000 characters")
        
        # Check language
        if algorithm.language not in ['C#', 'Py']:
            errors.append("Algorithm language must be 'C#' or 'Py'")
        
        metadata['name_length'] = len(algorithm.name) if algorithm.name else 0
        metadata['description_length'] = len(algorithm.description) if algorithm.description else 0
        metadata['language'] = algorithm.language
        
        return errors, warnings, metadata
    
    def _validate_files(self, files: List[AlgorithmFile]) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """Validate algorithm files."""
        errors = []
        warnings = []
        metadata = {}
        
        total_size = 0
        file_extensions = set()
        
        for file in files:
            # Check file name
            if not file.name or not file.name.strip():
                errors.append("File name is required")
                continue
            
            # Check file extension
            file_ext = Path(file.name).suffix.lower()
            if file_ext not in self.supported_extensions:
                errors.append(f"Unsupported file extension: {file_ext} for file {file.name}")
            else:
                file_extensions.add(file_ext)
            
            # Check file size
            if file.size > self.max_file_size:
                errors.append(f"File {file.name} exceeds maximum size limit ({self.max_file_size} bytes)")
            
            total_size += file.size
            
            # Check file content
            if not file.content:
                errors.append(f"File {file.name} has no content")
            elif len(file.content) != file.size:
                warnings.append(f"File {file.name} size mismatch")
        
        # Check total size
        if total_size > self.max_total_size:
            errors.append(f"Total algorithm size exceeds maximum limit ({self.max_total_size} bytes)")
        
        # Check for main file
        main_files = [f for f in files if f.is_main]
        if len(main_files) == 0:
            errors.append("No main file specified")
        elif len(main_files) > 1:
            errors.append("Multiple main files specified")
        
        metadata['total_files'] = len(files)
        metadata['total_size'] = total_size
        metadata['file_extensions'] = list(file_extensions)
        metadata['main_files'] = len(main_files)
        
        return errors, warnings, metadata
    
    def _validate_main_file(self, main_file: AlgorithmFile, language: str) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """Validate main algorithm file."""
        errors = []
        warnings = []
        metadata = {}
        
        if not main_file.content:
            errors.append("Main file has no content")
            return errors, warnings, metadata
        
        try:
            if language == 'C#':
                parse_errors, parse_warnings, parse_metadata = self._parse_csharp_file(main_file.content)
            else:  # Python
                parse_errors, parse_warnings, parse_metadata = self._parse_python_file(main_file.content)
            
            errors.extend(parse_errors)
            warnings.extend(parse_warnings)
            metadata.update(parse_metadata)
            
        except Exception as e:
            errors.append(f"Failed to parse main file: {str(e)}")
        
        metadata['main_file_name'] = main_file.name
        metadata['main_file_size'] = main_file.size
        
        return errors, warnings, metadata
    
    def _validate_algorithm_structure(self, files: List[AlgorithmFile], language: str) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """Validate overall algorithm structure."""
        errors = []
        warnings = []
        metadata = {}
        
        # Find main file
        main_file = next((f for f in files if f.is_main), None)
        if not main_file:
            return errors, warnings, metadata
        
        content = main_file.content
        
        if language == 'C#':
            structure_errors, structure_warnings, structure_metadata = self._validate_csharp_structure(content)
        else:  # Python
            structure_errors, structure_warnings, structure_metadata = self._validate_python_structure(content)
        
        errors.extend(structure_errors)
        warnings.extend(structure_warnings)
        metadata.update(structure_metadata)
        
        return errors, warnings, metadata
    
    def _parse_python_file(self, content: str) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """Parse Python file and extract structure."""
        errors = []
        warnings = []
        metadata = {}
        
        try:
            tree = ast.parse(content)
            
            # Extract imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        imports.append(f"{module}.{alias.name}")
            
            # Extract classes and functions
            classes = []
            functions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
            
            metadata['imports'] = imports
            metadata['classes'] = classes
            metadata['functions'] = functions
            metadata['ast_valid'] = True
            
        except SyntaxError as e:
            errors.append(f"Python syntax error: {str(e)}")
            metadata['ast_valid'] = False
        
        return errors, warnings, metadata
    
    def _parse_csharp_file(self, content: str) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """Parse C# file and extract structure."""
        errors = []
        warnings = []
        metadata = {}
        
        # Basic C# parsing using regex (simplified)
        try:
            # Extract using statements
            using_pattern = r'using\s+([\w\.]+);'
            imports = re.findall(using_pattern, content)
            
            # Extract class declarations
            class_pattern = r'(?:public\s+)?(?:partial\s+)?class\s+(\w+)'
            classes = re.findall(class_pattern, content)
            
            # Extract method declarations
            method_pattern = r'(?:public\s+|private\s+|protected\s+|internal\s+)?(?:virtual\s+|override\s+|static\s+)?(\w+)\s*\([^)]*\)\s*(?:{|=>)'
            methods = re.findall(method_pattern, content)
            
            metadata['imports'] = imports
            metadata['classes'] = classes
            metadata['methods'] = methods
            metadata['basic_parse'] = True
            
        except Exception as e:
            errors.append(f"C# parsing error: {str(e)}")
            metadata['basic_parse'] = False
        
        return errors, warnings, metadata
    
    def _validate_python_structure(self, content: str) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """Validate Python algorithm structure."""
        errors = []
        warnings = []
        metadata = {}
        
        # Check for required imports
        if 'from AlgorithmImports import *' not in content:
            warnings.append("Missing standard QuantConnect import")
        
        # Check for required methods in classes
        tree = ast.parse(content)
        algorithm_classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it inherits from QCAlgorithm
                has_qc_base = any(
                    (isinstance(base, ast.Name) and base.id == 'QCAlgorithm') or
                    (isinstance(base, ast.Attribute) and base.attr == 'QCAlgorithm')
                    for base in node.bases
                )
                
                if has_qc_base:
                    algorithm_classes.append(node)
                    
                    # Check for required methods
                    class_methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    
                    for required_method in self.required_methods:
                        if required_method not in class_methods:
                            errors.append(f"Missing required method: {required_method}")
        
        if not algorithm_classes:
            errors.append("No QCAlgorithm class found")
        
        metadata['algorithm_classes'] = len(algorithm_classes)
        metadata['required_methods_found'] = self.required_methods
        
        return errors, warnings, metadata
    
    def _validate_csharp_structure(self, content: str) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """Validate C# algorithm structure."""
        errors = []
        warnings = []
        metadata = {}
        
        # Check for required using statements
        required_using = ['QuantConnect.Algorithm', 'QuantConnect.Data']
        for using in required_using:
            if f'using {using};' not in content:
                warnings.append(f"Missing recommended using statement: {using}")
        
        # Check for algorithm class
        if 'class' not in content:
            errors.append("No class declaration found")
        
        # Check for inheritance from QCAlgorithm
        if ': QCAlgorithm' not in content and ' : QCAlgorithm' not in content:
            errors.append("Class must inherit from QCAlgorithm")
        
        # Check for required methods
        for required_method in self.required_methods:
            if f'public override void {required_method}' not in content:
                errors.append(f"Missing required method: {required_method}")
        
        metadata['required_methods_checked'] = self.required_methods
        
        return errors, warnings, metadata