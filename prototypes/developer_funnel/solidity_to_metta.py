"""
Solidity to MeTTa Transpiler (Proof of Concept)

This transpiler converts Solidity smart contracts to MeTTa code, making it easier
for Solidity developers to adopt MeTTa. It uses Slither for parsing Solidity AST.
"""

import re
import json
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field


@dataclass
class TranspilerConfig:
    """Configuration for the transpiler."""
    # Mapping from Solidity types to MeTTa types
    type_mapping: Dict[str, str] = field(default_factory=lambda: {
        "uint256": "Number",
        "uint": "Number",
        "int256": "Number",
        "int": "Number",
        "bool": "Bool",
        "address": "Address",
        "bytes32": "Bytes32",
        "string": "String",
        "bytes": "Bytes",
    })
    
    # Whether to include comments in output
    include_comments: bool = True
    
    # Whether to validate types
    validate_types: bool = True
    
    # Indentation settings
    indent: str = "  "


@dataclass
class TranspilerContext:
    """Context for the transpiler (current state)."""
    # Current contract being transpiled
    current_contract: Optional[str] = None
    
    # Current function being transpiled
    current_function: Optional[str] = None
    
    # Stack of nested expressions
    expression_stack: List[str] = field(default_factory=list)
    
    # Variables in scope
    variables: Dict[str, str] = field(default_factory=dict)
    
    # Type information
    types: Dict[str, str] = field(default_factory=dict)


class SolidityToMettaTranspiler:
    """
    Transpiles Solidity code to MeTTa.
    
    This is a proof of concept that demonstrates the basic approach.
    For a production transpiler, you would need:
    1. Full Solidity AST parsing (using slither or solc)
    2. Complete type system mapping
    3. Control flow conversion
    4. Error handling
    5. Optimization passes
    """
    
    def __init__(self, config: Optional[TranspilerConfig] = None):
        """
        Initialize the transpiler.
        
        Args:
            config: Transpiler configuration
        """
        self.config = config or TranspilerConfig()
        self.context = TranspilerContext()
        self.output: List[str] = []
        self.errors: List[str] = []
        
    def reset(self):
        """Reset the transpiler state."""
        self.context = TranspilerContext()
        self.output = []
        self.errors = []
        
    def add_output(self, line: str, indent: int = 0):
        """Add a line to the output with optional indentation."""
        if line.strip():
            self.output.append(self.config.indent * indent + line)
        
    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)
        
    def map_type(self, solidity_type: str) -> str:
        """
        Map a Solidity type to a MeTTa type.
        
        Args:
            solidity_type: Solidity type string (e.g., "uint256", "address")
            
        Returns:
            MeTTa type string
        """
        # Handle array types
        if solidity_type.endswith("]"):
            base_type = solidity_type.split("[")[0]
            metta_base = self.map_type(base_type)
            return f"(List {metta_base})"
        
        # Handle mapping types
        if solidity_type.startswith("mapping("):
            # Extract key and value types
            match = re.match(r"mapping\((.*?) => (.*?)\)", solidity_type)
            if match:
                key_type = self.map_type(match.group(1))
                value_type = self.map_type(match.group(2))
                return f"(HashMap {key_type} {value_type})"
            return "HashMap"
        
        # Handle struct types (keep as-is for now)
        if solidity_type.startswith("struct "):
            return solidity_type.replace("struct ", "")
        
        # Use configured mapping
        return self.config.type_mapping.get(solidity_type, "Any")
    
    def transpile_contract(self, contract_name: str, contract_ast: Dict[str, Any]) -> str:
        """
        Transpile a Solidity contract to MeTTa.
        
        Args:
            contract_name: Name of the contract
            contract_ast: AST of the contract
            
        Returns:
            MeTTa code string
        """
        self.reset()
        self.context.current_contract = contract_name
        
        # Add contract header
        self.add_output(f"; Contract: {contract_name}", 0)
        self.add_output("")
        
        # Transpile state variables
        state_vars = contract_ast.get("state_variables", [])
        if state_vars:
            self.add_output(f"(def {contract_name} (State", 0)
            for var in state_vars:
                var_name = var.get("name", "unknown")
                var_type = self.map_type(var.get("type", "Any"))
                self.context.variables[var_name] = var_type
                self.context.types[var_name] = var_type
                self.add_output(f"  {var_name} {var_type}", 1)
            self.add_output("))", 0)
            self.add_output("")
        
        # Transpile functions
        functions = contract_ast.get("functions", [])
        for func in functions:
            self.transpile_function(contract_name, func)
        
        # Transpile constructors
        constructors = contract_ast.get("constructors", [])
        for constructor in constructors:
            self.transpile_constructor(contract_name, constructor)
        
        return "\n".join(self.output)
    
    def transpile_function(self, contract_name: str, func_ast: Dict[str, Any]):
        """
        Transpile a Solidity function to MeTTa.
        
        Args:
            contract_name: Name of the containing contract
            func_ast: AST of the function
        """
        func_name = func_ast.get("name", "unknown")
        visibility = func_ast.get("visibility", "internal")
        state_mutability = func_ast.get("state_mutability", "non-payable")
        parameters = func_ast.get("parameters", [])
        return_type = func_ast.get("return_type", None)
        body = func_ast.get("body", None)
        
        self.context.current_function = func_name
        
        # Add function header
        self.add_output(f"; Function: {func_name}", 0)
        
        # Handle parameters
        param_names = []
        for param in parameters:
            param_name = param.get("name", "arg")
            param_type = self.map_type(param.get("type", "Any"))
            param_names.append(param_name)
            self.context.variables[param_name] = param_type
            self.context.types[param_name] = param_type
        
        # Transpile function body
        if body:
            metta_body = self.transpile_expression(body)
        else:
            metta_body = "nil"
        
        # Generate MeTTa function definition
        self.add_output(f"(def {func_name} (lambda ({' '.join(param_names)})", 0)
        self.add_output(f"  {metta_body}", 1)
        self.add_output("))", 0)
        self.add_output("")
        
        self.context.current_function = None
    
    def transpile_constructor(self, contract_name: str, constructor_ast: Dict[str, Any]):
        """
        Transpile a Solidity constructor to MeTTa.
        
        Args:
            contract_name: Name of the contract
            constructor_ast: AST of the constructor
        """
        parameters = constructor_ast.get("parameters", [])
        body = constructor_ast.get("body", None)
        
        self.add_output(f"; Constructor for {contract_name}", 0)
        
        # Handle parameters
        param_names = []
        for param in parameters:
            param_name = param.get("name", "arg")
            param_type = self.map_type(param.get("type", "Any"))
            param_names.append(param_name)
            self.context.variables[param_name] = param_type
            self.context.types[param_name] = param_type
        
        # Transpile constructor body
        if body:
            metta_body = self.transpile_expression(body)
        else:
            metta_body = "nil"
        
        # Generate MeTTa constructor
        self.add_output(f"(def constructor-{contract_name} (lambda ({' '.join(param_names)})", 0)
        self.add_output(f"  {metta_body}", 1)
        self.add_output("))", 0)
        self.add_output("")
    
    def transpile_expression(self, expr: Any) -> str:
        """
        Recursively transpile a Solidity expression to MeTTa.
        
        Args:
            expr: Expression AST or string
            
        Returns:
            MeTTa expression string
        """
        if isinstance(expr, str):
            return self.transpile_identifier(expr)
        
        if isinstance(expr, dict):
            expr_type = expr.get("type", "")
            
            # Handle different expression types
            if expr_type == "BinaryOperation":
                return self.transpile_binary_operation(expr)
            elif expr_type == "UnaryOperation":
                return self.transpile_unary_operation(expr)
            elif expr_type == "IfStatement":
                return self.transpile_if_statement(expr)
            elif expr_type == "ForStatement":
                return self.transpile_for_statement(expr)
            elif expr_type == "WhileStatement":
                return self.transpile_while_statement(expr)
            elif expr_type == "FunctionCall":
                return self.transpile_function_call(expr)
            elif expr_type == "MemberAccess":
                return self.transpile_member_access(expr)
            elif expr_type == "IndexAccess":
                return self.transpile_index_access(expr)
            elif expr_type == "Assignment":
                return self.transpile_assignment(expr)
            elif expr_type == "VariableDeclaration":
                return self.transpile_variable_declaration(expr)
            elif expr_type == "ReturnStatement":
                return self.transpile_return_statement(expr)
            elif expr_type == "Literal":
                return self.transpile_literal(expr)
            elif expr_type == "Identifier":
                return self.transpile_identifier(expr.get("name", "unknown"))
            else:
                # Unknown expression type - return as comment
                self.add_error(f"Unknown expression type: {expr_type}")
                return f"; TODO: {expr_type}"
        
        if isinstance(expr, list):
            # Transpile list of expressions
            metta_exprs = [self.transpile_expression(e) for e in expr]
            return "(do " + " ".join(metta_exprs) + ")"
        
        return str(expr)
    
    def transpile_binary_operation(self, expr: Dict[str, Any]) -> str:
        """Transpile a binary operation (e.g., a + b)."""
        left = self.transpile_expression(expr.get("left", ""))
        right = self.transpile_expression(expr.get("right", ""))
        operator = expr.get("operator", "?")
        
        # Map Solidity operators to MeTTa operators
        op_map = {
            "+": "+",
            "-": "-",
            "*": "*",
            "/": "/",
            "%": "mod",
            "**": "pow",
            "==": "=",
            "!=": "!=",
            ">": ">",
            "<": "<",
            ">=": ">=",
            "<=": "<=",
            "&&": "and",
            "||": "or",
            "^": "xor",
            "&": "bit-and",
            "|": "bit-or",
            "<<": "shift-left",
            ">>": "shift-right",
        }
        
        metta_op = op_map.get(operator, operator)
        return f"({metta_op} {left} {right})"
    
    def transpile_unary_operation(self, expr: Dict[str, Any]) -> str:
        """Transpile a unary operation (e.g., !x, -x)."""
        operand = self.transpile_expression(expr.get("operand", ""))
        operator = expr.get("operator", "?")
        
        op_map = {
            "!": "not",
            "-": "neg",
            "~": "bit-not",
        }
        
        metta_op = op_map.get(operator, operator)
        return f"({metta_op} {operand})"
    
    def transpile_if_statement(self, expr: Dict[str, Any]) -> str:
        """Transpile an if statement."""
        condition = self.transpile_expression(expr.get("condition", "true"))
        true_body = self.transpile_expression(expr.get("true_body", "nil"))
        false_body = self.transpile_expression(expr.get("false_body", "nil"))
        
        return f"(if {condition} {true_body} {false_body})"
    
    def transpile_for_statement(self, expr: Dict[str, Any]) -> str:
        """Transpile a for loop."""
        # For loops in Solidity are typically: for (init; condition; post) { body }
        init = expr.get("init", None)
        condition = expr.get("condition", "true")
        post = expr.get("post", None)
        body = expr.get("body", "nil")
        
        # Transpile to MeTTa's map or while loop
        # Simple approach: use while loop
        init_expr = self.transpile_expression(init) if init else "nil"
        condition_expr = self.transpile_expression(condition)
        body_expr = self.transpile_expression(body)
        post_expr = self.transpile_expression(post) if post else "nil"
        
        # For now, use a simple while loop structure
        # A better approach would be to use MeTTa's map for iterators
        return f"(do {init_expr} (while {condition_expr} (do {body_expr} {post_expr})))"
    
    def transpile_while_statement(self, expr: Dict[str, Any]) -> str:
        """Transpile a while loop."""
        condition = self.transpile_expression(expr.get("condition", "true"))
        body = self.transpile_expression(expr.get("body", "nil"))
        
        return f"(while {condition} {body})"
    
    def transpile_function_call(self, expr: Dict[str, Any]) -> str:
        """Transpile a function call."""
        func_name = expr.get("function", "unknown")
        args = expr.get("arguments", [])
        
        # Handle special functions
        if func_name == "require":
            condition = self.transpile_expression(args[0] if args else "true")
            message = self.transpile_expression(args[1] if len(args) > 1 else '"require failed"')
            return f"(unless {condition} (error {message}))"
        
        if func_name == "assert":
            condition = self.transpile_expression(args[0] if args else "true")
            return f"(assert {condition})"
        
        if func_name == "revert":
            message = self.transpile_expression(args[0] if args else '"revert"')
            return f"(error {message})"
        
        # Handle msg.value, msg.sender, etc.
        if func_name.startswith("msg."):
            member = func_name.split(".")[1]
            return f"({member} msg)"
        
        # Handle this.
        if func_name.startswith("this."):
            member = func_name.split(".")[1]
            return f"({member} {self.context.current_contract})"
        
        # Regular function call
        metta_args = [self.transpile_expression(arg) for arg in args]
        return f"({func_name} {' '.join(metta_args)})"
    
    def transpile_member_access(self, expr: Dict[str, Any]) -> str:
        """Transpile member access (e.g., x.y)."""
        obj = self.transpile_expression(expr.get("object", ""))
        member = expr.get("member", "unknown")
        
        return f"({member} {obj})"
    
    def transpile_index_access(self, expr: Dict[str, Any]) -> str:
        """Transpile index access (e.g., x[y])."""
        obj = self.transpile_expression(expr.get("object", ""))
        index = self.transpile_expression(expr.get("index", "0"))
        
        return f"(nth {obj} {index})"
    
    def transpile_assignment(self, expr: Dict[str, Any]) -> str:
        """Transpile an assignment (e.g., x = y)."""
        left = expr.get("left", "")
        right = expr.get("right", "")
        
        # Handle different assignment types
        if isinstance(left, dict) and left.get("type") == "MemberAccess":
            # x.y = z
            obj = self.transpile_expression(left.get("object", ""))
            member = left.get("member", "unknown")
            right_expr = self.transpile_expression(right)
            return f"(set! ({member} {obj}) {right_expr})"
        elif isinstance(left, dict) and left.get("type") == "IndexAccess":
            # x[y] = z
            obj = self.transpile_expression(left.get("object", ""))
            index = self.transpile_expression(left.get("index", "0"))
            right_expr = self.transpile_expression(right)
            return f"(set-nth! {obj} {index} {right_expr})"
        else:
            # Simple variable assignment
            left_name = left.get("name", left) if isinstance(left, dict) else left
            right_expr = self.transpile_expression(right)
            return f"(set! {left_name} {right_expr})"
    
    def transpile_variable_declaration(self, expr: Dict[str, Any]) -> str:
        """Transpile a variable declaration."""
        var_name = expr.get("name", "unknown")
        var_type = self.map_type(expr.get("type", "Any"))
        value = expr.get("value", None)
        
        self.context.variables[var_name] = var_type
        self.context.types[var_name] = var_type
        
        if value:
            value_expr = self.transpile_expression(value)
            return f"(let (({var_name} {value_expr})) {var_name})"
        else:
            return f"(let {var_name} {var_type})"
    
    def transpile_return_statement(self, expr: Dict[str, Any]) -> str:
        """Transpile a return statement."""
        value = expr.get("value", "nil")
        value_expr = self.transpile_expression(value)
        return f"(return {value_expr})"
    
    def transpile_literal(self, expr: Dict[str, Any]) -> str:
        """Transpile a literal value."""
        value = expr.get("value", "")
        type_ = expr.get("type", "")
        
        if type_ == "Number":
            return str(value)
        elif type_ == "Bool":
            return "true" if value else "false"
        elif type_ == "String":
            return f'"{value}"'
        elif type_ == "HexNumber":
            return str(int(value, 16))
        else:
            return str(value)
    
    def transpile_identifier(self, name: str) -> str:
        """Transpile an identifier (variable name)."""
        # Handle special identifiers
        if name == "msg.value":
            return "(value msg)"
        elif name == "msg.sender":
            return "(sender msg)"
        elif name == "block.timestamp":
            return "(timestamp block)"
        elif name == "block.number":
            return "(number block)"
        elif name == "tx.origin":
            return "(origin tx)"
        elif name == "address(this)":
            return f"(address {self.context.current_contract})"
        
        return name


# Simple Solidity AST parser (for demo without slither)
def parse_simple_solidity(solidity_code: str) -> Dict[str, Any]:
    """
    Simple parser for basic Solidity code (for demo purposes).
    In production, use slither or solc for full AST parsing.
    """
    # This is a simplified parser for the example
    # Real implementation would use slither
    
    ast = {
        "contracts": []
    }
    
    # Extract contract
    contract_match = re.search(r'contract\s+(\w+)\s*\{([^}]*)\}', solidity_code, re.DOTALL)
    if contract_match:
        contract_name = contract_match.group(1)
        contract_body = contract_match.group(2)
        
        contract = {
            "name": contract_name,
            "state_variables": [],
            "functions": [],
            "constructors": []
        }
        
        # Parse state variables
        var_matches = re.finditer(r'(\w+)\s+(\w+)\s*[;=]', contract_body)
        for match in var_matches:
            var_type = match.group(1)
            var_name = match.group(2)
            contract["state_variables"].append({
                "type": var_type,
                "name": var_name
            })
        
        # Parse functions
        func_matches = re.finditer(
            r'function\s+(\w+)\s*\(([^)]*)\)\s*(?:public|private|internal|external)?\s*'
            r'(?:pure|view|payable|non-payable)?\s*\{([^}]*)\}',
            contract_body, re.DOTALL
        )
        for match in func_matches:
            func_name = match.group(1)
            params_str = match.group(2)
            body = match.group(3)
            
            # Parse parameters
            params = []
            if params_str.strip():
                for param in params_str.split(","):
                    param = param.strip()
                    if param:
                        parts = param.split()
                        if len(parts) >= 2:
                            param_type = parts[0]
                            param_name = parts[1]
                            params.append({
                                "type": param_type,
                                "name": param_name
                            })
            
            # Parse body expressions
            body_exprs = []
            for line in body.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("//"):
                    body_exprs.append({"type": "Expression", "code": line})
            
            contract["functions"].append({
                "name": func_name,
                "parameters": params,
                "body": body_exprs[0] if body_exprs else None,
                "visibility": "public",
                "state_mutability": "non-payable"
            })
        
        ast["contracts"].append(contract)
    
    return ast


# Example usage
if __name__ == "__main__":
    # Example Solidity code
    solidity_code = """
    contract Escrow {
        address public owner;
        uint256 public balance;

        constructor() {
            owner = msg.sender;
        }

        function deposit() external payable {
            balance += msg.value;
        }

        function withdraw() external {
            require(msg.sender == owner, "Not owner");
            payable(msg.sender).transfer(balance);
            balance = 0;
        }
    }
    """
    
    # Parse Solidity (in real usage, use slither)
    ast = parse_simple_solidity(solidity_code)
    
    # Create transpiler
    transpiler = SolidityToMettaTranspiler()
    
    # Transpile each contract
    metta_code = ""
    for contract_ast in ast["contracts"]:
        metta_code += transpiler.transpile_contract(
            contract_ast["name"], contract_ast
        ) + "\n\n"
    
    print("=" * 60)
    print("SOLIDITY TO METTA TRANSPILER OUTPUT")
    print("=" * 60)
    print(metta_code)
    
    # Print any errors
    if transpiler.errors:
        print("\n" + "=" * 60)
        print("TRANSPILER ERRORS")
        print("=" * 60)
        for error in transpiler.errors:
            print(f"- {error}")
