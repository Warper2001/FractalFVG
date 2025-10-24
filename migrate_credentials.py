#!/usr/bin/env python3
"""
Migrate hardcoded credentials to secure credential management

This script finds and replaces hardcoded QuantConnect credentials
with calls to the secure credential manager.
"""

import os
import sys
import re
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def find_files_with_hardcoded_credentials():
    """Find Python files with hardcoded QuantConnect credentials"""
    patterns = [
        r'user_id\s*=\s*["\']421529["\']',
        r'api_token\s*=\s*["\'][a-f0-9]{64}["\']',
        r'"user_id":\s*"421529"',
        r'"api_token":\s*"[a-f0-9]{64}"'
    ]
    
    files_with_credentials = []
    
    for root, dirs, files in os.walk('.'):
        # Skip hidden directories and common non-source directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', '.git']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for pattern in patterns:
                            if re.search(pattern, content):
                                files_with_credentials.append(file_path)
                                break
                except Exception:
                    continue
    
    return files_with_credentials


def create_secure_version(file_path: str) -> bool:
    """Create a secure version of a file with hardcoded credentials"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create backup
        backup_path = file_path + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Add import for credential manager at the top
        import_line = "from src.utils.credential_manager import get_quantconnect_credential_manager\n"
        
        # Find the best place to insert the import (after other imports)
        lines = content.split('\n')
        import_inserted = False
        
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                continue
            elif line.strip() == '' or line.startswith('#'):
                # Insert after the last import
                if i > 0 and (lines[i-1].startswith('import ') or lines[i-1].startswith('from ')):
                    lines.insert(i, import_line)
                    import_inserted = True
                    break
            else:
                # Insert before first non-import, non-comment line
                lines.insert(i, import_line)
                import_inserted = True
                break
        
        if not import_inserted:
            lines.insert(0, import_line)
        
        # Replace hardcoded credentials
        new_content = '\n'.join(lines)
        
        # Replace user_id assignments
        new_content = re.sub(
            r'user_id\s*=\s*["\']421529["\']',
            'cred_mgr = get_quantconnect_credential_manager()\n    user_id, api_token, organization_id = cred_mgr.get_quantconnect_credentials()',
            new_content
        )
        
        # Replace api_token assignments (but only if not already replaced above)
        new_content = re.sub(
            r'(?<!cred_mgr\.get_quantconnect_credentials\(\)\n    )api_token\s*=\s*["\'][a-f0-9]{64}["\']',
            'api_token  # Already retrieved from credential manager above',
            new_content
        )
        
        # Replace JSON dictionary entries
        new_content = re.sub(
            r'"user_id":\s*"421529"',
            '"user_id": user_id',
            new_content
        )
        
        new_content = re.sub(
            r'"api_token":\s*"[a-f0-9]{64}"',
            '"api_token": api_token',
            new_content
        )
        
        # Write the new content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ Migrated {file_path} (backup: {backup_path})")
        return True
        
    except Exception as e:
        print(f"❌ Failed to migrate {file_path}: {e}")
        return False


def main():
    """Main migration function"""
    print("🔄 FractalFVG Credential Migration")
    print("=" * 40)
    
    # Find files with hardcoded credentials
    files = find_files_with_hardcoded_credentials()
    
    if not files:
        print("✅ No files with hardcoded credentials found!")
        return 0
    
    print(f"\n📁 Found {len(files)} files with hardcoded credentials:")
    for file_path in files:
        print(f"   - {file_path}")
    
    # Ask for confirmation
    response = input(f"\n🔄 Migrate {len(files)} files to secure credential management? (y/n): ").lower().strip()
    
    if response != 'y':
        print("❌ Migration cancelled")
        return 0
    
    # Migrate files
    success_count = 0
    for file_path in files:
        if create_secure_version(file_path):
            success_count += 1
    
    print(f"\n✅ Successfully migrated {success_count}/{len(files)} files")
    
    if success_count > 0:
        print("\n📋 Next steps:")
        print("1. Run 'python setup_secure_credentials.py' to set up secure credentials")
        print("2. Test your scripts to ensure they work with the new credential system")
        print("3. Remove .backup files once you've verified everything works")
        print("4. Add .env to .gitignore if using environment variables")
    
    return 0 if success_count == len(files) else 1


if __name__ == "__main__":
    sys.exit(main())