import subprocess, select

def non_breaking_communicate(proc, input, timeout=0.1, multiple_output=True):

    if not input.endswith('\n'):
        input += '\n'

    proc.stdin.write(input)
    proc.stdin.flush()

    res = ''

    if select.select([proc.stdout], [], [], timeout)[0]:
        print(res)
        res = proc.stdout.readline()

    if multiple_output:
        while select.select([proc.stdout], [], [], timeout)[0]:
            out = proc.stdout.readline()
            res +=  out

    return res


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
        
def call_and_check_template_with_commuinicate(process, instructinos):
    for (a,b) in instructinos:
        out = non_breaking_communicate(process, input = a)
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

def any_number_of_spaces_test():
    return make_test('Echo with spaces test', call_and_check_template, [('echo                                  "Hello    World!"','Hello    World!')])

def history_test():
    commands = []

    for _ in range(25):
        commands.append(('ls -al', 'total'))
        commands.append(('echo "Hola Mundo"', 'Hola Mundo'))

    commands.append((' echo algo', 'algo'))
    commands.append(('history | wc -l', '50'))
    commands.append(('echo algo2', 'algo2'))
    commands.append(('history | wc -l', '50'))

    print(commands)

    return make_test('history test', call_and_check_template_with_commuinicate, commands)

def command_reutilization_test():
    commands = []

    for _ in range(25):
        commands.append(('ls -al', 'total'))
        commands.append(('echo "test"', 'test'))

    commands.append(('!50', 'test'))
    commands.append(('!!', 'test'))
    commands.append(('!l', 'total'))

    return make_test('command reutilization test', call_and_check_template_with_commuinicate, commands)

def multiple_pipes_test():
    result = []

    result.append(make_test('echo test1', call_and_check_template, [('echo "Hola Mundo" >> file2.txt', '')]))
    result.append(make_test('echo test2', call_and_check_template, [('echo "mundo" >> file2.txt', '')]))
    result.append(make_test('echo test3', call_and_check_template, [('echo "pais" >> file2.txt', '')]))
    result.append(make_test('Multiple Pipes test', call_and_check_template, [(' cat file2.txt | grep o | grep Hola', 'Hola Mundo')]))

    return all(x for x in result)

def jobs_test():
    result = []

    result.append(make_test('ping test', call_and_check_template, [('ping localhost | grep ttl > archivo &\n jobs | wc -l', '1')]))

    return all(x for x in result)