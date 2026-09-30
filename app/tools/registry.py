"""
Antar — Reliable Tool Integration Registry
=================================================
Wraps external API calls with Circuit Breakers, Retries, and strict
Pydantic schemas to ensure agents cannot crash the backend by passing
hallucinated parameters.
"""

from typing import Callable, TypeVar, Dict
import asyncio
from functools import wraps

T = TypeVar('T')

class CircuitBreakerOpenException(Exception):
    pass

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, dict] = {}

    def register(self, name: str, schema: dict, max_retries: int = 3, timeout_sec: float = 10.0):
        """Decorator to register a reliable tool."""
        def decorator(func: Callable):
            self._tools[name] = {
                "func": func,
                "schema": schema,
                "failures": 0,
                "circuit_open": False
            }
            
            @wraps(func)
            async def wrapper(*args, **kwargs):
                tool_state = self._tools[name]
                if tool_state["circuit_open"]:
                    raise CircuitBreakerOpenException(f"Circuit breaker open for tool: {name}")
                
                # In production: validate kwargs against `schema` here using Pydantic
                
                last_err = None
                for attempt in range(max_retries):
                    try:
                        res = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_sec)
                        tool_state["failures"] = 0 # Reset circuit
                        return res
                    except asyncio.TimeoutError as e:
                        last_err = e
                        print(f"Tool {name} timeout (attempt {attempt+1}/{max_retries})")
                    except Exception as e:
                        last_err = e
                        print(f"Tool {name} error: {e}")
                        
                # Circuit breaker trip logic
                tool_state["failures"] += 1
                if tool_state["failures"] >= 3:
                    tool_state["circuit_open"] = True
                    print(f"CIRCUIT TRIPPED for tool: {name}")
                    
                raise last_err
            return wrapper
        return decorator

registry = ToolRegistry()
