"""
Main CLI entry point for the Automated QuantConnect Pipeline.
"""

import click
from .upload_commands import upload
from .backtest_commands import backtest


@click.group()
@click.version_option(version='1.0.0')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, verbose):
    """Automated QuantConnect Pipeline CLI."""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose


# Add command groups
cli.add_command(upload)
cli.add_command(backtest)


@cli.command()
def status():
    """Check pipeline status and configuration."""
    click.echo("🔧 Automated QuantConnect Pipeline Status")
    click.echo("=" * 40)
    
    # Check credentials
    try:
        from ..utils.credential_manager import get_quantconnect_credential_manager
        cred_manager = get_quantconnect_credential_manager()
        user_id, api_token, org_id = cred_manager.get_quantconnect_credentials()
        
        if user_id and api_token:
            click.echo("✅ Credentials: Configured")
            click.echo(f"   User ID: {user_id}")
            if org_id:
                click.echo(f"   Organization: {org_id}")
        else:
            click.echo("❌ Credentials: Not configured")
            click.echo("   Run 'pipeline auth setup' to configure")
            
    except Exception as e:
        click.echo(f"❌ Credentials: Error - {e}")
    
    # Check API connectivity
    try:
        from ..utils.api_client import QuantConnectAPIClient
        from ..utils.credential_manager import get_quantconnect_credential_manager
        
        cred_manager = get_quantconnect_credential_manager()
        user_id, api_token, org_id = cred_manager.get_quantconnect_credentials()
        
        if user_id and api_token:
            client = QuantConnectAPIClient(user_id=user_id, api_token=api_token)
            response = client.authenticate()
            
            if response:
                click.echo("✅ API Connection: Working")
            else:
                click.echo("⚠️  API Connection: Unknown response")
                
    except Exception as e:
        click.echo(f"❌ API Connection: Failed - {e}")


@cli.group()
def auth():
    """Authentication commands."""
    pass


@auth.command()
@click.option('--user-id', prompt=True, help='QuantConnect User ID')
@click.option('--api-token', prompt=True, hide_input=True, help='QuantConnect API Token')
@click.option('--organization-id', help='QuantConnect Organization ID (optional)')
def setup(user_id, api_token, organization_id):
    """Setup QuantConnect credentials."""
    try:
        from ..utils.credential_manager import get_quantconnect_credential_manager
        
        cred_manager = get_quantconnect_credential_manager()
        success = cred_manager.store_quantconnect_credentials(
            user_id=user_id,
            api_token=api_token,
            organization_id=organization_id
        )
        
        if success:
            click.echo("✅ Credentials stored successfully!")
            click.echo("You can now use the upload commands.")
        else:
            click.echo("❌ Failed to store credentials")
            
    except Exception as e:
        click.echo(f"❌ Setup failed: {e}")


@auth.command()
def check():
    """Check current credentials."""
    try:
        from ..utils.credential_manager import get_quantconnect_credential_manager
        
        cred_manager = get_quantconnect_credential_manager()
        user_id, api_token, org_id = cred_manager.get_quantconnect_credentials()
        
        if user_id and api_token:
            click.echo("✅ Credentials found:")
            click.echo(f"   User ID: {user_id}")
            if org_id:
                click.echo(f"   Organization ID: {org_id}")
            click.echo(f"   API Token: {'*' * len(api_token)}")
        else:
            click.echo("❌ No credentials found")
            click.echo("Run 'pipeline auth setup' to configure")
            
    except Exception as e:
        click.echo(f"❌ Check failed: {e}")


@auth.command()
def clear():
    """Clear stored credentials."""
    try:
        from ..utils.credential_manager import get_quantconnect_credential_manager
        
        cred_manager = get_quantconnect_credential_manager()
        
        if cred_manager.credentials_exist():
            if click.confirm('Are you sure you want to clear stored credentials?'):
                success = cred_manager.delete_credentials()
                
                if success:
                    click.echo("✅ Credentials cleared successfully")
                else:
                    click.echo("❌ Failed to clear credentials")
        else:
            click.echo("ℹ️  No credentials to clear")
            
    except Exception as e:
        click.echo(f"❌ Clear failed: {e}")


if __name__ == '__main__':
    cli()