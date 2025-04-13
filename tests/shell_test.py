import subprocess, os

def make_test(name, processing_function, extra_args = None):
    command = f"./run.sh"
    
    info = subprocess.Popen([command], stdin= subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        processing_function(info, extra_args)
    except Exception as e:
        print("\033[31m" + f"Test: {name} failed with error {e}\033[0m")
        return False
    
    print("\033[32m" + f"Test: {name} completed\033[0m")
    return True

def call_and_check_template(process, instructinos):
    for (a,b) in instructinos:
        out, _ = process.communicate(input = a)

        if len(out) > 0:
            print(f"Execution input:{a} output: {out}")

        if not b in out:
            raise Exception("\033[31m" + f" {a} failed\033[0m")

def prompt_test_function(process, _):
    out, err = process.communicate(input='\n')

    if len(out) > 0:
        print(f"Execution output: {out}")
    else:
        raise Exception("\033[31m" + f"Prompt not found\033[0m")
    
    print("\033[32m" + f"Test: Prompt check completed.\033[0m")

def prompt_after_execution_test_function(process, _):
    prompt, err = process.communicate()

    out, err = process.communicate(input='date\n')

    if len(out) > 0 and prompt in out:
        print(f"Execution output: {out}")
    else:
        raise Exception("\033[31m" + f"Prompt not found after command execution")
    
def prompt_test():
    return make_test('Check prompt Test', prompt_test_function)

def prompt_after_execution_test():
    return make_test('Check prompt after command execution Test', prompt_after_execution_test_function)

def basic_test():
    return make_test('Basic Test', call_and_check_template, [('echo "Hello, world!\n"', 'Hello, world!')])

def cd_test():
    return make_test('cd Test', call_and_check_template, [('mkdir holamundo\ncd holamundo\npwd\n', 'holamundo')])

def redirection_test():
    results = []

    results.append(make_test('< > and >> Test 1', call_and_check_template, [('echo "Hello, world!" > file.txt\n', '')]))
    results.append(make_test('< > and >> Test 2', call_and_check_template, [('cat file.txt\n', 'Hello, world!')]))
    results.append(make_test('< > and >> Test 3', call_and_check_template, [('echo "Goodbye, world!" >> file.txt\n', '')]))
    results.append(make_test('< > and >> Test 4', call_and_check_template, [('cat file.txt\n', 'Hello, world!\nGoodbye, world!')]))
    results.append(make_test('< > and >> Test 5', call_and_check_template, [('cat < file.txt\n', 'Hello, world!\nGoodbye, world!')]))

    return all(x for x in results)

def pipe_test():
    return make_test('pipe Test', call_and_check_template, [('ls -a | grep "."\n', '..')])