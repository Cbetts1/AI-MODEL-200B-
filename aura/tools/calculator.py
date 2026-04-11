"""aura/tools/calculator.py — Safe math expression evaluator.

Evaluates mathematical expressions without using ``eval()`` on arbitrary input.
Uses Python's ``ast`` module to parse and safely evaluate numeric expressions.

Usage (in chat)
---------------
    /tool calculator 2 + 2
    /tool calculator sqrt(144) + 3**2
    /tool calculator sin(pi/4)
"""

from __future__ import annotations

import ast
import math
import operator
from typing import Any

from .registry import Tool

# Allowed operators for safe evaluation
_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Allowed math functions and constants
_MATH_NAMES: dict[str, Any] = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "ceil": math.ceil,
    "floor": math.floor,
    "factorial": math.factorial,
    "gcd": math.gcd,
    "pow": math.pow,
    "degrees": math.degrees,
    "radians": math.radians,
}


def _safe_eval(node: ast.AST) -> Any:
    """Recursively evaluate an AST node using only allowed operations."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, complex)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

    if isinstance(node, ast.UnaryOp):
        op_func = _OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return op_func(_safe_eval(node.operand))

    if isinstance(node, ast.BinOp):
        op_func = _OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op_func(_safe_eval(node.left), _safe_eval(node.right))

    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in _MATH_NAMES:
            func = _MATH_NAMES[node.func.id]
            if callable(func):
                args = [_safe_eval(a) for a in node.args]
                return func(*args)
        raise ValueError(f"Unknown function: {ast.dump(node.func)}")

    if isinstance(node, ast.Name):
        if node.id in _MATH_NAMES:
            val = _MATH_NAMES[node.id]
            if not callable(val):
                return val
        raise ValueError(f"Unknown name: {node.id}")

    raise ValueError(f"Unsupported expression: {type(node).__name__}")


class CalculatorTool(Tool):
    """Safely evaluate mathematical expressions."""

    name = "calculator"
    description = "Evaluate a math expression. Usage: /tool calculator <expr>"

    def run(self, args: str) -> str:
        expr = args.strip()
        if not expr:
            return "[calculator] Please provide a math expression."
        try:
            tree = ast.parse(expr, mode="eval")
            result = _safe_eval(tree)
            return f"🔢 {expr} = {result}"
        except (ValueError, TypeError, SyntaxError, ZeroDivisionError) as exc:
            return f"[calculator] Error: {exc}"
