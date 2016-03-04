import unittest

import dockerbuild


class DockerfileBuildTests(unittest.TestCase):
    def _build(self, dockerfile_name):
        builder = dockerbuild.Builder()
        return builder.build(
            './tests/dockerfiles', dockerfile_name,
            tag='dockerbuildtests/{0}'.format(dockerfile_name)
        )

    def test_add(self):
        self._build('add')

    def test_add_array(self):
        self._build('add_array')

    def test_arg(self):
        self._build('arg')

    def test_cmd_exec_form(self):
        self._build('cmd_exec_form')

    def test_cmd_shell_form(self):
        self._build('cmd_shell_form')

    def test_copy(self):
        self._build('copy')

    def test_copy_array(self):
        self._build('copy')

    def test_copy_wildcard(self):
        self._build('copy_wildcard')

    def test_entrypoint_exec(self):
        self._build('entrypoint_exec_form')

    def test_entrypoint_shell(self):
        self._build('entrypoint_shell_form')

    def test_env(self):
        self._build('env')

    def test_expose(self):
        self._build('expose')

    def test_from(self):
        self._build('from')

    def test_label(self):
        self._build('label')

    def test_maintainer(self):
        self._build('maintainer')

    def test_run_exec_form(self):
        self._build('run_exec_form')

    def test_run_shell_form(self):
        self._build('run_shell_form')

    def test_signal(self):
        self._build('signal')

    def test_user(self):
        self._build('user')

    def test_volume(self):
        self._build('volume')

    def test_volume_array(self):
        self._build('volume_array')
