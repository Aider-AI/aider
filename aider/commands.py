
class Commands:
    def cmd_help(self, args):
        print('help')
    def cmd_ls(self, args):
        print('ls')

    def get_commands(self):
        commands = []
        for attr in dir(self):
            if attr.startswith("cmd_"):
                commands.append('/' + attr[4:])

        return commands

    def do_run(self, cmd_name, args):
        cmd_method_name = f"cmd_{cmd_name}"
        cmd_method = getattr(self, cmd_method_name, None)
        if cmd_method:
            cmd_method(args)
        else:
            print(f"Error: Command {cmd_name} not found.")
    def run(self, inp, console):
        words = inp.strip().split()
        if not words:
            return

        first_word = words[0]
        rest_inp = inp[len(words[0]):]

        all_commands = self.get_commands()
        matching_commands = [cmd for cmd in all_commands if cmd.startswith(first_word)]

        if len(matching_commands) == 1:
            console.print('[green]run', matching_commands[0])
            self.do_run(matching_commands[0][1:], rest_inp)
        elif len(matching_commands) > 1:
            console.print('[red]Ambiguous command:', ', '.join(matching_commands))
        else:
            console.print(f'[red]Error: {first_word} is not a valid command.')
