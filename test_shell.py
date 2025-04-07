import pexpect
import time
import os

SHELL_CMD = "python3 new_shell.py"


def run_test_case(description, inputs, expected_outputs):
    print(f"🧪 {description}")
    shell = pexpect.spawn(SHELL_CMD, encoding="utf-8", timeout=20)
    for input_line, expected in zip(inputs, expected_outputs):
        shell.expect(r"\$ ")
        shell.sendline(input_line)
        if expected:
            shell.expect(expected)
    shell.sendline("exit")
    shell.expect("Saliendo del shell")
    print("✅ Passed")


def cleanup():

    for f in ["test.txt", "output.txt", "input.txt", "append.txt"]:
        if os.path.exists(f):
            os.remove(f)


def main():
    cleanup()

    run_test_case(
        "Comando simple + redirección + lectura",
        ["echo hola mundo > test.txt", "cat < test.txt"],
        ["", "hola mundo"],
    )

    run_test_case(
        "Pipes simples",
        ["echo uno dos tres | tr ' ' '\\n' | sort"],
        ["dos", "tres", "uno"],
    )

    run_test_case(
        "Historial y reutilización con !!",
        ["echo primera", "!!"],
        ["primera", "primera"],
    )

    run_test_case(
        "Reutilización con !n y !prefix",
        ["echo uno", "echo dos", "history", "!1"],
        ["uno", "dos", "1 echo uno", "echo uno"],
    )

    run_test_case(
        "Background execution y jobs",
        ["sleep 2 &", "jobs"],
        ["ejecutándose en background", r"\[\d+\] \d+ sleep 2"],
    )

    run_test_case(
        "fg trae el proceso al foreground",
        ["sleep 2 &", "fg"],
        ["", "Ejecutando en foreground: sleep 2"],
    )

    run_test_case(
        "Reutilización dentro de pipes: !n | wc -w",
        ["echo hola mundo", "echo hola mundo | tr 'a-z' 'A-Z'", "!2 | wc -w"],
        ["", "HOLA MUNDO", "2"],
    )

    run_test_case(
        "Pipes múltiples con redirección",
        [
            "echo -e 'a\\nb\\nc' > input.txt",
            "cat input.txt | sort | uniq | wc -l > output.txt",
            "cat output.txt",
        ],
        ["", "", "1"],
    )

    run_test_case(
        "Redirección append (>>)",
        ["echo linea1 > append.txt", "echo linea2 >> append.txt", "cat append.txt"],
        ["", "", "linea1.*linea2"],
    )

    run_test_case(
        "Redirección de entrada y salida combinada",
        [
            "echo -e '3\\n1\\n2' > nums.txt",
            "sort < nums.txt > sorted.txt",
            "cat sorted.txt",
        ],
        ["", "", "1"],
    )

    run_test_case(
        "Comando no existente",
        ["comando_inexistente"],
        [
            "Error al ejecutar comando: Command 'comando_inexistente' returned non-zero exit status 127."
        ],
    )

    run_test_case(
        "Redirección a archivo no escribible",
        ["echo test > /no_existe/test.txt"],
        [""],
    )

    run_test_case(
        "Historial con comandos complejos",
        ["echo 'comando complejo' | wc -w", "history"],
        ["", "1 echo 'comando complejo' | wc -w"],
    )
    run_test_case(
        "Múltiples jobs en background",
        ["sleep 3 &", "sleep 2 &", "jobs"],
        ["", "", r"\[\d+\] \d+ sleep 3.*\[\d+\] \d+ sleep 2"],
    )
    run_test_case(
        "fg con número de job específico",
        ["sleep 5 &", "sleep 3 &", "jobs", "fg 1"],
        [
            "",
            "",
            r"\[\d+\] \d+ sleep 5.*\[\d+\] \d+ sleep 3",
            "Ejecutando en foreground: sleep 5",
        ],
    )
    run_test_case(
        "fg con número de job específico",
        ["sleep 5 &", "sleep 3 &", "jobs", "fg 1"],
        [
            "",
            "",
            r"\[\d+\] \d+ sleep 5.*\[\d+\] \d+ sleep 3",
            "Ejecutando en foreground: sleep 5",
        ],
    )
    run_test_case(
        "fg con número de job específico",
        ["sleep 5 &", "sleep 3 &", "jobs", "fg 1"],
        [
            "",
            "",
            r"\[\d+\] \d+ sleep 5.*\[\d+\] \d+ sleep 3",
            "Ejecutando en foreground: sleep 5",
        ],
    )

    # run_test_case(
    #   "Combinación compleja: pipes, redirección y background",
    #  [
    #     "echo -e 'a\\nb\\na' > input.txt",
    #    "cat input.txt | sort | uniq > output.txt &",
    #   "jobs",
    # ],
    # ["", "", r"\[\d+\] \d+ cat input.txt.*sort.*uniq"],
    # )

    run_test_case(
        "Reutilización de comando complejo con pipes",
        ["echo test | wc -c", "!!"],
        ["", "test | wc -c"],
    )

    run_test_case(
        "Historial ignora comandos con espacios iniciales",
        [" echo no en historial", "echo si en historial", "history"],
        ["", "", "1 echo si en historial \n 2 history"],
    )

    cleanup()
    print("\n🎉 Todos los tests completados!")


if __name__ == "__main__":
    main()
