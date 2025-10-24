"""
Adaptive Algorithm Parameter Tuner

Automatically tunes algorithm parameters based on backtest results
using machine learning and optimization techniques.
"""

import json
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))


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


class TuningStrategy(Enum):
    """Parameter tuning strategies"""
    GRID_SEARCH = "grid_search"
    BAYESIAN = "bayesian"
    GENETIC = "genetic"
    GRADIENT_ASCENT = "gradient_ascent"


@dataclass
class TuningConfig:
    """Configuration for adaptive tuning"""
    strategy: TuningStrategy
    max_iterations: int = 20
    convergence_threshold: float = 0.01
    exploration_rate: float = 0.3
    optimization_target: str = "composite_score"
    
    # Parameter bounds
    ml_confidence_range: Tuple[float, float] = (0.3, 0.8)
    volume_multiplier_range: Tuple[float, float] = (1.0, 3.0)
    confluence_score_range: Tuple[int, int] = (1, 6)
    risk_reward_range: Tuple[float, float] = (1.0, 3.0)
    stop_loss_range: Tuple[int, int] = (10, 30)


@dataclass
class TuningResult:
    """Result of tuning session"""
    best_parameters: ParameterSet
    best_score: float
    total_iterations: int
    convergence_achieved: bool
    optimization_history: List[Tuple[ParameterSet, float]]
    tuning_duration: timedelta
    improvement_percentage: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'best_parameters': self.best_parameters.to_dict(),
            'best_score': self.best_score,
            'total_iterations': self.total_iterations,
            'convergence_achieved': self.convergence_achieved,
            'optimization_history': [(params.to_dict(), score) for params, score in self.optimization_history],
            'tuning_duration_seconds': self.tuning_duration.total_seconds(),
            'improvement_percentage': self.improvement_percentage
        }


class AdaptiveTuner:
    """Adaptive parameter tuner using multiple optimization strategies"""
    
    def __init__(self, project_id: int, config: TuningConfig):
        self.project_id = project_id
        self.config = config
        self.logger = self._get_logger()
        
        # Tuning state
        self.current_iteration = 0
        self.best_score = float('-inf')
        self.best_parameters: Optional[ParameterSet] = None
        self.optimization_history: List[Tuple[ParameterSet, float]] = []
        self.consecutive_no_improvement = 0
        
    def _get_logger(self):
        """Simple logger for demonstration"""
        import logging
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)
    
    async def tune_parameters(self, initial_parameters: Optional[ParameterSet] = None) -> TuningResult:
        """Main tuning execution"""
        start_time = datetime.now()
        self.logger.info(f"Starting adaptive parameter tuning with strategy: {self.config.strategy.value}")
        
        # Initialize parameters
        if initial_parameters is None:
            initial_parameters = self._get_default_parameters()
        
        current_parameters = initial_parameters
        self.best_parameters = current_parameters
        
        # Evaluate initial parameters
        initial_score = await self._evaluate_parameters(current_parameters)
        self.best_score = initial_score
        self.optimization_history.append((current_parameters, initial_score))
        
        self.logger.info(f"Initial parameters score: {initial_score:.4f}")
        
        # Run optimization based on strategy
        if self.config.strategy == TuningStrategy.GRID_SEARCH:
            await self._grid_search_tuning()
        elif self.config.strategy == TuningStrategy.BAYESIAN:
            await self._bayesian_tuning()
        elif self.config.strategy == TuningStrategy.GENETIC:
            await self._genetic_tuning()
        elif self.config.strategy == TuningStrategy.GRADIENT_ASCENT:
            await self._gradient_ascent_tuning(current_parameters)
        
        # Calculate results
        tuning_duration = datetime.now() - start_time
        improvement = ((self.best_score - initial_score) / abs(initial_score)) * 100 if initial_score != 0 else 0
        
        result = TuningResult(
            best_parameters=self.best_parameters,
            best_score=self.best_score,
            total_iterations=self.current_iteration,
            convergence_achieved=self.consecutive_no_improvement >= 5,
            optimization_history=self.optimization_history,
            tuning_duration=tuning_duration,
            improvement_percentage=improvement
        )
        
        self.logger.info(f"Tuning completed. Best score: {self.best_score:.4f}, Improvement: {improvement:.1f}%")
        
        return result
    
    def _get_default_parameters(self) -> ParameterSet:
        """Get default parameter set"""
        return ParameterSet(
            ml_confidence_threshold=0.55,
            volume_anomaly_multiplier=1.75,
            min_confluence_score=3,
            risk_reward_ratio=2.0,
            stop_loss_ticks=20,
            take_profit_ticks=40
        )
    
    async def _evaluate_parameters(self, parameters: ParameterSet) -> float:
        """Evaluate parameter set by running backtest"""
        # Simulate evaluation for demonstration
        # In real implementation, this would run actual backtests
        
        # Simulate some realistic scoring based on parameters
        base_score = 0.5
        
        # Reward lower ML confidence (more trades)
        ml_score = (0.8 - parameters.ml_confidence_threshold) * 0.3
        
        # Reward moderate volume multiplier
        vol_score = 1.0 - abs(parameters.volume_anomaly_multiplier - 1.5) * 0.2
        
        # Reward moderate confluence score
        conf_score = 1.0 - abs(parameters.min_confluence_score - 3) * 0.1
        
        # Add some randomness
        noise = np.random.normal(0, 0.05)
        
        total_score = base_score + ml_score + vol_score + conf_score + noise
        total_score = max(0, min(1, total_score))  # Clamp to [0, 1]
        
        self.logger.info(f"Iteration {self.current_iteration}: Score = {total_score:.4f}")
        
        # Simulate processing time
        await asyncio.sleep(1)
        
        return total_score
    
    async def _grid_search_tuning(self):
        """Grid search optimization"""
        # Generate parameter combinations
        ml_values = np.linspace(self.config.ml_confidence_range[0], self.config.ml_confidence_range[1], 5)
        vol_values = np.linspace(self.config.volume_multiplier_range[0], self.config.volume_multiplier_range[1], 4)
        conf_values = range(self.config.confluence_score_range[0], self.config.confluence_score_range[1] + 1)
        
        combinations = []
        for ml in ml_values:
            for vol in vol_values:
                for conf in conf_values:
                    params = ParameterSet(
                        ml_confidence_threshold=ml,
                        volume_anomaly_multiplier=vol,
                        min_confluence_score=conf,
                        risk_reward_ratio=2.0,
                        stop_loss_ticks=20,
                        take_profit_ticks=40
                    )
                    combinations.append(params)
        
        # Evaluate combinations
        for i, params in enumerate(combinations[:self.config.max_iterations]):
            self.current_iteration += 1
            
            score = await self._evaluate_parameters(params)
            self.optimization_history.append((params, score))
            
            if score > self.best_score:
                self.best_score = score
                self.best_parameters = params
                self.consecutive_no_improvement = 0
            else:
                self.consecutive_no_improvement += 1
            
            if self.consecutive_no_improvement >= 5:
                break
    
    async def _bayesian_tuning(self):
        """Bayesian optimization (simplified version)"""
        current_params = self.best_parameters
        
        for iteration in range(self.config.max_iterations):
            self.current_iteration += 1
            
            # Generate new parameters with exploration/exploitation balance
            if np.random.random() < self.config.exploration_rate:
                # Exploration: random parameters
                new_params = self._generate_random_parameters()
            else:
                # Exploitation: perturb best parameters
                new_params = self._perturb_parameters(current_params or self._get_default_parameters())
            
            score = await self._evaluate_parameters(new_params)
            self.optimization_history.append((new_params, score))
            
            if score > self.best_score:
                self.best_score = score
                self.best_parameters = new_params
                current_params = new_params
                self.consecutive_no_improvement = 0
            else:
                self.consecutive_no_improvement += 1
            
            if self.consecutive_no_improvement >= 5:
                break
    
    async def _genetic_tuning(self):
        """Genetic algorithm optimization"""
        population_size = 8
        mutation_rate = 0.2
        crossover_rate = 0.7
        
        # Initialize population
        population = [self._generate_random_parameters() for _ in range(population_size)]
        
        for generation in range(self.config.max_iterations):
            self.current_iteration += 1
            
            # Evaluate population
            scores = []
            for params in population:
                score = await self._evaluate_parameters(params)
                scores.append(score)
                self.optimization_history.append((params, score))
                
                if score > self.best_score:
                    self.best_score = score
                    self.best_parameters = params
            
            # Selection (elitism)
            sorted_population = [p for _, p in sorted(zip(scores, population), key=lambda x: x[0], reverse=True)]
            elite = sorted_population[:2]
            
            # Crossover and mutation
            new_population = elite
            
            while len(new_population) < population_size:
                if np.random.random() < crossover_rate and len(elite) >= 2:
                    # Crossover
                    parent1, parent2 = elite[0], elite[1]  # Simple selection
                    child = self._crossover_parameters(parent1, parent2)
                else:
                    # Random selection
                    child = population[np.random.randint(len(population))]
                
                # Mutation
                if np.random.random() < mutation_rate:
                    child = self._perturb_parameters(child)
                
                new_population.append(child)
            
            population = new_population
            
            if self.consecutive_no_improvement >= 5:
                break
    
    async def _gradient_ascent_tuning(self, initial_parameters: ParameterSet):
        """Gradient ascent optimization"""
        current_params = initial_parameters
        learning_rate = 0.1
        
        for iteration in range(self.config.max_iterations):
            self.current_iteration += 1
            
            # Simple gradient approximation
            new_params = self._perturb_parameters(current_params)
            
            # Evaluate new parameters
            score = await self._evaluate_parameters(new_params)
            self.optimization_history.append((new_params, score))
            
            if score > self.best_score:
                self.best_score = score
                self.best_parameters = new_params
                current_params = new_params
                self.consecutive_no_improvement = 0
            else:
                self.consecutive_no_improvement += 1
                learning_rate *= 0.9  # Decay learning rate
            
            if self.consecutive_no_improvement >= 5:
                break
    
    def _generate_random_parameters(self) -> ParameterSet:
        """Generate random parameter set within bounds"""
        return ParameterSet(
            ml_confidence_threshold=np.random.uniform(*self.config.ml_confidence_range),
            volume_anomaly_multiplier=np.random.uniform(*self.config.volume_multiplier_range),
            min_confluence_score=np.random.randint(*self.config.confluence_score_range),
            risk_reward_ratio=np.random.uniform(*self.config.risk_reward_range),
            stop_loss_ticks=np.random.randint(*self.config.stop_loss_range),
            take_profit_ticks=40  # Will be calculated based on risk_reward_ratio
        )
    
    def _perturb_parameters(self, params: ParameterSet) -> ParameterSet:
        """Perturb parameters slightly"""
        return ParameterSet(
            ml_confidence_threshold=np.clip(
                params.ml_confidence_threshold + np.random.normal(0, 0.05),
                *self.config.ml_confidence_range
            ),
            volume_anomaly_multiplier=np.clip(
                params.volume_anomaly_multiplier + np.random.normal(0, 0.2),
                *self.config.volume_multiplier_range
            ),
            min_confluence_score=np.clip(
                params.min_confluence_score + np.random.randint(-1, 2),
                *self.config.confluence_score_range
            ),
            risk_reward_ratio=np.clip(
                params.risk_reward_ratio + np.random.normal(0, 0.2),
                *self.config.risk_reward_range
            ),
            stop_loss_ticks=np.clip(
                params.stop_loss_ticks + np.random.randint(-3, 4),
                *self.config.stop_loss_range
            ),
            take_profit_ticks=int(params.stop_loss_ticks * params.risk_reward_ratio)
        )
    
    def _crossover_parameters(self, parent1: ParameterSet, parent2: ParameterSet) -> ParameterSet:
        """Crossover two parameter sets"""
        return ParameterSet(
            ml_confidence_threshold=(parent1.ml_confidence_threshold + parent2.ml_confidence_threshold) / 2,
            volume_anomaly_multiplier=(parent1.volume_anomaly_multiplier + parent2.volume_anomaly_multiplier) / 2,
            min_confluence_score=np.random.choice([parent1.min_confluence_score, parent2.min_confluence_score]),
            risk_reward_ratio=(parent1.risk_reward_ratio + parent2.risk_reward_ratio) / 2,
            stop_loss_ticks=np.random.choice([parent1.stop_loss_ticks, parent2.stop_loss_ticks]),
            take_profit_ticks=40  # Will be calculated
        )
    
    def save_tuning_results(self, result: TuningResult, filename: Optional[str] = None):
        """Save tuning results to file"""
        if filename is None:
            filename = f"adaptive_tuning_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        
        self.logger.info(f"Tuning results saved to {filename}")
        return filename


async def main():
    """Example usage"""
    PROJECT_ID = 25780050
    
    # Configure tuning
    config = TuningConfig(
        strategy=TuningStrategy.BAYESIAN,
        max_iterations=10,
        optimization_target="composite_score"
    )
    
    # Create tuner
    tuner = AdaptiveTuner(PROJECT_ID, config)
    
    # Run tuning
    result = await tuner.tune_parameters()
    
    print("Tuning Results:")
    print(f"Best Score: {result.best_score:.4f}")
    print(f"Best Parameters: {result.best_parameters.to_dict()}")
    print(f"Improvement: {result.improvement_percentage:.1f}%")
    
    # Save results
    results_file = tuner.save_tuning_results(result)
    print(f"Results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())