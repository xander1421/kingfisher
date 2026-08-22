"""
Hardware Simulator for MeTTa Fuel System Calibration

Simulates CPU cache behavior to estimate hardware costs for MeTTa operations.
This is used to calibrate fuel weights when actual hardware profiling is unavailable.
"""

import time
import random
from typing import Dict, Any, Optional


class HardwareSimulator:
    """
    Simulates hardware costs (cache misses, TLB misses) for MeTTa operations.
    
    Attributes:
        cache: Simulated CPU cache (address -> data)
        cache_size: Maximum cache entries (simulated L1/L2 cache)
        cache_misses: Counter for cache misses
        tlb_misses: Counter for TLB misses (simulated)
        memory_accesses: Total memory accesses
    """
    
    def __init__(self, cache_size: int = 100, tlb_size: int = 50):
        """
        Initialize the hardware simulator.
        
        Args:
            cache_size: Simulated cache size (number of entries)
            tlb_size: Simulated TLB size (number of page table entries)
        """
        self.cache: Dict[int, Any] = {}
        self.cache_size = cache_size
        self.cache_misses = 0
        
        self.tlb: Dict[int, int] = {}  # Page number -> frame number
        self.tlb_size = tlb_size
        self.tlb_misses = 0
        
        self.memory_accesses = 0
        self.access_pattern: list = []  # Track access patterns for analysis
        
    def reset(self):
        """Reset all counters and caches."""
        self.cache.clear()
        self.tlb.clear()
        self.cache_misses = 0
        self.tlb_misses = 0
        self.memory_accesses = 0
        self.access_pattern.clear()
        
    def access_memory(self, address: int, data: Any = None) -> str:
        """
        Simulate a memory access with cache hit/miss behavior.
        
        Args:
            address: Memory address to access
            data: Optional data to store at address
            
        Returns:
            "hit" if cache hit, "miss" if cache miss
        """
        self.memory_accesses += 1
        self.access_pattern.append(address)
        
        # Simulate TLB lookup (for virtual memory)
        page_number = address // 4096  # Assume 4KB pages
        if page_number not in self.tlb:
            self.tlb_misses += 1
            # Evict oldest TLB entry if full
            if len(self.tlb) >= self.tlb_size:
                oldest_page = next(iter(self.tlb))
                self.tlb.pop(oldest_page)
            self.tlb[page_number] = address
        
        # Simulate cache lookup
        if address in self.cache:
            return "hit"
        else:
            self.cache_misses += 1
            # Evict oldest cache entry if full (LRU simulation)
            if len(self.cache) >= self.cache_size:
                oldest_addr = next(iter(self.cache))
                self.cache.pop(oldest_addr)
            self.cache[address] = data
            return "miss"
    
    def run_metta_op(self, op: str, context: Dict[str, Any], 
                    base_fuel: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """
        Simulate running a MeTTa operation with hardware costs.
        
        Args:
            op: MeTTa operation name (e.g., "UNIFY", "QUERY_ATOM", "RECURSE")
            context: Context dictionary with operation parameters
            base_fuel: Optional base fuel costs per operation
            
        Returns:
            Dictionary with fuel_used, wall_time, cache_misses, tlb_misses
        """
        # Default base fuel costs (calibrated via profiling)
        if base_fuel is None:
            base_fuel = {
                "ADD": 1,
                "MUL": 2,
                "UNIFY": 100,
                "QUERY_ATOM": 50,
                "RECURSE": 20,
                "MATCH": 30,
                "BIND": 15,
                "CONS": 5,
            }
        
        # Dynamic fuel weights
        cache_miss_penalty = 10
        tlb_miss_penalty = 5
        recursion_penalty = 5
        
        start_time = time.time()
        fuel_used = 0
        
        # Reset per-operation counters
        self.reset()
        
        # Base fuel cost
        fuel_used += base_fuel.get(op, 1)
        
        # Simulate memory accesses based on operation type
        if op in ["UNIFY", "QUERY_ATOM", "MATCH"]:
            # These operations touch many atoms -> more cache misses
            graph_width = context.get("graph_width", 1)
            graph_depth = context.get("graph_depth", 1)
            atom_space_size = context.get("atom_space_size", 100)
            
            # Simulate accessing atoms in the graph
            num_accesses = graph_width * graph_depth
            for i in range(num_accesses):
                # Generate addresses that might cause cache misses
                address = (i * atom_space_size + random.randint(0, 1000)) % 1000000
                self.access_memory(address)
                
        elif op == "RECURSE":
            # Recursion causes stack growth and potential cache pressure
            recursion_depth = context.get("recursion_depth", 1)
            for i in range(recursion_depth * 10):  # Simulate stack frames
                address = random.randint(0, 10000)
                self.access_memory(address)
                
        elif op in ["ADD", "MUL", "SUB"]:
            # Arithmetic operations have minimal memory access
            self.access_memory(random.randint(0, 100))
            
        # Add dynamic fuel costs
        fuel_used += self.cache_misses * cache_miss_penalty
        fuel_used += self.tlb_misses * tlb_miss_penalty
        
        # Recursion depth penalty
        if op == "RECURSE":
            recursion_depth = context.get("recursion_depth", 0)
            fuel_used += recursion_depth * recursion_penalty
            
        end_time = time.time()
        wall_time = end_time - start_time
        
        return {
            "fuel_used": fuel_used,
            "wall_time": wall_time,
            "cache_misses": self.cache_misses,
            "tlb_misses": self.tlb_misses,
            "memory_accesses": self.memory_accesses,
            "cache_hit_rate": 1.0 - (self.cache_misses / self.memory_accesses) if self.memory_accesses > 0 else 0.0,
        }
    
    def estimate_cache_misses(self, context: Dict[str, Any]) -> int:
        """
        Estimate cache misses based on graph structure.
        
        Args:
            context: Context with graph_depth, graph_width, atom_space_size
            
        Returns:
            Estimated number of cache misses
        """
        depth = context.get("graph_depth", 0)
        width = context.get("graph_width", 0)
        atom_space_size = context.get("atom_space_size", 0)
        
        # Heuristic: Deeper/wider graphs have more cache misses
        # This simulates pointer chasing in complex hypergraphs
        cache_misses = (depth * width) // 10  # Tune this based on real profiling
        
        # Larger atom spaces increase miss rate
        if atom_space_size > 1000:
            cache_misses += atom_space_size // 100
            
        return cache_misses


# Example usage
if __name__ == "__main__":
    simulator = HardwareSimulator()
    
    # Test different operations
    operations = [
        ("UNIFY", {"graph_width": 10, "graph_depth": 5, "atom_space_size": 1000}),
        ("QUERY_ATOM", {"graph_width": 5, "graph_depth": 3, "atom_space_size": 500}),
        ("RECURSE", {"recursion_depth": 5}),
        ("ADD", {}),
    ]
    
    print("Hardware Simulation Results:")
    print("-" * 60)
    
    for op, context in operations:
        result = simulator.run_metta_op(op, context)
        print(f"\nOperation: {op}")
        print(f"  Fuel used: {result['fuel_used']}")
        print(f"  Wall time: {result['wall_time']:.6f}s")
        print(f"  Cache misses: {result['cache_misses']}")
        print(f"  TLB misses: {result['tlb_misses']}")
        print(f"  Cache hit rate: {result['cache_hit_rate']:.2%}")
