# Proyecto 1 - Intérprete de comandos estilo Linux (Python)

Este es un shell básico escrito en Python como parte de la materia **Sistemas Computacionales y Redes**. Soporta ejecución de comandos con redirección, pipes, historial y más.

## Funcionalidades implementadas

- Prompt con `$` y lectura interactiva.
- Ejecución de comandos del sistema.
- Comando interno `cd`.
- Redirección de entrada (`<`), salida (`>`), y append (`>>`).
- Pipes (`|`) entre múltiples comandos.
- Ejecución en segundo plano (`&`).
- Comando `jobs` para ver procesos en background.
- Comando `fg <n>` para traer un job al foreground.
- Historial de comandos (`history`), limitado a 50 entradas.
- Reutilización de comandos:
  - `!!` → último comando.
  - `!n` → comando número n.
  - `!cmd` → último comando que empieza con `cmd`.
- Expansión correcta dentro de líneas con pipes (`!1 | cmd2 | cmd3`).
- Manejo de espacios múltiples entre tokens.

## Instrucciones de uso

1. Ejecuta el script con Python 3:

   ```bash
   python3 shell.py
