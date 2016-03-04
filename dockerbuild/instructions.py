import glob
import json
import os.path
import shlex

from docker.errors import NotFound

from . import errors
from . import utils


class Instruction(object):
    name = 'GENRICINSTRUCTION'

    def __init__(self, argstr):
        self.argstr = argstr

    def __str__(self):
        return '<{name}> {argstr}'.format(name=self.name, argstr=self.argstr)

    def execute(self, builder):
        raise NotImplementedError()

    def commit(self, builder, container_id):
        image_id = builder.client.commit(
            container_id, author=builder.maintainer,
            message=str(self)
        )['Id']
        return image_id


class Var(object):
    def __init__(self, s):
        self.neg_default = False
        print(s)
        var = s.strip('${}')
        default = ''
        if ':' in var:
            var, default = var.split(':')
            if default.startswith('+'):
                self.neg_default = True
            default = default[1:]
        self.default = default
        self.name = var
        self.replace_target = s

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.replace_target == other.replace_target

    def __hash__(self):
        return hash(self.replace_target)


class KeyValueArgString(object):
    def parse_args(self):
        result = {}
        labels = shlex.split(self.argstr)
        for label in labels:
            if '=' not in label:
                raise errors.ParseError(0, label)
            k, v = label.split('=', 1)
            result[k] = v
        return result


class TemplatedInstruction(Instruction):
    def __init__(self, argstr):
        super(TemplatedInstruction, self).__init__(argstr)
        self.vars = set()
        self._find_next_var(argstr)

    def _find_next_var(self, s):
        idx = s.find('$')
        if idx == -1:
            return
        if not (idx == 0 or s[idx - 1] != '\\'):
            return self._find_next_var(s[idx:].split(None, 1)[1])
        else:
            if s[idx + 1] == '{':
                end = s[idx:].find('}') + 1
                self.vars.add(Var(s[idx:end]))
                return self._find_next_var(s[end:])
            else:
                split = s[idx:].split(None, 1)
                self.vars.add(Var(split[0]))
                if not len(split) == 1:
                    return self._find_next_var(split[1])

    def apply_substitutions(self, args):
        result = self.argstr
        for var in self.vars:
            if var.name in args:
                if var.neg_default:
                    result = result.replace(var.replace_target, '')
                else:
                    result = result.replace(var.replace_target, args[var.name])
            else:
                if var.neg_default:
                    result = result.replace(var.replace_target, '')
                else:
                    result = result.replace(var.replace_target, var.default)
        return result


class ShellInstruction(Instruction):
    def __init__(self, argstr):
        super(ShellInstruction, self).__init__(argstr)
        if argstr.startswith('['):
            self.shell_command = json.loads(argstr)
        else:
            self.shell_command = argstr

    def __str__(self):
        return '<{name}> {cmd}'.format(name=self.name, cmd=self.shell_command)


class FromInstr(Instruction):
    name = 'FROM'

    def __init__(self, argstr):
        super(FromInstr, self).__init__(argstr)
        if len(self.argstr.split()) > 1:
            raise errors.InvalidArgumentsError(
                self, "This command takes exactly one argument"
            )
        self.image_name = argstr

    def execute(self, builder):
        try:
            builder.client.inspect_image(self.image_name)
        except NotFound:
            pull_log = builder.client.pull(
                self.image_name, stream=True
            )
            for data in pull_log:
                data = json.loads(data)
                if 'error' in data:
                    raise errors.BuildError(data['error'])
                print(data.get('status'))

        return self.image_name


class MaintainerInstr(Instruction):
    name = 'MAINTAINER'

    def execute(self, builder):
        builder.maintainer = self.argstr
        return builder.previous_image


class RunInstr(ShellInstruction):
    name = 'RUN'

    def execute(self, builder):
        container_id = builder.client.create_container(
            builder.previous_image, self.shell_command,
            **builder.container_context()
        )
        builder.client.start(container_id)
        builder.client.wait(container_id)
        return self.commit(builder, container_id)


class CmdInstr(ShellInstruction):
    name = 'CMD'

    def execute(self, builder):
        builder.default_command = self.argstr
        return builder.previous_image


class LabelInstr(TemplatedInstruction, KeyValueArgString):
    name = 'LABEL'

    def execute(self, builder):
        self.argstr = self.apply_substitutions(builder.variables())
        builder.update_labels(self.parse_args())
        return builder.previous_image


class ExposeInstr(TemplatedInstruction):
    name = 'EXPOSE'

    def execute(self, builder):
        self.argstr = self.apply_substitutions(builder.variables())
        ports = [int(port) for port in self.argstr.split()]
        builder.expose_ports(ports)
        return builder.previous_image


class EnvInstr(TemplatedInstruction):
    name = 'ENV'

    def execute(self, builder):
        self.argstr = self.apply_substitutions(builder.variables())
        args = shlex.split(self.argstr)
        if len(args) == 2 and '=' not in args[0]:
            builder.update_environment({args[0]: args[1]})
            return builder.previous_image
        envs = {}
        for env in args:
            k, v = env.split('=')
            envs[k] = v
        builder.update_environment(envs)
        return builder.previous_image


class CopyInstr(TemplatedInstruction):
    name = 'COPY'

    def execute(self, builder):
        is_json = False
        if self.argstr.startswith('['):
            is_json = True
        self.argstr = self.apply_substitutions(builder.variables())
        paths = shlex.split(self.argstr) if not is_json else json.loads(
            self.argstr
        )
        dest_path = paths.pop()
        arc_name = None
        expanded_paths = []
        for path in paths:
            expanded_paths.extend(glob.glob(path))

        if dest_path[-1] != '/' and len(expanded_paths) == 1:
            expanded_paths[0] = (
                expanded_paths[0], os.path.basename(dest_path)
            )
            dest_path = os.path.dirname(dest_path)
        elif dest_path[-1] != '/':
            raise errors.InvalidArgumentsError(
                self, 'Destination directory must end with a slash'
            )
        else:
            arc_name = os.path.basename(dest_path)
            dest_path = dest_path.rsplit('/', 2)[0]

        archive = utils.tar(
            builder.base_dir, expanded_paths, dest_subdir=arc_name
        )
        container_id = builder.client.create_container(
            builder.previous_image, builder.default_command,
            **builder.container_context()
        )
        builder.client.put_archive(container_id, dest_path or '/', archive)
        return self.commit(builder, container_id)


class AddInstr(CopyInstr):
    name = 'ADD'


class EntryPointInstr(ShellInstruction):
    name = 'ENTRYPOINT'

    def execute(self, builder):
        builder.entrypoint = self.shell_command
        if builder.default_command:
            builder.default_command = False
        return builder.previous_image


class VolumeInstr(TemplatedInstruction):
    name = 'VOLUME'

    def execute(self, builder):
        is_json = False
        if self.argstr.startswith('['):
            is_json = True
        self.argstr = self.apply_substitutions(builder.variables())
        if is_json:
            volumes = json.loads(self.argstr)
        else:
            volumes = shlex.split(self.argstr)

        builder.update_volumes(volumes)
        return builder.previous_image


class UserInstr(TemplatedInstruction):
    name = 'USER'

    def execute(self, builder):
        self.argstr = self.apply_substitutions(builder.variables())
        builder.user = self.argstr
        return builder.previous_image


class WorkdirInstr(TemplatedInstruction):
    name = 'WORKDIR'

    def execute(self, builder):
        self.argstr = self.apply_substitutions(builder.variables())
        builder.workdir = self.argstr
        return builder.previous_image


class ArgInstr(Instruction, KeyValueArgString):
    name = 'ARG'

    def execute(self, builder):
        builder.update_variables(self.parse_args())
        return builder.previous_image


class StopsignalInstr(TemplatedInstruction):
    name = 'STOPSIGNAL'

    def execute(self, builder):
        builder.stopsignal = self.argstr
        return builder.previous_image


class OnbuildInstr(TemplatedInstruction):
    name = 'ONBUILD'
