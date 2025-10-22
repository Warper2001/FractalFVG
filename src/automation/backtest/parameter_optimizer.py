"""
Automated Parameter Optimization for MNQ FVG ML Algorithm

Implements grid search optimization for key algorithm parameters to address
conservative trade generation and improve performance.
"""

import json
import time
import asyncio
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import sys
import os

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Use absolute imports from project root
from src.utils.api_client import QuantConnectAPIClient
from src.utils.logger import get_logger
from src.utils.credential_manager import get_quantconnect_credential_manager


@dataclass
class ParameterSet:
    """Parameter configuration for optimization"""
    ml_confidence_threshold: float
    volume_anomaly_multiplier: float
    min_confluence_score: int
    risk_reward_ratio: float
    stop_loss_ticks: int
    take_profit_ticks: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ml_confidence_threshold": self.ml_confidence_threshold,
            "volume_anomaly_multiplier": self.volume_anomaly_multiplier,
            "min_confluence_score": self.min_confluence_score,
            "risk_reward_ratio": self.risk_reward_ratio,
            "stop_loss_ticks": self.stop_loss_ticks,
            "take_profit_ticks": self.take_profit_ticks
        }


@dataclass
class OptimizationResult:
    """Results from a single parameter set backtest"""
    parameter_set: ParameterSet
    backtest_id: str
    trades: int
    win_rate: Optional[float]
    sharpe_ratio: Optional[float]
    net_profit: Optional[float]
    max_drawdown: Optional[float]
    completion_time: datetime
    
    def score(self) -> float:
        """Calculate optimization score"""
        if self.trades == 0:
            return 0.0
        
        # Weighted score: trades (40%), win_rate (30%), sharpe (30%)
        trade_score = min(self.trades / 50.0, 1.0) * 0.4  # Normalize to 50 trades max
        win_rate_score = (self.win_rate or 0.0) * 0.3
        sharpe_score = min((self.sharpe_ratio or 0.0) / 2.0, 1.0) * 0.3  # Normalize to 2.0 max
        
        return trade_score + win_rate_score + sharpe_score


class ParameterOptimizer:
    """Automated parameter optimization engine"""
    
    def __init__(self, project_id: int, client: Optional[QuantConnectAPIClient] = None):
        self.project_id = project_id
        if client:
            self.client = client
        else:
            # Get credentials from credential manager
            cred_manager = get_quantconnect_credential_manager()
            user_id, api_token, organization_id = cred_manager.get_quantconnect_credentials()
            self.client = QuantConnectAPIClient(
                user_id=user_id,
                api_token=api_token,
                organization_id=organization_id
            )
        self.logger = get_logger()
        self.results: List[OptimizationResult] = []
        
    def generate_parameter_grid(self) -> List[ParameterSet]:
        """Generate parameter grid for optimization"""
        parameter_sets = []
        
        # ML confidence thresholds (conservative to aggressive)
        ml_thresholds = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
        
        # Volume anomaly multipliers
        volume_multipliers = [1.25, 1.5, 1.75, 2.0, 2.25]
        
        # Minimum confluence scores
        confluence_scores = [2, 3, 4, 5]
        
        # Risk/reward ratios
        risk_rewards = [1.5, 2.0, 2.5]
        
        # Stop loss/take profit combinations
        stop_loss_options = [15, 20, 25]
        take_profit_options = [30, 40, 50, 60]
        
        # Generate combinations (focus on most promising ranges)
        for ml_thresh in ml_thresholds:
            for vol_mult in volume_multipliers:
                for conf_score in confluence_scores:
                    for rr_ratio in risk_rewards:
                        for sl_ticks in stop_loss_options:
                            tp_ticks = int(sl_ticks * rr_ratio)
                            if tp_ticks in take_profit_options:
                                param_set = ParameterSet(
                                    ml_confidence_threshold=ml_thresh,
                                    volume_anomaly_multiplier=vol_mult,
                                    min_confluence_score=conf_score,
                                    risk_reward_ratio=rr_ratio,
                                    stop_loss_ticks=sl_ticks,
                                    take_profit_ticks=tp_ticks
                                )
                                parameter_sets.append(param_set)
        
        # Limit to top 50 combinations for manageable optimization
        return parameter_sets[:50]
    
    async def run_single_backtest(self, param_set: ParameterSet, compile_id: str) -> OptimizationResult:
        """Run single backtest with given parameters"""
        try:
            # Create backtest with parameters
            backtest_name = f"Optimization - ML:{param_set.ml_confidence_threshold:.2f} - Vol:{param_set.volume_anomaly_multiplier:.2f}"
            
            backtest_result = self.client.create_backtest(
                project_id=self.project_id,
                compile_id=compile_id,
                backtest_name=backtest_name,
                parameters=param_set.to_dict()
            )
            
            if not backtest_result.get('success'):
                raise Exception(f"Failed to create backtest: {backtest_result}")
            
            backtest_id = backtest_result['backtestId']
            self.logger.info(f"Started backtest {backtest_id} with parameters: {param_set.to_dict()}")
            
            # Monitor completion
            await self._monitor_backtest_completion(backtest_id)
            
            # Get results
            orders_result = self.client.read_backtest_orders(self.project_id, backtest_id, 0, 1000)
            trades = len(orders_result.get('orders', []))
            
            # Get detailed statistics
            backtest_stats = self._get_backtest_statistics(backtest_id)
            
            result = OptimizationResult(
                parameter_set=param_set,
                backtest_id=backtest_id,
                trades=trades,
                win_rate=backtest_stats.get('winRate'),
                sharpe_ratio=backtest_stats.get('sharpeRatio'),
                net_profit=backtest_stats.get('netProfit'),
                max_drawdown=backtest_stats.get('drawdown'),
                completion_time=datetime.now()
            )
            
            self.logger.info(f"Backtest {backtest_id} completed: {trades} trades, score: {result.score():.3f}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error running backtest for parameters {param_set.to_dict()}: {e}")
            # Return failed result
            return OptimizationResult(
                parameter_set=param_set,
                backtest_id="failed",
                trades=0,
                win_rate=0.0,
                sharpe_ratio=0.0,
                net_profit=0.0,
                max_drawdown=0.0,
                completion_time=datetime.now()
            )
    
    async def _monitor_backtest_completion(self, backtest_id: str, timeout_minutes: int = 30):
        """Monitor backtest until completion"""
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while True:
            try:
                # Check backtest status
                backtest_result = self.client.read_backtest(self.project_id, backtest_id)
                
                if backtest_result.get('completed', False):
                    self.logger.info(f"Backtest {backtest_id} completed successfully")
                    return
                
                progress = backtest_result.get('progress', 0)
                self.logger.info(f"Backtest {backtest_id} progress: {progress:.1%}")
                
                # Check timeout
                if time.time() - start_time > timeout_seconds:
                    raise Exception(f"Backtest {backtest_id} timed out after {timeout_minutes} minutes")
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error monitoring backtest {backtest_id}: {e}")
                await asyncio.sleep(30)
    
    def _get_backtest_statistics(self, backtest_id: str) -> Dict[str, Any]:
        """Extract backtest statistics"""
        try:
            backtest_result = self.client.read_backtest(self.project_id, backtest_id)
            return {
                'winRate': backtest_result.get('winRate'),
                'sharpeRatio': backtest_result.get('sharpeRatio'),
                'netProfit': backtest_result.get('netProfit'),
                'drawdown': backtest_result.get('drawdown')
            }
        except Exception as e:
            self.logger.error(f"Error getting statistics for backtest {backtest_id}: {e}")
            return {}
    
    async def run_optimization(self, compile_id: str, max_concurrent: int = 3) -> List[OptimizationResult]:
        """Run full parameter optimization"""
        self.logger.info("Starting parameter optimization...")
        
        parameter_sets = self.generate_parameter_grid()
        self.logger.info(f"Generated {len(parameter_sets)} parameter combinations")
        
        # Run optimization in batches to manage API limits
        results = []
        batch_size = max_concurrent
        
        for i in range(0, len(parameter_sets), batch_size):
            batch = parameter_sets[i:i + batch_size]
            self.logger.info(f"Running batch {i//batch_size + 1}/{(len(parameter_sets) + batch_size - 1)//batch_size}")
            
            # Run batch concurrently
            tasks = [self.run_single_backtest(param_set, compile_id) for param_set in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and add valid results
            for result in batch_results:
                if isinstance(result, OptimizationResult):
                    results.append(result)
                else:
                    self.logger.error(f"Batch result error: {result}")
            
            # Brief pause between batches to respect rate limits
            if i + batch_size < len(parameter_sets):
                await asyncio.sleep(10)
        
        self.results = results
        self.logger.info(f"Optimization completed. {len(results)} results collected.")
        
        return results
    
    def get_best_parameters(self, top_n: int = 5) -> List[Tuple[ParameterSet, float]]:
        """Get top N parameter sets by optimization score"""
        scored_results = [(result.parameter_set, result.score()) for result in self.results]
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return scored_results[:top_n]
    
    def save_results(self, filename: Optional[str] = None):
        """Save optimization results to file"""
        if filename is None:
            filename = f"optimization_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        results_data = {
            'timestamp': datetime.now().isoformat(),
            'project_id': self.project_id,
            'total_results': len(self.results),
            'results': [
                {
                    'parameters': result.parameter_set.to_dict(),
                    'backtest_id': result.backtest_id,
                    'trades': result.trades,
                    'win_rate': result.win_rate,
                    'sharpe_ratio': result.sharpe_ratio,
                    'net_profit': result.net_profit,
                    'max_drawdown': result.max_drawdown,
                    'score': result.score(),
                    'completion_time': result.completion_time.isoformat()
                }
                for result in self.results
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        self.logger.info(f"Optimization results saved to {filename}")
        return filename


async def main():
    """Main optimization execution"""
    # Configuration
    PROJECT_ID = 25780050
    
    optimizer = ParameterOptimizer(PROJECT_ID)
    
    # Get latest compile ID
    compile_result = optimizer.client.compile_project(PROJECT_ID)
    if not compile_result.get('success'):
        raise Exception(f"Failed to compile project: {compile_result}")
    
    compile_id = compile_result['compileId']
    print(f"Using compile ID: {compile_id}")
    
    # Run optimization
    results = await optimizer.run_optimization(compile_id, max_concurrent=2)
    
    # Get best parameters
    best_params = optimizer.get_best_parameters(5)
    print("\nTop 5 Parameter Sets:")
    for i, (params, score) in enumerate(best_params, 1):
        print(f"{i}. Score: {score:.3f}")
        print(f"   Parameters: {params.to_dict()}")
    
    # Save results
    results_file = optimizer.save_results()
    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())