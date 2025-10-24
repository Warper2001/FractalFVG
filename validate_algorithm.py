#!/usr/bin/env python3
"""
Local validation of MNQ FVG algorithm to identify issues before QuantConnect deployment
"""

import re
import os
from pathlib import Path

def validate_algorithm_file(file_path):
    """Validate algorithm file for common issues"""
    
    print(f"🔍 Validating {file_path}")
    print("=" * 50)
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    issues = []
    warnings = []
    
    # Check for common QuantConnect issues
    checks = [
        # Futures symbol should be string, not enum
        (r'Futures\.Indices\.NASDAQ100Micro', '❌ Use "MNQ" instead of Futures.Indices.NASDAQ100Micro'),
        
        # WarmUpIndicator should be SetWarmUp
        (r'WarmUpIndicator\(', '❌ Use SetWarmUp() instead of WarmUpIndicator()'),
        
        # Check for proper Time property usage
        (r'var currentHoldTime = Time - _tradeEntryTime', '⚠️  Check Time property initialization'),
        
        # Check for division by zero protection
        (r'currentVolume / avgVolume', '⚠️  Ensure avgVolume > 0'),
        
        # Check for proper decimal casting
        (r'currentVolume / avgVolume', '⚠️  Cast to decimal if needed'),
        
        # Check for missing null checks
        (r'_tradeEntryTime\.Value', '⚠️  Ensure _tradeEntryTime.HasValue'),
        
        # Check for proper symbol usage
        (r'Symbol = "MNQ"', '✅ Correct symbol usage'),
        
        # Check for proper AddFuture usage
        (r'AddFuture\("MNQ"', '✅ Correct AddFuture usage'),
        
        # Check for SetWarmUp usage
        (r'SetWarmUp\(', '✅ Correct SetWarmUp usage'),
    ]
    
    for pattern, message in checks:
        if re.search(pattern, content):
            if message.startswith('✅'):
                print(message)
            elif message.startswith('⚠️'):
                warnings.append(message)
                print(message)
            else:
                issues.append(message)
                print(message)
    
    # Check for required methods
    required_methods = ['Initialize()', 'OnData(Slice data)', 'OnEndOfAlgorithm()']
    for method in required_methods:
        if method in content:
            print(f"✅ Found {method}")
        else:
            issues.append(f"❌ Missing {method}")
    
    # Check for using statements
    required_usings = [
        'using QuantConnect.Algorithm;',
        'using QuantConnect.Data.Market;',
        'using QuantConnect.Securities.Future;'
    ]
    
    for using_stmt in required_usings:
        if using_stmt in content:
            print(f"✅ Found {using_stmt}")
        else:
            warnings.append(f"⚠️  Missing {using_stmt}")
    
    # Check for potential runtime issues
    runtime_checks = [
        (r'Time - _tradeEntryTime\.Value', 'Check _tradeEntryTime.HasValue before accessing Value'),
        (r'Portfolio\[.*\]\.AveragePrice', 'Check if portfolio is invested before accessing AveragePrice'),
        (r'bars\.Skip\(.*\)\.Take\(.*\)\.Average\(', 'Ensure enough bars exist before calculating average'),
    ]
    
    for pattern, message in runtime_checks:
        if re.search(pattern, content):
            warnings.append(f"⚠️  {message}")
    
    print("\n📊 VALIDATION SUMMARY:")
    print(f"• Issues: {len(issues)}")
    print(f"• Warnings: {len(warnings)}")
    
    if issues:
        print("\n❌ CRITICAL ISSUES:")
        for issue in issues:
            print(f"  - {issue}")
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")
    
    if not issues and not warnings:
        print("\n✅ No issues found!")
    
    return len(issues) == 0

def main():
    """Main validation function"""
    
    algorithm_file = "/root/FractalFVG/quantconnect_mnq_fvg/Main.cs"
    
    print("🔍 MNQ FVG Algorithm Validation")
    print("=" * 60)
    
    is_valid = validate_algorithm_file(algorithm_file)
    
    if is_valid:
        print("\n✅ Algorithm validation passed!")
        print("Ready for QuantConnect deployment.")
    else:
        print("\n❌ Algorithm validation failed!")
        print("Please fix the issues before deploying.")
    
    return is_valid

if __name__ == "__main__":
    main()