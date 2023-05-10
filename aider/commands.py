
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
        console.print('[red]', inp)
        words = inp.strip().split()
