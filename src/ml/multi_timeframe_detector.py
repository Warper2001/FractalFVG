"""
Multi-Timeframe FVG Detection System
Detects FVGs across 60 timeframes and prepares ML features
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

@dataclass
class TimeframeConfig:
    """Configuration for a timeframe"""
    name: str
    minutes: int
    weight: float
    priority: int  # Lower = higher priority
    
@dataclass 
class MultiTimeframeFVG:
    """FVG detected across multiple timeframes"""
    timestamp: datetime
    price_level: float
    type: str  # 'bullish' or 'bearish'
    timeframes: List[str]  # Timeframes where this FVG appears
    confluence_score: float
    strength_features: Dict[str, float]
    fill_probability: Optional[float] = None
    predicted_hold_time: Optional[float] = None

class MultiTimeframeFVGDector:
    """Advanced FVG detector across 60 timeframes with ML features"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.timeframes = self._initialize_timeframes()
        self.ml_features = {}
        
    def _initialize_timeframes(self) -> List[TimeframeConfig]:
        """Initialize 60 timeframes from 1 minute to 1 week"""
        timeframes = []
        
        # Intraday timeframes (1-60 minutes)
        for minutes in [1, 2, 3, 5, 8, 10, 12, 15, 20, 30, 45, 60]:
            timeframes.append(TimeframeConfig(
                name=f"{minutes}min",
                minutes=minutes,
                weight=1.0 - (minutes / 120),  # Higher weight for shorter timeframes
                priority=minutes
            ))
        
        # Daily timeframes (2-8 hours)
        for hours in range(2, 9):
            minutes = hours * 60
            timeframes.append(TimeframeConfig(
                name=f"{hours}h",
                minutes=minutes,
                weight=0.5 - (hours / 20),
                priority=100 + hours
            ))
        
        # Multi-day timeframes (1-4 days)
        for days in range(1, 5):
            minutes = days * 24 * 60
            timeframes.append(TimeframeConfig(
                name=f"{days}d",
                minutes=minutes,
                weight=0.3 - (days / 15),
                priority=200 + days
            ))
        
        # Weekly timeframes (1-4 weeks)
        for weeks in range(1, 5):
            minutes = weeks * 7 * 24 * 60
            timeframes.append(TimeframeConfig(
                name=f"{weeks}w",
                minutes=minutes,
                weight=0.2 - (weeks / 25),
                priority=300 + weeks
            ))
        
        # Monthly timeframes (1-3 months)
        for months in range(1, 4):
            minutes = months * 30 * 24 * 60
            timeframes.append(TimeframeConfig(
                name=f"{months}m",
                minutes=minutes,
                weight=0.1 - (months / 40),
                priority=400 + months
            ))
        
        # Sort by priority
        timeframes.sort(key=lambda x: x.priority)
        
        self.logger.info(f"Initialized {len(timeframes)} timeframes")
        return timeframes
    
    def resample_data(self, data: pd.DataFrame, timeframe_minutes: int) -> pd.DataFrame:
        """Resample data to specific timeframe"""
        freq = f"{timeframe_minutes}min"
        
        # For timeframes > 1 day, use different resampling
        if timeframe_minutes >= 1440:  # 1 day+
            if timeframe_minutes >= 10080:  # 1 week+
                freq = f"{timeframe_minutes//1440}D"
            else:
                freq = f"{timeframe_minutes//1440}D"
        
        resampled = data.resample(freq).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min', 
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        return pd.DataFrame(resampled)
    
    def detect_fvgs_timeframe(self, data: pd.DataFrame, timeframe: TimeframeConfig) -> List[Dict]:
        """Detect FVGs in a specific timeframe"""
        try:
            fvgs = []
            
            for i in range(2, len(data)):
                candle1 = data.iloc[i-2]
                candle2 = data.iloc[i-1]
                candle3 = data.iloc[i]
                
                # Bullish FVG: candle2.low > candle1.high
                if candle2.low > candle1.high:
                    fvg_size = candle2.low - candle1.high
                    if fvg_size > 0:
                        fvg = {
                            'timestamp': data.index[i-1],
                            'type': 'bullish',
                            'top': candle2.low,
                            'bottom': candle1.high,
                            'size': fvg_size,
                            'size_pct': fvg_size / candle1.close,
                            'timeframe': timeframe.name,
                            'volume': candle2.volume,
                            'candle1_range': candle1.high - candle1.low,
                            'candle2_range': candle2.high - candle2.low,
                            'candle3_range': candle3.high - candle3.low,
                            'price_momentum': (candle3.close - candle1.close) / candle1.close,
                            'volume_ratio': candle2.volume / max(candle1.volume, 1),
                            'gap_strength': fvg_size / max(candle1.high - candle1.low, 1)
                        }
                        fvgs.append(fvg)
                
                # Bearish FVG: candle2.high < candle1.low
                elif candle2.high < candle1.low:
                    fvg_size = candle1.low - candle2.high
                    if fvg_size > 0:
                        fvg = {
                            'timestamp': data.index[i-1],
                            'type': 'bearish',
                            'top': candle1.low,
                            'bottom': candle2.high,
                            'size': fvg_size,
                            'size_pct': fvg_size / candle1.close,
                            'timeframe': timeframe.name,
                            'volume': candle2.volume,
                            'candle1_range': candle1.high - candle1.low,
                            'candle2_range': candle2.high - candle2.low,
                            'candle3_range': candle3.high - candle3.low,
                            'price_momentum': (candle3.close - candle1.close) / candle1.close,
                            'volume_ratio': candle2.volume / max(candle1.volume, 1),
                            'gap_strength': fvg_size / max(candle1.high - candle1.low, 1)
                        }
                        fvgs.append(fvg)
            
            return fvgs
            
        except Exception as e:
            self.logger.error(f"Error detecting FVGs for {timeframe.name}: {e}")
            return []
    
    def detect_multi_timeframe_fvgs(self, data: pd.DataFrame, 
                                   max_workers: int = 8) -> List[MultiTimeframeFVG]:
        """Detect FVGs across all timeframes and find confluence"""
        self.logger.info(f"Detecting FVGs across {len(self.timeframes)} timeframes...")
        
        # Detect FVGs in parallel
        all_fvgs = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit detection tasks
            future_to_timeframe = {}
            for timeframe in self.timeframes:
                try:
                    resampled_data = self.resample_data(data, timeframe.minutes)
                    if len(resampled_data) >= 3:
                        future = executor.submit(
                            self.detect_fvgs_timeframe, 
                            resampled_data, 
                            timeframe
                        )
                        future_to_timeframe[future] = timeframe
                except Exception as e:
                    self.logger.error(f"Error resampling for {timeframe.name}: {e}")
                    continue
            
            # Collect results
            for future in as_completed(future_to_timeframe):
                timeframe = future_to_timeframe[future]
                try:
                    fvgs = future.result()
                    all_fvgs[timeframe.name] = fvgs
                    self.logger.info(f"Found {len(fvgs)} FVGs in {timeframe.name}")
                except Exception as e:
                    self.logger.error(f"Error processing {timeframe.name}: {e}")
        
        # Find confluence zones
        confluence_fvgs = self._find_confluence_zones(all_fvgs)
        
        # Extract ML features for each confluence FVG
        enhanced_fvgs = []
        for fvg in confluence_fvgs:
            ml_features = self._extract_ml_features(fvg, all_fvgs, data)
            
            enhanced_fvg = MultiTimeframeFVG(
                timestamp=fvg['timestamp'],
                price_level=fvg['price_level'],
                type=fvg['type'],
                timeframes=fvg['timeframes'],
                confluence_score=fvg['confluence_score'],
                strength_features=ml_features
            )
            enhanced_fvgs.append(enhanced_fvg)
        
        self.logger.info(f"Found {len(enhanced_fvgs)} confluence FVGs")
        return enhanced_fvgs
    
    def _find_confluence_zones(self, all_fvgs: Dict[str, List[Dict]]) -> List[Dict]:
        """Find FVGs that appear across multiple timeframes"""
        confluence_zones = []
        
        # Group FVGs by timestamp and type
        fvg_groups = {}
        
        for timeframe_name, fvgs in all_fvgs.items():
            for fvg in fvgs:
                # Round timestamp to nearest 5 minutes for grouping
                rounded_time = fvg['timestamp'].floor('5min')
                key = (rounded_time, fvg['type'], fvg['top'], fvg['bottom'])
                
                if key not in fvg_groups:
                    fvg_groups[key] = []
                fvg_groups[key].append({**fvg, 'timeframe': timeframe_name})
        
        # Find confluence zones (FVGs appearing in multiple timeframes)
        for key, fvg_list in fvg_groups.items():
            if len(fvg_list) >= 2:  # At least 2 timeframes
                # Calculate confluence score
                timeframes = [fvg['timeframe'] for fvg in fvg_list]
                weights = [tf.weight for tf in self.timeframes if tf.name in timeframes]
                confluence_score = sum(weights) / sum(tf.weight for tf in self.timeframes)
                
                # Calculate average price level
                price_levels = [(fvg['top'] + fvg['bottom']) / 2 for fvg in fvg_list]
                avg_price_level = np.mean(price_levels)
                
                confluence_zones.append({
                    'timestamp': key[0],
                    'type': key[1],
                    'price_level': avg_price_level,
                    'timeframes': timeframes,
                    'confluence_score': confluence_score,
                    'individual_fvgs': fvg_list
                })
        
        # Sort by confluence score
        confluence_zones.sort(key=lambda x: x['confluence_score'], reverse=True)
        
        return confluence_zones
    
    def _extract_ml_features(self, confluence_fvg: Dict, 
                           all_fvgs: Dict[str, List[Dict]], 
                           original_data: pd.DataFrame) -> Dict[str, float]:
        """Extract ML features for a confluence FVG"""
        features = {}
        
        # Basic FVG features
        features['confluence_score'] = confluence_fvg['confluence_score']
        features['num_timeframes'] = len(confluence_fvg['timeframes'])
        features['timeframe_diversity'] = len(set(tf.split('min')[0].split('h')[0].split('d')[0] 
                                               for tf in confluence_fvg['timeframes']))
        
        # Price-based features
        individual_fvgs = confluence_fvg['individual_fvgs']
        sizes = [fvg['size_pct'] for fvg in individual_fvgs]
        features['avg_size_pct'] = np.mean(sizes)
        features['max_size_pct'] = np.max(sizes)
        features['size_variance'] = np.var(sizes)
        
        # Volume features
        volumes = [fvg['volume'] for fvg in individual_fvgs]
        volume_ratios = [fvg['volume_ratio'] for fvg in individual_fvgs]
        features['avg_volume'] = np.mean(volumes)
        features['avg_volume_ratio'] = np.mean(volume_ratios)
        features['max_volume_ratio'] = np.max(volume_ratios)
        
        # Momentum features
        momentums = [fvg['price_momentum'] for fvg in individual_fvgs]
        features['avg_momentum'] = np.mean(momentums)
        features['momentum_consistency'] = 1 - np.std(momentums) if momentums else 0
        
        # Gap strength features
        gap_strengths = [fvg['gap_strength'] for fvg in individual_fvgs]
        features['avg_gap_strength'] = np.mean(gap_strengths)
        features['max_gap_strength'] = np.max(gap_strengths)
        
        # Time-based features
        timestamp = confluence_fvg['timestamp']
        features['hour_of_day'] = timestamp.hour
        features['day_of_week'] = timestamp.dayofweek
        features['is_session_open'] = 1 if 9 <= timestamp.hour <= 10 else 0
        features['is_session_close'] = 1 if 15 <= timestamp.hour <= 16 else 0
        
        # Market context features (from original data)
        try:
            recent_data = original_data.loc[:timestamp].tail(20)
            if len(recent_data) > 0:
                features['recent_volatility'] = recent_data['close'].pct_change().std()
                features['recent_trend'] = (recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0]
                features['avg_range'] = (recent_data['high'] - recent_data['low']).mean()
                features['price_position'] = (timestamp - recent_data.index[0]).total_seconds() / 3600  # Hours from start
        except:
            features['recent_volatility'] = 0
            features['recent_trend'] = 0
            features['avg_range'] = 0
            features['price_position'] = 0
        
        # Timeframe weight features
        timeframe_weights = []
        for tf_name in confluence_fvg['timeframes']:
            tf = next((t for t in self.timeframes if t.name == tf_name), None)
            if tf:
                timeframe_weights.append(tf.weight)
        
        if timeframe_weights:
            features['avg_timeframe_weight'] = np.mean(timeframe_weights)
            features['max_timeframe_weight'] = np.max(timeframe_weights)
        else:
            features['avg_timeframe_weight'] = 0
            features['max_timeframe_weight'] = 0
        
        return features
    
    def prepare_ml_dataset(self, data: pd.DataFrame, 
                          lookback_days: int = 30) -> pd.DataFrame:
        """Prepare dataset for ML training with historical FVG outcomes"""
        self.logger.info("Preparing ML dataset...")
        
        # Detect FVGs across all timeframes
        confluence_fvgs = self.detect_multi_timeframe_fvgs(data)
        
        # For each FVG, determine if it was filled and how long it took
        ml_data = []
        
        for fvg in confluence_fvgs:
            # Find fill outcome
            fill_result = self._determine_fill_outcome(fvg, data)
            
            # Combine features with outcome
            row = {**fvg.strength_features}
            row['filled'] = fill_result['filled']
            row['hold_time_hours'] = fill_result['hold_time_hours']
            row['fill_price'] = fill_result['fill_price']
            row['profit_pct'] = fill_result['profit_pct']
            
            ml_data.append(row)
        
        df = pd.DataFrame(ml_data)
        self.logger.info(f"Created ML dataset with {len(df)} samples")
        
        return df
    
    def _determine_fill_outcome(self, fvg: MultiTimeframeFVG, 
                               data: pd.DataFrame, max_hours: int = 24) -> Dict:
        """Determine if and when an FVG was filled"""
        try:
            # Find the index of FVG timestamp - use simple approach
            try:
                fvg_idx = int(np.where(data.index == fvg.timestamp)[0][0])
            except (IndexError, ValueError):
                # Find nearest timestamp if exact match not found
                nearest_idx = np.argmin(np.abs(data.index - fvg.timestamp))
                fvg_idx = int(nearest_idx)
            
            # Look ahead for fill
            max_bars = int(max_hours * 12)  # 5-minute bars
            end_idx = min(fvg_idx + max_bars, len(data) - 1)
            
            filled = False
            fill_bar = None
            fill_price = None
            
            for j in range(fvg_idx + 1, end_idx + 1):
                current_bar = data.iloc[j]
                
                if fvg.type == 'bullish':
                    if current_bar.low <= fvg.price_level:
                        filled = True
                        fill_bar = j
                        fill_price = current_bar.low
                        break
                else:  # bearish
                    if current_bar.high >= fvg.price_level:
                        filled = True
                        fill_bar = j
                        fill_price = current_bar.high
                        break
            
            if filled and fill_bar:
                hold_bars = fill_bar - fvg_idx
                hold_time_hours = hold_bars * 5 / 60  # Convert 5-min bars to hours
                
                # Calculate profit if filled
                entry_price = fvg.price_level
                if fill_price is not None:
                    if fvg.type == 'bullish':
                        profit_pct = (fill_price - entry_price) / entry_price * 100
                    else:
                        profit_pct = (entry_price - fill_price) / entry_price * 100
                else:
                    profit_pct = 0
            else:
                hold_time_hours = max_hours
                fill_price = None
                profit_pct = 0
            
            return {
                'filled': filled,
                'hold_time_hours': hold_time_hours,
                'fill_price': fill_price,
                'profit_pct': profit_pct
            }
            
        except Exception as e:
            self.logger.error(f"Error determining fill outcome: {e}")
            return {
                'filled': False,
                'hold_time_hours': max_hours,
                'fill_price': None,
                'profit_pct': 0
            }