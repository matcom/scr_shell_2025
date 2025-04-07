def test_lexer():
    lexer = ShellLexer()

    test_cases = [
        # Redirecciones básicas
        (
            "ls > file.txt",
            [
                ("ls", ShellTokenType.COMMAND),
                (">", ShellTokenType.REDIRECT_STDOUT),
                ("file.txt", ShellTokenType.ARGUMENT),
            ],
        ),
        (
            "ls 2> error.log",
            [
                ("ls", ShellTokenType.COMMAND),
                ("2>", ShellTokenType.REDIRECT_STDERR),
                ("error.log", ShellTokenType.ARGUMENT),
            ],
        ),
        (
            "ls &> output.log",
            [
                ("ls", ShellTokenType.COMMAND),
                ("&>", ShellTokenType.REDIRECT_STDOUT_ERR),
                ("output.log", ShellTokenType.ARGUMENT),
            ],
        ),
        # Redirecciones append
        (
            "ls >> file.txt",
            [
                ("ls", ShellTokenType.COMMAND),
                (">>", ShellTokenType.REDIRECT_APPEND),
                ("file.txt", ShellTokenType.ARGUMENT),
            ],
        ),
        (
            "ls 2>> error.log",
            [
                ("ls", ShellTokenType.COMMAND),
                ("2>>", ShellTokenType.REDIRECT_APPEND_ERR),
                ("error.log", ShellTokenType.ARGUMENT),
            ],
        ),
        (
            "ls &>> output.log",
            [
                ("ls", ShellTokenType.COMMAND),
                ("&>>", ShellTokenType.REDIRECT_APPEND_OUT_ERR),
                ("output.log", ShellTokenType.ARGUMENT),
            ],
        ),
        # Redirecciones combinadas
        (
            "cmd >file 2> a.log",
            [
                ("cmd", ShellTokenType.COMMAND),
                (">", ShellTokenType.REDIRECT_STDOUT),
                ("file", ShellTokenType.ARGUMENT),
                ("2>", ShellTokenType.REDIRECT_STDERR),
                ("a.log", ShellTokenType.ARGUMENT),
            ],
        ),
        # Heredoc y here-string
        (
            "cat << EOF\ncontent\nEOF",
            [
                ("cat", ShellTokenType.COMMAND),
                ("<<", ShellTokenType.REDIRECT_HEREDOC),
                ("EOF", ShellTokenType.ARGUMENT),
            ],
        ),
        (
            "tr a-z A-Z <<< 'hello'",
            [
                ("tr", ShellTokenType.COMMAND),
                ("a-z", ShellTokenType.ARGUMENT),
                ("A-Z", ShellTokenType.ARGUMENT),
                ("<<<", ShellTokenType.REDIRECT_HERE_STRING),
                ("hello", ShellTokenType.SINGLE_QUOTE_STRING),
            ],
        ),
        (
            'find /path/to/search -type f -name "*.log" -mtime +30 '
            "-exec gzip {} ; 2>>error.log | tee -a full_report.txt | "
            'grep "error" > critical_errors.txt & disown',
            [
                ("find", ShellTokenType.COMMAND),
                ("/path/to/search", ShellTokenType.ARGUMENT),
                ("-type", ShellTokenType.ARGUMENT),
                ("f", ShellTokenType.ARGUMENT),
                ("-name", ShellTokenType.ARGUMENT),
                ("*.log", ShellTokenType.DOUBLE_QUOTE_STRING),
                ("-mtime", ShellTokenType.ARGUMENT),
                ("+30", ShellTokenType.ARGUMENT),
                ("-exec", ShellTokenType.ARGUMENT),
                ("gzip", ShellTokenType.COMMAND),
                ("{}", ShellTokenType.ARGUMENT),
                (";", ShellTokenType.SEMICOLON),  # El \ es interpretado como escape
                ("2>>", ShellTokenType.REDIRECT_APPEND_ERR),
                ("error.log", ShellTokenType.ARGUMENT),
                ("|", ShellTokenType.PIPE),
                ("tee", ShellTokenType.COMMAND),
                ("-a", ShellTokenType.ARGUMENT),
                ("full_report.txt", ShellTokenType.ARGUMENT),
                ("|", ShellTokenType.PIPE),
                ("grep", ShellTokenType.COMMAND),
                ("error", ShellTokenType.DOUBLE_QUOTE_STRING),
                (">", ShellTokenType.REDIRECT_STDOUT),
                ("critical_errors.txt", ShellTokenType.ARGUMENT),
                ("&", ShellTokenType.BACKGROUND),
                ("disown", ShellTokenType.COMMAND),
            ],
        ),
        (
            "find . -exec grep -l 'pattern' {};",
            [
                ("find", ShellTokenType.COMMAND),
                (".", ShellTokenType.ARGUMENT),
                ("-exec", ShellTokenType.ARGUMENT),
                ("grep", ShellTokenType.COMMAND),
                ("-l", ShellTokenType.ARGUMENT),
                ("pattern", ShellTokenType.SINGLE_QUOTE_STRING),
                ("{}", ShellTokenType.ARGUMENT),
                (";", ShellTokenType.SEMICOLON),
            ],
        ),
    ]

    for cmd, expected in test_cases:
        print(f"\nTesting: '{cmd}'")
        try:
            tokens = lexer.tokenize(cmd)
            for token, (exp_lex, exp_type) in zip(tokens, expected):
                assert (
                    token.lex == exp_lex
                ), f"Expected lex '{exp_lex}', got '{token.lex}'"
                assert (
                    token.token_type == exp_type
                ), f"Expected type {exp_type}, got {token.token_type}"
                print(f"  ✓ {token}")
            print("  Test passed!")
        except ValueError as e:
            print(f"  ERROR: {e}")
        except AssertionError as e:
            print(f"  FAIL: {e}")
