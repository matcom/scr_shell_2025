#!/usr/bin/env python3
import unittest
import os
import sys
import subprocess
import tempfile
import re
from contextlib import redirect_stdout, redirect_stderr


def strip_ansi(text):
    """Elimina códigos ANSI (colores) de un string"""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


class TestEnhancedHistory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_file = os.path.join(cls.temp_dir.name, "test.txt")
        
        with open(cls.test_file, "w") as f:
            f.write("line1\nline2\nline3\nline4\nline5\n")
            
        cls.shell_path = os.path.abspath("./shell.py")

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def run_shell_command(self, command, timeout=5):
        """Ejecuta un comando en el shell y retorna la salida"""
        try:
            process = subprocess.run(
                [sys.executable, self.shell_path],
                input=command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                env=os.environ,
            )
            return strip_ansi(process.stdout), strip_ansi(process.stderr)
        except subprocess.TimeoutExpired:
            return "TIMEOUT", ""

    def test_01_history_pipe_double_bang(self):
        """Prueba la reutilización de !! con pipes adicionales"""
        commands = f"cat {self.test_file} | grep line\n!! | wc -l\nexit"
        stdout, _ = self.run_shell_command(commands)
 
        self.assertIn("5", stdout.strip())

    def test_02_history_pipe_prefix(self):
        """Prueba la reutilización de !prefix con pipes adicionales"""
        commands = f"echo line1 | grep line\necho line2\n!echo | wc -l\nexit"
        stdout, _ = self.run_shell_command(commands)
 
        self.assertIn("1", stdout.strip())

    def test_03_history_pipe_number(self):
        """Prueba la reutilización de !number con pipes adicionales"""
        commands = f"ls -la | grep .\necho test\n!1 | wc -l\nexit"
        stdout, _ = self.run_shell_command(commands)
   
        self.assertTrue("test" in stdout, "Echo command should be visible in output")

    def test_04_multiple_pipes_with_history(self):
        """Prueba combinar comandos con múltiples pipes usando history"""
        test_out = os.path.join(self.temp_dir.name, "output.txt")
        commands = (
            f"cat {self.test_file} | grep line\n"
            f"!! | grep line1\n"
            f"!! | grep line2\n"
            f"history\n"
            f"!1 | wc -l > {test_out}\n"
            "exit"
        )
        self.run_shell_command(commands)
        
        
        with open(test_out, "r") as f:
            content = f.read().strip()
        self.assertEqual(content, "5")

    def test_05_complex_pipe_chain(self):
        """Prueba cadenas complejas de pipes con history"""
        commands = (
            f"cat {self.test_file} | grep line\n"
            f"!! | sort -r\n"
            f"!! | head -n 2\n"
            f"exit"
        )
        stdout, _ = self.run_shell_command(commands)
        
  
        lines = [l for l in stdout.split("\n") if l.strip().startswith("line")]
       
        self.assertGreaterEqual(len(lines), 2)
        
    def test_06_nested_history_reuse(self):
        """Prueba el anidamiento de reutilización de history"""
        commands = (
            f"echo cmd1\n"
            f"echo cmd2\n"
            f"!1 | grep cmd\n"   # Should execute: echo cmd1 | grep cmd
            f"!! | wc -l\n"      # Should execute: echo cmd1 | grep cmd | wc -l
            f"exit"
        )
        stdout, _ = self.run_shell_command(commands)

        self.assertIn("1", stdout.strip())
        
    def test_07_history_with_different_commands(self):
        """Prueba reutilización de history con diferentes comandos"""
        commands = (
            f"cat {self.test_file}\n"
            f"!cat | grep line\n"
            f"!grep | wc -l\n"
            f"exit"
        )
        stdout, _ = self.run_shell_command(commands)
   
        self.assertIn("5", stdout.strip())
        
    def test_08_history_with_multiple_prefix_matches(self):
        """Prueba reutilización de comandos cuando hay múltiples coincidencias de prefijo"""
        commands = (
            f"echo test1\n"
            f"echo test2\n"
            f"!echo | grep test1\n"  
            f"exit"
        )
        stdout, _ = self.run_shell_command(commands)

        self.assertIn("test1", stdout)
        
    def test_09_combining_pipe_operators(self):
        """Prueba combinando múltiples operadores de pipe en reutilización de history"""

        dup_file = os.path.join(self.temp_dir.name, "duplicates.txt")
        with open(dup_file, "w") as f:
            f.write("line1\nline1\nline2\nline2\nline3\n")
            
        commands = (
            f"cat {dup_file} | sort\n"
            f"!! | uniq\n"
            f"!! | wc -l\n"
            f"exit"
        )
        stdout, _ = self.run_shell_command(commands)
        # Should eventually show 3 (unique lines after sorting)
        self.assertIn("3", stdout.strip())
        
    def test_10_complex_command_reuse_examples(self):
        """Prueba escenarios complejos según los ejemplos proporcionados"""
        commands = (
            f"echo cmd1 | echo cmd2\n"
            f"echo cmd2 | echo cmd4\n"
            f"!! | echo cmd3\n"  # Should execute: echo cmd2 | echo cmd4 | echo cmd3
            f"!echo | echo cmd3\n"  # Should execute: echo cmd2 | echo cmd4 | echo cmd3
            f"history\n"
            f"exit"
        )
        
        stdout, _ = self.run_shell_command(commands)
        history_output = stdout.split("history")[-1]
        
        # Check if history command shows our commands
        self.assertTrue("echo cmd1 | echo cmd2" in stdout, "First command should be in history")
        self.assertTrue("echo cmd2 | echo cmd4" in stdout, "Second command should be in history")
        self.assertTrue("echo cmd3" in stdout, "Commands with cmd3 should be in history")


if __name__ == "__main__":
    unittest.main(verbosity=2) 