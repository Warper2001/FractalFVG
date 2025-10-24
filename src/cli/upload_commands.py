"""
CLI commands for algorithm upload functionality.
"""

import click
import json
from pathlib import Path
from typing import Optional

try:
    from ..models.algorithm import Algorithm, AlgorithmFile, AlgorithmStatus
    from ..automation.upload.algorithm_uploader import AlgorithmUploader
    from ..utils.logger import configure_logging, get_logger
except ImportError:
    # Fallback for development
    Algorithm = None
    AlgorithmFile = None
    AlgorithmStatus = None
    AlgorithmUploader = None
    
    def configure_logging():
        pass
    
    def get_logger(name):
        import logging
        return logging.getLogger(name)


@click.group()
def upload():
    """Algorithm upload commands."""
    pass


@upload.command()
@click.argument('algorithm_path', type=click.Path(exists=True, path_type=Path))
@click.option('--name', '-n', help='Algorithm name (defaults to directory name)')
@click.option('--description', '-d', help='Algorithm description')
@click.option('--language', '-l', type=click.Choice(['C#', 'Py']), default='Py', help='Algorithm language')
@click.option('--main-file', '-m', help='Main algorithm file name')
@click.option('--verbose', '-v', is_flag=True, help='Verbose logging')
def file(algorithm_path: Path, name: Optional[str], description: Optional[str], 
         language: str, main_file: Optional[str], verbose: bool):
    """Upload algorithm from file or directory."""
    
    # Configure logging
    log_level = "DEBUG" if verbose else "INFO"
    configure_logging(log_level=log_level)
    logger = get_logger()
    
    try:
        # Load algorithm
        algorithm = _load_algorithm_from_path(algorithm_path, name, description, language, main_file)
        
        # Upload algorithm
        uploader = AlgorithmUploader()
        result = uploader.upload_algorithm(algorithm)
        
        # Display results
        _display_upload_result(result)
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        click.echo(f"❌ Upload failed: {e}", err=True)
        raise click.Abort()


@upload.command()
@click.argument('config_file', type=click.Path(exists=True, path_type=Path))
@click.option('--verbose', '-v', is_flag=True, help='Verbose logging')
def batch(config_file: Path, verbose: bool):
    """Upload multiple algorithms from config file."""
    
    # Configure logging
    log_level = "DEBUG" if verbose else "INFO"
    configure_logging(log_level=log_level)
    logger = get_logger()
    
    try:
        # Load batch configuration
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        algorithms = config.get('algorithms', [])
        
        if not algorithms:
            click.echo("No algorithms found in config file")
            return
        
        click.echo(f"Processing {len(algorithms)} algorithms...")
        
        uploader = AlgorithmUploader()
        successful = []
        failed = []
        
        for i, algo_config in enumerate(algorithms, 1):
            click.echo(f"\n[{i}/{len(algorithms)}] Processing: {algo_config.get('name', 'Unknown')}")
            
            try:
                # Load algorithm
                algorithm_path = Path(algo_config['path'])
                algorithm = _load_algorithm_from_config(algo_config)
                
                # Upload algorithm
                result = uploader.upload_algorithm(algorithm)
                
                if result['success']:
                    successful.append({
                        'name': algorithm.name,
                        'project_id': result['project_id']
                    })
                    click.echo(f"✅ Uploaded successfully (Project ID: {result['project_id']})")
                else:
                    failed.append({
                        'name': algorithm.name,
                        'error': result.get('error', 'Unknown error')
                    })
                    click.echo(f"❌ Upload failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                failed.append({
                    'name': algo_config.get('name', 'Unknown'),
                    'error': str(e)
                })
                click.echo(f"❌ Processing failed: {e}")
        
        # Display summary
        click.echo(f"\n📊 Upload Summary:")
        click.echo(f"✅ Successful: {len(successful)}")
        click.echo(f"❌ Failed: {len(failed)}")
        
        if successful:
            click.echo("\nSuccessful uploads:")
            for algo in successful:
                click.echo(f"  • {algo['name']} (Project ID: {algo['project_id']})")
        
        if failed:
            click.echo("\nFailed uploads:")
            for algo in failed:
                click.echo(f"  • {algo['name']}: {algo['error']}")
        
    except Exception as e:
        logger.error(f"Batch upload failed: {e}")
        click.echo(f"❌ Batch upload failed: {e}", err=True)
        raise click.Abort()


@upload.command()
@click.argument('project_id', type=int)
@click.argument('algorithm_path', type=click.Path(exists=True, path_type=Path))
@click.option('--main-file', '-m', help='Main algorithm file name')
@click.option('--verbose', '-v', is_flag=True, help='Verbose logging')
def update(project_id: int, algorithm_path: Path, main_file: Optional[str], verbose: bool):
    """Update existing algorithm."""
    
    # Configure logging
    log_level = "DEBUG" if verbose else "INFO"
    configure_logging(log_level=log_level)
    logger = get_logger()
    
    try:
        # Load algorithm
        algorithm = _load_algorithm_from_path(algorithm_path, main_file=main_file)
        algorithm.project_id = project_id
        
        # Update algorithm
        uploader = AlgorithmUploader()
        result = uploader.update_algorithm(algorithm)
        
        # Display results
        _display_upload_result(result)
        
    except Exception as e:
        logger.error(f"Update failed: {e}")
        click.echo(f"❌ Update failed: {e}", err=True)
        raise click.Abort()


@upload.command()
@click.argument('algorithm_path', type=click.Path(exists=True, path_type=Path))
@click.option('--language', '-l', type=click.Choice(['C#', 'Py']), default='Py', help='Algorithm language')
@click.option('--main-file', '-m', help='Main algorithm file name')
@click.option('--verbose', '-v', is_flag=True, help='Verbose logging')
def validate(algorithm_path: Path, language: str, main_file: Optional[str], verbose: bool):
    """Validate algorithm without uploading."""
    
    # Configure logging
    log_level = "DEBUG" if verbose else "INFO"
    configure_logging(log_level=log_level)
    logger = get_logger()
    
    try:
        # Load algorithm
        algorithm = _load_algorithm_from_path(algorithm_path, language=language, main_file=main_file)
        
        # Validate algorithm
        from ..automation.upload.validation import AlgorithmValidator
        validator = AlgorithmValidator()
        result = validator.validate_algorithm(algorithm)
        
        # Display results
        if result.is_valid:
            click.echo("✅ Algorithm validation passed")
        else:
            click.echo("❌ Algorithm validation failed")
            
        if result.errors:
            click.echo("\n🚨 Errors:")
            for error in result.errors:
                click.echo(f"  • {error}")
        
        if result.warnings:
            click.echo("\n⚠️  Warnings:")
            for warning in result.warnings:
                click.echo(f"  • {warning}")
        
        if result.metadata:
            click.echo(f"\n📊 Validation Metadata:")
            for key, value in result.metadata.items():
                click.echo(f"  • {key}: {value}")
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        click.echo(f"❌ Validation failed: {e}", err=True)
        raise click.Abort()


def _load_algorithm_from_path(algorithm_path: Path, name: Optional[str] = None,
                             description: Optional[str] = None, language: str = 'Py',
                             main_file: Optional[str] = None) -> Algorithm:
    """Load algorithm from file or directory."""
    
    if algorithm_path.is_file():
        # Single file
        files = [_create_algorithm_file(algorithm_path, is_main=True)]
        algorithm_name = name or algorithm_path.stem
    else:
        # Directory
        files = []
        main_file_found = False
        
        for file_path in algorithm_path.rglob('*'):
            if file_path.is_file() and _is_supported_file(file_path):
                is_main = False
                
                # Determine if this is the main file
                if main_file and file_path.name == main_file:
                    is_main = True
                    main_file_found = True
                elif not main_file and _is_likely_main_file(file_path):
                    is_main = True
                    main_file_found = True
                
                files.append(_create_algorithm_file(file_path, is_main))
        
        if not main_file_found and main_file:
            raise ValueError(f"Main file '{main_file}' not found")
        
        algorithm_name = name or algorithm_path.name
    
    if not files:
        raise ValueError("No supported files found")
    
    return Algorithm(
        name=algorithm_name,
        description=description or f"Algorithm {algorithm_name}",
        language=language,
        files=files,
        status=AlgorithmStatus.DRAFT
    )


def _load_algorithm_from_config(config: dict) -> Algorithm:
    """Load algorithm from configuration."""
    algorithm_path = Path(config['path'])
    
    return _load_algorithm_from_path(
        algorithm_path=algorithm_path,
        name=config.get('name'),
        description=config.get('description'),
        language=config.get('language', 'Py'),
        main_file=config.get('main_file')
    )


def _create_algorithm_file(file_path: Path, is_main: bool = False) -> AlgorithmFile:
    """Create AlgorithmFile from path."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return AlgorithmFile(
        name=file_path.name,
        content=content,
        size=len(content.encode('utf-8')),
        is_main=is_main
    )


def _is_supported_file(file_path: Path) -> bool:
    """Check if file is supported."""
    return file_path.suffix.lower() in {'.cs', '.py'}


def _is_likely_main_file(file_path: Path) -> bool:
    """Check if file is likely the main algorithm file."""
    name_lower = file_path.name.lower()
    
    # Common main file patterns
    main_patterns = [
        'main.py', 'main.cs',
        'algorithm.py', 'algorithm.cs',
        'strategy.py', 'strategy.cs',
        'tradingbot.py', 'tradingbot.cs'
    ]
    
    return name_lower in main_patterns


def _display_upload_result(result: dict):
    """Display upload result."""
    if result['success']:
        click.echo("✅ Algorithm uploaded successfully!")
        click.echo(f"📁 Project ID: {result['project_id']}")
        click.echo(f"🔨 Compile ID: {result['compile_id']}")
        click.echo(f"📄 Files uploaded: {result['uploaded_files']}")
        
        if result.get('validation_warnings'):
            click.echo("\n⚠️  Validation warnings:")
            for warning in result['validation_warnings']:
                click.echo(f"  • {warning}")
    else:
        click.echo("❌ Algorithm upload failed!")
        click.echo(f"🚨 Error: {result['error']}")
        
        if result.get('validation_errors'):
            click.echo("\n🚨 Validation errors:")
            for error in result['validation_errors']:
                click.echo(f"  • {error}")
        
        if result.get('validation_warnings'):
            click.echo("\n⚠️  Validation warnings:")
            for warning in result['validation_warnings']:
                click.echo(f"  • {warning}")