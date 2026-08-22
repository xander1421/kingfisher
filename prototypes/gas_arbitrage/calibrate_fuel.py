"""
Fuel Calibration System for MeTTa

Calibrates fuel weights based on simulated hardware costs to ensure fuel
costs accurately reflect wall-clock time and hardware strain.
"""

import random
import time
import json
import os
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from hardware_simulator import HardwareSimulator


@dataclass
class FuelWeight:
    """Represents a fuel weight for an operation."""
    base: int = 1
    cache_miss_penalty: int = 10
    tlb_miss_penalty: int = 5
    recursion_penalty: int = 5
    
    def to_dict(self) -> Dict[str, int]:
        return {
            "base": self.base,
            "cache_miss_penalty": self.cache_miss_penalty,
            "tlb_miss_penalty": self.tlb_miss_penalty,
            "recursion_penalty": self.recursion_penalty,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "FuelWeight":
        return cls(
            base=data.get("base", 1),
            cache_miss_penalty=data.get("cache_miss_penalty", 10),
            tlb_miss_penalty=data.get("tlb_miss_penalty", 5),
            recursion_penalty=data.get("recursion_penalty", 5),
        )


@dataclass
class CalibrationConfig:
    """Configuration for fuel calibration."""
    operations: List[str] = field(default_factory=lambda: [
        "ADD", "MUL", "SUB", "DIV",
        "UNIFY", "QUERY_ATOM", "MATCH",
        "RECURSE", "BIND", "CONS", "CAR", "CDR"
    ])
    iterations: int = 1000
    cache_size: int = 100
    tlb_size: int = 50
    target_correlation: float = 0.9  # Target fuel-time correlation
    learning_rate: float = 0.1
    output_file: str = "fuel_weights.json"


@dataclass
class CalibrationResult:
    """Result of a calibration run."""
    weights: Dict[str, FuelWeight]
    correlation: float
    improvement: float
    iterations: int
    time_elapsed: float


class FuelCalibrator:
    """
    Calibrates fuel weights to minimize the difference between fuel costs
    and actual hardware strain (wall-clock time).
    """
    
    def __init__(self, config: Optional[CalibrationConfig] = None):
        """
        Initialize the fuel calibrator.
        
        Args:
            config: Calibration configuration
        """
        self.config = config or CalibrationConfig()
        self.simulator = HardwareSimulator(
            cache_size=self.config.cache_size,
            tlb_size=self.config.tlb_size
        )
        self.weights: Dict[str, FuelWeight] = {}
        self.history: List[float] = []  # History of correlation values
        
        # Initialize with default weights
        self._initialize_weights()
        
    def _initialize_weights(self):
        """Initialize fuel weights with reasonable defaults."""
        # Simple operations
        self.weights["ADD"] = FuelWeight(base=1, cache_miss_penalty=1)
        self.weights["SUB"] = FuelWeight(base=1, cache_miss_penalty=1)
        self.weights["MUL"] = FuelWeight(base=2, cache_miss_penalty=2)
        self.weights["DIV"] = FuelWeight(base=3, cache_miss_penalty=3)
        
        # Complex operations (hypergraph-specific)
        self.weights["UNIFY"] = FuelWeight(base=100, cache_miss_penalty=10)
        self.weights["QUERY_ATOM"] = FuelWeight(base=50, cache_miss_penalty=8)
        self.weights["MATCH"] = FuelWeight(base=30, cache_miss_penalty=6)
        
        # Control flow
        self.weights["RECURSE"] = FuelWeight(base=20, recursion_penalty=5)
        self.weights["BIND"] = FuelWeight(base=15, cache_miss_penalty=3)
        
        # List operations
        self.weights["CONS"] = FuelWeight(base=5, cache_miss_penalty=2)
        self.weights["CAR"] = FuelWeight(base=2, cache_miss_penalty=1)
        self.weights["CDR"] = FuelWeight(base=2, cache_miss_penalty=1)
        
    def generate_test_context(self, op: str) -> Dict[str, Any]:
        """
        Generate a test context for a given operation.
        
        Args:
            op: Operation name
            
        Returns:
            Context dictionary with operation parameters
        """
        context: Dict[str, Any] = {}
        
        if op in ["UNIFY", "QUERY_ATOM", "MATCH"]:
            context["graph_depth"] = random.randint(1, 10)
            context["graph_width"] = random.randint(1, 20)
            context["atom_space_size"] = random.randint(100, 10000)
            
        elif op == "RECURSE":
            context["recursion_depth"] = random.randint(1, 10)
            
        return context
    
    def calculate_fuel(self, op: str, context: Dict[str, Any], 
                      result: Dict[str, Any]) -> int:
        """
        Calculate fuel cost for an operation based on current weights.
        
        Args:
            op: Operation name
            context: Operation context
            result: Hardware simulation result
            
        Returns:
            Calculated fuel cost
        """
        weight = self.weights.get(op, FuelWeight())
        
        # Base fuel
        fuel = weight.base
        
        # Add cache miss penalty
        fuel += result.get("cache_misses", 0) * weight.cache_miss_penalty
        
        # Add TLB miss penalty
        fuel += result.get("tlb_misses", 0) * weight.tlb_miss_penalty
        
        # Add recursion penalty
        if op == "RECURSE":
            recursion_depth = context.get("recursion_depth", 0)
            fuel += recursion_depth * weight.recursion_penalty
            
        return fuel
    
    def simulate_operation(self, op: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Simulate an operation and return both context and hardware results.
        
        Args:
            op: Operation name
            
        Returns:
            Tuple of (context, hardware_result)
        """
        context = self.generate_test_context(op)
        hardware_result = self.simulator.run_metta_op(
            op, context, 
            base_fuel={op: self.weights.get(op, FuelWeight()).base}
        )
        return context, hardware_result
    
    def calculate_correlation(self, data: List[Tuple[int, float]]) -> float:
        """
        Calculate Pearson correlation coefficient.
        
        Args:
            data: List of (fuel, time) tuples
            
        Returns:
            Correlation coefficient
        """
        if len(data) < 2:
            return 0.0
        
        n = len(data)
        sum_x = sum(p[0] for p in data)
        sum_y = sum(p[1] for p in data)
        sum_xy = sum(p[0] * p[1] for p in data)
        sum_x2 = sum(p[0] ** 2 for p in data)
        sum_y2 = sum(p[1] ** 2 for p in data)
        
        numerator = sum_xy - (sum_x * sum_y) / n
        denominator_x = (sum_x2 - (sum_x ** 2) / n) ** 0.5
        denominator_y = (sum_y2 - (sum_y ** 2) / n) ** 0.5
        
        if denominator_x == 0 or denominator_y == 0:
            return 0.0
        
        return numerator / (denominator_x * denominator_y)
    
    def adjust_weights(self, data: List[Tuple[int, float, str, Dict, Dict]]) -> None:
        """
        Adjust fuel weights based on calibration data.
        
        Args:
            data: List of (fuel, time, op, context, hardware_result) tuples
        """
        # Group by operation
        op_data: Dict[str, List[Tuple[int, float]]] = {}
        for fuel, wall_time, op, _, _ in data:
            if op not in op_data:
                op_data[op] = []
            op_data[op].append((fuel, wall_time))
        
        # Adjust weights for each operation
        for op, pairs in op_data.items():
            if op not in self.weights:
                self.weights[op] = FuelWeight()
            
            weight = self.weights[op]
            
            # Calculate current correlation for this operation
            correlation = self.calculate_correlation(pairs)
            
            # If correlation is low, increase the base fuel
            # If correlation is high but fuel is too low, increase penalties
            if correlation < self.config.target_correlation:
                # Increase base fuel
                weight.base = int(weight.base * (1 + self.config.learning_rate))
                
                # Also increase penalties if cache misses are high
                if any(p[1] > 0.01 for p in pairs):  # If any operation took significant time
                    weight.cache_miss_penalty = int(
                        weight.cache_miss_penalty * (1 + self.config.learning_rate * 0.5)
                    )
            else:
                # Fine-tune: if fuel is consistently higher than time would suggest, reduce
                avg_fuel = sum(p[0] for p in pairs) / len(pairs)
                avg_time = sum(p[1] for p in pairs) / len(pairs)
                
                # Simple heuristic: fuel should be roughly proportional to time
                # We want fuel to be in a reasonable range (e.g., 1-1000)
                if avg_fuel > 1000 and avg_time < 0.01:
                    weight.base = int(weight.base * (1 - self.config.learning_rate * 0.1))
        
    def calibrate(self) -> CalibrationResult:
        """
        Run calibration to find optimal fuel weights.
        
        Returns:
            CalibrationResult with optimized weights and statistics
        """
        start_time = time.time()
        best_weights = {op: FuelWeight.from_dict(self.weights[op].to_dict()) 
                        for op in self.weights}
        best_correlation = 0.0
        
        print("Starting fuel calibration...")
        print(f"Target correlation: {self.config.target_correlation}")
        print(f"Operations: {len(self.config.operations)}")
        print(f"Iterations: {self.config.iterations}")
        print("-" * 60)
        
        for iteration in range(self.config.iterations):
            # Collect data for this iteration
            data: List[Tuple[int, float, str, Dict, Dict]] = []
            
            # Test each operation multiple times
            for op in self.config.operations:
                context, hardware_result = self.simulate_operation(op)
                fuel = self.calculate_fuel(op, context, hardware_result)
                data.append((
                    fuel,
                    hardware_result["wall_time"],
                    op,
                    context,
                    hardware_result
                ))
            
            # Calculate overall correlation
            all_pairs = [(fuel, wall_time) for fuel, wall_time, _, _, _ in data]
            correlation = self.calculate_correlation(all_pairs)
            self.history.append(correlation)
            
            # Update best weights
            if correlation > best_correlation:
                best_correlation = correlation
                best_weights = {op: FuelWeight.from_dict(self.weights[op].to_dict()) 
                                for op in self.weights}
            
            # Adjust weights
            self.adjust_weights(data)
            
            # Print progress every 100 iterations
            if (iteration + 1) % 100 == 0:
                print(f"Iteration {iteration + 1}: correlation = {correlation:.4f}")
        
        elapsed = time.time() - start_time
        improvement = best_correlation - (self.history[0] if self.history else 0)
        
        print("-" * 60)
        print(f"Calibration complete in {elapsed:.2f}s")
        print(f"Initial correlation: {self.history[0] if self.history else 0:.4f}")
        print(f"Final correlation: {best_correlation:.4f}")
        print(f"Improvement: {improvement:.4f}")
        
        # Apply best weights
        self.weights = best_weights
        
        return CalibrationResult(
            weights=best_weights,
            correlation=best_correlation,
            improvement=improvement,
            iterations=self.config.iterations,
            time_elapsed=elapsed
        )
    
    def save_weights(self, filepath: Optional[str] = None):
        """
        Save calibrated weights to a JSON file.
        
        Args:
            filepath: Path to save file (defaults to config.output_file)
        """
        filepath = filepath or self.config.output_file
        
        weights_dict = {
            op: weight.to_dict() 
            for op, weight in self.weights.items()
        }
        
        with open(filepath, 'w') as f:
            json.dump(weights_dict, f, indent=2)
        
        print(f"Fuel weights saved to {filepath}")
        
    def load_weights(self, filepath: str):
        """
        Load fuel weights from a JSON file.
        
        Args:
            filepath: Path to load file
        """
        with open(filepath, 'r') as f:
            weights_dict = json.load(f)
        
        self.weights = {
            op: FuelWeight.from_dict(data)
            for op, data in weights_dict.items()
        }
        
        print(f"Fuel weights loaded from {filepath}")
    
    def print_weights(self):
        """Print current fuel weights in a readable format."""
        print("\n" + "=" * 60)
        print("CURRENT FUEL WEIGHTS")
        print("=" * 60)
        print(f"{'Operation':<15} {'Base':<8} {'Cache Penalty':<15} {'TLB Penalty':<12} {'Recursion':<10}")
        print("-" * 60)
        
        for op in sorted(self.weights.keys()):
            weight = self.weights[op]
            print(f"{op:<15} {weight.base:<8} {weight.cache_miss_penalty:<15} "
                  f"{weight.tlb_miss_penalty:<12} {weight.recursion_penalty:<10}")


# Example usage
if __name__ == "__main__":
    # Create calibrator
    calibrator = FuelCalibrator()
    
    # Configure (optional)
    calibrator.config.iterations = 500
    calibrator.config.target_correlation = 0.85
    calibrator.config.learning_rate = 0.15
    
    # Print initial weights
    calibrator.print_weights()
    
    # Run calibration
    result = calibrator.calibrate()
    
    # Print final weights
    calibrator.print_weights()
    
    # Save weights
    calibrator.save_weights()
    
    # Print calibration summary
    print("\n" + "=" * 60)
    print("CALIBRATION SUMMARY")
    print("=" * 60)
    print(f"Final correlation: {result.correlation:.4f}")
    print(f"Improvement: {result.improvement:.4f}")
    print(f"Time elapsed: {result.time_elapsed:.2f}s")
    print(f"Weights saved to: {calibrator.config.output_file}")
