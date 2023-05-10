class Commands:
    def __init__(self, console):
        self.console = console

    def cmd_help(self, args):
        "Show help about all commands"
        pass

    def cmd_ls(self, args):
        "List files and show their chat status"
        print("ls")

    def get_commands(self):
        commands = []
        for attr in dir(self):
            if attr.startswith("cmd_"):
                commands.append("/" + attr[4:])

        return commands

    def do_run(self, cmd_name, args):
        cmd_method_name = f"cmd_{cmd_name}"
        cmd_method = getattr(self, cmd_method_name, None)
        if cmd_method:
            cmd_method(args)
        else:
            self.console.print(f"Error: Command {cmd_name} not found.")

    def run(self, inp):
        words = inp.strip().split()
        if not words:
            return

        first_word = words[0]
        rest_inp = inp[len(words[0]) :]

        all_commands = self.get_commands()
        matching_commands = [cmd for cmd in all_commands if cmd.startswith(first_word)]

        if len(matching_commands) == 1:
            self.console.print("[green]run", matching_commands[0])
            self.do_run(matching_commands[0][1:], rest_inp)
        elif len(matching_commands) > 1:
            self.console.print("[red]Ambiguous command:", ", ".join(matching_commands))
        else:
            self.console.print(f"[red]Error: {first_word} is not a valid command.")
