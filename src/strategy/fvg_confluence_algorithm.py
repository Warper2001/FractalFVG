"""
FVG Confluence Trading Strategy Algorithm.

This module implements the main algorithm that integrates FVG detection across
multiple timeframes (1-60 minutes) with volume confirmation for MNQ futures trading.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging

# Import FVG components
try:
    from ..data.timeframe_manager import TimeframeManager
    from ..data.volume_analyzer import VolumeAnalyzer
    from ..indicators.fvg_indicator import FairValueGapIndicator
    from ..indicators.confluence_scorer import ConfluenceScorer
    from ..utils.config import StrategyConfig, TimeframeConfig
    from ..models.fvg import FVG, FVGType, ConfluenceArea, VolumeAnomaly
    from ..models.confluence_score import ConfluenceScore
    COMPONENTS_AVAILABLE = True
except ImportError:
    COMPONENTS_AVAILABLE = False
    logging.warning("FVG components not available - using mock implementation")

# QuantConnect imports (these will be available in LEAN environment)
try:
    from AlgorithmImports import QCAlgorithm, Resolution, Time, Slice, TradeBar, Symbol
    from QuantConnect.Data.UniverseSelection import Universe
    from QuantConnect.Securities import Security
    from QuantConnect.Orders import OrderStatus
    from QuantConnect.Securities.Future import Futures
except ImportError:
    # Mock classes for development/testing outside LEAN
    class QCAlgorithm:
        def __init__(self):
            self.Time = datetime.now()
            self.Portfolio = {}
            self.Securities = {}
            self.Debug = print
            self.Log = print
            self.Error = print
            self.Warn = print
            
        def Initialize(self):
            pass
            
        def OnData(self, data):
            pass
            
        def SetWarmUp(self, timedelta):
            pass
            
        def AddFuture(self, symbol, resolution):
            return None
            
        def SetStartDate(self, year, month, day):
            pass
            
        def SetEndDate(self, year, month, day):
            pass
            
        def SetCash(self, amount):
            pass
            
        def Consolidate(self, symbol, period, handler):
            pass
            
        def ScheduleOn(self, date_rule, time_rule, handler):
            pass
            
        def Plot(self, chart_name, series_name, value):
            pass
    
    class Resolution:
        Tick = "tick"
        Second = "second"
        Minute = "minute"
        Hour = "hour"
        Daily = "daily"
    
    class Time:
        @staticmethod
        def Midnight():
            return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    class Slice:
        pass
    
    class TradeBar:
        pass
    
    class Symbol:
        pass
    
    class Security:
        pass
    
    class Futures:
        pass
    
    class OrderStatus:
        Filled = "filled"
        Submitted = "submitted"
        Cancelled = "cancelled"


class FVGConfluenceAlgorithm(QCAlgorithm):
    """
    Main algorithm for FVG Confluence Trading Strategy.
    
    This algorithm implements comprehensive FVG detection across multiple timeframes
    (1-60 minutes) with volume confirmation and confluence analysis for MNQ futures.
    """
    
    def __init__(self):
        """Initialize the FVG Confluence algorithm."""
        super().__init__()
        
        # Algorithm configuration
        self.mnq_symbol: Optional[Symbol] = None
        self.timeframes: List[int] = list(range(1, 61))  # 1-60 minute timeframes
        self.consolidators: Dict[int, object] = {}
        
        # Data storage
        self.price_data: Dict[int, pd.DataFrame] = {}  # Multi-timeframe price data
        self.fvg_data: Dict[int, List[Dict]] = {}  # FVGs by timeframe
        self.volume_data: Dict[int, pd.Series] = {}  # Volume data by timeframe
        
        # Analysis parameters
        self.volume_period: int = 20  # Period for volume moving average
        self.confluence_threshold: int = 3  # Minimum timeframes for confluence
        self.volume_multiplier: float = 2.0  # Volume anomaly threshold
        
        # Performance tracking
        self.trade_count: int = 0
        self.daily_trades: List[datetime] = []
        self.performance_metrics: Dict = {}
        
        # Research mode flag
        self.research_mode: bool = True  # True for research, False for live trading
        
        # Enhanced FVG components
        self.timeframe_manager = None
        self.fvg_indicators: Dict[int, FairValueGapIndicator] = {}
        self.volume_analyzer: Optional[VolumeAnalyzer] = None
        self.confluence_scorer: Optional[ConfluenceScorer] = None
        
        # Configuration
        self.config = None
        self.timeframe_config = None
        
        # Initialize enhanced components if available
        if COMPONENTS_AVAILABLE:
            self._initialize_enhanced_components()
        
    def Initialize(self) -> None:
        """
        Initialize the algorithm with MNQ futures and required consolidators.
        """
        # Set algorithm parameters
        self.SetStartDate(2023, 1, 1)  # Start date for backtesting
        self.SetEndDate(2024, 12, 31)  # End date for backtesting
        self.SetCash(100000)  # Starting capital
        
        # Add MNQ futures
        self.mnq_symbol = self.AddFuture("MNQ", Resolution.Minute).Symbol
        
        # Set warmup period for indicators
        self.SetWarmUp(timedelta(days=30))
        
        # Initialize consolidators for all timeframes
        self._initialize_consolidators()
        
        # Schedule daily analysis
        self._schedule_analysis()
        
        self.Debug("FVG Confluence Algorithm initialized")
        self.Debug(f"Timeframes: {self.timeframes}")
        self.Debug(f"Volume period: {self.volume_period}")
        self.Debug(f"Confluence threshold: {self.confluence_threshold}")
        
        # Log initialization status
        if COMPONENTS_AVAILABLE:
            self.Debug("Enhanced FVG components: AVAILABLE")
            self.Debug(f"Initialized {len(self.fvg_indicators)} timeframe indicators")
        else:
            self.Debug("Enhanced FVG components: NOT AVAILABLE - using legacy detection")
            
        self.Debug(f"Research mode: {self.research_mode}")
        self.Debug(f"Algorithm ready for MNQ futures trading")
        
    def _initialize_consolidators(self) -> None:
        """Initialize consolidators for all timeframes (1-60 minutes)."""
        for timeframe in self.timeframes:
            # Create consolidator for each timeframe
            consolidator = self.Consolidate(
                self.mnq_symbol, 
                timedelta(minutes=timeframe), 
                lambda data, tf=timeframe: self._on_consolidated_data(data, tf)
            )
            self.consolidators[timeframe] = consolidator
            
            # Initialize data storage for this timeframe
            self.price_data[timeframe] = pd.DataFrame()
            self.fvg_data[timeframe] = []
            self.volume_data[timeframe] = pd.Series(dtype=float)
            
    def _schedule_analysis(self) -> None:
        """Schedule regular analysis tasks."""
        # Schedule FVG analysis every 5 minutes during market hours
        self.ScheduleOn(
            self.DateRules.EveryDay(self.mnq_symbol),
            self.TimeRules.Every(timedelta(minutes=5)),
            self._analyze_fvg_confluence
        )
        
        # Schedule daily performance analysis at market close
        self.ScheduleOn(
            self.DateRules.EveryDay(self.mnq_symbol),
            self.TimeRules.BeforeMarketClose(self.mnq_symbol, 5),
            self._daily_performance_analysis
        )
        
    def OnData(self, slice: Slice) -> None:
        """
        Handle incoming data slices.
        
        Args:
            slice: Current data slice containing market data
        """
        if not slice.HasData:
            return
            
        # Update current time reference
        self.Time = slice.Time
        
        # Log data reception for debugging
        if self.research_mode and slice.Time.minute % 30 == 0:  # Log every 30 minutes
            self.Debug(f"Data received at {self.Time}")
            
    def _on_consolidated_data(self, data: TradeBar, timeframe: int) -> None:
        """
        Handle consolidated data for specific timeframe.
        
        Args:
            data: Consolidated trade bar data
            timeframe: Timeframe in minutes
        """
        if data is None:
            return
            
        # Convert to pandas DataFrame for analysis
        new_row = pd.DataFrame({
            'time': [data.Time],
            'open': [data.Open],
            'high': [data.High],
            'low': [data.Low],
            'close': [data.Close],
            'volume': [data.Volume]
        })
        
        # Append to existing data
        if self.price_data[timeframe].empty:
            self.price_data[timeframe] = new_row
        else:
            self.price_data[timeframe] = pd.concat([self.price_data[timeframe], new_row], ignore_index=True)
            
        # Keep only recent data (last 1000 bars to manage memory)
        if len(self.price_data[timeframe]) > 1000:
            self.price_data[timeframe] = self.price_data[timeframe].tail(1000).reset_index(drop=True)
            
        # Update volume data
        self.volume_data[timeframe] = self.price_data[timeframe]['volume']
        
        # Detect FVGs for this timeframe
        self._detect_fvgs(timeframe)
        
    def _detect_fvgs(self, timeframe: int) -> None:
        """
        Detect Fair Value Gaps for a specific timeframe using enhanced FVG indicator.
        
        Args:
            timeframe: Timeframe in minutes
        """
        df = self.price_data[timeframe]
        if len(df) < 3:
            return
            
        # Use enhanced FVG indicator if available
        if COMPONENTS_AVAILABLE and timeframe in self.fvg_indicators:
            self._detect_fvgs_enhanced(timeframe, df)
        else:
            self._detect_fvgs_legacy(timeframe, df)
            
    def _detect_fvgs_enhanced(self, timeframe: int, df: pd.DataFrame) -> None:
        """
        Detect FVGs using enhanced FairValueGapIndicator.
        
        Args:
            timeframe: Timeframe in minutes
            df: Price data DataFrame
        """
        try:
            indicator = self.fvg_indicators[timeframe]
            
            # Update indicator with latest data
            for _, row in df.tail(3).iterrows():  # Last 3 bars for FVG detection
                # Create mock trade bar for indicator
                mock_bar = type('MockTradeBar', (), {
                    'Open': row['open'],
                    'High': row['high'],
                    'Low': row['low'],
                    'Close': row['close'],
                    'Volume': row['volume'],
                    'EndTime': row['time'],
                    'Time': row['time']
                })()
                
                indicator.Update(mock_bar)
                
            # Get detected FVGs with validation
            validation_report = indicator.validate_fvg_data_structures()
            
            if not validation_report['is_valid']:
                if self.research_mode:
                    self.Debug(f"FVG validation issues for {timeframe}min: {validation_report['issues']}")
                    
            # Clean FVG data
            cleaning_report = indicator.clean_fvg_data()
            if cleaning_report['modifications'] and self.research_mode:
                self.Debug(f"Cleaned {len(cleaning_report['modifications'])} FVGs for {timeframe}min")
                
            # Get active FVGs
            active_fvgs = indicator.get_active_fvgs(max_age_minutes=240)  # 4 hours
            
            # Store detected FVGs
            self.fvg_data[timeframe] = active_fvgs
            
            # Log detection statistics
            if self.research_mode and active_fvgs:
                stats = indicator.get_fvg_statistics()
                self.Debug(f"{timeframe}min FVG Detection: {len(active_fvgs)} active, "
                          f"Detection rate: {stats.get('detection_rate', 0):.3f}, "
                          f"Filter efficiency: {stats.get('filter_efficiency', 0):.3f}")
                          
                # Log detailed statistics
                self.Debug(f"{timeframe}min FVG Stats: Total analyzed: {stats.get('total_patterns_analyzed', 0)}, "
                          f"Bullish: {stats.get('bullish_fvgs', 0)}, Bearish: {stats.get('bearish_fvgs', 0)}, "
                          f"Avg size: {stats.get('average_fvg_size', 0):.2f}")
                          
            elif self.research_mode:
                self.Debug(f"{timeframe}min FVG Detection: No active FVGs found")
                          
        except Exception as e:
            self.Error(f"Error in enhanced FVG detection for {timeframe}min: {e}")
            # Fallback to legacy detection
            self._detect_fvgs_legacy(timeframe, df)
            
    def _detect_fvgs_legacy(self, timeframe: int, df: pd.DataFrame) -> None:
        """
        Detect FVGs using legacy three-candle pattern detection.
        
        Args:
            timeframe: Timeframe in minutes
            df: Price data DataFrame
        """
        # FVG detection logic (three-candle pattern)
        # Bullish FVG: gap between high of first candle and low of third candle
        # Bearish FVG: gap between low of first candle and high of third candle
        
        fvgs = []
        
        for i in range(len(df) - 2):
            candle1 = df.iloc[i]
            candle2 = df.iloc[i + 1]
            candle3 = df.iloc[i + 2]
            
            # Bullish FVG (upward move)
            if candle1['high'] < candle3['low']:
                fvg = {
                    'type': 'bullish',
                    'time': candle2['time'],
                    'top': candle1['high'],
                    'bottom': candle3['low'],
                    'size': candle3['low'] - candle1['high'],
                    'timeframe': timeframe,
                    'volume': candle2['volume'],
                    'strength': self._calculate_fvg_strength(candle1, candle2, candle3)
                }
                fvgs.append(fvg)
                
            # Bearish FVG (downward move)
            elif candle1['low'] > candle3['high']:
                fvg = {
                    'type': 'bearish',
                    'time': candle2['time'],
                    'top': candle3['high'],
                    'bottom': candle1['low'],
                    'size': candle1['low'] - candle3['high'],
                    'timeframe': timeframe,
                    'volume': candle2['volume'],
                    'strength': self._calculate_fvg_strength(candle1, candle2, candle3)
                }
                fvgs.append(fvg)
                
        # Store detected FVGs
        self.fvg_data[timeframe] = fvgs
        
    def _calculate_fvg_strength(self, candle1: pd.Series, candle2: pd.Series, candle3: pd.Series) -> float:
        """
        Calculate the strength of an FVG based on candle characteristics.
        
        Args:
            candle1: First candle in the pattern
            candle2: Second candle (middle candle)
            candle3: Third candle in the pattern
            
        Returns:
            Strength score between 0 and 1
        """
        # Base strength from FVG size relative to candle ranges
        avg_range = (candle1['high'] - candle1['low'] + 
                    candle2['high'] - candle2['low'] + 
                    candle3['high'] - candle3['low']) / 3
        
        if avg_range == 0:
            return 0.0
            
        # Volume contribution
        volume_factor = min(candle2['volume'] / 1000000, 1.0)  # Normalize volume
        
        # Price movement contribution
        price_move = abs(candle3['close'] - candle1['open']) / avg_range
        price_factor = min(price_move / 2, 1.0)  # Normalize price movement
        
        # Combined strength
        strength = (volume_factor + price_factor) / 2
        return min(strength, 1.0)
        
    def _analyze_fvg_confluence(self) -> None:
        """Analyze FVG confluence across all timeframes using enhanced ConfluenceScorer."""
        if self.research_mode:
            self.Debug(f"Analyzing FVG confluence at {self.Time}")
            
        # Use enhanced confluence scorer if available
        if COMPONENTS_AVAILABLE and self.confluence_scorer:
            self._analyze_fvg_confluence_enhanced()
        else:
            self._analyze_fvg_confluence_legacy()
            
    def _analyze_fvg_confluence_enhanced(self) -> None:
        """Analyze FVG confluence using enhanced ConfluenceScorer with volume analysis."""
        try:
            # Feed FVG data to confluence scorer
            for timeframe, fvgs in self.fvg_data.items():
                if fvgs:
                    # Convert legacy FVG dicts to FVG objects if needed
                    fvg_objects = self._convert_to_fvg_objects(fvgs, timeframe)
                    self.confluence_scorer.add_fvg_data(timeframe, fvg_objects)
                    
            # Calculate confluence scores
            confluence_scores = self.confluence_scorer.calculate_confluence_scores()
            
            # Filter for high-quality setups with volume confirmation
            high_quality_setups = self._filter_high_quality_setups(confluence_scores)
            
            # Apply volume confirmation filtering
            volume_confirmed_setups = self._apply_volume_confirmation_filter(high_quality_setups)
            
            # Filter for trade frequency management (5-20 trades per day)
            filtered_setups = self._filter_trade_opportunities_enhanced(volume_confirmed_setups)
            
            # Store results for performance analysis
            self.performance_metrics['latest_setups'] = filtered_setups
            self.performance_metrics['confluence_scores'] = confluence_scores
            
            if self.research_mode and filtered_setups:
                self.Debug(f"Found {len(filtered_setups)} high-priority setups (enhanced)")
                
                # Log setup details
                for i, setup in enumerate(filtered_setups[:3]):  # Log top 3 setups
                    self.Debug(f"Setup #{i+1}: Price {setup['price_level']:.2f}, "
                              f"Confluence {setup['timeframe_count']} timeframes, "
                              f"Score {setup['final_score']:.3f}, "
                              f"Volume: {setup['volume_score']:.3f}")
                              
            elif self.research_mode:
                self.Debug("No high-priority setups found (enhanced)")
                
                # Log confluence analysis summary
                if confluence_scores:
                    high_quality_count = len([cs for cs in confluence_scores if cs.is_high_quality()])
                    volume_confirmed_count = len([cs for cs in confluence_scores if cs.volume_score > 0.2])
                    self.Debug(f"Confluence Summary: Total {len(confluence_scores)}, "
                              f"High Quality {high_quality_count}, "
                              f"Volume Confirmed {volume_confirmed_count}")
                              
        except Exception as e:
            self.Error(f"Error in enhanced confluence analysis: {e}")
            # Fallback to legacy analysis
            self._analyze_fvg_confluence_legacy()
            
    def _analyze_fvg_confluence_legacy(self) -> None:
        """Analyze FVG confluence using legacy method."""
        if self.research_mode:
            self.Debug("Using legacy confluence analysis")
            
        # Collect all FVGs from all timeframes
        all_fvgs = []
        for timeframe, fvgs in self.fvg_data.items():
            for fvg in fvgs:
                all_fvgs.append(fvg)
                
        if not all_fvgs:
            return
            
        # Find confluence areas (overlapping FVGs from different timeframes)
        confluence_areas = self._find_confluence_areas(all_fvgs)
        
        # Analyze volume at confluence areas
        high_priority_setups = self._analyze_volume_confluence(confluence_areas)
        
        # Filter for trade frequency management (5-20 trades per day)
        filtered_setups = self._filter_trade_opportunities(high_priority_setups)
        
        # Store results for performance analysis
        self.performance_metrics['latest_setups'] = filtered_setups
        
        if self.research_mode and filtered_setups:
            self.Debug(f"Found {len(filtered_setups)} high-priority setups (legacy)")
            
            # Log setup details
            for i, setup in enumerate(filtered_setups[:3]):  # Log top 3 setups
                self.Debug(f"Setup #{i+1}: Price {setup['price_level']:.2f}, "
                          f"Confluence {setup['timeframe_count']} timeframes, "
                          f"Score {setup['priority_score']:.1f}")
                          
        elif self.research_mode:
            self.Debug("No high-priority setups found (legacy)")
            
    def _convert_to_fvg_objects(self, fvgs: List[Dict], timeframe: int) -> List[FVG]:
        """
        Convert legacy FVG dictionaries to FVG objects.
        
        Args:
            fvgs: List of FVG dictionaries
            timeframe: Timeframe in minutes
            
        Returns:
            List of FVG objects
        """
        fvg_objects = []
        
        for fvg_dict in fvgs:
            try:
                # Convert dict to FVG object
                if isinstance(fvg_dict, dict):
                    fvg_obj = FVG(
                        type=FVGType.BULLISH if fvg_dict.get('type') == 'bullish' else FVGType.BEARISH,
                        time=fvg_dict.get('time', datetime.now()),
                        top=fvg_dict.get('top', 0.0),
                        bottom=fvg_dict.get('bottom', 0.0),
                        size=fvg_dict.get('size', 0.0),
                        timeframe=timeframe,
                        volume=fvg_dict.get('volume', 0),
                        strength=fvg_dict.get('strength', 0.5),
                        symbol="MNQ"
                    )
                    fvg_objects.append(fvg_obj)
                elif isinstance(fvg_dict, FVG):
                    fvg_objects.append(fvg_dict)
            except Exception as e:
                if self.research_mode:
                    self.Debug(f"Error converting FVG to object: {e}")
                    
        return fvg_objects
        
    def _filter_high_quality_setups(self, confluence_scores: List[ConfluenceScore]) -> List[ConfluenceScore]:
        """
        Filter for high-quality confluence setups.
        
        Args:
            confluence_scores: List of confluence scores
            
        Returns:
            List of high-quality confluence scores
        """
        # Filter for high-quality setups
        high_quality = []
        
        for cs in confluence_scores:
            # High quality criteria:
            # - Final score >= 0.6
            # - At least 5 timeframes
            # - Strong or very strong confluence level
            # - Volume confirmation (optional but preferred)
            
            if (cs.final_score >= 0.6 and 
                cs.total_timeframes >= 5 and 
                cs.confluence_level.value in ['strong', 'very_strong']):
                high_quality.append(cs)
                
        # Sort by final score (descending)
        high_quality.sort(key=lambda cs: cs.final_score, reverse=True)
        
        return high_quality
        
    def _apply_volume_confirmation_filter(self, setups: List[ConfluenceScore]) -> List[ConfluenceScore]:
        """
        Apply advanced volume confirmation filtering to setups.
        
        Args:
            setups: List of confluence scores
            
        Returns:
            List of volume-confirmed setups
        """
        volume_confirmed = []
        
        for setup in setups:
            # Multi-tier volume confirmation criteria:
            
            # Tier 1: Strong volume confirmation (volume_score >= 0.4)
            # - Automatic pass regardless of confluence score
            if setup.volume_score >= 0.4:
                volume_confirmed.append(setup)
                if self.research_mode:
                    self.Debug(f"Tier 1 volume confirmation: score {setup.volume_score:.3f}")
                continue
                
            # Tier 2: Moderate volume confirmation (0.2 <= volume_score < 0.4)
            # - Requires confluence_score >= 0.5
            if (setup.volume_score >= 0.2 and 
                setup.final_score >= 0.5):
                volume_confirmed.append(setup)
                if self.research_mode:
                    self.Debug(f"Tier 2 volume confirmation: volume {setup.volume_score:.3f}, confluence {setup.final_score:.3f}")
                continue
                
            # Tier 3: Exceptional confluence (final_score >= 0.8)
            # - Can pass with minimal volume confirmation (volume_score >= 0.1)
            if (setup.final_score >= 0.8 and 
                setup.volume_score >= 0.1):
                volume_confirmed.append(setup)
                if self.research_mode:
                    self.Debug(f"Tier 3 exceptional confluence: score {setup.final_score:.3f}, volume {setup.volume_score:.3f}")
                continue
                
            # Tier 4: Outstanding confluence (final_score >= 0.9)
            # - Can override volume requirement entirely
            if setup.final_score >= 0.9:
                volume_confirmed.append(setup)
                if self.research_mode:
                    self.Debug(f"Tier 4 outstanding confluence: score {setup.final_score:.3f} (volume override)")
                continue
                
            # Additional volume analysis using VolumeAnalyzer if available
            if COMPONENTS_AVAILABLE and self.volume_analyzer:
                volume_analysis = self._enhanced_volume_analysis(setup)
                if volume_analysis['passes_filter']:
                    volume_confirmed.append(setup)
                    if self.research_mode:
                        self.Debug(f"Enhanced volume confirmation: {volume_analysis['reason']}")
                        
        return volume_confirmed
        
    def _enhanced_volume_analysis(self, setup: ConfluenceScore) -> Dict[str, Any]:
        """
        Perform enhanced volume analysis using VolumeAnalyzer.
        
        Args:
            setup: Confluence score to analyze
            
        Returns:
            Enhanced volume analysis results
        """
        try:
            # Get volume analysis from confluence score
            volume_analysis = setup.get_volume_analysis()
            
            # Enhanced filtering criteria
            passes_filter = False
            reason = ""
            
            # Check for multiple timeframe volume confirmation
            if volume_analysis.get('confirmation_rate', 0) >= 0.6:  # 60% of timeframes confirm
                passes_filter = True
                reason = f"High timeframe confirmation rate: {volume_analysis.get('confirmation_rate', 0):.2f}"
                
            # Check for exceptional volume multiplier
            elif volume_analysis.get('max_multiplier', 0) >= 3.0:  # 3x+ volume on any timeframe
                passes_filter = True
                reason = f"Exceptional volume multiplier: {volume_analysis.get('max_multiplier', 0):.1f}x"
                
            # Check for consistent elevated volume
            elif (volume_analysis.get('avg_multiplier', 0) >= 1.5 and 
                  setup.total_timeframes >= 7):  # 1.5x avg volume with 7+ timeframes
                passes_filter = True
                reason = f"Consistent elevated volume: {volume_analysis.get('avg_multiplier', 0):.1f}x avg"
                
            # Check for volume anomaly presence
            elif volume_analysis.get('volume_anomaly'):
                anomaly = volume_analysis['volume_anomaly']
                if anomaly.get('severity', 'low') in ['medium', 'high']:
                    passes_filter = True
                    reason = f"Volume anomaly detected: {anomaly.get('severity', 'unknown')} severity"
                    
            return {
                'passes_filter': passes_filter,
                'reason': reason,
                'volume_analysis': volume_analysis
            }
            
        except Exception as e:
            if self.research_mode:
                self.Debug(f"Error in enhanced volume analysis: {e}")
            return {'passes_filter': False, 'reason': 'analysis_error'}
        
    def _filter_trade_opportunities_enhanced(self, setups: List[ConfluenceScore]) -> List[Dict]:
        """
        Filter trade opportunities using enhanced confluence scores.
        
        Args:
            setups: List of confluence scores
            
        Returns:
            List of filtered setup dictionaries
        """
        # Convert ConfluenceScore objects to setup dictionaries
        setup_dicts = []
        
        for cs in setups:
            setup_dict = {
                'price_level': cs.price_level,
                'timeframe_count': cs.total_timeframes,
                'final_score': cs.final_score,
                'volume_score': cs.volume_score,
                'base_score': cs.base_score,
                'ml_enhanced_score': cs.ml_enhanced_score,
                'confluence_level': cs.confluence_level.value,
                'dominant_timeframes': cs.dominant_timeframes,
                'is_high_quality': cs.is_high_quality(),
                'trade_recommendation': cs.get_trade_recommendation(),
                'timeframe_distribution': cs.get_timeframe_distribution(),
                'volume_analysis': cs.get_volume_analysis(),
                'confluence_score': cs  # Keep original object for reference
            }
            setup_dicts.append(setup_dict)
            
        # Check daily trade count
        today = self.Time.date()
        today_trades = [t for t in self.daily_trades if t.date() == today]
        
        # Maximum trades per day
        max_trades_per_day = 20
        min_trades_per_day = 5
        
        # Filter based on daily limits
        if len(today_trades) >= max_trades_per_day:
            return []  # Already at max trades for today
            
        # Sort by final score
        setup_dicts.sort(key=lambda x: x['final_score'], reverse=True)
        
        remaining_slots = max_trades_per_day - len(today_trades)
        return setup_dicts[:remaining_slots]
            
    def _find_confluence_areas(self, all_fvgs: List[Dict]) -> List[Dict]:
        """
        Find areas where FVGs from multiple timeframes overlap.
        
        Args:
            all_fvgs: List of all FVGs from all timeframes
            
        Returns:
            List of confluence areas with overlapping FVGs
        """
        confluence_areas = []
        
        # Group FVGs by price level (with tolerance)
        price_tolerance = 0.25  # MNQ tick size is 0.25
        
        for i, fvg1 in enumerate(all_fvgs):
            overlapping_fvgs = [fvg1]
            
            for j, fvg2 in enumerate(all_fvgs):
                if i >= j:  # Avoid duplicates
                    continue
                    
                # Check if FVGs overlap in price
                if self._fvgs_overlap(fvg1, fvg2, price_tolerance):
                    overlapping_fvgs.append(fvg2)
                    
            # Only keep areas with multiple timeframe confluence
            if len(overlapping_fvgs) >= self.confluence_threshold:
                # Get unique timeframes
                unique_timeframes = list(set(fvg['timeframe'] for fvg in overlapping_fvgs))
                
                confluence_area = {
                    'time': fvg1['time'],
                    'price_level': (fvg1['top'] + fvg1['bottom']) / 2,
                    'fvgs': overlapping_fvgs,
                    'timeframe_count': len(unique_timeframes),
                    'timeframes': unique_timeframes,
                    'confluence_score': self._calculate_confluence_score(overlapping_fvgs)
                }
                confluence_areas.append(confluence_area)
                
        return confluence_areas
        
    def _fvgs_overlap(self, fvg1: Dict, fvg2: Dict, tolerance: float) -> bool:
        """
        Check if two FVGs overlap in price.
        
        Args:
            fvg1: First FVG
            fvg2: Second FVG
            tolerance: Price tolerance for overlap
            
        Returns:
            True if FVGs overlap
        """
        # Check if price ranges overlap
        return not (fvg1['top'] + tolerance < fvg2['bottom'] - tolerance or 
                   fvg2['top'] + tolerance < fvg1['bottom'] - tolerance)
                   
    def _calculate_confluence_score(self, overlapping_fvgs: List[Dict]) -> float:
        """
        Calculate confluence score for overlapping FVGs.
        
        Args:
            overlapping_fvgs: List of overlapping FVGs
            
        Returns:
            Confluence score between 0 and 100
        """
        # Timeframe contribution (70% weight)
        unique_timeframes = len(set(fvg['timeframe'] for fvg in overlapping_fvgs))
        timeframe_score = (unique_timeframes / len(self.timeframes)) * 70
        
        # Volume contribution (30% weight)
        avg_volume = np.mean([fvg['volume'] for fvg in overlapping_fvgs])
        volume_score = min(avg_volume / 1000000 * 30, 30)  # Normalize volume contribution
        
        return timeframe_score + volume_score
        
    def _analyze_volume_confluence(self, confluence_areas: List[Dict]) -> List[Dict]:
        """
        Analyze volume patterns at confluence areas.
        
        Args:
            confluence_areas: List of confluence areas
            
        Returns:
            List of high-priority setups with volume confirmation
        """
        high_priority_setups = []
        
        for area in confluence_areas:
            # Get volume data around the confluence area
            volume_anomaly = self._detect_volume_anomaly(area)
            
            if volume_anomaly['is_anomaly']:
                setup = {
                    **area,
                    'volume_anomaly': volume_anomaly,
                    'priority_score': self._calculate_priority_score(area, volume_anomaly)
                }
                high_priority_setups.append(setup)
                
        return high_priority_setups
        
    def _detect_volume_anomaly(self, confluence_area: Dict) -> Dict:
        """
        Detect volume anomalies at confluence area.
        
        Args:
            confluence_area: Confluence area to analyze
            
        Returns:
            Volume anomaly information
        """
        # Get volume from the most recent timeframe (1-minute)
        timeframe_1 = 1
        if timeframe_1 not in self.volume_data or self.volume_data[timeframe_1].empty:
            return {'is_anomaly': False, 'multiplier': 0.0}
            
        volume_series = self.volume_data[timeframe_1]
        
        # Calculate volume moving average
        if len(volume_series) < self.volume_period:
            return {'is_anomaly': False, 'multiplier': 0.0}
            
        volume_ma = volume_series.tail(self.volume_period).mean()
        current_volume = volume_series.iloc[-1]
        
        # Check for volume anomaly (2x+ average)
        multiplier = current_volume / volume_ma if volume_ma > 0 else 0
        is_anomaly = multiplier >= self.volume_multiplier
        
        return {
            'is_anomaly': is_anomaly,
            'multiplier': multiplier,
            'current_volume': current_volume,
            'average_volume': volume_ma
        }
        
    def _calculate_priority_score(self, confluence_area: Dict, volume_anomaly: Dict) -> float:
        """
        Calculate overall priority score for a setup.
        
        Args:
            confluence_area: Confluence area information
            volume_anomaly: Volume anomaly information
            
        Returns:
            Priority score between 0 and 100
        """
        # Base confluence score (70% weight)
        confluence_weight = 0.7
        volume_weight = 0.3
        
        # Volume bonus for anomalies
        volume_bonus = min(volume_anomaly['multiplier'] / 5, 2.0)  # Cap at 2x bonus
        
        priority_score = (confluence_area['confluence_score'] * confluence_weight + 
                         volume_bonus * 50 * volume_weight)  # Volume bonus up to 100 points
                         
        return min(priority_score, 100)
        
    def _filter_trade_opportunities(self, setups: List[Dict]) -> List[Dict]:
        """
        Filter trade opportunities to maintain 5-20 trades per day.
        
        Args:
            setups: List of potential setups
            
        Returns:
            Filtered list of setups
        """
        # Sort by priority score
        sorted_setups = sorted(setups, key=lambda x: x['priority_score'], reverse=True)
        
        # Check daily trade count
        today = self.Time.date()
        today_trades = [t for t in self.daily_trades if t.date() == today]
        
        # Maximum trades per day
        max_trades_per_day = 20
        min_trades_per_day = 5
        
        # Filter based on daily limits
        if len(today_trades) >= max_trades_per_day:
            return []  # Already at max trades for today
            
        remaining_slots = max_trades_per_day - len(today_trades)
        return sorted_setups[:remaining_slots]
        
    def _daily_performance_analysis(self) -> None:
        """Perform daily performance analysis."""
        if self.research_mode:
            self.Debug(f"Daily performance analysis at {self.Time}")
            
        # Calculate daily metrics
        today = self.Time.date()
        today_trades = [t for t in self.daily_trades if t.date() == today]
        
        daily_metrics = {
            'date': today,
            'trade_count': len(today_trades),
            'setups_analyzed': len(self.performance_metrics.get('latest_setups', [])),
            'confluence_areas': len([s for s in self.performance_metrics.get('latest_setups', []) 
                                   if s.get('timeframe_count', 0) >= self.confluence_threshold])
        }
        
        # Store metrics
        if 'daily_metrics' not in self.performance_metrics:
            self.performance_metrics['daily_metrics'] = []
        self.performance_metrics['daily_metrics'].append(daily_metrics)
        
        # Log summary
        if self.research_mode:
            self.Debug(f"Daily Summary - Trades: {daily_metrics['trade_count']}, "
                      f"Setups: {daily_metrics['setups_analyzed']}, "
                      f"Confluence Areas: {daily_metrics['confluence_areas']}")
                      
            # Log additional daily statistics
            total_fvgs_today = sum(len(fvgs) for fvgs in self.fvg_data.values())
            active_timeframes = len([tf for tf, fvgs in self.fvg_data.items() if fvgs])
            self.Debug(f"FVG Summary - Total FVGs: {total_fvgs_today}, "
                      f"Active timeframes: {active_timeframes}/{len(self.timeframes)}")
                      
    def get_performance_metrics(self) -> Dict:
        """
        Get comprehensive performance metrics.
        
        Returns:
            Dictionary containing all performance metrics
        """
        return self.performance_metrics
        
    def get_fvg_data(self, timeframe: Optional[int] = None) -> Dict:
        """
        Get FVG data for specific timeframe or all timeframes.
        
        Args:
            timeframe: Specific timeframe to get data for, or None for all
            
        Returns:
            FVG data dictionary
        """
        if timeframe is not None:
            return {timeframe: self.fvg_data.get(timeframe, [])}
        return self.fvg_data
        
    def get_price_data(self, timeframe: Optional[int] = None) -> Dict:
        """
        Get price data for specific timeframe or all timeframes.
        
        Args:
            timeframe: Specific timeframe to get data for, or None for all
            
        Returns:
            Price data dictionary
        """
        if timeframe is not None:
            return {timeframe: self.price_data.get(timeframe, pd.DataFrame())}
        return self.price_data
        
    def _initialize_enhanced_components(self) -> None:
        """Initialize enhanced FVG components for real-time processing."""
        try:
            if not COMPONENTS_AVAILABLE:
                return
                
            # Initialize configuration
            self.config = StrategyConfig()
            self.timeframe_config = TimeframeConfig()
            
            # Initialize volume analyzer
            self.volume_analyzer = VolumeAnalyzer()
            
            # Initialize confluence scorer
            self.confluence_scorer = ConfluenceScorer(
                name="Main_Confluence_Scorer",
                timeframes=self.timeframes,
                volume_analyzer=self.volume_analyzer,
                config=self.config
            )
            
            # Initialize timeframe manager
            self.timeframe_manager = TimeframeManager(
                symbol=str(self.mnq_symbol) if self.mnq_symbol else "MNQ",
                config=self.timeframe_config
            )
            
            # Initialize FVG indicators for all timeframes
            for timeframe in self.timeframes:
                indicator = FairValueGapIndicator(
                    name=f"FVG_{timeframe}min",
                    timeframe=timeframe,
                    min_fvg_size=0.25,
                    enable_volume_filter=True,
                    enable_strength_filter=True,
                    min_strength_threshold=0.3
                )
                self.fvg_indicators[timeframe] = indicator
                
            self.Debug("Enhanced FVG components initialized successfully")
            self.Debug(f"Volume analyzer: {self.volume_analyzer is not None}")
            self.Debug(f"Confluence scorer: {self.confluence_scorer is not None}")
            
        except Exception as e:
            self.Error(f"Error initializing enhanced components: {e}")
            COMPONENTS_AVAILABLE = False