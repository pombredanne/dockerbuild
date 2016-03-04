from . import errors
from .instructions import (
    FromInstr, MaintainerInstr, RunInstr, CmdInstr, LabelInstr, ExposeInstr,
    EnvInstr, AddInstr, CopyInstr, EntryPointInstr, VolumeInstr, UserInstr,
    WorkdirInstr, ArgInstr, StopsignalInstr, OnbuildInstr
)


class Parser(object):
    def parse(self, filedata):
        blueprint = []
        for line in self._lex(filedata):
            command_name, args = line.split(None, 1)
            blueprint.append(self._create_command(command_name, args))
        return blueprint

    def parse_from(self, path):
        with open(path, 'r') as f:
            return self.parse(f)

    def _lex(self, filedata):
        buf = ''
        for line in filedata.readlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line[-1] == '\\':
                buf += line[:-1]
            elif buf:
                yield buf + line
                buf = ''
            else:
                yield line
        if buf:
            raise errors.ParseError(lineno=0, snippet=buf)

    def _create_command(self, cmd_name, argstring):
        class_index = {
            'from': FromInstr,
            'maintainer': MaintainerInstr,
            'run': RunInstr,
            'cmd': CmdInstr,
            'label': LabelInstr,
            'expose': ExposeInstr,
            'env': EnvInstr,
            'add': AddInstr,
            'copy': CopyInstr,
            'entrypoint': EntryPointInstr,
            'volume': VolumeInstr,
            'user': UserInstr,
            'workdir': WorkdirInstr,
            'arg': ArgInstr,
            'stopsignal': StopsignalInstr,
            'onbuild': OnbuildInstr,
        }
        try:
            return class_index[cmd_name.lower()](argstring)
        except KeyError:
            raise errors.InvalidCommandError(cmd_name)
