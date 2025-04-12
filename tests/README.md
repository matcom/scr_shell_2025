# Pruebas para Shell

Este directorio contiene pruebas automatizadas para la implementación de Shell.

## Estructura de Pruebas

- `test_runner.py`: Script principal para ejecutar todas las pruebas o un archivo específico
- `cases/`: Directorio con archivos de casos de prueba (extensión .test)

## Formato de Casos de Prueba

Los archivos de prueba son archivos de texto con extensión `.test` que contienen comandos de shell para ejecutar. El ejecutor de pruebas:
1. Analiza cada línea como un comando de shell independiente
2. Ejecuta cada comando usando la infraestructura de shell
3. Reporta éxito o fallo basado en varios criterios (no solo el código de retorno)

### Sintaxis Especial

- Líneas que comienzan con `#` son tratadas como comentarios y se ignoran
- Líneas que comienzan con `EXPECT_FAIL:` se espera que produzcan errores o excepciones

## Ejecución de Pruebas

Para ejecutar todas las pruebas:
```bash
python tests/test_runner.py
```

Para ejecutar un archivo de prueba específico:
```bash
python tests/test_runner.py tests/cases/pipe_and_bg.test
```

## Categorías de Pruebas

1. **pipe_and_bg.test**: Pruebas para operaciones de tubería (pipe) y procesamiento en segundo plano
2. **redirection.test**: Pruebas para operaciones de redirección de entrada/salida
3. **redirection_errors.test**: Pruebas específicas para errores de redirección
4. **error_handling.test**: Pruebas para escenarios de manejo de errores generales
5. **builtins.test**: Pruebas para comandos integrados de la shell
6. **complex.test**: Pruebas para combinaciones complejas de características
7. **pipe_test.test**: Pruebas específicas para verificar el correcto funcionamiento de tuberías

## Características del Sistema de Pruebas

- **Aislamiento**: Cada prueba se ejecuta de forma completamente independiente
- **Detección de errores en 3 niveles**: 
  - Lexer (análisis léxico)
  - Parser (análisis sintáctico)
  - Executor (ejecución)
- **Manejo de procesos en segundo plano**: Limpieza automática de procesos
- **Captura de errores**: Detección de mensajes de error incluso cuando el código de retorno es 0

## Creación de Nuevas Pruebas

Para crear nuevos casos de prueba:
1. Cree un archivo `.test` en el directorio `cases/`
2. Agregue comandos de shell, uno por línea
3. Añada comentarios que empiecen con `#` para documentación
4. Agregue el prefijo `EXPECT_FAIL:` a los comandos que se espera que fallen
5. Incluya comandos de limpieza al final del archivo si es necesario

## Solución de Problemas

Si las pruebas están fallando, verifique:
1. El entorno de shell y sus dependencias
2. Los permisos de los archivos de prueba
3. Si los comandos en las pruebas están disponibles en su sistema
4. Los mensajes detallados en la salida para identificar el tipo de error

## Interpretación de la Salida

- **Verde ✓**: Prueba exitosa
- **Rojo ✘**: Prueba fallida
- **Amarillo ⚠**: Advertencia (la prueba pasa pero con advertencias)
- **Azul**: Información sobre la prueba que se está ejecutando
- **Cyan**: Resumen de resultados 