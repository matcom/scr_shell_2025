class Shell:
    def __init__(self):
        pass

    def run(self):
        while True:
            print("$", end="", flush=True)


if __name__ == "__main__":
    shell = Shell()
    shell.run()
