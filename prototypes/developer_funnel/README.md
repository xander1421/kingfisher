# Developer Funnel - Prototype Implementation

## Overview

This directory contains prototypes for building the MeTTa developer funnel, making it easier for Solidity and Rust developers to adopt MeTTa. The goal is to provide familiar tooling and workflows that reduce the learning curve.

## Problem Statement

MeTTa currently has a steep learning curve for developers coming from Solidity or Rust:
- **No familiar tooling**: No VS Code extension, no debugging support
- **No migration path**: No way to convert existing Solidity contracts to MeTTa
- **No testing framework**: No equivalent to Foundry or Hardhat for testing
- **Limited IDE support**: No syntax highlighting, autocomplete, or linting

This creates a significant barrier to adoption.

## Proposed Solutions

### 1. Solidity → MeTTa Transpiler

A tool that converts Solidity smart contracts to MeTTa code, allowing developers to:
- Migrate existing contracts to MeTTa
- Learn MeTTa syntax by seeing Solidity constructs mapped to MeTTa equivalents
- Gradually adopt MeTTa by transpiling parts of their codebase

### 2. VS Code Extension

A full-featured VS Code extension providing:
- Syntax highlighting
- Linting (unbound variables, type errors)
- Autocomplete
- Debugging
- Fuel estimation

### 3. Testing Framework

A testing framework inspired by Foundry that provides:
- Test case definitions
- Assertions
- Mocking
- Coverage tracking
- Fuel estimation

## Files

### 1. `solidity_to_metta.py`

Proof-of-concept Solidity to MeTTa transpiler.

**Features:**
- Parses basic Solidity syntax (in production, would use slither or solc)
- Maps Solidity types to MeTTa types
- Converts control structures (if, for, while)
- Handles function calls and expressions
- Supports special Solidity variables (msg.value, msg.sender, etc.)

**Usage:**
```python
from solidity_to_metta import SolidityToMettaTranspiler

solidity_code = """
contract Escrow {
    address public owner;
    uint256 public balance;

    function deposit() external payable {
        balance += msg.value;
    }

    function withdraw() external {
        require(msg.sender == owner, "Not owner");
        payable(msg.sender).transfer(balance);
    }
}
"""

transpiler = SolidityToMettaTranspiler()
metta_code = transpiler.transpile_contract("Escrow", parse_solidity(solidity_code))
print(metta_code)
```

**Example Output:**
```metta
; Contract: Escrow
(def Escrow (State
  owner Address
  balance Number
))

; Function: deposit
(def deposit (lambda ()
  (set! balance (+ balance (value msg)))
))

; Function: withdraw
(def withdraw (lambda ()
  (unless (= (sender msg) owner) (error "Not owner"))
  (transfer (sender msg) balance)
))
```

**Type Mapping:**

| Solidity Type | MeTTa Type |
|---------------|------------|
| uint256 | Number |
| int256 | Number |
| bool | Bool |
| address | Address |
| bytes32 | Bytes32 |
| string | String |
| bytes | Bytes |
| T[] | (List T) |
| mapping(K => V) | (HashMap K V) |
| struct S | S |

**Control Structure Mapping:**

| Solidity | MeTTa |
|---------|-------|
| if (cond) { ... } else { ... } | (if cond then ... else ...) |
| for (init; cond; post) { ... } | (do init (while cond (do ... post))) |
| while (cond) { ... } | (while cond ...) |
| require(cond, "msg") | (unless cond (error "msg")) |
| assert(cond) | (assert cond) |
| revert("msg") | (error "msg") |

### 2. VS Code Extension Files

#### `package.json`

VS Code extension manifest with:
- Language support registration
- Syntax highlighting
- Commands for debugging, fuel estimation, and testing
- Configuration options

**Key Features:**
- Language ID: `metta`
- File extensions: `.metta`, `.mtt`
- Commands:
  - `metta.startDebug`: Start MeTTa debugger
  - `metta.estimateFuel`: Estimate fuel cost
  - `metta.runTest`: Run MeTTa tests
  - `metta.formatDocument`: Format MeTTa document

#### `metta.tmLanguage.json`

Syntax highlighting rules for MeTTa.

**Highlighted Elements:**
- Comments (line and block)
- Strings
- Numbers (decimal, hex, float)
- Booleans (true, false, nil)
- Keywords (def, lambda, if, unless, when, cond, do, while, etc.)
- Special forms (let, set!, match, unify, query, assert, error)
- Type keywords (State, Type, Number, String, Bool, Address, List, HashMap, Atom, Symbol)
- Operators (+, -, *, /, %, =, !=, >, <, >=, <=, and, or, not)
- Punctuation (parentheses, brackets, braces)
- Variables and functions

#### `language-configuration.json`

Language configuration for VS Code:
- Comments syntax
- Brackets and auto-closing pairs
- Indentation rules
- Word pattern for identifier recognition
- On-enter rules for automatic indentation
- Folding markers

### 3. `metta_test.py`

Testing framework for MeTTa programs.

**Features:**
- Programmatic test definitions with decorators
- File-based test execution
- Assertions (equal, true, false, fuel_less_than, error)
- Test hooks (before_all, after_all, before_each, after_each)
- Test result reporting
- Fuel tracking
- Execution time tracking
- Fail-fast mode

**Usage:**

**Programmatic Testing:**
```python
from metta_test import MeTTaTest

test_suite = MeTTaTest("escrow.metta")

@test_suite.test
def test_deposit():
    result = contract.deposit(value=100)
    test_suite.assert_equal(result.balance, 100)

@test_suite.test
def test_withdraw_not_owner():
    with test_suite.assert_raises("Not owner"):
        contract.withdraw(sender="0x123")

success = test_suite.run()
```

**File-Based Testing:**
Create a test file `escrow_test.metta`:
```metta
(test "deposit increases balance"
  (let ((contract (Escrow))
       (result (deposit contract 100)))
    (assert (= (balance result) 100))))

(test "withdraw fails if not owner"
  (let ((contract (Escrow owner "0x123")))
    (assert-error "Not owner"
      (withdraw contract sender "0x456"))))
```

Run with:
```python
from metta_test import MeTTaTestFile

test_file = MeTTaTestFile("escrow_test.metta")
test_file.run()
```

**Quick Testing:**
```python
from metta_test import test_metta

result = test_metta(
    "escrow.metta",
    {"function": "deposit", "value": 100},
    {"balance": 100},
    fuel_limit=1000
)
print(result)
```

## Integration Guide

### Step 1: Set Up VS Code Extension

1. Install dependencies:
```bash
npm install
```

2. Build the extension:
```bash
npm run compile
```

3. Package for distribution:
```bash
vsce package
```

4. Install in VS Code:
- Open VS Code
- Run `Extensions: Install from VSIX...`
- Select the generated `.vsix` file

### Step 2: Use the Transpiler

1. Install slither for full Solidity parsing:
```bash
pip install slither-analyzer
```

2. Run the transpiler:
```bash
python solidity_to_metta.py input.sol output.metta
```

3. Review and refine the generated MeTTa code

### Step 3: Write Tests

1. Create a test file:
```bash
touch my_contract_test.metta
```

2. Write tests using the test syntax:
```metta
(test "test name"
  (assert (= (function arg1 arg2) expected)))
```

3. Run tests:
```bash
python metta_test.py my_contract_test.metta
```

## Testing the Prototypes

### Test the Transpiler

```bash
python solidity_to_metta.py
```

This runs the example in the file, showing Solidity to MeTTa conversion.

### Test the Testing Framework

```bash
python metta_test.py
```

This runs the example tests defined in the file.

## Next Steps

### For the Transpiler

1. **Integrate slither**: Use slither for full Solidity AST parsing
2. **Handle more constructs**: Add support for:
   - Events
   - Modifiers
   - Inheritance
   - Interfaces
   - Try/catch
   - Assembly blocks
3. **Type system**: Implement full type checking and conversion
4. **Optimization**: Add optimization passes for generated MeTTa code
5. **CLI**: Create a command-line interface

### For the VS Code Extension

1. **Implement language server**: Use vscode-languageserver for full LSP support
2. **Add linting**: Implement semantic analysis for:
   - Unbound variables
   - Type errors
   - Unused variables
   - Shadowed variables
3. **Add autocomplete**: Provide suggestions for:
   - MeTTa keywords
   - Variables in scope
   - Function names
   - Type names
4. **Add debugger**: Implement a debugger adapter for MeTTa
5. **Add fuel estimator**: Analyze code to estimate fuel costs

### For the Testing Framework

1. **Add mocking**: Support for mocking external calls
2. **Add coverage**: Track which lines of code are executed
3. **Add fixtures**: Support for test fixtures
4. **Add parameterized tests**: Support for running the same test with different inputs
5. **Add CI integration**: GitHub Actions support

## Architecture

### Transpiler Architecture

```
Solidity Source
    ↓
Slither/Solc Parser (AST)
    ↓
AST Transformer (Solidity → MeTTa)
    ↓
MeTTa Code Generator
    ↓
MeTTa Source
```

### VS Code Extension Architecture

```
VS Code API
    ↓
Extension Host
    ↓
Language Server Protocol (LSP)
    ↓
MeTTa Language Server
    ↓
MeTTa Interpreter (for execution, fuel estimation)
```

### Testing Framework Architecture

```
Test Definitions
    ↓
Test Runner
    ↓
MeTTa Interpreter (with fuel tracking)
    ↓
Test Results (pass/fail, fuel used, time)
```

## References

- [VS Code Extension Guide](https://code.visualstudio.com/api)
- [Language Server Protocol](https://microsoft.github.io/language-server-protocol/)
- [Slither Documentation](https://github.com/crytic/slither)
- [Foundry Testing Framework](https://book.getfoundry.sh/forge/tests)
- [Hardhat Testing](https://hardhat.org/docs/guides/writing-tests)
