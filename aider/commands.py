class Commands:
    def __init__(self, console, obj):
        self.console = console
        self.obj = obj

    def help(self):
        "Show help about all commands"
        commands = self.get_commands()
        for cmd in commands:
            cmd_method_name = f"cmd_{cmd[1:]}"
            cmd_method = getattr(self.obj, cmd_method_name, None)
            if cmd_method:
                description = cmd_method.__doc__
                self.console.print(f"{cmd} {description}")
            else:
                self.console.print(f"{cmd} No description available.")

    def get_commands(self):
        commands = ["/help"]
        for attr in dir(self.obj):
            if attr.startswith("cmd_"):
                commands.append("/" + attr[4:])

        return commands

    def do_run(self, cmd_name, args):
        cmd_method_name = f"cmd_{cmd_name}"
        cmd_method = getattr(self.obj, cmd_method_name, None)
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
            if matching_commands[0] == "/help":
                self.help()
            else:
                self.do_run(matching_commands[0][1:], rest_inp)
        elif len(matching_commands) > 1:
            self.console.print("[red]Ambiguous command:", ", ".join(matching_commands))
        else:
            self.console.print(f"[red]Error: {first_word} is not a valid command.")
