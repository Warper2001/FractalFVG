# Secure Credential Management for FractalFVG

This document describes the secure credential management system implemented for the FractalFVG trading automation project.

## Overview

The FractalFVG project previously contained hardcoded API credentials, which poses significant security risks. We've implemented a comprehensive credential management system that provides:

- **Secure Storage**: Multiple storage backends (environment variables, encrypted files, system keyring)
- **Credential Rotation**: Built-in support for rotating credentials with audit trails
- **Access Control**: Centralized credential access with validation
- **Audit Logging**: Complete audit trail of credential operations

## Security Features

### 1. Multiple Storage Backends

#### Environment Variables (Recommended for Development)
- Credentials stored in environment variables
- Easy to use in development environments
- Supports `.env` file generation

#### Encrypted File Storage (Production)
- Credentials encrypted using AES-256 encryption
- Stored in `~/.fractal_fvg/credentials.enc`
- System-specific encryption key derivation

#### System Keyring (Most Secure)
- Uses operating system's secure credential storage
- Requires `keyring` library
- Best for production environments

### 2. Credential Rotation
- Automatic credential rotation with metadata tracking
- Audit trail of all rotation events
- Previous credential hash storage for verification

### 3. Audit Logging
- All credential operations logged to `~/.fractal_fvg/audit.log`
- Timestamp, user, action, and service tracking
- JSON format for easy parsing and analysis

## Installation

### Required Dependencies

```bash
# For encrypted file storage
pip install cryptography

# For system keyring storage (optional)
pip install keyring

# For environment variable loading (optional)
pip install python-dotenv
```

## Quick Start

### 1. Set Up Credentials

Run the interactive setup script:

```bash
python setup_secure_credentials.py
```

This will:
- Scan for existing hardcoded credentials
- Prompt for QuantConnect API credentials
- Test credential validity
- Store credentials securely
- Generate `.env` file if using environment variables

### 2. Migrate Existing Code

Run the migration script to replace hardcoded credentials:

```bash
python migrate_credentials.py
```

This will:
- Find all files with hardcoded credentials
- Create backup files
- Replace hardcoded values with credential manager calls
- Preserve original functionality

### 3. Use in Your Code

```python
from src.utils.credential_manager import get_quantconnect_credential_manager

# Get credential manager
cred_mgr = get_quantconnect_credential_manager()

# Retrieve credentials
user_id, api_token, organization_id = cred_mgr.get_quantconnect_credentials()

# Use in API calls
import requests
import base64

headers = {
    'Authorization': f'Basic {base64.b64encode(f"{user_id}:{api_token}".encode()).decode()}'
}
response = requests.get("https://www.quantconnect.com/api/v2/projects", headers=headers)
```

## API Reference

### CredentialManager Class

#### Methods

- `store_credential(service, credential_type, value, metadata=None)`: Store a credential
- `retrieve_credential(service, credential_type)`: Retrieve a credential
- `rotate_credential(service, credential_type, new_value)`: Rotate a credential
- `validate_credentials(service, required_credentials)`: Validate required credentials

### QuantConnectCredentialManager Class

Specialized manager for QuantConnect API credentials.

#### Methods

- `store_quantconnect_credentials(user_id, api_token, organization_id=None)`: Store QC credentials
- `get_quantconnect_credentials()`: Get QC credentials (returns tuple)
- `validate_quantconnect_credentials()`: Validate QC credentials are present

## Configuration

### Environment Variables

When using environment variable storage, the following variables are used:

- `QUANTCONNECT_USER_ID`: Your QuantConnect user ID
- `QUANTCONNECT_API_TOKEN`: Your QuantConnect API token
- `QUANTCONNECT_ORGANIZATION_ID`: (Optional) Organization ID

### Encrypted File Configuration

Encrypted files are stored at:
- Credential file: `~/.fractal_fvg/credentials.enc`
- Audit log: `~/.fractal_fvg/audit.log`

### Keyring Configuration

When using keyring storage:
- Service name: `fractal_fvg`
- Credential keys: `{service}_{credential_type}`

## Security Best Practices

### 1. Development Environment
- Use environment variable storage
- Add `.env` to `.gitignore`
- Never commit credentials to version control

### 2. Production Environment
- Use encrypted file or keyring storage
- Implement regular credential rotation
- Monitor audit logs for suspicious activity
- Use separate credentials for different environments

### 3. CI/CD Pipeline
- Use environment variables or secret management
- Never pass credentials as command line arguments
- Rotate credentials regularly

### 4. Access Control
- Limit access to credential files
- Use file permissions appropriately
- Implement principle of least privilege

## Migration Guide

### From Hardcoded Credentials

1. **Backup**: Always backup your code before migration
2. **Run Setup**: Use `setup_secure_credentials.py` to configure secure storage
3. **Migrate Code**: Use `migrate_credentials.py` to update your files
4. **Test**: Verify all scripts work with new credential system
5. **Clean Up**: Remove backup files once verified

### Manual Migration

If you prefer manual migration:

```python
# Before (insecure)
user_id = "421529"
api_token = "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"

# After (secure)
from src.utils.credential_manager import get_quantconnect_credential_manager

cred_mgr = get_quantconnect_credential_manager()
user_id, api_token, organization_id = cred_mgr.get_quantconnect_credentials()
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running from the FractalFVG root directory
2. **Permission Denied**: Check file permissions for `~/.fractal_fvg/`
3. **Invalid Credentials**: Verify credentials on QuantConnect website
4. **Missing Dependencies**: Install required packages with pip

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Recovery

If you lose access to credentials:
1. Check backup files created during migration
2. Recover from QuantConnect website
3. Check audit logs for recent access

## File Structure

```
FractalFVG/
├── src/utils/
│   └── credential_manager.py          # Core credential management
├── setup_secure_credentials.py        # Interactive setup script
├── migrate_credentials.py             # Migration script
├── CREDENTIAL_MANAGEMENT.md           # This documentation
└── .env                              # Environment variables (if used)
```

## Security Considerations

### Threat Model

This system protects against:
- Accidental credential exposure in code
- Unauthorized access to credential files
- Credential leakage through logs or debugging
- Lack of audit trail for credential access

### Limitations

- Does not protect against compromised systems
- Requires proper file system permissions
- Environment variables can be accessed by processes with same user
- Encrypted files rely on system security

### Recommendations

1. **Regular Rotation**: Rotate credentials every 90 days
2. **Monitoring**: Monitor audit logs regularly
3. **Access Control**: Limit who can run credential setup
4. **Backup**: Securely backup credential files
5. **Testing**: Test credential recovery procedures

## Support

For issues or questions:
1. Check this documentation
2. Review audit logs for error messages
3. Test with debug logging enabled
4. Verify credential format and validity

## License

This credential management system is part of the FractalFVG project and follows the same license terms.