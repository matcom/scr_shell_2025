from shell_test import basic_test, cd_test, pipe_test, redirection_test

basic_tests = [basic_test, cd_test, pipe_test, redirection_test]

if not all([x() for x in basic_tests]):
    print("\033[31m" + f"Grade: 2 points \033[0m")
    exit(1)

print("\033[32m" + f"Grade: 3 points \033[0m")