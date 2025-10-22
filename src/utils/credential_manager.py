"""
Secure Credential Management for FractalFVG Trading System

Provides secure storage, retrieval, and rotation of API credentials
with support for multiple storage backends and audit logging.
"""

import os
import json
import base64
import hashlib
import secrets
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import logging

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

import logging

logger = logging.getLogger(__name__)


class CredentialError(Exception):
    """Credential management related errors"""
    pass


class CredentialManager:
    """
    Secure credential manager with multiple storage backends
    and automatic token rotation capabilities.
    """
    
    def __init__(self, storage_backend: str = "env", encryption_key: Optional[str] = None):
        """
        Initialize credential manager
        
        Args:
            storage_backend: Storage method ('env', 'encrypted_file', 'keyring')
            encryption_key: Optional encryption key for file storage
        """
        self.storage_backend = storage_backend
        self.encryption_key = encryption_key
        self._fernet = None
        
        if storage_backend == "encrypted_file" and not CRYPTOGRAPHY_AVAILABLE:
            raise CredentialError("cryptography library required for encrypted file storage")
        
        if storage_backend == "keyring" and not KEYRING_AVAILABLE:
            raise CredentialError("keyring library required for keyring storage")
            
        self._initialize_encryption()
        
    def _initialize_encryption(self):
        """Initialize encryption for file storage"""
        if self.storage_backend == "encrypted_file":
            if self.encryption_key:
                key = self.encryption_key.encode()
            else:
                # Generate key from system-specific info
                key = self._derive_key_from_system()
            
            if CRYPTOGRAPHY_AVAILABLE:
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b'fractal_fvg_salt',  # In production, use random salt per deployment
                    iterations=100000,
                )
                key_bytes = key.encode() if isinstance(key, str) else key
                key = base64.urlsafe_b64encode(kdf.derive(key_bytes))
                self._fernet = Fernet(key)
    
    def _derive_key_from_system(self) -> str:
        """Derive encryption key from system-specific information"""
        system_info = f"{os.environ.get('USER', 'default')}{os.environ.get('HOME', 'default')}"
        return hashlib.sha256(system_info.encode()).hexdigest()
    
    def store_credential(self, service: str, credential_type: str, value: str, 
                        metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Securely store a credential
        
        Args:
            service: Service name (e.g., 'quantconnect')
            credential_type: Type of credential ('api_token', 'user_id', etc.)
            value: The credential value
            metadata: Optional metadata (expiry, rotation info, etc.)
            
        Returns:
            True if stored successfully
        """
        try:
            credential_data = {
                'value': value,
                'created_at': datetime.utcnow().isoformat(),
                'metadata': metadata or {}
            }
            
            if self.storage_backend == "env":
                return self._store_env_credential(service, credential_type, credential_data)
            elif self.storage_backend == "encrypted_file":
                return self._store_file_credential(service, credential_type, credential_data)
            elif self.storage_backend == "keyring":
                return self._store_keyring_credential(service, credential_type, credential_data)
            else:
                raise CredentialError(f"Unsupported storage backend: {self.storage_backend}")
                
        except Exception as e:
            logger.error(f"Failed to store credential {service}.{credential_type}: {e}")
            return False
    
    def retrieve_credential(self, service: str, credential_type: str) -> Optional[str]:
        """
        Retrieve a credential securely
        
        Args:
            service: Service name
            credential_type: Type of credential
            
        Returns:
            Credential value or None if not found
        """
        try:
            if self.storage_backend == "env":
                return self._retrieve_env_credential(service, credential_type)
            elif self.storage_backend == "encrypted_file":
                return self._retrieve_file_credential(service, credential_type)
            elif self.storage_backend == "keyring":
                return self._retrieve_keyring_credential(service, credential_type)
            else:
                raise CredentialError(f"Unsupported storage backend: {self.storage_backend}")
                
        except Exception as e:
            logger.error(f"Failed to retrieve credential {service}.{credential_type}: {e}")
            return None
    
    def _store_env_credential(self, service: str, credential_type: str, data: Dict[str, Any]) -> bool:
        """Store credential in environment variable"""
        env_var = f"{service.upper()}_{credential_type.upper()}"
        os.environ[env_var] = data['value']
        logger.info(f"Stored credential in environment: {env_var}")
        return True
    
    def _retrieve_env_credential(self, service: str, credential_type: str) -> Optional[str]:
        """Retrieve credential from environment variable"""
        env_var = f"{service.upper()}_{credential_type.upper()}"
        return os.environ.get(env_var)
    
    def _store_file_credential(self, service: str, credential_type: str, data: Dict[str, Any]) -> bool:
        """Store encrypted credential to file"""
        if not self._fernet:
            raise CredentialError("Encryption not initialized")
        
        cred_file = Path.home() / '.fractal_fvg' / 'credentials.enc'
        cred_file.parent.mkdir(exist_ok=True)
        
        # Load existing credentials
        credentials = {}
        if cred_file.exists():
            try:
                with open(cred_file, 'rb') as f:
                    encrypted_data = f.read()
                    decrypted_data = self._fernet.decrypt(encrypted_data)
                    credentials = json.loads(decrypted_data.decode())
            except Exception as e:
                logger.warning(f"Could not load existing credentials: {e}")
        
        # Add/update credential
        if service not in credentials:
            credentials[service] = {}
        credentials[service][credential_type] = data
        
        # Encrypt and save
        json_data = json.dumps(credentials).encode()
        encrypted_data = self._fernet.encrypt(json_data)
        
        with open(cred_file, 'wb') as f:
            f.write(encrypted_data)
        
        logger.info(f"Stored encrypted credential: {service}.{credential_type}")
        return True
    
    def _retrieve_file_credential(self, service: str, credential_type: str) -> Optional[str]:
        """Retrieve encrypted credential from file"""
        if not self._fernet:
            raise CredentialError("Encryption not initialized")
        
        cred_file = Path.home() / '.fractal_fvg' / 'credentials.enc'
        if not cred_file.exists():
            return None
        
        try:
            with open(cred_file, 'rb') as f:
                encrypted_data = f.read()
                decrypted_data = self._fernet.decrypt(encrypted_data)
                credentials = json.loads(decrypted_data.decode())
            
            return credentials.get(service, {}).get(credential_type, {}).get('value')
            
        except Exception as e:
            logger.error(f"Failed to retrieve file credential: {e}")
            return None
    
    def _store_keyring_credential(self, service: str, credential_type: str, data: Dict[str, Any]) -> bool:
        """Store credential in system keyring"""
        if not KEYRING_AVAILABLE:
            raise CredentialError("keyring library not available")
        keyring_key = f"{service}_{credential_type}"
        keyring.set_password("fractal_fvg", keyring_key, json.dumps(data))
        logger.info(f"Stored credential in keyring: {keyring_key}")
        return True
    
    def _retrieve_keyring_credential(self, service: str, credential_type: str) -> Optional[str]:
        """Retrieve credential from system keyring"""
        if not KEYRING_AVAILABLE:
            raise CredentialError("keyring library not available")
        keyring_key = f"{service}_{credential_type}"
        try:
            data = keyring.get_password("fractal_fvg", keyring_key)
            if data:
                credential_data = json.loads(data)
                return credential_data.get('value')
        except Exception as e:
            logger.error(f"Failed to retrieve keyring credential: {e}")
        return None
    
    def rotate_credential(self, service: str, credential_type: str, new_value: str) -> bool:
        """
        Rotate a credential with audit trail
        
        Args:
            service: Service name
            credential_type: Type of credential
            new_value: New credential value
            
        Returns:
            True if rotated successfully
        """
        try:
            # Get old value for audit
            old_value = self.retrieve_credential(service, credential_type)
            
            # Store new value with rotation metadata
            metadata = {
                'rotated_at': datetime.utcnow().isoformat(),
                'previous_value_hash': hashlib.sha256((old_value or '').encode()).hexdigest() if old_value else None
            }
            
            success = self.store_credential(service, credential_type, new_value, metadata)
            
            if success:
                logger.info(f"Successfully rotated credential: {service}.{credential_type}")
                self._audit_log("credential_rotated", service, credential_type)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to rotate credential {service}.{credential_type}: {e}")
            return False
    
    def _audit_log(self, action: str, service: str, credential_type: str):
        """Log credential actions for audit trail"""
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'service': service,
            'credential_type': credential_type,
            'user': os.environ.get('USER', 'unknown')
        }
        
        audit_file = Path.home() / '.fractal_fvg' / 'audit.log'
        audit_file.parent.mkdir(exist_ok=True)
        
        with open(audit_file, 'a') as f:
            f.write(json.dumps(audit_entry) + '\n')
    
    def validate_credentials(self, service: str, required_credentials: list) -> bool:
        """
        Validate that all required credentials are present
        
        Args:
            service: Service name
            required_credentials: List of required credential types
            
        Returns:
            True if all credentials are present
        """
        missing = []
        for cred_type in required_credentials:
            if not self.retrieve_credential(service, cred_type):
                missing.append(cred_type)
        
        if missing:
            logger.error(f"Missing credentials for {service}: {missing}")
            return False
        
        return True
    
    def get_credential_metadata(self, service: str, credential_type: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a credential"""
        # This would need to be implemented based on storage backend
        # For now, return None as env storage doesn't support metadata
        return None


class QuantConnectCredentialManager(CredentialManager):
    """Specialized credential manager for QuantConnect API"""
    
    def __init__(self, storage_backend: str = "env"):
        super().__init__(storage_backend)
        self.service = "quantconnect"
    
    def store_quantconnect_credentials(self, user_id: str, api_token: str, 
                                     organization_id: Optional[str] = None) -> bool:
        """Store QuantConnect credentials"""
        success = True
        success &= self.store_credential(self.service, "user_id", user_id)
        success &= self.store_credential(self.service, "api_token", api_token)
        
        if organization_id:
            success &= self.store_credential(self.service, "organization_id", organization_id)
        
        return success
    
    def get_quantconnect_credentials(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Get QuantConnect credentials"""
        user_id = self.retrieve_credential(self.service, "user_id")
        api_token = self.retrieve_credential(self.service, "api_token")
        organization_id = self.retrieve_credential(self.service, "organization_id")
        
        return user_id, api_token, organization_id
    
    def validate_quantconnect_credentials(self) -> bool:
        """Validate QuantConnect credentials are present"""
        return self.validate_credentials(self.service, ["user_id", "api_token"])


# Global credential manager instance
_credential_manager = None


def get_credential_manager(storage_backend: str = "env") -> CredentialManager:
    """Get global credential manager instance"""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager(storage_backend)
    return _credential_manager


def get_quantconnect_credential_manager(storage_backend: str = "env") -> QuantConnectCredentialManager:
    """Get QuantConnect credential manager instance"""
    return QuantConnectCredentialManager(storage_backend)