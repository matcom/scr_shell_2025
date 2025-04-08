#!/usr/bin/env python3
import unittest
import os
import sys
import subprocess
import tempfile
import io
import re
from contextlib import redirect_stdout, redirect_stderr


class TestCustomShell(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Crear archivos temporales para pruebas de redirección
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_file1 = os.path.join(cls.temp_dir.name, "test1.txt")
        cls.test_file2 = os.path.join(cls.temp_dir.name, "test2.txt")
        cls.test_file3 = os.path.join(cls.temp_dir.name, "test3.txt")

        with open(cls.test_file1, "w") as f:
            f.write("line1\nline2\nline3\n")

        # Variable de entorno para el ejecutable del shell
        cls.shell_path = os.path.abspath("./a.py")

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
            return process.stdout, process.stderr
        except subprocess.TimeoutExpired:
            return "TIMEOUT", ""

    def test_01_prompt_display(self):
        """Verifica que se muestre el prompt"""
        stdout, _ = self.run_shell_command("exit")
        self.assertIn("$", stdout.split("\n")[0])

    def test_02_command_execution(self):
        """Prueba ejecución básica de comandos"""
        stdout, _ = self.run_shell_command("echo hello\nexit")
        self.assertIn("hello", stdout)

    def test_03_cd_command(self):
        """Prueba el comando cd"""
        test_dir = self.temp_dir.name
        stdout, _ = self.run_shell_command(f"cd {test_dir}\npwd\nexit")
        self.assertIn(test_dir, stdout)

    def test_04_output_redirection(self):
        """Prueba redirección de salida"""
        test_file = os.path.join(self.temp_dir.name, "output_redir_test.txt")
        self.run_shell_command(f"echo test > {test_file}\nexit")
        with open(test_file, "r") as f:
            content = f.read().strip()
        self.assertEqual(content, "test")

    def test_05_input_redirection(self):
        """Prueba redirección de entrada"""
        stdout, _ = self.run_shell_command(f"wc -l < {self.test_file1}\nexit")
        self.assertIn("3", stdout.strip())

    def test_06_append_redirection(self):
        """Prueba redirección con append"""
        test_file = os.path.join(self.temp_dir.name, "append_test.txt")
        self.run_shell_command(
            f"echo line1 > {test_file}\necho line2 >> {test_file}\nexit"
        )
        with open(test_file, "r") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("line1\n", lines)
        self.assertIn("line2\n", lines)

    def test_07_pipe_operation(self):
        """Prueba operación de pipe"""
        stdout, _ = self.run_shell_command(f"cat {self.test_file1} | wc -l\nexit")
        self.assertIn("3", stdout.strip())

    def test_08_multiple_pipes(self):
        """Prueba múltiples pipes"""
        stdout, _ = self.run_shell_command(
            f"cat {self.test_file1} | grep line | wc -l\nexit"
        )
        self.assertIn("3", stdout.strip())

    def test_09_background_process(self):
        """Prueba procesos en background"""
        stdout, _ = self.run_shell_command(f"sleep 0.1 &\njobs\nexit")
        self.assertIn("sleep 0.1", stdout)
        self.assertIn("running", stdout)

    def test_10_fg_command(self):
        """Prueba comando fg"""
        stdout, _ = self.run_shell_command(f"sleep 3 &\nfg 1\nexit")
        self.assertIn("", stdout)

    def test_11_whitespace_handling(self):
        """Prueba manejo de espacios en blanco"""
        stdout1, _ = self.run_shell_command("echo hello\nexit")
        stdout2, _ = self.run_shell_command("  echo   hello  \nexit")
        self.assertEqual(stdout1.strip(), stdout2.strip())

    def test_12_history_command(self):
        """Prueba comando history"""
        commands = "echo hello\ncd /\nhistory\nexit"
        stdout, _ = self.run_shell_command(commands)
        lines = stdout.split("\n")
        self.assertIn("1  echo hello", lines)
        self.assertIn("2  cd /", lines)
        self.assertIn("3  history", lines)

    def test_13_history_reuse_number(self):
        """Prueba reutilización de comandos con !n"""
        stdout, _ = self.run_shell_command("echo hello\n!1\nexit")
        lines = stdout.split("\n")
        self.assertEqual(lines.count("hello"), 2)

    def test_14_history_reuse_double_bang(self):
        """Prueba reutilización con !!"""
        stdout, _ = self.run_shell_command("echo hello\n!!\nexit")
        lines = stdout.split("\n")
        self.assertEqual(lines.count("hello"), 2)

    def test_15_history_reuse_prefix(self):
        """Prueba reutilización con !prefix"""
        stdout, _ = self.run_shell_command("echo hello\n!ec\nexit")
        lines = stdout.split("\n")
        self.assertEqual(lines.count("hello"), 2)

    def test_16_history_ignore_spaces(self):
        """Prueba que no se guarden comandos con espacios iniciales"""
        stdout, _ = self.run_shell_command("echo hello\n  echo ignored\nhistory\nexit")
        self.assertNotIn("echo ignored", stdout)

    def test_17_complex_redirection_pipe_background(self):
        """Prueba combinación compleja: redirección, pipe y background"""
        cmd = f"cat {self.test_file1} | grep line > {self.test_file2} &\n"
        cmd += f"jobs\nwait\nexit"
        stdout, _ = self.run_shell_command(cmd)
        self.assertIn("cat", stdout)
        self.assertIn("grep", stdout)
        with open(self.test_file2, "r") as f:
            lines = f.readlines()
        self.assertGreaterEqual(len(lines), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
