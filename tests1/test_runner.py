#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import signal
import io
import traceback
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout

# Add the parent directory to sys.path to import shell modules
sys.path.append(str(Path(__file__).parent.parent))

from src.lexer import ShellLexer
from src.parser import ShellParser
from src.executer import CommandExecutor

COLORS = {
    "RESET": "\033[0m",
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "MAGENTA": "\033[95m",
    "CYAN": "\033[96m",
}

def execute_command(command, expect_fail=False):
    """
    Ejecuta un único comando y retorna si pasó o no la prueba.
    Aísla cada paso para mejor detección de errores.
    """
    # Capturar todas las salidas
    stderr_capture = io.StringIO()
    stdout_capture = io.StringIO()
    
    # Objetos nuevos para cada prueba
    lexer = ShellLexer()
    executor = CommandExecutor()
    
    # 1. FASE DE LEXER
    try:
        tokens = lexer.tokenize(command)
    except Exception as e:
        if expect_fail:
            print(f"{COLORS['GREEN']}✓ Passed: Lexer raised exception as expected: {str(e)}{COLORS['RESET']}")
            return True
        else:
            print(f"{COLORS['RED']}✘ Lexer exception: {str(e)}{COLORS['RESET']}")
            return False
    
    # 2. FASE DE PARSER
    try:
        parser = ShellParser(tokens)
        ast = parser.parse()
    except Exception as e:
        if expect_fail:
            print(f"{COLORS['GREEN']}✓ Passed: Parser raised exception as expected: {str(e)}{COLORS['RESET']}")
            return True
        else:
            print(f"{COLORS['RED']}✘ Parser exception: {str(e)}{COLORS['RESET']}")
            return False
    
    # 3. FASE DE EJECUCIÓN
    is_background = command.strip().endswith("&")
    
    # Capturar salida y errores
    with redirect_stderr(stderr_capture), redirect_stdout(stdout_capture):
        try:
            executor.execute(ast)
            return_code = executor.last_return_code
        except Exception as e:
            if expect_fail:
                print(f"{COLORS['GREEN']}✓ Passed: Executor raised exception as expected: {str(e)}{COLORS['RESET']}")
                return True
            else:
                print(f"{COLORS['RED']}✘ Execution exception: {str(e)}{COLORS['RESET']}")
                return False
    
    # 4. ANALIZAR RESULTADOS
    stderr_content = stderr_capture.getvalue()
    
    # Si esperamos fallo, verificar que haya habido error
    if expect_fail:
        if stderr_content and any(msg in stderr_content.lower() for msg in 
                               ["error", "no such", "cannot", "not found", "no existe", "no encontrado"]):
            print(f"{COLORS['GREEN']}✓ Passed: Command produced error output as expected{COLORS['RESET']}")
            return True
        elif return_code != 0:
            print(f"{COLORS['GREEN']}✓ Passed: Command returned non-zero code as expected: {return_code}{COLORS['RESET']}")
            return True
        else:
            print(f"{COLORS['RED']}✘ Failed: Command should have failed but succeeded: {command}{COLORS['RESET']}")
            return False
    else:
        # Para comandos normales
        if is_background:
            print(f"{COLORS['GREEN']}✓ Background process started: {command}{COLORS['RESET']}")
            # Pequeño delay para permitir que el proceso comience
            time.sleep(0.2)
            # Limpiar procesos
            _clean_background_processes(executor)
            return True
        else:
            # Mostrar advertencia si hay errores pero no fallamos la prueba
            #if stderr_content:
               # print(f"{COLORS['YELLOW']}⚠ Warning: Command produced output to stderr{COLORS['RESET']}")
            
            print(f"{COLORS['GREEN']}✓ Passed: Command executed (return code: {return_code}){COLORS['RESET']}")
            return True   
def _clean_background_processes(executor):
    """Limpia los procesos en background de forma segura"""
    for job_id, job in list(executor.jobs.items()):
        try:
            os.killpg(os.getpgid(job.pid), signal.SIGTERM)
            print(f"{COLORS['YELLOW']}Terminated background process: {job.cmd}{COLORS['RESET']}")
            del executor.jobs[job_id]
        except (ProcessLookupError, OSError):
            pass

def run_test(test_case_file):
    """Ejecuta todas las pruebas en un archivo de test"""
    print(f"{COLORS['CYAN']}Running test: {test_case_file}{COLORS['RESET']}")
    
    # Leer el archivo de pruebas
    with open(test_case_file, 'r') as f:
        test_lines = [line.strip() for line in f.readlines() if line.strip() and not line.strip().startswith('#')]
    
    if not test_lines:
        print(f"{COLORS['YELLOW']}Warning: No test cases found in {test_case_file}{COLORS['RESET']}")
        return True
    
    # Ejecutar cada línea como una prueba independiente
    results = []
    for i, line in enumerate(test_lines):
        print(f"{COLORS['BLUE']}[{i+1}/{len(test_lines)}] Testing: {line}{COLORS['RESET']}")
        
        # Verificar si es una prueba que esperamos que falle
        expect_fail = line.startswith("EXPECT_FAIL:")
        if expect_fail:
            command = line[len("EXPECT_FAIL:"):].strip()
        else:
            command = line
        
        # Ejecutar el comando en un entorno totalmente aislado
        try:
            success = execute_command(command, expect_fail)
            results.append(success)
        except Exception as e:
            print(f"{COLORS['RED']}✘ Test runner error: {str(e)}{COLORS['RESET']}")
            traceback.print_exc()
            results.append(False)
        
        print()  # Línea en blanco entre pruebas para mejor legibilidad
    
    # Resumen de la prueba
    passed = sum(results)
    total = len(results)
    success_rate = passed / total if total else 0
    print(f"{COLORS['CYAN']}Test completed: {passed}/{total} passed ({success_rate:.0%}){COLORS['RESET']}")
    return all(results)

def run_all_tests():
    """Ejecuta todos los archivos de prueba en el directorio cases"""
    test_dir = Path(__file__).parent / "cases"
    test_files = list(test_dir.glob("*.test"))
    
    if not test_files:
        print(f"{COLORS['RED']}No test files found in {test_dir}{COLORS['RESET']}")
        return False
    
    print(f"{COLORS['CYAN']}Found {len(test_files)} test files{COLORS['RESET']}")
    
    # Ejecutar cada archivo de prueba
    results = []
    for test_file in sorted(test_files):
        success = run_test(test_file)
        results.append(success)
        print("\n" + "="*50 + "\n")  # Separador entre archivos de prueba
    
    # Resumen global
    passed = sum(results)
    total = len(results)
    success_rate = passed / total if total else 0
    print(f"{COLORS['CYAN']}All tests completed: {passed}/{total} test files passed ({success_rate:.0%}){COLORS['RESET']}")
    
    return all(results)

if __name__ == "__main__":
    print(f"{COLORS['CYAN']}=============== Shell Test Runner ==============={COLORS['RESET']}")
    
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        if os.path.exists(test_file):
            run_test(test_file)
        else:
            print(f"{COLORS['RED']}Test file not found: {test_file}{COLORS['RESET']}")
            sys.exit(1)
    else:
        run_all_tests() 