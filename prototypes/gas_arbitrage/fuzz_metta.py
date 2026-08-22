"""
Fuzz Testing Framework for MeTTa

Generates adversarial hypergraphs to test fuel vs. wall-clock time correlation.
This helps identify operations where fuel costs don't reflect actual hardware strain.
"""

import random
import time
import sys
from typing import Optional, Dict, Any, List, Callable

# Try to import the actual MeTTa interpreter if available
try:
    from metta_interpreter import interpret, FuelExhaustedError
    METTA_AVAILABLE = True
except ImportError:
    METTA_AVAILABLE = False
    
    # Mock interpreter for testing without actual MeTTa
    class FuelExhaustedError(Exception):
        pass
    
    class MockInterpreter:
        last_fuel_used = 0
        
        @staticmethod
        def interpret(program: str, fuel_limit: int = 10000) -> Any:
            """Mock interpretation that consumes fuel based on program complexity."""
            # Simple fuel estimation based on program length and structure
            fuel = len(program)
            fuel += program.count('(') * 10
            fuel += program.count('unify') * 100
            fuel += program.count('recurse') * 50
            fuel += program.count('lambda') * 30
            
            MockInterpreter.last_fuel_used = fuel
            
            if fuel > fuel_limit:
                raise FuelExhaustedError(f"Fuel exhausted: {fuel} > {fuel_limit}")
            
            return "OK"
    
    interpret = MockInterpreter.interpret


class FuzzConfig:
    """Configuration for fuzz testing."""
    
    def __init__(self):
        self.max_depth = 10
        self.max_width = 10
        self.max_atoms = 1000
        self.max_recursion = 5
        self.fuel_limit = 10000
        self.iterations = 100
        self.timeout_seconds = 5
        

class FuzzResult:
    """Result of a single fuzz test iteration."""
    
    def __init__(self, iteration: int, program: str, fuel_used: int, 
                 wall_time: float, status: str, error: Optional[str] = None):
        self.iteration = iteration
        self.program = program
        self.fuel_used = fuel_used
        self.wall_time = wall_time
        self.status = status  # "OK", "FUEL_EXHAUSTED", "ERROR", "TIMEOUT"
        self.error = error
        
    def __repr__(self):
        return (f"FuzzResult(iter={self.iteration}, status={self.status}, "
                f"fuel={self.fuel_used}, time={self.wall_time:.6f}s)")


class FuzzTester:
    """
    Fuzz tester for MeTTa programs.
    
    Generates adversarial hypergraphs and tests fuel consumption vs. wall-clock time.
    """
    
    def __init__(self, config: Optional[FuzzConfig] = None):
        """
        Initialize the fuzz tester.
        
        Args:
            config: Fuzz configuration (defaults to reasonable values)
        """
        self.config = config or FuzzConfig()
        self.results: List[FuzzResult] = []
        self.adversarial_patterns: List[str] = []
        
    def generate_adversarial_hypergraph(self, max_depth: Optional[int] = None,
                                         max_width: Optional[int] = None) -> str:
        """
        Generate a hypergraph designed to trigger worst-case behavior.
        
        Args:
            max_depth: Maximum recursion depth
            max_width: Maximum branching factor
            
        Returns:
            MeTTa program string
        """
        depth = max_depth or self.config.max_depth
        width = max_width or self.config.max_width
        
        if depth <= 0:
            return "()"
        
        # Randomly choose a structure designed to be adversarial
        structure = random.choices(
            [
                "unification_heavy",  # Deep recursion + wide unification
                "pointer_chasing",    # Long chains of atom references
                "memory_hog",         # Large atom space
                "deep_recursion",     # Deeply nested operations
                "wide_branching",     # Many parallel operations
            ],
            weights=[30, 25, 20, 15, 10],  # Weight towards more expensive ops
            k=1
        )[0]
        
        if structure == "unification_heavy":
            # Generate a deeply nested unification
            if depth <= 1:
                return "(unify a b)"
            left = self.generate_adversarial_hypergraph(depth - 1, width)
            right = self.generate_adversarial_hypergraph(depth - 1, width)
            return f"(unify {left} {right})"
            
        elif structure == "pointer_chasing":
            # Generate a long chain of references
            if depth <= 1:
                return f"(atom {random.randint(0, self.config.max_atoms)})"
            inner = self.generate_adversarial_hypergraph(depth - 1, width)
            return f"(ref {inner})"
            
        elif structure == "memory_hog":
            # Generate a large atom space with many unique atoms
            num_atoms = min(random.randint(100, self.config.max_atoms), self.config.max_atoms)
            atoms = [f"(atom {random.randint(0, 1000000)})" for _ in range(num_atoms)]
            return f"(and {' '.join(atoms)})"
            
        elif structure == "deep_recursion":
            # Generate deeply nested lambda/recursion
            if depth <= 1:
                return "(lambda (x) x)"
            inner = self.generate_adversarial_hypergraph(depth - 1, width)
            return f"(lambda (x) ({inner} x))"
            
        elif structure == "wide_branching":
            # Generate many parallel operations
            num_ops = min(width, 20)  # Limit width for practicality
            ops = []
            for _ in range(num_ops):
                op = random.choice(["unify", "match", "query"])
                arg1 = f"(atom {random.randint(0, 1000)})"
                arg2 = f"(atom {random.randint(0, 1000)})"
                ops.append(f"({op} {arg1} {arg2})")
            return f"(do {' '.join(ops)})"
        
        return "()"
    
    def measure_wall_time(self, func: Callable, *args, **kwargs) -> tuple:
        """
        Measure wall-clock time for a function call.
        
        Args:
            func: Function to measure
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Tuple of (result, time_in_seconds)
        """
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            return result, end_time - start_time
        except Exception as e:
            end_time = time.time()
            raise e
    
    def run_iteration(self, iteration: int) -> FuzzResult:
        """
        Run a single fuzz test iteration.
        
        Args:
            iteration: Iteration number
            
        Returns:
            FuzzResult with test outcome
        """
        # Generate adversarial program
        program = self.generate_adversarial_hypergraph()
        
        try:
            # Measure wall-clock time
            result, wall_time = self.measure_wall_time(
                interpret,
                program,
                fuel_limit=self.config.fuel_limit
            )
            
            # Get fuel used (from mock or real interpreter)
            fuel_used = getattr(interpret, 'last_fuel_used', 0)
            
            return FuzzResult(
                iteration=iteration,
                program=program,
                fuel_used=fuel_used,
                wall_time=wall_time,
                status="OK"
            )
            
        except FuelExhaustedError as e:
            fuel_used = getattr(interpret, 'last_fuel_used', self.config.fuel_limit + 1)
            return FuzzResult(
                iteration=iteration,
                program=program,
                fuel_used=fuel_used,
                wall_time=0.0,  # Fuel exhausted before completion
                status="FUEL_EXHAUSTED",
                error=str(e)
            )
            
        except TimeoutError:
            return FuzzResult(
                iteration=iteration,
                program=program,
                fuel_used=self.config.fuel_limit,
                wall_time=self.config.timeout_seconds,
                status="TIMEOUT",
                error="Operation timed out"
            )
            
        except Exception as e:
            return FuzzResult(
                iteration=iteration,
                program=program,
                fuel_used=0,
                wall_time=0.0,
                status="ERROR",
                error=str(e)
            )
    
    def run(self, iterations: Optional[int] = None) -> List[FuzzResult]:
        """
        Run fuzz testing for the specified number of iterations.
        
        Args:
            iterations: Number of iterations (defaults to config.iterations)
            
        Returns:
            List of FuzzResult objects
        """
        iterations = iterations or self.config.iterations
        self.results = []
        
        print(f"Running {iterations} fuzz test iterations...")
        print("-" * 60)
        
        for i in range(iterations):
            try:
                result = self.run_iteration(i)
                self.results.append(result)
                
                # Print progress
                status_symbol = {
                    "OK": "✓",
                    "FUEL_EXHAUSTED": "⚠",
                    "ERROR": "✗",
                    "TIMEOUT": "⏰"
                }.get(result.status, "?")
                
                print(f"Iteration {i}: {status_symbol} {result.status} "
                      f"(fuel: {result.fuel_used}, time: {result.wall_time:.6f}s)")
                
                # Save adversarial patterns (high fuel or long time)
                if result.fuel_used > self.config.fuel_limit * 0.8 or result.wall_time > 0.1:
                    self.adversarial_patterns.append(result.program)
                    
            except KeyboardInterrupt:
                print(f"\nStopped after {i} iterations")
                break
            except Exception as e:
                print(f"Iteration {i}: CRASH - {e}")
                self.results.append(FuzzResult(
                    iteration=i,
                    program="",
                    fuel_used=0,
                    wall_time=0.0,
                    status="CRASH",
                    error=str(e)
                ))
        
        return self.results
    
    def analyze_results(self) -> Dict[str, Any]:
        """
        Analyze fuzz test results.
        
        Returns:
            Dictionary with analysis statistics
        """
        if not self.results:
            return {"error": "No results to analyze"}
        
        # Count statuses
        status_counts = {}
        for result in self.results:
            status_counts[result.status] = status_counts.get(result.status, 0) + 1
        
        # Calculate fuel statistics
        fuels = [r.fuel_used for r in self.results if r.fuel_used > 0]
        times = [r.wall_time for r in self.results if r.wall_time > 0]
        
        # Correlation between fuel and time
        fuel_time_pairs = [(r.fuel_used, r.wall_time) for r in self.results 
                          if r.fuel_used > 0 and r.wall_time > 0]
        
        return {
            "total_iterations": len(self.results),
            "status_counts": status_counts,
            "fuel_stats": {
                "min": min(fuels) if fuels else 0,
                "max": max(fuels) if fuels else 0,
                "avg": sum(fuels) / len(fuels) if fuels else 0,
                "median": sorted(fuels)[len(fuels) // 2] if fuels else 0,
            },
            "time_stats": {
                "min": min(times) if times else 0,
                "max": max(times) if times else 0,
                "avg": sum(times) / len(times) if times else 0,
            },
            "fuel_time_correlation": self._calculate_correlation(fuel_time_pairs),
            "adversarial_patterns_found": len(self.adversarial_patterns),
        }
    
    def _calculate_correlation(self, pairs: List[tuple]) -> float:
        """
        Calculate Pearson correlation coefficient between fuel and time.
        
        Args:
            pairs: List of (fuel, time) tuples
            
        Returns:
            Correlation coefficient (-1 to 1)
        """
        if len(pairs) < 2:
            return 0.0
        
        n = len(pairs)
        sum_x = sum(p[0] for p in pairs)
        sum_y = sum(p[1] for p in pairs)
        sum_xy = sum(p[0] * p[1] for p in pairs)
        sum_x2 = sum(p[0] ** 2 for p in pairs)
        sum_y2 = sum(p[1] ** 2 for p in pairs)
        
        numerator = sum_xy - (sum_x * sum_y) / n
        denominator_x = (sum_x2 - (sum_x ** 2) / n) ** 0.5
        denominator_y = (sum_y2 - (sum_y ** 2) / n) ** 0.5
        
        if denominator_x == 0 or denominator_y == 0:
            return 0.0
        
        return numerator / (denominator_x * denominator_y)
    
    def print_summary(self):
        """Print a summary of fuzz test results."""
        analysis = self.analyze_results()
        
        print("\n" + "=" * 60)
        print("FUZZ TEST SUMMARY")
        print("=" * 60)
        print(f"Total iterations: {analysis['total_iterations']}")
        print(f"Status counts: {analysis['status_counts']}")
        print(f"\nFuel Statistics:")
        print(f"  Min: {analysis['fuel_stats']['min']}")
        print(f"  Max: {analysis['fuel_stats']['max']}")
        print(f"  Avg: {analysis['fuel_stats']['avg']:.2f}")
        print(f"  Median: {analysis['fuel_stats']['median']}")
        print(f"\nTime Statistics:")
        print(f"  Min: {analysis['time_stats']['min']:.6f}s")
        print(f"  Max: {analysis['time_stats']['max']:.6f}s")
        print(f"  Avg: {analysis['time_stats']['avg']:.6f}s")
        print(f"\nFuel-Time Correlation: {analysis['fuel_time_correlation']:.4f}")
        print(f"Adversarial patterns found: {analysis['adversarial_patterns_found']}")
        
        # Warn if correlation is low (fuel doesn't reflect wall-clock time)
        if analysis['fuel_time_correlation'] < 0.5:
            print("\n⚠️  WARNING: Low correlation between fuel and wall-clock time!")
            print("   Fuel costs may not reflect actual hardware strain.")


# Example usage
if __name__ == "__main__":
    # Create fuzz tester
    fuzzer = FuzzTester()
    
    # Configure (optional)
    fuzzer.config.max_depth = 15
    fuzzer.config.max_width = 15
    fuzzer.config.fuel_limit = 5000
    fuzzer.config.iterations = 50
    
    # Run fuzz tests
    fuzzer.run()
    
    # Print summary
    fuzzer.print_summary()
    
    # Print some adversarial patterns
    if fuzzer.adversarial_patterns:
        print("\n" + "=" * 60)
        print("ADVERSARIAL PATTERNS FOUND:")
        print("=" * 60)
        for i, pattern in enumerate(fuzzer.adversarial_patterns[:5]):
            print(f"\nPattern {i+1}:")
            print(pattern[:200] + "..." if len(pattern) > 200 else pattern)
