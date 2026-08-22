# Gas Arbitrage Fixes - Prototype Implementation

## Overview

This directory contains prototypes for addressing the structural gas arbitrage issue in MeTTa. The goal is to ensure that fuel costs accurately reflect real hardware strain (CPU/memory/cache usage).

## Problem Statement

MeTTa's current fuel system uses static costs per operation, which doesn't account for:
- **Memory access patterns**: Cache misses, TLB misses
- **Graph topology**: Depth, width, recursion in hypergraphs
- **Hardware variability**: Different CPUs have different cache characteristics

This can lead to situations where operations with high hardware cost have low fuel cost (arbitrage opportunity).

## Proposed Solution

A **memory/cache-aware fuel system** that dynamically adjusts fuel costs based on:
1. Base operation costs (static)
2. Cache miss penalties (dynamic)
3. TLB miss penalties (dynamic)
4. Recursion depth penalties (dynamic)

## Files

### 1. `hardware_simulator.py`

Simulates CPU cache and TLB behavior to estimate hardware costs for MeTTa operations.

**Key Features:**
- Simulates L1/L2 cache with configurable size
- Simulates TLB (Translation Lookaside Buffer)
- Tracks cache hits/misses and TLB misses
- Estimates wall-clock time for operations

**Usage:**
```python
from hardware_simulator import HardwareSimulator

simulator = HardwareSimulator(cache_size=100, tlb_size=50)
context = {"graph_width": 10, "graph_depth": 5, "atom_space_size": 1000}
result = simulator.run_metta_op("UNIFY", context)

print(f"Fuel used: {result['fuel_used']}")
print(f"Wall time: {result['wall_time']:.6f}s")
print(f"Cache misses: {result['cache_misses']}")
```

**Output Metrics:**
- `fuel_used`: Calculated fuel cost
- `wall_time`: Simulated wall-clock time
- `cache_misses`: Number of cache misses
- `tlb_misses`: Number of TLB misses
- `memory_accesses`: Total memory accesses
- `cache_hit_rate`: Cache hit rate (0.0 to 1.0)

### 2. `fuzz_metta.py`

Fuzz testing framework that generates adversarial hypergraphs to test fuel vs. wall-clock time correlation.

**Key Features:**
- Generates adversarial hypergraph structures:
  - Unification-heavy (deep recursion + wide unification)
  - Pointer chasing (long chains of references)
  - Memory hog (large atom spaces)
  - Deep recursion
  - Wide branching
- Measures fuel consumption and wall-clock time
- Calculates correlation between fuel and time
- Identifies adversarial patterns

**Usage:**
```python
from fuzz_metta import FuzzTester

fuzzer = FuzzTester()
fuzzer.config.max_depth = 15
fuzzer.config.max_width = 15
fuzzer.config.fuel_limit = 5000
fuzzer.config.iterations = 100

fuzzer.run()
fuzzer.print_summary()
```

**Output:**
- Per-iteration results (status, fuel used, wall time)
- Summary statistics (min/max/avg fuel and time)
- Correlation coefficient between fuel and time
- Adversarial patterns found

### 3. `calibrate_fuel.py`

Calibrates fuel weights to ensure they accurately reflect hardware strain.

**Key Features:**
- Uses hardware simulator to estimate real costs
- Adjusts fuel weights to maximize correlation between fuel and wall-clock time
- Supports saving/loading calibrated weights
- Configurable learning rate and target correlation

**Usage:**
```python
from calibrate_fuel import FuelCalibrator

calibrator = FuelCalibrator()
calibrator.config.iterations = 1000
calibrator.config.target_correlation = 0.9

result = calibrator.calibrate()
calibrator.print_weights()
calibrator.save_weights("fuel_weights.json")
```

**Calibration Process:**
1. Simulate operations with current weights
2. Calculate correlation between fuel and wall-clock time
3. Adjust weights to improve correlation
4. Repeat until target correlation is reached

## Integration Guide

### Step 1: Integrate Hardware-Aware Fuel into MeTTa Interpreter

Modify the MeTTa interpreter to use the hardware-aware fuel system:

```python
# In the interpreter's operation handler

def execute_operation(op, context):
    # Base fuel cost
    base_fuel = BASE_FUEL.get(op, 1)
    
    # Dynamic costs
    memory_fuel = 0
    
    if op in ["UNIFY", "QUERY_ATOM", "MATCH"]:
        # Estimate cache misses based on graph structure
        cache_misses = estimate_cache_misses(context)
        memory_fuel = cache_misses * CACHE_MISS_PENALTY
    
    if op == "RECURSE":
        depth_penalty = context.recursion_depth * RECURSION_PENALTY
        memory_fuel += depth_penalty
    
    total_fuel = base_fuel + memory_fuel
    consume_fuel(total_fuel)
    
    # Execute operation...
```

### Step 2: Run Fuzz Tests on Real Hardware

Use `fuzz_metta.py` with the actual MeTTa interpreter to identify operations where fuel doesn't reflect wall-clock time:

```bash
python fuzz_metta.py --iterations 1000 --output results.json
```

### Step 3: Calibrate Weights

Use `calibrate_fuel.py` to find optimal fuel weights:

```bash
python calibrate_fuel.py --iterations 10000 --target-correlation 0.95
```

### Step 4: Validate

Verify that fuel costs now correlate well with wall-clock time:

```python
from fuzz_metta import FuzzTester

fuzzer = FuzzTester()
fuzzer.run(iterations=1000)
analysis = fuzzer.analyze_results()

# Should be close to 1.0
print(f"Correlation: {analysis['fuel_time_correlation']}")
```

## Default Fuel Weights

Based on initial calibration, these are reasonable starting weights:

| Operation | Base | Cache Penalty | TLB Penalty | Recursion Penalty |
|-----------|------|---------------|-------------|-------------------|
| ADD       | 1    | 1             | 1           | 0                 |
| SUB       | 1    | 1             | 1           | 0                 |
| MUL       | 2    | 2             | 1           | 0                 |
| DIV       | 3    | 3             | 1           | 0                 |
| UNIFY     | 100  | 10            | 5           | 0                 |
| QUERY_ATOM | 50  | 8             | 5           | 0                 |
| MATCH     | 30   | 6             | 3           | 0                 |
| RECURSE   | 20   | 0             | 0           | 5                 |
| BIND      | 15   | 3             | 2           | 0                 |
| CONS      | 5    | 2             | 1           | 0                 |
| CAR       | 2    | 1             | 1           | 0                 |
| CDR       | 2    | 1             | 1           | 0                 |

## Cache Miss Estimation

The `estimate_cache_misses` function uses this heuristic:

```python
def estimate_cache_misses(context):
    depth = context.graph_depth
    width = context.graph_width
    atom_space_size = context.atom_space_size
    
    # Heuristic: deeper/wider graphs have more cache misses
    cache_misses = (depth * width) // 10
    
    # Larger atom spaces increase miss rate
    if atom_space_size > 1000:
        cache_misses += atom_space_size // 100
    
    return cache_misses
```

This should be replaced with actual hardware profiling when available.

## Testing

Run the prototypes:

```bash
# Test hardware simulator
python hardware_simulator.py

# Run fuzz tests
python fuzz_metta.py

# Calibrate weights
python calibrate_fuel.py
```

## Next Steps

1. **Integrate into MeTTa**: Add the hardware-aware fuel calculation to the actual interpreter
2. **Profile on real hardware**: Use `perf` or similar tools to get real cache miss data
3. **Fine-tune weights**: Run calibration on actual workloads
4. **Monitor in production**: Track fuel vs. time correlation in real usage
5. **Adjust dynamically**: Consider making weights configurable per-chain/network

## References

- [EVM Gas Costs](https://www.evm.codes/)
- [Solana Compute Budget](https://docs.solana.com/developing/programming-model/compute-budget)
- [Sway Fuel VM](https://fuellabs.github.io/sway/)
- [CosmWasm Gas Metering](https://docs.cosmwasm.com/docs/1.0/smart-contracts/gas/)
