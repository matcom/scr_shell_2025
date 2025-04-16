from shell_test import basic_test, cd_test, pipe_test, redirection_test, any_number_of_spaces_test, history_test, command_reutilization_test, multiple_pipes_test, jobs_test

basic_tests = [basic_test, cd_test, pipe_test, redirection_test]

points = 0

if not all([x() for x in basic_tests]):
    print("\033[31m" + f"Grade: 2 points \033[0m")
    exit(1)

points += 3

if multiple_pipes_test():
    points += 1

if jobs_test():
    points += 1

if any_number_of_spaces_test():
    points += 0.5

if history_test():
    points += 0.5

if command_reutilization_test():
    points += 0.5

print("\033[32m" + f"Grade: {points} points \033[0m")

