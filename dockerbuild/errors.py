
class ParseError(Exception):
    def __init__(self, lineno, snippet):
        message = 'Parse error at line {lineno}: "{snippet}" is invalid'
        ' syntax'.format(lineno=lineno, snippet=snippet)
        super(self.__class__, self).__init__(message)
        self.lineno = lineno
        self.snippet = snippet


class InvalidCommandError(Exception):
    def __init__(self, command_name, lineno=0):
        super(self.__class__, self).__init__(
            'Invalid command name: "{}" is not a recognized command'.format(
                command_name
            )
        )
        self.command_name = command_name
        self.lineno = lineno


class InvalidArgumentsError(Exception):
    def __init__(self, command, explanation):
        super(self.__class__, self).__init__(
            'Command {name} argument string is invalid. {explanation}'.format(
                name=command.name, explanation=explanation
            )
        )
        self.command = command
        self.explanation = explanation


class BuildError(Exception):
    pass
