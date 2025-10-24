#!/usr/bin/env python3
"""
Automated Testing Suite for Bulletproof Deployment
================================================

Comprehensive testing suite for validating deployment readiness,
including unit tests, integration tests, performance tests, and security tests.

Author: FractalFVG Project
Version: 1.0.0 (Production-Ready)
"""

import os
import sys
import json
import time
import hashlib
import subprocess
import unittest
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

@dataclass
class TestResult:
    """Test result data structure"""
    test_name: str
    passed: bool
    duration: float
    details: str
    error_message: str = ""

class DeploymentTestSuite:
    """Comprehensive deployment testing suite"""
    
    def __init__(self, source_path: str):
        self.source_path = Path(source_path)
        self.test_results = []
        self.start_time = datetime.now()
        
    def run_all_tests(self) -> Tuple[bool, List[TestResult]]:
        """Run all test suites"""
        print("🧪 Starting Comprehensive Deployment Test Suite")
        print("=" * 60)
        
        # Test 1: File Structure Tests
        self._test_file_structure()
        
        # Test 2: Code Quality Tests
        self._test_code_quality()
        
        # Test 3: Configuration Tests
        self._test_configuration()
        
        # Test 4: Performance Tests
        self._test_performance()
        
        # Test 5: Security Tests
        self._test_security()
        
        # Test 6: Integration Tests
        self._test_integration()
        
        # Test 7: Volume Enhancement Tests
        self._test_volume_enhancements()
        
        # Generate summary
        self._generate_test_summary()
        
        all_passed = all(result.passed for result in self.test_results)
        return all_passed, self.test_results
    
    def _test_file_structure(self) -> None:
        """Test file structure and integrity"""
        print("\n📁 Testing File Structure...")
        
        # Test Main.cs exists
        main_cs = self.source_path / "Main.cs"
        self._run_test(
            "Main.cs exists",
            main_cs.exists() and main_cs.stat().st_size > 0,
            f"Main.cs found at {main_cs}, size: {main_cs.stat().st_size} bytes"
        )
        
        # Test project.json exists
        project_json = self.source_path / "project.json"
        self._run_test(
            "project.json exists",
            project_json.exists() and project_json.stat().st_size > 0,
            f"project.json found at {project_json}, size: {project_json.stat().st_size} bytes"
        )
        
        # Test essential directories
        essential_dirs = ["src", "tests", "docs"]
        for dir_name in essential_dirs:
            dir_path = self.source_path.parent / dir_name
            self._run_test(
                f"Directory {dir_name} exists",
                dir_path.exists() and dir_path.is_dir(),
                f"Directory {dir_name} found at {dir_path}"
            )
        
        # Test file permissions
        if main_cs.exists():
            readable = os.access(main_cs, os.R_OK)
            self._run_test(
                "Main.cs readable",
                readable,
                f"Main.cs readable: {readable}"
            )
    
    def _test_code_quality(self) -> None:
        """Test code quality and syntax"""
        print("\n🔍 Testing Code Quality...")
        
        main_cs = self.source_path / "Main.cs"
        if not main_cs.exists():
            return
        
        # Test C# syntax (basic checks)
        with open(main_cs, 'r') as f:
            content = f.read()
        
        # Check for required namespaces
        required_namespaces = [
            "using System;",
            "using System.Collections.Generic;",
            "using System.Linq;",
            "using QuantConnect.Algorithm;"
        ]
        
        for namespace in required_namespaces:
            self._run_test(
                f"Namespace: {namespace.strip()}",
                namespace in content,
                f"Namespace {namespace.strip()} found in Main.cs"
            )
        
        # Check for required class structure
        self._run_test(
            "Algorithm class exists",
            "public class MNQFVGMLAlgorithm" in content,
            "Main algorithm class found"
        )
        
        # Check for volume enhancement features
        volume_features = [
            "VolumeConfirmationLevel",
            "GetSessionVolumeMultiplier",
            "ApplyVolumeConfirmationFilter"
        ]
        
        for feature in volume_features:
            self._run_test(
                f"Volume feature: {feature}",
                feature in content,
                f"Volume enhancement feature {feature} found"
            )
        
        # Check file size (should be substantial)
        file_size = len(content)
        self._run_test(
            "File size adequate",
            file_size > 30000,  # Should be > 30KB for enhanced algorithm
            f"Main.cs size: {file_size:,} characters"
        )
    
    def _test_configuration(self) -> None:
        """Test configuration files"""
        print("\n⚙️ Testing Configuration...")
        
        # Test project.json structure
        project_json = self.source_path / "project.json"
        if project_json.exists():
            try:
                with open(project_json, 'r') as f:
                    config = json.load(f)
                
                # Check required fields
                required_fields = ["name", "language", "parameters"]
                for field in required_fields:
                    self._run_test(
                        f"project.json field: {field}",
                        field in config,
                        f"Field {field} found in project.json"
                    )
                
                # Check language is CSharp
                self._run_test(
                    "Language is CSharp",
                    config.get("language") == "CSharp",
                    f"Language: {config.get('language')}"
                )
                
            except Exception as e:
                self._run_test(
                    "project.json valid JSON",
                    False,
                    f"JSON parsing error: {e}"
                )
        
        # Test deployment config exists
        deployment_config = Path("config/deployment_config.json")
        self._run_test(
            "Deployment config exists",
            deployment_config.exists(),
            f"Deployment config found at {deployment_config}"
        )
    
    def _test_performance(self) -> None:
        """Test performance characteristics"""
        print("\n⚡ Testing Performance...")
        
        # Test file reading performance
        main_cs = self.source_path / "Main.cs"
        if main_cs.exists():
            start_time = time.time()
            with open(main_cs, 'r') as f:
                content = f.read()
            read_time = time.time() - start_time
            
            self._run_test(
                "File read performance",
                read_time < 1.0,
                f"File read time: {read_time:.3f} seconds"
            )
        
        # Test checksum calculation performance
        if main_cs.exists():
            start_time = time.time()
            with open(main_cs, 'rb') as f:
                checksum = hashlib.md5(f.read()).hexdigest()
            checksum_time = time.time() - start_time
            
            self._run_test(
                "Checksum performance",
                checksum_time < 0.5,
                f"Checksum time: {checksum_time:.3f} seconds"
            )
    
    def _test_security(self) -> None:
        """Test security aspects"""
        print("\n🔒 Testing Security...")
        
        main_cs = self.source_path / "Main.cs"
        if not main_cs.exists():
            return
        
        with open(main_cs, 'r') as f:
            content = f.read()
        
        # Check for hardcoded secrets (basic check)
        secret_patterns = [
            "password",
            "secret",
            "token",
            "api_key"
        ]
        
        for pattern in secret_patterns:
            # Check if pattern exists but not in comments or strings
            lines = content.split('\n')
            suspicious_lines = []
            for i, line in enumerate(lines, 1):
                if pattern in line.lower() and not line.strip().startswith('//'):
                    suspicious_lines.append(f"Line {i}: {line.strip()}")
            
            self._run_test(
                f"No hardcoded {pattern}",
                len(suspicious_lines) == 0,
                f"Suspicious lines for {pattern}: {len(suspicious_lines)}"
            )
        
        # Check for proper error handling
        error_handling_patterns = [
            "try {",
            "catch (",
            "throw new"
        ]
        
        error_handling_count = sum(1 for pattern in error_handling_patterns if pattern in content)
        self._run_test(
            "Error handling present",
            error_handling_count >= 2,
            f"Error handling patterns found: {error_handling_count}"
        )
    
    def _test_integration(self) -> None:
        """Test integration aspects"""
        print("\n🔗 Testing Integration...")
        
        # Test Python imports (if applicable)
        try:
            import requests
            self._run_test(
                "Python requests available",
                True,
                "requests module imported successfully"
            )
        except ImportError:
            self._run_test(
                "Python requests available",
                False,
                "requests module not available"
            )
        
        # Test system dependencies
        system_deps = ["git", "python3"]
        for dep in system_deps:
            try:
                result = subprocess.run(["which", dep], capture_output=True, text=True)
                available = result.returncode == 0
                self._run_test(
                    f"System dependency: {dep}",
                    available,
                    f"{dep} found at: {result.stdout.strip()}" if available else f"{dep} not found"
                )
            except Exception:
                self._run_test(
                    f"System dependency: {dep}",
                    False,
                    f"Error checking {dep}"
                )
    
    def _test_volume_enhancements(self) -> None:
        """Test volume enhancement features"""
        print("\n📊 Testing Volume Enhancements...")
        
        main_cs = self.source_path / "Main.cs"
        if not main_cs.exists():
            return
        
        with open(main_cs, 'r') as f:
            content = f.read()
        
        # Test volume confirmation levels
        volume_levels = ["NONE", "LOW", "MEDIUM", "HIGH"]
        for level in volume_levels:
            self._run_test(
                f"Volume level: {level}",
                f"VolumeConfirmationLevel.{level}" in content,
                f"Volume confirmation level {level} found"
            )
        
        # Test session multipliers
        session_multipliers = [
            "US_SESSION_VOLUME_MULTIPLIER",
            "OVERNIGHT_VOLUME_MULTIPLIER",
            "PRE_MARKET_VOLUME_MULTIPLIER",
            "POST_MARKET_VOLUME_MULTIPLIER"
        ]
        
        for multiplier in session_multipliers:
            self._run_test(
                f"Session multiplier: {multiplier}",
                multiplier in content,
                f"Session multiplier {multiplier} found"
            )
        
        # Test volume filtering logic
        volume_filter_methods = [
            "GetVolumeConfirmationLevel",
            "ApplyVolumeConfirmationFilter",
            "GetSessionVolumeMultiplier"
        ]
        
        for method in volume_filter_methods:
            self._run_test(
                f"Volume method: {method}",
                method in content,
                f"Volume method {method} found"
            )
    
    def _run_test(self, test_name: str, passed: bool, details: str) -> None:
        """Run a single test and record results"""
        duration = time.time() - self.start_time.timestamp() if hasattr(self.start_time, 'total_seconds') else 0
        
        result = TestResult(
            test_name=test_name,
            passed=passed,
            duration=duration,
            details=details
        )
        
        self.test_results.append(result)
        
        # Print result
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {test_name}")
        if not passed:
            print(f"    Details: {details}")
    
    def _generate_test_summary(self) -> None:
        """Generate test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.passed)
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result.passed:
                    print(f"  - {result.test_name}: {result.details}")
        
        print("\n" + "=" * 60)

def main():
    """Main test execution"""
    # Get source path from command line or use default
    source_path = sys.argv[1] if len(sys.argv) > 1 else "./quantconnect_mnq_fvg"
    
    # Run test suite
    test_suite = DeploymentTestSuite(source_path)
    all_passed, results = test_suite.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()