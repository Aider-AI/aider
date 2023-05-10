
class Commands:
    def cmd_help(self):
        print('help')
    def cmd_ls(self):
        print('ls')

    def get_commands(self):
        commands = []
        for attr in dir(self):
            if attr.startswith("cmd_"):
                commands.append('/' + attr[4:])

        return commands

    def run(self, inp, console):
        words = inp.strip().split()
        if not words:
            return

        first_word = words[0]
        all_commands = self.get_commands()
        matching_commands = [cmd for cmd in all_commands if cmd.startswith(first_word)]

        if len(matching_commands) == 1:
            console.print('[green]run', matching_commands[0])
        elif len(matching_commands) > 1:
            console.print('[yellow]Partial matches:', ', '.join(matching_commands))
        else:
            console.print('[red]Error: Command not found')
