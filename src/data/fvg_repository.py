"""
FVG Repository for managing Fair Value Gaps across 60 timeframes.
Provides efficient storage, retrieval, and validation of FVG data.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict
import logging
from dataclasses import dataclass, field
import json

from ..models.fvg import FVG, FVGType, ConfluenceArea, VolumeAnomaly
from ..utils.helpers import validate_fvg_conditions, create_fvg_id, filter_fvgs_by_size, filter_fvgs_by_age


@dataclass
class FVGMetadata:
    """Metadata for FVG tracking and validation."""
    fvg_id: str
    timeframe: int
    fvg_type: str
    creation_time: datetime
    last_updated: datetime
    is_active: bool = True
    fill_count: int = 0
    touch_count: int = 0
    strength_score: float = 0.0
    confidence_score: float = 0.0
    volume_anomaly_score: float = 0.0
    confluence_count: int = 0
    confluence_timeframes: List[int] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'fvg_id': self.fvg_id,
            'timeframe': self.timeframe,
            'fvg_type': self.fvg_type,
            'creation_time': self.creation_time.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'is_active': self.is_active,
            'fill_count': self.fill_count,
            'touch_count': self.touch_count,
            'strength_score': self.strength_score,
            'confidence_score': self.confidence_score,
            'volume_anomaly_score': self.volume_anomaly_score,
            'confluence_count': self.confluence_count,
            'confluence_timeframes': self.confluence_timeframes
        }


@dataclass
class FVGData:
    """Core FVG data structure."""
    top: float
    bottom: float
    midpoint: float
    size: float
    volume: float
    price_momentum: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'top': self.top,
            'bottom': self.bottom,
            'midpoint': self.midpoint,
            'size': self.size,
            'volume': self.volume,
            'price_momentum': self.price_momentum
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FVGData':
        """Create from dictionary."""
        return cls(
            top=data['top'],
            bottom=data['bottom'],
            midpoint=data['midpoint'],
            size=data['size'],
            volume=data['volume'],
            price_momentum=data['price_momentum']
        )


class FVGRepository:
    """
    Repository for managing FVGs across all 60 timeframes.
    
    Provides efficient storage, retrieval, validation, and analysis
    of Fair Value Gaps with multi-timeframe support.
    """
    
    def __init__(self, max_fvgs_per_timeframe: int = 1000, 
                 max_age_hours: int = 24,
                 min_fvg_size: float = 0.25):
        """
        Initialize FVG Repository.
        
        Args:
            max_fvgs_per_timeframe: Maximum FVGs to store per timeframe
            max_age_hours: Maximum age of FVGs to keep active
            min_fvg_size: Minimum FVG size for validation
        """
        self.max_fvgs_per_timeframe = max_fvgs_per_timeframe
        self.max_age_hours = max_age_hours
        self.min_fvg_size = min_fvg_size
        self.logger = logging.getLogger(__name__)
        
        # Storage for FVGs by timeframe
        self.fvgs_by_timeframe: Dict[int, Dict[str, Tuple[FVGData, FVGMetadata]]] = defaultdict(dict)
        
        # Index structures for efficient querying
        self.price_level_index: Dict[float, Set[str]] = defaultdict(set)  # price -> FVG IDs
        self.timeframe_index: Dict[int, Set[str]] = defaultdict(set)     # timeframe -> FVG IDs
        self.active_fvgs: Set[str] = set()
        self.confluence_groups: Dict[str, Set[str]] = defaultdict(set)   # confluence group -> FVG IDs
        
        # Statistics tracking
        self.stats = {
            'total_fvgs_created': 0,
            'total_fvgs_filled': 0,
            'total_fvgs_touched': 0,
            'current_active_fvgs': 0,
            'fvgs_by_timeframe': defaultdict(int),
            'fvgs_by_type': defaultdict(int),
            'average_fvg_size': 0.0,
            'average_strength': 0.0,
            'last_cleanup_time': None
        }
        
        self.logger.info(f"FVG Repository initialized: max {max_fvgs_per_timeframe} FVGs per timeframe")
        
    def add_fvg(self, fvg_data: Dict[str, Any]) -> str:
        """
        Add a new FVG to the repository.
        
        Args:
            fvg_data: Dictionary containing FVG information
            
        Returns:
            FVG ID for the added FVG
        """
        try:
            # Validate FVG data
            if not self._validate_fvg_data(fvg_data):
                raise ValueError("Invalid FVG data")
                
            # Create FVG components
            fvg_id = create_fvg_id(
                fvg_data['time'], 
                fvg_data['timeframe'], 
                fvg_data['type']
            )
            
            fvg_core = FVGData(
                top=fvg_data['top'],
                bottom=fvg_data['bottom'],
                midpoint=fvg_data['midpoint'],
                size=fvg_data['size'],
                volume=fvg_data['volume'],
                price_momentum=fvg_data.get('price_momentum', 0.0)
            )
            
            metadata = FVGMetadata(
                fvg_id=fvg_id,
                timeframe=fvg_data['timeframe'],
                fvg_type=fvg_data['type'],
                creation_time=fvg_data['time'],
                last_updated=fvg_data['time'],
                is_active=True,
                strength_score=fvg_data.get('strength', 0.0),
                confidence_score=fvg_data.get('confidence', 0.0),
                volume_anomaly_score=fvg_data.get('volume_anomaly', 0.0),
                confluence_count=fvg_data.get('confluence_count', 0),
                confluence_timeframes=fvg_data.get('confluence_timeframes', [])
            )
            
            # Store FVG
            timeframe = fvg_data['timeframe']
            self.fvgs_by_timeframe[timeframe][fvg_id] = (fvg_core, metadata)
            
            # Update indexes
            self._update_indexes(fvg_id, fvg_core, metadata)
            
            # Update statistics
            self._update_stats_on_add(fvg_core, metadata)
            
            # Cleanup if necessary
            if len(self.fvgs_by_timeframe[timeframe]) > self.max_fvgs_per_timeframe:
                self._cleanup_old_fvgs(timeframe)
                
            self.logger.debug(f"Added FVG {fvg_id} on {timeframe}min timeframe")
            return fvg_id
            
        except Exception as e:
            self.logger.error(f"Error adding FVG: {e}")
            raise
            
    def _validate_fvg_data(self, fvg_data: Dict[str, Any]) -> bool:
        """Validate FVG data structure and values."""
        required_fields = ['top', 'bottom', 'midpoint', 'size', 'volume', 
                          'timeframe', 'type', 'time']
        
        # Check required fields
        if not all(field in fvg_data for field in required_fields):
            return False
            
        # Validate data types and ranges
        try:
            top = float(fvg_data['top'])
            bottom = float(fvg_data['bottom'])
            size = float(fvg_data['size'])
            timeframe = int(fvg_data['timeframe'])
            fvg_type = str(fvg_data['type'])
            
            # Validate logical constraints
            if top <= bottom:
                return False
                
            if size != abs(top - bottom):
                return False
                
            if size < self.min_fvg_size:
                return False
                
            if not (1 <= timeframe <= 60):
                return False
                
            if fvg_type not in ['bullish', 'bearish']:
                return False
                
            # Validate midpoint
            midpoint = float(fvg_data['midpoint'])
            expected_midpoint = (top + bottom) / 2
            if abs(midpoint - expected_midpoint) > 0.01:  # Small tolerance for floating point
                return False
                
        except (ValueError, TypeError):
            return False
            
        return True
        
    def _update_indexes(self, fvg_id: str, fvg_core: FVGData, metadata: FVGMetadata) -> None:
        """Update index structures for efficient querying."""
        # Price level index (index by midpoint for range queries)
        price_key = round(fvg_core.midpoint, 2)  # Round to 2 decimal places for indexing
        self.price_level_index[price_key].add(fvg_id)
        
        # Timeframe index
        self.timeframe_index[metadata.timeframe].add(fvg_id)
        
        # Active FVGs set
        if metadata.is_active:
            self.active_fvgs.add(fvg_id)
            
    def _update_stats_on_add(self, fvg_core: FVGData, metadata: FVGMetadata) -> None:
        """Update statistics when adding FVG."""
        self.stats['total_fvgs_created'] += 1
        self.stats['current_active_fvgs'] += 1
        self.stats['fvgs_by_timeframe'][metadata.timeframe] += 1
        self.stats['fvgs_by_type'][metadata.fvg_type] += 1
        
        # Update running averages
        total_fvgs = self.stats['total_fvgs_created']
        current_avg_size = self.stats['average_fvg_size']
        current_avg_strength = self.stats['average_strength']
        
        self.stats['average_fvg_size'] = (
            (current_avg_size * (total_fvgs - 1) + fvg_core.size) / total_fvgs
        )
        self.stats['average_strength'] = (
            (current_avg_strength * (total_fvgs - 1) + metadata.strength_score) / total_fvgs
        )
        
    def get_fvg_by_id(self, fvg_id: str) -> Optional[Tuple[FVGData, FVGMetadata]]:
        """
        Get FVG by ID.
        
        Args:
            fvg_id: FVG identifier
            
        Returns:
            Tuple of (FVGData, FVGMetadata) or None if not found
        """
        for timeframe_fvgs in self.fvgs_by_timeframe.values():
            if fvg_id in timeframe_fvgs:
                return timeframe_fvgs[fvg_id]
        return None
        
    def get_fvgs_by_timeframe(self, timeframe: int, active_only: bool = True) -> List[Tuple[FVGData, FVGMetadata]]:
        """
        Get FVGs for a specific timeframe.
        
        Args:
            timeframe: Timeframe in minutes
            active_only: Whether to return only active FVGs
            
        Returns:
            List of (FVGData, FVGMetadata) tuples
        """
        if timeframe not in self.fvgs_by_timeframe:
            return []
            
        fvgs = []
        for fvg_id, (fvg_data, metadata) in self.fvgs_by_timeframe[timeframe].items():
            if not active_only or metadata.is_active:
                fvgs.append((fvg_data, metadata))
                
        # Sort by creation time (newest first)
        fvgs.sort(key=lambda x: x[1].creation_time, reverse=True)
        return fvgs
        
    def get_fvgs_by_price_range(self, price_min: float, price_max: float, 
                               timeframes: Optional[List[int]] = None) -> List[Tuple[FVGData, FVGMetadata]]:
        """
        Get FVGs within a price range.
        
        Args:
            price_min: Minimum price
            price_max: Maximum price
            timeframes: Optional list of timeframes to filter
            
        Returns:
            List of (FVGData, FVGMetadata) tuples
        """
        matching_fvgs = []
        
        # Search through price level index
        for price_key, fvg_ids in self.price_level_index.items():
            if price_min <= price_key <= price_max:
                for fvg_id in fvg_ids:
                    fvg = self.get_fvg_by_id(fvg_id)
                    if fvg:
                        fvg_data, metadata = fvg
                        # Check if FVG actually overlaps with price range
                        if (fvg_data.bottom <= price_max and fvg_data.top >= price_min):
                            # Filter by timeframes if specified
                            if not timeframes or metadata.timeframe in timeframes:
                                matching_fvgs.append((fvg_data, metadata))
                                
        return matching_fvgs
        
    def get_confluence_fvgs(self, min_timeframes: int = 2) -> List[Tuple[FVGData, FVGMetadata, List[int]]]:
        """
        Get FVGs that show confluence across multiple timeframes.
        
        Args:
            min_timeframes: Minimum number of timeframes for confluence
            
        Returns:
            List of (FVGData, FVGMetadata, confluence_timeframes) tuples
        """
        confluence_fvgs = []
        
        # Group FVGs by price level
        price_groups = defaultdict(list)
        for timeframe_fvgs in self.fvgs_by_timeframe.values():
            for fvg_id, (fvg_data, metadata) in timeframe_fvgs.items():
                if metadata.is_active:
                    price_key = round(fvg_data.midpoint, 1)  # Group by 0.1 price levels
                    price_groups[price_key].append((fvg_data, metadata, metadata.timeframe))
                    
        # Find confluence groups
        for price_key, fvgs in price_groups.items():
            if len(fvgs) >= min_timeframes:
                # Get unique timeframes
                unique_timeframes = list(set(tf for _, _, tf in fvgs))
                
                if len(unique_timeframes) >= min_timeframes:
                    # Return the strongest FVG from this group
                    strongest_fvg = max(fvgs, key=lambda x: x[1].strength_score)
                    confluence_fvgs.append((*strongest_fvg[:2], unique_timeframes))
                    
        return confluence_fvgs
        
    def update_fvg_status(self, fvg_id: str, is_active: Optional[bool] = None,
                         fill_count: Optional[int] = None, touch_count: Optional[int] = None) -> bool:
        """
        Update FVG status.
        
        Args:
            fvg_id: FVG identifier
            is_active: New active status
            fill_count: New fill count
            touch_count: New touch count
            
        Returns:
            True if update successful
        """
        fvg = self.get_fvg_by_id(fvg_id)
        if not fvg:
            return False
            
        fvg_data, metadata = fvg
        
        # Update metadata
        if is_active is not None:
            metadata.is_active = is_active
            if is_active:
                self.active_fvgs.add(fvg_id)
            else:
                self.active_fvgs.discard(fvg_id)
                
        if fill_count is not None:
            metadata.fill_count = fill_count
            
        if touch_count is not None:
            metadata.touch_count = touch_count
            
        metadata.last_updated = datetime.now()
        
        # Update statistics
        if not metadata.is_active:
            self.stats['current_active_fvgs'] = max(0, self.stats['current_active_fvgs'] - 1)
            
        return True
        
    def _cleanup_old_fvgs(self, timeframe: int) -> None:
        """Remove old FVGs for a specific timeframe."""
        current_time = datetime.now()
        max_age = timedelta(hours=self.max_age_hours)
        
        fvgs_to_remove = []
        timeframe_fvgs = self.fvgs_by_timeframe[timeframe]
        
        for fvg_id, (fvg_data, metadata) in timeframe_fvgs.items():
            age = current_time - metadata.creation_time
            
            # Remove if too old or inactive
            if age > max_age or not metadata.is_active:
                fvgs_to_remove.append(fvg_id)
                
        # Remove old FVGs
        for fvg_id in fvgs_to_remove:
            self._remove_fvg(fvg_id)
            
        self.logger.debug(f"Cleaned up {len(fvgs_to_remove)} old FVGs from {timeframe}min timeframe")
        
    def _remove_fvg(self, fvg_id: str) -> None:
        """Remove FVG from repository."""
        # Find and remove from timeframe storage
        for timeframe, timeframe_fvgs in self.fvgs_by_timeframe.items():
            if fvg_id in timeframe_fvgs:
                fvg_data, metadata = timeframe_fvgs[fvg_id]
                del timeframe_fvgs[fvg_id]
                
                # Update indexes
                price_key = round(fvg_data.midpoint, 2)
                self.price_level_index[price_key].discard(fvg_id)
                self.timeframe_index[timeframe].discard(fvg_id)
                self.active_fvgs.discard(fvg_id)
                
                # Update statistics
                self.stats['current_active_fvgs'] = max(0, self.stats['current_active_fvgs'] - 1)
                self.stats['fvgs_by_timeframe'][timeframe] = max(0, self.stats['fvgs_by_timeframe'][timeframe] - 1)
                
                break
                
    def get_repository_statistics(self) -> Dict[str, Any]:
        """Get comprehensive repository statistics."""
        stats = self.stats.copy()
        
        # Add current state information
        stats.update({
            'total_timeframes_active': len(self.fvgs_by_timeframe),
            'total_fvgs_stored': sum(len(fvgs) for fvgs in self.fvgs_by_timeframe.values()),
            'price_levels_indexed': len(self.price_level_index),
            'confluence_groups': len(self.confluence_groups),
            'last_cleanup': self.stats['last_cleanup_time'],
            'repository_age_hours': (datetime.now() - datetime.now()).total_seconds() / 3600  # Placeholder
        })
        
        # Calculate efficiency metrics
        if stats['total_fvgs_created'] > 0:
            stats['fill_rate'] = stats['total_fvgs_filled'] / stats['total_fvgs_created']
            stats['touch_rate'] = stats['total_fvgs_touched'] / stats['total_fvgs_created']
        else:
            stats['fill_rate'] = 0.0
            stats['touch_rate'] = 0.0
            
        return stats
        
    def export_repository_data(self, filename: str, include_metadata: bool = True) -> bool:
        """
        Export repository data to file.
        
        Args:
            filename: Output filename
            include_metadata: Whether to include metadata
            
        Returns:
            True if export successful
        """
        try:
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'repository_stats': self.get_repository_statistics(),
                'fvgs': []
            }
            
            # Collect all FVGs
            for timeframe, timeframe_fvgs in self.fvgs_by_timeframe.items():
                for fvg_id, (fvg_data, metadata) in timeframe_fvgs.items():
                    fvg_entry = {
                        'fvg_id': fvg_id,
                        'timeframe': timeframe,
                        'data': fvg_data.to_dict()
                    }
                    
                    if include_metadata:
                        fvg_entry['metadata'] = metadata.to_dict()
                        
                    export_data['fvgs'].append(fvg_entry)
                    
            # Write to file
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
                
            self.logger.info(f"Exported {len(export_data['fvgs'])} FVGs to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting repository data: {e}")
            return False
            
    def validate_repository_integrity(self) -> Dict[str, Any]:
        """
        Validate repository integrity and consistency.
        
        Returns:
            Integrity validation report
        """
        report = {
            'is_valid': True,
            'issues': [],
            'warnings': [],
            'statistics': {}
        }
        
        try:
            # Check index consistency
            indexed_fvg_count = sum(len(fvg_ids) for fvg_ids in self.price_level_index.values())
            stored_fvg_count = sum(len(fvgs) for fvgs in self.fvgs_by_timeframe.values())
            
            if indexed_fvg_count != stored_fvg_count:
                report['issues'].append(f"Index count mismatch: {indexed_fvg_count} indexed vs {stored_fvg_count} stored")
                report['is_valid'] = False
                
            # Check for orphaned indexes
            orphaned_price_indexes = 0
            for price_key, fvg_ids in self.price_level_index.items():
                for fvg_id in fvg_ids:
                    if self.get_fvg_by_id(fvg_id) is None:
                        orphaned_price_indexes += 1
                        
            if orphaned_price_indexes > 0:
                report['warnings'].append(f"Found {orphaned_price_indexes} orphaned price index entries")
                
            # Check active FVGs consistency
            active_count_in_storage = sum(
                1 for timeframe_fvgs in self.fvgs_by_timeframe.values()
                for _, metadata in timeframe_fvgs.values()
                if metadata.is_active
            )
            
            if active_count_in_storage != len(self.active_fvgs):
                report['issues'].append(f"Active FVG count mismatch: {active_count_in_storage} in storage vs {len(self.active_fvgs)} in index")
                report['is_valid'] = False
                
            # Validate FVG data integrity
            invalid_fvgs = 0
            for timeframe, timeframe_fvgs in self.fvgs_by_timeframe.items():
                for fvg_id, (fvg_data, metadata) in timeframe_fvgs.items():
                    # Validate FVG geometry
                    if fvg_data.top <= fvg_data.bottom:
                        invalid_fvgs += 1
                        
                    # Validate midpoint
                    expected_midpoint = (fvg_data.top + fvg_data.bottom) / 2
                    if abs(fvg_data.midpoint - expected_midpoint) > 0.01:
                        invalid_fvgs += 1
                        
            if invalid_fvgs > 0:
                report['issues'].append(f"Found {invalid_fvgs} FVGs with invalid geometry")
                report['is_valid'] = False
                
            # Add statistics
            report['statistics'] = {
                'total_fvgs_checked': stored_fvg_count,
                'invalid_fvgs_found': invalid_fvgs,
                'orphaned_indexes': orphaned_price_indexes,
                'index_consistency': indexed_fvg_count == stored_fvg_count,
                'active_consistency': active_count_in_storage == len(self.active_fvgs)
            }
            
        except Exception as e:
            report['issues'].append(f"Error during validation: {e}")
            report['is_valid'] = False
            
        return report