import sys
import io
import contextlib
from RestrictedPython import compile_restricted
from RestrictedPython.Guards import safe_globals

def execute_python_code(code):
    """
    Safely execute Python code with restrictions.
    Returns a dictionary with output, error, and success status.
    """
    try:
        # Compile the code with restrictions
        compiled_code = compile_restricted(code, filename="<user_code>", mode="exec")
        
        if compiled_code is None:
            return {
                'output': '',
                'error': 'Code compilation failed - syntax error or restricted operation',
                'success': False
            }
        
        # Create a restricted execution environment
        restricted_globals = safe_globals.copy()
        restricted_globals['__builtins__'] = {
            'print': print,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'range': range,
            'enumerate': enumerate,
            'zip': zip,
            'max': max,
            'min': min,
            'sum': sum,
            'abs': abs,
            'round': round,
            'sorted': sorted,
            'reversed': reversed,
            'type': type,
            'isinstance': isinstance,
        }
        
        # Capture stdout
        stdout_capture = io.StringIO()
        
        # Execute the code with captured output
        with contextlib.redirect_stdout(stdout_capture):
            exec(compiled_code, restricted_globals, {})
        
        output = stdout_capture.getvalue()
        
        return {
            'output': output,
            'error': '',
            'success': True
        }
        
    except SyntaxError as e:
        return {
            'output': '',
            'error': f'Syntax Error: {str(e)}',
            'success': False
        }
    except Exception as e:
        return {
            'output': '',
            'error': f'Runtime Error: {str(e)}',
            'success': False
        }
