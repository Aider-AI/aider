
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

    def do_run(self, cmd_name, args):
        pass

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
