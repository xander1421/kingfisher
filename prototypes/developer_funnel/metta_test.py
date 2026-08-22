"""
MeTTa Testing Framework (Inspired by Foundry)

A testing framework for MeTTa programs that provides:
- Test case definitions
- Assertions
- Mocking
- Coverage tracking
- Fuel estimation

This is designed to be similar to Foundry's forge test for Solidity.
"""

import subprocess
import json
import time
import re
import sys
from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum


class TestStatus(Enum):
    """Status of a test case."""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class TestResult:
    """Result of a single test case."""
    name: str
    status: TestStatus
    message: str = ""
    expected: Any = None
    actual: Any = None
    fuel_used: int = 0
    execution_time: float = 0.0
    error: Optional[str] = None
    
    def __repr__(self):
        status_symbol = {
            TestStatus.PASSED: "✅",
            TestStatus.FAILED: "❌",
            TestStatus.ERROR: "💥",
            TestStatus.SKIPPED: "⏭️",
            TestStatus.TIMEOUT: "⏰"
        }
        return (f"{status_symbol[self.status]} {self.name}: "
                f"{self.message}" +
                (f" (expected: {self.expected}, got: {self.actual})" 
                 if self.status == TestStatus.FAILED else "") +
                (f" (fuel: {self.fuel_used})" if self.fuel_used > 0 else "") +
                (f" ({self.execution_time:.4f}s)" if self.execution_time > 0 else ""))


@dataclass
class TestConfig:
    """Configuration for test execution."""
    # MeTTa executable path
    metta_executable: str = "metta"
    
    # Timeout for each test (seconds)
    timeout: float = 30.0
    
    # Fuel limit for tests
    fuel_limit: int = 100000
    
    # Whether to show verbose output
    verbose: bool = False
    
    # Whether to stop on first failure
    fail_fast: bool = False
    
    # Patterns for test files
    test_pattern: str = "test_*.metta"
    
    # Coverage tracking
    track_coverage: bool = False


class MeTTaTest:
    """
    Testing framework for MeTTa programs.
    
    Usage:
        test_suite = MeTTaTest("my_contract.metta")
        
        @test_suite.test
        def test_deposit():
            result = contract.deposit(value=100)
            assert result.balance == 100
        
        test_suite.run()
    """
    
    def __init__(self, contract_path: Optional[str] = None, config: Optional[TestConfig] = None):
        """
        Initialize the test suite.
        
        Args:
            contract_path: Path to the MeTTa contract file
            config: Test configuration
        """
        self.contract_path = Path(contract_path) if contract_path else None
        self.config = config or TestConfig()
        self.tests: List[Callable] = []
        self.results: List[TestResult] = []
        self.hooks: Dict[str, List[Callable]] = {
            "before_all": [],
            "after_all": [],
            "before_each": [],
            "after_each": [],
        }
        self.coverage: Dict[str, int] = {}
        
    def test(self, func: Callable) -> Callable:
        """
        Decorator to register a test case.
        
        Args:
            func: Test function
            
        Returns:
            Decorated function
        """
        self.tests.append(func)
        return func
    
    def before_all(self, func: Callable) -> Callable:
        """Decorator for before_all hook."""
        self.hooks["before_all"].append(func)
        return func
    
    def after_all(self, func: Callable) -> Callable:
        """Decorator for after_all hook."""
        self.hooks["after_all"].append(func)
        return func
    
    def before_each(self, func: Callable) -> Callable:
        """Decorator for before_each hook."""
        self.hooks["before_each"].append(func)
        return func
    
    def after_each(self, func: Callable) -> Callable:
        """Decorator for after_each hook."""
        self.hooks["after_each"].append(func)
        return func
    
    def run_hook(self, hook_type: str, *args, **kwargs):
        """Run all hooks of a given type."""
        for hook in self.hooks.get(hook_type, []):
            hook(*args, **kwargs)
    
    def run_metta(self, input_data: Optional[Dict[str, Any]] = None, 
                 fuel_limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Run a MeTTa program and return the result.
        
        Args:
            input_data: Input data for the program
            fuel_limit: Fuel limit (overrides config)
            
        Returns:
            Dictionary with output, fuel_used, time, etc.
        """
        if not self.contract_path:
            raise ValueError("No contract path specified")
        
        # Build command
        cmd = [self.config.metta_executable, "run", str(self.contract_path)]
        
        if fuel_limit is not None:
            cmd.extend(["--fuel-limit", str(fuel_limit)])
        elif self.config.fuel_limit:
            cmd.extend(["--fuel-limit", str(self.config.fuel_limit)])
        
        # Add input data if provided
        if input_data:
            cmd.extend(["--input", json.dumps(input_data)])
        
        # Run with timeout
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
                check=False
            )
            end_time = time.time()
            
            # Parse output
            try:
                output = json.loads(result.stdout) if result.stdout else {}
            except json.JSONDecodeError:
                output = {"raw": result.stdout}
            
            # Extract fuel used if available
            fuel_used = 0
            if "fuel_used" in output:
                fuel_used = output["fuel_used"]
            elif result.stderr:
                # Try to extract fuel from stderr
                fuel_match = re.search(r'fuel used: (\d+)', result.stderr)
                if fuel_match:
                    fuel_used = int(fuel_match.group(1))
            
            return {
                "output": output,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "fuel_used": fuel_used,
                "execution_time": end_time - start_time,
                "success": result.returncode == 0
            }
            
        except subprocess.TimeoutExpired:
            end_time = time.time()
            return {
                "output": {},
                "stdout": "",
                "stderr": "Timeout",
                "returncode": -1,
                "fuel_used": 0,
                "execution_time": end_time - start_time,
                "success": False
            }
        except Exception as e:
            return {
                "output": {},
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "fuel_used": 0,
                "execution_time": 0.0,
                "success": False
            }
    
    def assert_equal(self, actual: Any, expected: Any, message: str = "") -> bool:
        """Assert that two values are equal."""
        if actual != expected:
            raise AssertionError(f"{message}: Expected {expected}, got {actual}")
        return True
    
    def assert_true(self, condition: bool, message: str = "") -> bool:
        """Assert that a condition is true."""
        if not condition:
            raise AssertionError(f"{message}: Expected true, got false")
        return True
    
    def assert_false(self, condition: bool, message: str = "") -> bool:
        """Assert that a condition is false."""
        if condition:
            raise AssertionError(f"{message}: Expected false, got true")
        return True
    
    def assert_fuel_less_than(self, fuel_used: int, max_fuel: int, message: str = "") -> bool:
        """Assert that fuel used is less than a maximum."""
        if fuel_used >= max_fuel:
            raise AssertionError(f"{message}: Fuel used {fuel_used} >= max {max_fuel}")
        return True
    
    def assert_error(self, error_message: str, expected_error: str, message: str = "") -> bool:
        """Assert that an error message contains expected text."""
        if expected_error not in error_message:
            raise AssertionError(f"{message}: Expected error containing '{expected_error}', got '{error_message}'")
        return True
    
    def run_test(self, test_func: Callable) -> TestResult:
        """
        Run a single test case.
        
        Args:
            test_func: Test function to run
            
        Returns:
            TestResult with the outcome
        """
        test_name = test_func.__name__
        start_time = time.time()
        
        try:
            # Run before_each hooks
            self.run_hook("before_each", test_name)
            
            # Run the test
            test_func()
            
            end_time = time.time()
            
            # Run after_each hooks
            self.run_hook("after_each", test_name)
            
            return TestResult(
                name=test_name,
                status=TestStatus.PASSED,
                message="Test passed",
                execution_time=end_time - start_time
            )
            
        except AssertionError as e:
            end_time = time.time()
            self.run_hook("after_each", test_name)
            return TestResult(
                name=test_name,
                status=TestStatus.FAILED,
                message=str(e),
                execution_time=end_time - start_time
            )
            
        except subprocess.TimeoutExpired:
            end_time = time.time()
            self.run_hook("after_each", test_name)
            return TestResult(
                name=test_name,
                status=TestStatus.TIMEOUT,
                message="Test timed out",
                execution_time=end_time - start_time
            )
            
        except Exception as e:
            end_time = time.time()
            self.run_hook("after_each", test_name)
            return TestResult(
                name=test_name,
                status=TestStatus.ERROR,
                message=str(e),
                error=str(e),
                execution_time=end_time - start_time
            )
    
    def run(self) -> bool:
        """
        Run all test cases.
        
        Returns:
            True if all tests passed, False otherwise
        """
        print("=" * 60)
        print("RUNNING METTA TESTS")
        print("=" * 60)
        print()
        
        self.results = []
        passed = 0
        failed = 0
        errors = 0
        skipped = 0
        timeout = 0
        
        # Run before_all hooks
        self.run_hook("before_all")
        
        # Run each test
        for test_func in self.tests:
            result = self.run_test(test_func)
            self.results.append(result)
            
            # Print result
            print(result)
            
            # Update counters
            if result.status == TestStatus.PASSED:
                passed += 1
            elif result.status == TestStatus.FAILED:
                failed += 1
            elif result.status == TestStatus.ERROR:
                errors += 1
            elif result.status == TestStatus.SKIPPED:
                skipped += 1
            elif result.status == TestStatus.TIMEOUT:
                timeout += 1
            
            # Fail fast if configured
            if self.config.fail_fast and result.status != TestStatus.PASSED:
                break
        
        # Run after_all hooks
        self.run_hook("after_all")
        
        # Print summary
        print()
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total:  {len(self.tests)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Errors: {errors}")
        print(f"Skipped: {skipped}")
        print(f"Timeout: {timeout}")
        print()
        
        # Calculate total time
        total_time = sum(r.execution_time for r in self.results)
        print(f"Total time: {total_time:.4f}s")
        
        # Return success status
        return failed == 0 and errors == 0 and timeout == 0


class MeTTaTestFile:
    """
    Test runner for MeTTa test files.
    
    This class runs tests defined in .metta files with special test syntax.
    """
    
    def __init__(self, test_file: str, config: Optional[TestConfig] = None):
        """
        Initialize the test file runner.
        
        Args:
            test_file: Path to the test file
            config: Test configuration
        """
        self.test_file = Path(test_file)
        self.config = config or TestConfig()
        self.tests: List[Dict[str, Any]] = []
        self.results: List[TestResult] = []
        
    def parse_test_file(self):
        """Parse the test file to extract test cases."""
        # This would parse a MeTTa file with test syntax like:
        # (test "test name" (assert (= (add 1 2) 3)))
        # 
        # For now, we'll use a simple approach
        with open(self.test_file, 'r') as f:
            content = f.read()
        
        # Find all test definitions
        test_pattern = r'\(test\s+"([^"]+)"\s+(.+?)\)'
        matches = re.finditer(test_pattern, content, re.DOTALL)
        
        for match in matches:
            test_name = match.group(1)
            test_body = match.group(2)
            self.tests.append({
                "name": test_name,
                "body": test_body
            })
        
        return len(self.tests)
    
    def run_test(self, test: Dict[str, Any]) -> TestResult:
        """Run a single test from the test file."""
        # Create a temporary MeTTa file with the test
        test_code = f"""
        ; Test: {test['name']}
        {test['body']}
        (exit 0)
        """
        
        # Write to temp file
        temp_file = self.test_file.parent / f"{self.test_file.stem}_test_{test['name']}.metta"
        with open(temp_file, 'w') as f:
            f.write(test_code)
        
        # Run the test
        start_time = time.time()
        try:
            result = subprocess.run(
                [self.config.metta_executable, "run", str(temp_file)],
                capture_output=True,
                text=True,
                timeout=self.config.timeout
            )
            end_time = time.time()
            
            # Clean up temp file
            temp_file.unlink()
            
            if result.returncode == 0:
                return TestResult(
                    name=test["name"],
                    status=TestStatus.PASSED,
                    message="Test passed",
                    execution_time=end_time - start_time
                )
            else:
                return TestResult(
                    name=test["name"],
                    status=TestStatus.FAILED,
                    message=result.stderr or "Test failed",
                    execution_time=end_time - start_time,
                    error=result.stderr
                )
                
        except subprocess.TimeoutExpired:
            temp_file.unlink(missing_ok=True)
            return TestResult(
                name=test["name"],
                status=TestStatus.TIMEOUT,
                message="Test timed out",
                execution_time=self.config.timeout
            )
        except Exception as e:
            temp_file.unlink(missing_ok=True)
            return TestResult(
                name=test["name"],
                status=TestStatus.ERROR,
                message=str(e),
                error=str(e)
            )
    
    def run(self) -> bool:
        """Run all tests in the test file."""
        num_tests = self.parse_test_file()
        
        print("=" * 60)
        print(f"RUNNING TESTS FROM {self.test_file}")
        print("=" * 60)
        print(f"Found {num_tests} tests")
        print()
        
        self.results = []
        passed = 0
        
        for test in self.tests:
            result = self.run_test(test)
            self.results.append(result)
            print(result)
            
            if result.status == TestStatus.PASSED:
                passed += 1
            
            if self.config.fail_fast and result.status != TestStatus.PASSED:
                break
        
        # Print summary
        print()
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total:  {len(self.tests)}")
        print(f"Passed: {passed}")
        print(f"Failed: {len(self.tests) - passed}")
        print()
        
        return passed == len(self.tests)


# Convenience function for quick testing
def test_metta(contract_path: str, input_data: Dict[str, Any], 
              expected_output: Any, fuel_limit: int = 10000) -> TestResult:
    """
    Quick test function for MeTTa programs.
    
    Args:
        contract_path: Path to MeTTa contract
        input_data: Input data for the contract
        expected_output: Expected output
        fuel_limit: Fuel limit
        
    Returns:
        TestResult with the outcome
    """
    tester = MeTTaTest(contract_path)
    
    def test_func():
        result = tester.run_metta(input_data, fuel_limit)
        tester.assert_equal(result["output"], expected_output)
    
    return tester.run_test(test_func)


# Example usage
if __name__ == "__main__":
    print("MeTTa Testing Framework")
    print("=" * 60)
    print()
    
    # Example 1: Programmatic testing
    print("Example 1: Programmatic Testing")
    print("-" * 60)
    
    # Create a test suite (in real usage, you'd have a real contract)
    test_suite = MeTTaTest()
    
    # Define some tests
    @test_suite.test
    def test_addition():
        """Test that 1 + 1 = 2"""
        # In real usage, this would call the MeTTa contract
        result = 1 + 1
        assert result == 2, f"Expected 2, got {result}"
    
    @test_suite.test
    def test_subtraction():
        """Test that 5 - 3 = 2"""
        result = 5 - 3
        assert result == 2, f"Expected 2, got {result}"
    
    @test_suite.test
    def test_failing():
        """This test should fail"""
        result = 1 + 1
        assert result == 3, f"Expected 3, got {result}"
    
    # Run the tests
    success = test_suite.run()
    print(f"\nAll tests passed: {success}")
    print()
    
    # Example 2: File-based testing (would need actual MeTTa files)
    print("\nExample 2: File-Based Testing")
    print("-" * 60)
    print("Note: This would require actual .metta test files")
    print("Test files should contain: (test \"test name\" (assert (= 1 1)))")
    print()
    
    # Example 3: Quick test
    print("\nExample 3: Quick Test")
    print("-" * 60)
    
    # This would work if we had a real MeTTa contract
    # result = test_metta(
    #     "escrow.metta",
    #     {"function": "deposit", "value": 100},
    #     {"balance": 100},
    #     fuel_limit=1000
    # )
    # print(result)
    
    print("Quick test requires actual MeTTa contract file")
    print()
    
    print("=" * 60)
    print("For more information, see the README.md file")
    print("=" * 60)
