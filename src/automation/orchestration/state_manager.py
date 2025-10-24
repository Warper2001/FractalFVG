"""
Pipeline state manager for persistence and resumption.

This module provides functionality to save and restore pipeline execution state,
enabling the pipeline to resume from where it left off after interruptions.
"""

import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from ...utils.logger import get_logger
from ...models.pipeline_execution import PipelineExecution, PipelineStatus


@dataclass
class StateSnapshot:
    """Snapshot of pipeline state at a specific point in time."""
    timestamp: datetime
    pipeline_execution: PipelineExecution
    context: Dict[str, Any]
    checkpoint_data: Dict[str, Any]


class PipelineStateManager:
    """
    Manages pipeline state persistence and resumption.
    
    Provides functionality to:
    - Save pipeline state at checkpoints
    - Restore pipeline from saved state
    - Manage multiple pipeline executions
    - Clean up old state files
    """
    
    def __init__(self, state_dir: Optional[Path] = None):
        """
        Initialize the state manager.
        
        Args:
            state_dir: Directory to store state files (default: data/pipeline_state)
        """
        self.logger = get_logger(__name__)
        
        if state_dir is None:
            state_dir = Path("data/pipeline_state")
        
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"State manager initialized with directory: {self.state_dir}")
    
    def save_state(self, pipeline: PipelineExecution, 
                   context: Optional[Dict[str, Any]] = None,
                   checkpoint_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Save pipeline state to disk.
        
        Args:
            pipeline: Pipeline execution object to save
            context: Additional context information
            checkpoint_data: Checkpoint-specific data
            
        Returns:
            Path to saved state file
        """
        try:
            timestamp = datetime.now()
            
            # Create state snapshot
            snapshot = StateSnapshot(
                timestamp=timestamp,
                pipeline_execution=pipeline,
                context=context or {},
                checkpoint_data=checkpoint_data or {}
            )
            
            # Generate filename
            filename = f"pipeline_{pipeline.execution_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            filepath = self.state_dir / filename
            
            # Convert to serializable format
            state_data = {
                'timestamp': timestamp.isoformat(),
                'pipeline': asdict(pipeline),
                'context': snapshot.context,
                'checkpoint_data': snapshot.checkpoint_data
            }
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump(state_data, f, indent=2, default=str)
            
            self.logger.info(f"Pipeline state saved to: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Failed to save pipeline state: {e}")
            raise
    
    def load_state(self, state_file: str) -> StateSnapshot:
        """
        Load pipeline state from disk.
        
        Args:
            state_file: Path to state file
            
        Returns:
            Loaded state snapshot
        """
        try:
            filepath = Path(state_file)
            if not filepath.exists():
                raise FileNotFoundError(f"State file not found: {state_file}")
            
            with open(filepath, 'r') as f:
                state_data = json.load(f)
            
            # Reconstruct pipeline execution object
            pipeline_data = state_data['pipeline']
            pipeline = PipelineExecution(**pipeline_data)
            
            # Create snapshot
            snapshot = StateSnapshot(
                timestamp=datetime.fromisoformat(state_data['timestamp']),
                pipeline_execution=pipeline,
                context=state_data.get('context', {}),
                checkpoint_data=state_data.get('checkpoint_data', {})
            )
            
            self.logger.info(f"Pipeline state loaded from: {filepath}")
            return snapshot
            
        except Exception as e:
            self.logger.error(f"Failed to load pipeline state: {e}")
            raise
    
    def list_saved_states(self, pipeline_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all saved pipeline states.
        
        Args:
            pipeline_id: Optional filter for specific pipeline ID
            
        Returns:
            List of state information
        """
        try:
            states = []
            
            for state_file in self.state_dir.glob("pipeline_*.json"):
                try:
                    with open(state_file, 'r') as f:
                        state_data = json.load(f)
                    
                    pipeline_id_match = state_data['pipeline'].get('execution_id')
                    
                    if pipeline_id is None or pipeline_id_match == pipeline_id:
                        states.append({
                            'file': str(state_file),
                            'timestamp': state_data['timestamp'],
                            'pipeline_id': pipeline_id_match,
                            'status': state_data['pipeline'].get('status'),
                            'stage': state_data['pipeline'].get('current_stage')
                        })
                        
                except Exception as e:
                    self.logger.warning(f"Failed to read state file {state_file}: {e}")
                    continue
            
            # Sort by timestamp (newest first)
            states.sort(key=lambda x: x['timestamp'], reverse=True)
            return states
            
        except Exception as e:
            self.logger.error(f"Failed to list saved states: {e}")
            return []
    
    def get_latest_state(self, pipeline_id: Optional[str] = None) -> Optional[StateSnapshot]:
        """
        Get the most recent saved state.
        
        Args:
            pipeline_id: Optional filter for specific pipeline ID
            
        Returns:
            Latest state snapshot or None if no states found
        """
        states = self.list_saved_states(pipeline_id)
        
        if not states:
            return None
        
        latest_state_file = states[0]['file']
        return self.load_state(latest_state_file)
    
    def delete_state(self, state_file: str) -> bool:
        """
        Delete a saved state file.
        
        Args:
            state_file: Path to state file
            
        Returns:
            True if deleted successfully
        """
        try:
            filepath = Path(state_file)
            if filepath.exists():
                filepath.unlink()
                self.logger.info(f"State file deleted: {filepath}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete state file {state_file}: {e}")
            return False
    
    def cleanup_old_states(self, keep_count: int = 10) -> int:
        """
        Clean up old state files, keeping only the most recent ones.
        
        Args:
            keep_count: Number of recent states to keep per pipeline
            
        Returns:
            Number of files deleted
        """
        try:
            deleted_count = 0
            
            # Group states by pipeline ID
            pipeline_states = {}
            for state in self.list_saved_states():
                pipeline_id = state['pipeline_id']
                if pipeline_id not in pipeline_states:
                    pipeline_states[pipeline_id] = []
                pipeline_states[pipeline_id].append(state)
            
            # Clean up old states for each pipeline
            for pipeline_id, states in pipeline_states.items():
                if len(states) > keep_count:
                    # Keep the most recent 'keep_count' states
                    states_to_delete = states[keep_count:]
                    
                    for state in states_to_delete:
                        if self.delete_state(state['file']):
                            deleted_count += 1
            
            self.logger.info(f"Cleaned up {deleted_count} old state files")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old states: {e}")
            return 0
    
    def create_checkpoint(self, pipeline: PipelineExecution, 
                         checkpoint_name: str,
                         data: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a named checkpoint for the pipeline.
        
        Args:
            pipeline: Current pipeline execution
            checkpoint_name: Name of the checkpoint
            data: Additional checkpoint data
            
        Returns:
            Path to checkpoint file
        """
        checkpoint_data = {
            'name': checkpoint_name,
            'data': data or {}
        }
        
        return self.save_state(pipeline, checkpoint_data=checkpoint_data)
    
    def resume_from_checkpoint(self, checkpoint_name: str) -> Optional[StateSnapshot]:
        """
        Resume pipeline from a named checkpoint.
        
        Args:
            checkpoint_name: Name of the checkpoint to resume from
            
        Returns:
            State snapshot if found, None otherwise
        """
        states = self.list_saved_states()
        
        for state in states:
            try:
                snapshot = self.load_state(state['file'])
                
                checkpoint_data = snapshot.checkpoint_data
                if checkpoint_data.get('name') == checkpoint_name:
                    self.logger.info(f"Resumed from checkpoint: {checkpoint_name}")
                    return snapshot
                    
            except Exception as e:
                self.logger.warning(f"Failed to load checkpoint {state['file']}: {e}")
                continue
        
        self.logger.warning(f"Checkpoint not found: {checkpoint_name}")
        return None