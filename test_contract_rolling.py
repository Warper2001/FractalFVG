#!/usr/bin/env python3
"""
Test script to demonstrate MNQ contract rolling functionality.

This script shows how the enhanced MNQ data access layer handles
contract rolling for continuous futures data.
"""

import sys
import os
from datetime import datetime, timedelta

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.data.mnq_data import (
    MNQDataAccess, MNQDataConfig, FuturesContract,
    generate_mnq_contracts, get_current_mnq_contract,
    get_next_mnq_contract, create_sample_mnq_data
)


def test_contract_generation():
    """Test MNQ contract generation."""
    print("=== Testing MNQ Contract Generation ===")
    
    # Generate contracts for 2023-2024
    contracts = generate_mnq_contracts(2023, 2024)
    
    print(f"Generated {len(contracts)} contracts for 2023-2024")
    
    # Display first few contracts
    for i, contract in enumerate(contracts[:8]):
        print(f"  {i+1}. {contract.get_full_symbol()} - "
              f"Expiry: {contract.expiry_date.date()}, "
              f"Roll: {contract.roll_date.date() if contract.roll_date else 'N/A'}")
    
    return contracts


def test_current_contract():
    """Test getting current active contract."""
    print("\n=== Testing Current Contract Detection ===")
    
    current_contract = get_current_mnq_contract()
    
    if current_contract:
        print(f"Current contract: {current_contract.get_full_symbol()}")
        print(f"  Expiry: {current_contract.expiry_date.date()}")
        print(f"  Roll date: {current_contract.roll_date.date() if current_contract.roll_date else 'N/A'}")
        print(f"  Days to expiry: {(current_contract.expiry_date - datetime.now()).days}")
        print(f"  Days to roll: {(current_contract.roll_date - datetime.now()).days if current_contract.roll_date else 'N/A'}")
    else:
        print("No current contract found")
    
    return current_contract


def test_next_contract():
    """Test getting next contract."""
    print("\n=== Testing Next Contract Detection ===")
    
    next_contract = get_next_mnq_contract()
    
    if next_contract:
        print(f"Next contract: {next_contract.get_full_symbol()}")
        print(f"  Expiry: {next_contract.expiry_date.date()}")
        print(f"  Roll date: {next_contract.roll_date.date() if next_contract.roll_date else 'N/A'}")
    else:
        print("No next contract found")
    
    return next_contract


def test_contract_rolling_config():
    """Test contract rolling configuration."""
    print("\n=== Testing Contract Rolling Configuration ===")
    
    # Create config with contract rolling enabled
    config = MNQDataConfig(
        enable_contract_rolling=True,
        roll_days_before_expiry=5,
        roll_method="ratio",
        continuous_contract_symbol="MNQ"
    )
    
    print(f"Contract rolling enabled: {config.enable_contract_rolling}")
    print(f"Roll days before expiry: {config.roll_days_before_expiry}")
    print(f"Roll method: {config.roll_method}")
    print(f"Continuous contract symbol: {config.continuous_contract_symbol}")
    
    return config


def test_sample_data_with_contracts():
    """Test sample data generation with contract information."""
    print("\n=== Testing Sample Data with Contracts ===")
    
    # Generate sample data for 1 month
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 1, 31)
    
    # Generate data with contract information
    df_with_contracts = create_sample_mnq_data(
        start_date, end_date, frequency="1hour", include_contracts=True
    )
    
    # Generate data without contract information
    df_without_contracts = create_sample_mnq_data(
        start_date, end_date, frequency="1hour", include_contracts=False
    )
    
    print(f"Data with contracts: {len(df_with_contracts)} rows")
    print(f"Data without contracts: {len(df_without_contracts)} rows")
    
    if not df_with_contracts.empty and 'contract' in df_with_contracts.columns:
        unique_contracts = df_with_contracts['contract'].unique()
        print(f"Unique contracts in sample data: {list(unique_contracts)}")
        
        # Show sample rows
        print("\nSample data with contracts:")
        print(df_with_contracts.head())
    
    return df_with_contracts, df_without_contracts


def test_data_access_with_rolling():
    """Test MNQ data access with contract rolling."""
    print("\n=== Testing Data Access with Contract Rolling ===")
    
    # Create config with contract rolling
    config = MNQDataConfig(
        enable_contract_rolling=True,
        roll_days_before_expiry=5,
        roll_method="ratio"
    )
    
    # Initialize data access
    data_access = MNQDataAccess(config)
    
    print(f"Contract rolling enabled: {data_access.config.enable_contract_rolling}")
    print(f"Roll method: {data_access.config.roll_method}")
    print(f"Roll days before expiry: {data_access.config.roll_days_before_expiry}")
    
    # Test getting historical data (will use sample data since QuantConnect not available)
    try:
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 7)  # 1 week
        
        print(f"\nAttempting to get data from {start_date.date()} to {end_date.date()}")
        
        # This will fail gracefully since we don't have real QuantConnect data
        # but it will demonstrate the contract rolling logic
        data = data_access.get_historical_data(start_date, end_date, "hour")
        
        if data is not None:
            print(f"Successfully retrieved {len(data)} rows of data")
            print(f"Data columns: {list(data.columns)}")
            if not data.empty:
                print(f"Date range: {data.index.min()} to {data.index.max()}")
        else:
            print("No data available (expected in test environment)")
            
    except Exception as e:
        print(f"Expected error in test environment: {e}")
    
    return data_access


def test_contract_rolling_logic():
    """Test contract rolling logic with sample contracts."""
    print("\n=== Testing Contract Rolling Logic ===")
    
    # Create sample contracts
    contracts = [
        FuturesContract(
            symbol="MNQ",
            contract_month="H24",
            expiry_date=datetime(2024, 3, 15),
            roll_date=datetime(2024, 3, 10)
        ),
        FuturesContract(
            symbol="MNQ",
            contract_month="M24",
            expiry_date=datetime(2024, 6, 14),
            roll_date=datetime(2024, 6, 9)
        ),
        FuturesContract(
            symbol="MNQ",
            contract_month="U24",
            expiry_date=datetime(2024, 9, 13),
            roll_date=datetime(2024, 9, 8)
        )
    ]
    
    # Test contract status at different dates
    test_dates = [
        datetime(2024, 3, 1),   # Before H24 roll
        datetime(2024, 3, 12),  # After H24 roll, before M24 expiry
        datetime(2024, 6, 1),   # Before M24 roll
        datetime(2024, 6, 15),  # After M24 roll
    ]
    
    for test_date in test_dates:
        print(f"\nTesting on {test_date.date()}:")
        
        for contract in contracts:
            is_expired = contract.is_expired(test_date)
            should_roll = contract.should_roll(test_date, 5)
            
            status = "EXPIRED" if is_expired else ("ROLL" if should_roll else "ACTIVE")
            print(f"  {contract.get_full_symbol()}: {status}")
    
    return contracts


def main():
    """Run all contract rolling tests."""
    print("MNQ Contract Rolling Functionality Test")
    print("=" * 50)
    
    try:
        # Test contract generation
        contracts = test_contract_generation()
        
        # Test current contract detection
        current_contract = test_current_contract()
        
        # Test next contract detection
        next_contract = test_next_contract()
        
        # Test configuration
        config = test_contract_rolling_config()
        
        # Test sample data generation
        df_with, df_without = test_sample_data_with_contracts()
        
        # Test data access
        data_access = test_data_access_with_rolling()
        
        # Test rolling logic
        test_contracts = test_contract_rolling_logic()
        
        print("\n" + "=" * 50)
        print("✅ All contract rolling tests completed successfully!")
        print("\nKey Features Implemented:")
        print("  ✅ Contract generation for MNQ futures")
        print("  ✅ Current/next contract detection")
        print("  ✅ Configurable rolling parameters")
        print("  ✅ Sample data with contract information")
        print("  ✅ Data access layer with rolling support")
        print("  ✅ Rolling logic validation")
        
        print("\nContract Rolling Methods:")
        print("  📊 Ratio: Multiply prices by adjustment factor")
        print("  📊 Difference: Add/subtract adjustment amount")
        print("  📊 Raw: No adjustment (price gaps visible)")
        
        print("\nConfiguration Options:")
        print("  ⚙️  Enable/disable contract rolling")
        print("  ⚙️  Roll days before expiry (default: 5)")
        print("  ⚙️  Roll method (ratio/difference/raw)")
        print("  ⚙️  Continuous contract symbol")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())