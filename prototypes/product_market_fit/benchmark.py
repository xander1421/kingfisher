"""
MeTTa Benchmarking Framework

Benchmarks MeTTa performance against EVM and Wasm for various operations.
This helps identify areas where MeTTa excels and where it needs improvement.
"""

import subprocess
import json
import time
import statistics
import re
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum


class VMType(Enum):
    """Supported virtual machine types."""
    METTA = "metta"
    EVM = "evm"
    WASM = "wasm"


@dataclass
class BenchmarkConfig:
    """Configuration for benchmarking."""
    # Paths to executables
    metta_executable: str = "metta"
    evm_executable: str = "evm"  # Could be ganache, geth, etc.
    wasm_executable: str = "wasmtime"  # Or other Wasm runtime
    
    # Number of runs per benchmark
    runs: int = 100
    
    # Warmup runs (to account for JIT, caching, etc.)
    warmup_runs: int = 10
    
    # Timeout for each run (seconds)
    timeout: float = 30.0
    
    # Fuel/gas limit
    fuel_limit: int = 1000000
    gas_limit: int = 10000000
    
    # Whether to show verbose output
    verbose: bool = False
    
    # Output directory for results
    output_dir: str = "benchmark_results"


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    vm: VMType
    operation: str
    input_size: int
    time: float  # seconds
    fuel_gas_used: int
    memory_used: int = 0
    success: bool = True
    error: Optional[str] = None


@dataclass
class BenchmarkComparison:
    """Comparison of benchmark results across VMs."""
    operation: str
    input_size: int
    results: Dict[VMType, List[BenchmarkResult]] = field(default_factory=dict)
    
    def get_stats(self, vm: VMType) -> Dict[str, float]:
        """Get statistics for a VM."""
        times = [r.time for r in self.results.get(vm, []) if r.success]
        fuels = [r.fuel_gas_used for r in self.results.get(vm, []) if r.success]
        
        return {
            "min_time": min(times) if times else 0,
            "max_time": max(times) if times else 0,
            "avg_time": statistics.mean(times) if times else 0,
            "median_time": statistics.median(times) if times else 0,
            "std_time": statistics.stdev(times) if len(times) > 1 else 0,
            "min_fuel": min(fuels) if fuels else 0,
            "max_fuel": max(fuels) if fuels else 0,
            "avg_fuel": statistics.mean(fuels) if fuels else 0,
        }
    
    def compare(self, vm1: VMType, vm2: VMType) -> Dict[str, float]:
        """Compare two VMs for this operation."""
        stats1 = self.get_stats(vm1)
        stats2 = self.get_stats(vm2)
        
        return {
            "time_ratio": stats1["avg_time"] / stats2["avg_time"] if stats2["avg_time"] > 0 else 0,
            "fuel_ratio": stats1["avg_fuel"] / stats2["avg_fuel"] if stats2["avg_fuel"] > 0 else 0,
            "time_diff": stats1["avg_time"] - stats2["avg_time"],
            "fuel_diff": stats1["avg_fuel"] - stats2["avg_fuel"],
        }


class MeTTaBenchmark:
    """
    Benchmarking framework for MeTTa vs. EVM vs. Wasm.
    
    Usage:
        benchmark = MeTTaBenchmark()
        
        # Define benchmarks
        benchmark.add_benchmark("graph_traversal", [10, 100, 1000])
        benchmark.add_benchmark("unification", [10, 100, 1000])
        benchmark.add_benchmark("recursion", [5, 10, 20])
        
        # Run benchmarks
        results = benchmark.run()
        
        # Generate report
        benchmark.generate_report(results)
    """
    
    def __init__(self, config: Optional[BenchmarkConfig] = None):
        """
        Initialize the benchmark framework.
        
        Args:
            config: Benchmark configuration
        """
        self.config = config or BenchmarkConfig()
        self.benchmarks: List[Dict[str, Any]] = []
        self.results: List[BenchmarkComparison] = []
        
        # Create output directory
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
        
    def add_benchmark(self, name: str, input_sizes: List[int], 
                     description: str = "", category: str = "general"):
        """
        Add a benchmark to run.
        
        Args:
            name: Name of the benchmark
            input_sizes: List of input sizes to test
            description: Description of what the benchmark tests
            category: Category (e.g., "graph", "arithmetic", "control")
        """
        self.benchmarks.append({
            "name": name,
            "input_sizes": input_sizes,
            "description": description,
            "category": category,
        })
    
    def run_metta(self, program: str, input_data: Optional[Dict[str, Any]] = None,
                 fuel_limit: Optional[int] = None) -> BenchmarkResult:
        """
        Run a MeTTa program and collect benchmark data.
        
        Args:
            program: MeTTa program code or path to file
            input_data: Input data for the program
            fuel_limit: Fuel limit
            
        Returns:
            BenchmarkResult with timing and fuel data
        """
        # Determine if program is a file path or code
        program_path = Path(program)
        temp_file = None
        
        try:
            if program_path.exists():
                # It's a file path
                cmd = [self.config.metta_executable, "run", str(program_path)]
            else:
                # It's code - write to temp file
                temp_file = Path(self.config.output_dir) / f"temp_{int(time.time())}.metta"
                with open(temp_file, 'w') as f:
                    f.write(program)
                cmd = [self.config.metta_executable, "run", str(temp_file)]
            
            # Add fuel limit
            limit = fuel_limit or self.config.fuel_limit
            cmd.extend(["--fuel-limit", str(limit)])
            
            # Add input data
            if input_data:
                cmd.extend(["--input", json.dumps(input_data)])
            
            # Run with timeout
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout
            )
            end_time = time.time()
            
            # Extract fuel used
            fuel_used = 0
            if result.stderr:
                fuel_match = re.search(r'fuel used: (\d+)', result.stderr)
                if fuel_match:
                    fuel_used = int(fuel_match.group(1))
            
            # Clean up temp file if created
            if temp_file and temp_file.exists():
                temp_file.unlink()
            
            return BenchmarkResult(
                vm=VMType.METTA,
                operation=program,
                input_size=0,  # Will be set by caller
                time=end_time - start_time,
                fuel_gas_used=fuel_used,
                success=result.returncode == 0,
                error=result.stderr if result.returncode != 0 else None
            )
            
        except subprocess.TimeoutExpired:
            if not program_path.exists():
                temp_file.unlink(missing_ok=True)
            return BenchmarkResult(
                vm=VMType.METTA,
                operation=program,
                input_size=0,
                time=self.config.timeout,
                fuel_gas_used=0,
                success=False,
                error="Timeout"
            )
        except Exception as e:
            if not program_path.exists():
                temp_file.unlink(missing_ok=True)
            return BenchmarkResult(
                vm=VMType.METTA,
                operation=program,
                input_size=0,
                time=0.0,
                fuel_gas_used=0,
                success=False,
                error=str(e)
            )
    
    def run_evm(self, program: str, input_data: Optional[Dict[str, Any]] = None,
                gas_limit: Optional[int] = None) -> BenchmarkResult:
        """
        Run an EVM program and collect benchmark data.
        
        Args:
            program: EVM bytecode or path to .sol file
            input_data: Input data for the program
            gas_limit: Gas limit
            
        Returns:
            BenchmarkResult with timing and gas data
        """
        # For demo purposes, we'll simulate EVM execution
        # In production, this would use ganache, geth, or similar
        
        program_path = Path(program)
        
        # Simulate execution time based on program size
        start_time = time.time()
        
        # Simulate EVM execution
        if program_path.exists():
            # Read file to get size
            with open(program_path, 'r') as f:
                content = f.read()
            size = len(content)
        else:
            size = len(program)
        
        # Simulate execution time (EVM is slower for complex ops)
        time.sleep(0.01 * (size / 1000))
        
        end_time = time.time()
        
        # Simulate gas used
        gas_used = size * 100  # Rough estimate
        
        return BenchmarkResult(
            vm=VMType.EVM,
            operation=program,
            input_size=0,  # Will be set by caller
            time=end_time - start_time,
            fuel_gas_used=gas_used,
            success=True
        )
    
    def run_wasm(self, program: str, input_data: Optional[Dict[str, Any]] = None) -> BenchmarkResult:
        """
        Run a Wasm program and collect benchmark data.
        
        Args:
            program: Wasm bytecode or path to .wasm file
            input_data: Input data for the program
            
        Returns:
            BenchmarkResult with timing data
        """
        # For demo purposes, we'll simulate Wasm execution
        # In production, this would use wasmtime, wasmer, or similar
        
        program_path = Path(program)
        
        # Simulate execution time based on program size
        start_time = time.time()
        
        # Simulate Wasm execution
        if program_path.exists():
            # Read file to get size
            with open(program_path, 'r') as f:
                content = f.read()
            size = len(content)
        else:
            size = len(program)
        
        # Simulate execution time (Wasm is fast for computation)
        time.sleep(0.001 * (size / 1000))
        
        end_time = time.time()
        
        # Simulate gas/fuel used
        fuel_used = size * 10  # Rough estimate
        
        return BenchmarkResult(
            vm=VMType.WASM,
            operation=program,
            input_size=0,  # Will be set by caller
            time=end_time - start_time,
            fuel_gas_used=fuel_used,
            success=True
        )
    
    def generate_metta_program(self, benchmark_name: str, input_size: int) -> str:
        """
        Generate a MeTTa program for a specific benchmark.
        
        Args:
            benchmark_name: Name of the benchmark
            input_size: Size of input (e.g., number of nodes in graph)
            
        Returns:
            MeTTa program code
        """
        if benchmark_name == "graph_traversal":
            return self._generate_graph_traversal(input_size)
        elif benchmark_name == "unification":
            return self._generate_unification(input_size)
        elif benchmark_name == "recursion":
            return self._generate_recursion(input_size)
        elif benchmark_name == "pattern_matching":
            return self._generate_pattern_matching(input_size)
        elif benchmark_name == "list_operations":
            return self._generate_list_operations(input_size)
        elif benchmark_name == "arithmetic":
            return self._generate_arithmetic(input_size)
        else:
            # Default: simple program
            return "(def main (lambda () (print \"Hello\")))"
    
    def _generate_graph_traversal(self, size: int) -> str:
        """Generate a graph traversal benchmark."""
        # Create a graph with 'size' nodes
        nodes = "\n".join([f"  (node-{i} (Atom \"node-{i}\"))" for i in range(size)])
        edges = "\n".join([f"  (edge-{i} (Edge node-{i} node-{i+1}))" 
                          for i in range(size - 1)])
        
        return f"""
; Graph Traversal Benchmark
; Tests MeTTa's ability to traverse hypergraph structures

(def Atom (Type
  value String
))

(def Edge (Type
  from Atom
  to Atom
))

(def Graph (State
{nodes}
{edges}
))

(def traverse (lambda (graph start-node visited)
  (if (contains? visited start-node)
    visited
    (let ((new-visited (append visited (List start-node))))
      ; Find all edges from start-node
      (let ((edges (filter (lambda (e)
                             (= (from e) start-node))
                           (edges graph))))
        ; Recursively traverse to connected nodes
        (fold (lambda (v e)
                (traverse graph (to e) v))
              new-visited
              edges))))))

(def main (lambda ()
  (let ((graph (Graph)))
    (traverse graph node-0 (List)))
))

(main)
"""
    
    def _generate_unification(self, size: int) -> str:
        """Generate a unification benchmark."""
        # Create 'size' unification operations
        unifications = "\n".join([
            f"  (unify (atom-{i} (Atom \"a\")) (atom-{i+1} (Atom \"a\")))"
            for i in range(size)
        ])
        
        return f"""
; Unification Benchmark
; Tests MeTTa's unification performance

(def main (lambda ()
{unifications}
))

(main)
"""
    
    def _generate_recursion(self, depth: int) -> str:
        """Generate a recursion benchmark."""
        return f"""
; Recursion Benchmark
; Tests MeTTa's recursion performance

(def factorial (lambda (n)
  (if (<= n 1)
    1
    (* n (factorial (- n 1))))))

(def main (lambda ()
  (factorial {depth})
))

(main)
"""
    
    def _generate_pattern_matching(self, size: int) -> str:
        """Generate a pattern matching benchmark."""
        patterns = "\n".join([
            f"  (match data (pattern-{i} (Atom \"x\")) (do-something {i}))"
            for i in range(size)
        ])
        
        return f"""
; Pattern Matching Benchmark
; Tests MeTTa's pattern matching performance

(def data (Atom "test"))

(def main (lambda ()
{patterns}
))

(main)
"""
    
    def _generate_list_operations(self, size: int) -> str:
        """Generate a list operations benchmark."""
        return f"""
; List Operations Benchmark
; Tests MeTTa's list manipulation performance

(def main (lambda ()
  (let ((list (List {' '.join([str(i) for i in range(size)])})))
    ; Map
    (map (lambda (x) (* x 2)) list)
    
    ; Filter
    (filter (lambda (x) (> x 50)) list)
    
    ; Fold
    (fold (lambda (acc x) (+ acc x)) 0 list)
    
    ; Sort
    (sort list (lambda (a b) (< a b)))
    
    ; Reverse
    (reverse list)
  )
))

(main)
"""
    
    def _generate_arithmetic(self, size: int) -> str:
        """Generate an arithmetic benchmark."""
        operations = "\n".join([
            f"  (+ {i} {i+1})"
            for i in range(size)
        ])
        
        return f"""
; Arithmetic Benchmark
; Tests MeTTa's arithmetic performance

(def main (lambda ()
{operations}
))

(main)
"""
    
    def run_benchmark(self, benchmark_name: str, input_size: int) -> BenchmarkComparison:
        """
        Run a single benchmark across all VMs.
        
        Args:
            benchmark_name: Name of the benchmark
            input_size: Input size
            
        Returns:
            BenchmarkComparison with results for all VMs
        """
        comparison = BenchmarkComparison(
            operation=benchmark_name,
            input_size=input_size
        )
        
        # Generate MeTTa program
        metta_program = self.generate_metta_program(benchmark_name, input_size)
        
        print(f"Running benchmark: {benchmark_name} (size={input_size})")
        
        # Warmup runs
        for _ in range(self.config.warmup_runs):
            self.run_metta(metta_program)
        
        # Run MeTTa
        print(f"  MeTTa...", end=" ", flush=True)
        metta_results = []
        for _ in range(self.config.runs):
            result = self.run_metta(metta_program)
            result.input_size = input_size
            metta_results.append(result)
        comparison.results[VMType.METTA] = metta_results
        print("done")
        
        # Run EVM (simulated)
        print(f"  EVM...", end=" ", flush=True)
        evm_results = []
        for _ in range(self.config.runs):
            result = self.run_evm(metta_program)
            result.input_size = input_size
            evm_results.append(result)
        comparison.results[VMType.EVM] = evm_results
        print("done")
        
        # Run Wasm (simulated)
        print(f"  Wasm...", end=" ", flush=True)
        wasm_results = []
        for _ in range(self.config.runs):
            result = self.run_wasm(metta_program)
            result.input_size = input_size
            wasm_results.append(result)
        comparison.results[VMType.WASM] = wasm_results
        print("done")
        
        return comparison
    
    def run(self) -> List[BenchmarkComparison]:
        """
        Run all benchmarks.
        
        Returns:
            List of BenchmarkComparison objects
        """
        self.results = []
        
        print("=" * 60)
        print("RUNNING BENCHMARKS")
        print("=" * 60)
        print(f"Runs per benchmark: {self.config.runs}")
        print(f"Warmup runs: {self.config.warmup_runs}")
        print()
        
        for benchmark in self.benchmarks:
            benchmark_name = benchmark["name"]
            input_sizes = benchmark["input_sizes"]
            
            print(f"\nBenchmark: {benchmark_name}")
            print(f"Description: {benchmark.get('description', 'N/A')}")
            print(f"Category: {benchmark.get('category', 'general')}")
            print("-" * 60)
            
            for input_size in input_sizes:
                comparison = self.run_benchmark(benchmark_name, input_size)
                self.results.append(comparison)
            
            print()
        
        return self.results
    
    def generate_report(self, results: Optional[List[BenchmarkComparison]] = None):
        """
        Generate a benchmark report.
        
        Args:
            results: Benchmark results (defaults to self.results)
        """
        results = results or self.results
        
        print("=" * 80)
        print("BENCHMARK REPORT")
        print("=" * 80)
        print()
        
        # Group by benchmark
        benchmarks: Dict[str, List[BenchmarkComparison]] = {}
        for result in results:
            if result.operation not in benchmarks:
                benchmarks[result.operation] = []
            benchmarks[result.operation].append(result)
        
        for benchmark_name, comparisons in benchmarks.items():
            print(f"## {benchmark_name}")
            print("-" * 80)
            
            # Create a table
            print(f"{'Size':<10} {'VM':<10} {'Avg Time (s)':<15} {'Avg Fuel/Gas':<15} {'Ratio'}")
            print("-" * 80)
            
            # Get first comparison for reference
            first_comparison = comparisons[0]
            
            for comparison in comparisons:
                input_size = comparison.input_size
                
                # MeTTa
                metta_stats = comparison.get_stats(VMType.METTA)
                print(f"{input_size:<10} {'MeTTa':<10} {metta_stats['avg_time']:<15.6f} "
                      f"{metta_stats['avg_fuel']:<15} -")
                
                # EVM
                evm_stats = comparison.get_stats(VMType.EVM)
                metta_evm_ratio = metta_stats['avg_time'] / evm_stats['avg_time'] if evm_stats['avg_time'] > 0 else 0
                print(f"{input_size:<10} {'EVM':<10} {evm_stats['avg_time']:<15.6f} "
                      f"{evm_stats['avg_fuel']:<15} {metta_evm_ratio:.2f}x")
                
                # Wasm
                wasm_stats = comparison.get_stats(VMType.WASM)
                metta_wasm_ratio = metta_stats['avg_time'] / wasm_stats['avg_time'] if wasm_stats['avg_time'] > 0 else 0
                print(f"{input_size:<10} {'Wasm':<10} {wasm_stats['avg_time']:<15.6f} "
                      f"{wasm_stats['avg_fuel']:<15} {metta_wasm_ratio:.2f}x")
                
                print()
        
        # Summary statistics
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()
        
        # Calculate overall ratios
        metta_times = []
        evm_times = []
        wasm_times = []
        
        for result in results:
            metta_stats = result.get_stats(VMType.METTA)
            evm_stats = result.get_stats(VMType.EVM)
            wasm_stats = result.get_stats(VMType.WASM)
            
            if metta_stats['avg_time'] > 0:
                metta_times.append(metta_stats['avg_time'])
            if evm_stats['avg_time'] > 0:
                evm_times.append(evm_stats['avg_time'])
            if wasm_stats['avg_time'] > 0:
                wasm_times.append(wasm_stats['avg_time'])
        
        avg_metta = statistics.mean(metta_times) if metta_times else 0
        avg_evm = statistics.mean(evm_times) if evm_times else 0
        avg_wasm = statistics.mean(wasm_times) if wasm_times else 0
        
        print(f"Average Time (all benchmarks):")
        print(f"  MeTTa: {avg_metta:.6f}s")
        print(f"  EVM:   {avg_evm:.6f}s")
        print(f"  Wasm:  {avg_wasm:.6f}s")
        print()
        
        if avg_evm > 0:
            print(f"MeTTa vs EVM: {avg_metta / avg_evm:.2f}x")
        if avg_wasm > 0:
            print(f"MeTTa vs Wasm: {avg_metta / avg_wasm:.2f}x")
        print()
        
        # Save to file
        report_path = Path(self.config.output_dir) / "report.txt"
        with open(report_path, 'w') as f:
            # Redirect print to file
            import sys
            from io import StringIO
            
            old_stdout = sys.stdout
            sys.stdout = f
            
            self.generate_report(results)
            
            sys.stdout = old_stdout
        
        print(f"Report saved to: {report_path}")
    
    def generate_html_report(self, results: Optional[List[BenchmarkComparison]] = None):
        """
        Generate an HTML benchmark report.
        
        Args:
            results: Benchmark results
        """
        results = results or self.results
        
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>MeTTa Benchmark Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        h2 { color: #555; border-bottom: 2px solid #ddd; padding-bottom: 10px; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .good { color: green; }
        .bad { color: red; }
        .neutral { color: gray; }
        .summary { background-color: #e6f7ff; padding: 15px; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>MeTTa Benchmark Report</h1>
    <p>Generated on: {date}</p>
    
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total Benchmarks:</strong> {total_benchmarks}</p>
        <p><strong>Average Time (MeTTa):</strong> {avg_metta:.6f}s</p>
        <p><strong>Average Time (EVM):</strong> {avg_evm:.6f}s</p>
        <p><strong>Average Time (Wasm):</strong> {avg_wasm:.6f}s</p>
    </div>
    
    <h2>Benchmark Results</h2>
"""
        
        # Add benchmark tables
        benchmarks: Dict[str, List[BenchmarkComparison]] = {}
        for result in results:
            if result.operation not in benchmarks:
                benchmarks[result.operation] = []
            benchmarks[result.operation].append(result)
        
        for benchmark_name, comparisons in benchmarks.items():
            html += f"""
    <h3>{benchmark_name}</h3>
    <table>
        <tr>
            <th>Input Size</th>
            <th>VM</th>
            <th>Avg Time (s)</th>
            <th>Avg Fuel/Gas</th>
            <th>MeTTa vs EVM</th>
            <th>MeTTa vs Wasm</th>
        </tr>
"""
            for comparison in comparisons:
                input_size = comparison.input_size
                metta_stats = comparison.get_stats(VMType.METTA)
                evm_stats = comparison.get_stats(VMType.EVM)
                wasm_stats = comparison.get_stats(VMType.WASM)
                
                metta_evm_ratio = metta_stats['avg_time'] / evm_stats['avg_time'] if evm_stats['avg_time'] > 0 else 0
                metta_wasm_ratio = metta_stats['avg_time'] / wasm_stats['avg_time'] if wasm_stats['avg_time'] > 0 else 0
                
                metta_evm_class = "good" if metta_evm_ratio < 1 else "bad"
                metta_wasm_class = "good" if metta_wasm_ratio < 1 else "bad"
                
                html += f"""
        <tr>
            <td>{input_size}</td>
            <td>MeTTa</td>
            <td>{metta_stats['avg_time']:.6f}</td>
            <td>{metta_stats['avg_fuel']}</td>
            <td>-</td>
            <td>-</td>
        </tr>
        <tr>
            <td>{input_size}</td>
            <td>EVM</td>
            <td>{evm_stats['avg_time']:.6f}</td>
            <td>{evm_stats['avg_fuel']}</td>
            <td class="{metta_evm_class}">{metta_evm_ratio:.2f}x</td>
            <td>-</td>
        </tr>
        <tr>
            <td>{input_size}</td>
            <td>Wasm</td>
            <td>{wasm_stats['avg_time']:.6f}</td>
            <td>{wasm_stats['avg_fuel']}</td>
            <td>-</td>
            <td class="{metta_wasm_class}">{metta_wasm_ratio:.2f}x</td>
        </tr>
"""
            
            html += """
    </table>
"""
        
        html += """
</body>
</html>
"""
        
        # Save HTML report
        html_path = Path(self.config.output_dir) / "report.html"
        with open(html_path, 'w') as f:
            f.write(html)
        
        print(f"HTML report saved to: {html_path}")


# Example usage
if __name__ == "__main__":
    print("MeTTa Benchmarking Framework")
    print("=" * 60)
    print()
    
    # Create benchmark suite
    benchmark = MeTTaBenchmark()
    
    # Configure
    benchmark.config.runs = 10
    benchmark.config.warmup_runs = 2
    benchmark.config.verbose = True
    
    # Add benchmarks
    benchmark.add_benchmark(
        "graph_traversal",
        [10, 100, 500],
        "Traverse a hypergraph with N nodes",
        "graph"
    )
    
    benchmark.add_benchmark(
        "unification",
        [10, 100, 500],
        "Perform N unification operations",
        "hypergraph"
    )
    
    benchmark.add_benchmark(
        "recursion",
        [5, 10, 20],
        "Compute factorial with depth N",
        "control"
    )
    
    benchmark.add_benchmark(
        "pattern_matching",
        [10, 100, 500],
        "Match N patterns against data",
        "hypergraph"
    )
    
    benchmark.add_benchmark(
        "list_operations",
        [100, 1000, 5000],
        "Perform map, filter, fold, sort, reverse on list of size N",
        "data"
    )
    
    # Run benchmarks
    print("Running benchmarks... (this may take a while)")
    print()
    
    results = benchmark.run()
    
    # Generate reports
    print()
    print("=" * 60)
    print("GENERATING REPORTS")
    print("=" * 60)
    print()
    
    benchmark.generate_report(results)
    benchmark.generate_html_report(results)
    
    print()
    print("Benchmark complete!")
    print(f"Results saved to: {benchmark.config.output_dir}")
