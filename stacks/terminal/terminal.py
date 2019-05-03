import zmq

import readline
import code

import reactor.terminal.commands as commands

class Terminal:
    def run(self, context, config):
        self._context = context

        variables = {}
        for name, func in commands.__dict__.items():
            if callable(func):
                variables[name] = func

        commands.set_context(context)

        # Now connect any requested sockets
        if 'sockets' in config:
            for conf,endpoint in config['sockets'].items():
                parts = conf.split(':')
                if parts[0] == 'connect':
                    commands.connect_socket(parts[2], parts[1], endpoint)
                elif parts[0] == 'bind':
                    commands.bind_socket(parts[2], parts[1], endpoint)

        shell = code.InteractiveConsole(variables)
        shell.interact()
