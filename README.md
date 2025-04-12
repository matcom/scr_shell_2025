# 🐚 Shell

[![Python](https://img.shields.io/badge/Python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Una implementación personalizada de shell en Python con soporte para tuberías, redirecciones de entrada/salida, historial de comandos, y más.



## ✨ Características

- 🔍 **Sintaxis similar a Bash**: comandos familiares y fáciles de usar
- 📦 **Comandos integrados**: incluye `cd`, `exit`, `history` y más
- 🔄 **Redirección de I/O**: `>`, `>>`, `<` para manipulación de flujos
- 📋 **Historial de comandos**: acceder a comandos previos con `!!` y `!n`
- 🔗 **Tuberías**: conectar la salida de un comando con la entrada de otro usando `|`
- 🔙 **Ejecución en segundo plano**: ejecutar comandos con `&`

## 🚀 Instalación

```bash
# Clonar el repositorio
git clone https://github.com/ALbertE03/Shell.git
cd Shell

```

## 🔧 Uso

```bash
# Iniciar la shell
python3 -m shell
```

### Ejemplos de comandos

```bash
# Comando simple
$ ls -l

# Redirección de salida
$ echo "Hola Mundo" > saludo.txt

# Redirección de entrada
$ sort < numeros.txt

# Tuberías
$ cat archivo.txt | grep "palabra" | sort

# Ejecución en segundo plano
$ sleep 10 &

# Historial
$ history
$ !!        # Ejecutar último comando
$ !3        # Ejecutar tercer comando del historial
```

## 📁 Estructura del Proyecto

```
pyshell/
├── src/                   
│   ├── __init__.py                
│   ├── lexer.py            
│   ├── parser.py           
│   ├── ast_tree.py         
│   └── executer.py         
│
├── docs/                   
│   └── documentation.md    
│
├── LICENSE                 
├── README.md               
│
├── shell.py     
```

## 🏗️ Arquitectura

El proyecto está organizado en varios componentes:

- **Lexer**: Analiza la entrada del usuario y la divide en tokens
- **Parser**: Construye un árbol de sintaxis abstracta (AST) a partir de los tokens
- **AST**: Define las estructuras para representar comandos y tuberías
- **Ejecutor**: Ejecuta comandos basados en el AST
- **Shell Principal**: Gestiona la interacción con el usuario

## 📚 Documentación

Para documentación detallada, consulte [docs/documentation.md](docs/documentation.md).

## 🤝 Contribuir

Las contribuciones son bienvenidas! Por favor, siéntase libre de enviar un PR.

1. Fork el proyecto
2. Cree su rama de características (`git checkout -b feature/nueva-caracteristica`)
3. Commit sus cambios (`git commit -m 'Añadir nueva característica'`)
4. Push a la rama (`git push origin feature/nueva-caracteristica`)
5. Abra un Pull Request

## 📄 Licencia

Este proyecto está licenciado bajo la licencia MIT - vea el archivo [LICENSE](LICENSE) para más detalles.

## 🙏 Agradecimientos

- Inspirado en shells UNIX tradicionales como Bash y Zsh.
- Desarrollado como proyecto educativo para entender mejor el funcionamiento interno de las shells.
