import os

import docker

from .parser import Parser


# FIXME: not thread-safe
class Builder(object):
    def __init__(self, ssl_version=None, assert_hostname=False):
        kwargs = docker.utils.kwargs_from_env(ssl_version, assert_hostname)
        self.client = docker.Client(version='auto', **kwargs)
        self.parser = Parser()
        self._reset_context()

    def _reset_context(self, base_dir=None):
        self.base_dir = base_dir
        self.previous_images = []
        self.maintainer = None
        self.workdir = None
        self.user = None
        self.stopsignal = None
        self.entrypoint = None
        self.default_command = None
        self.__environment = {}
        self.__variables = {}
        self.__labels = {}
        self.__ports = set()
        self.__volumes = set()

    def build(self, context_dir, dockerfile='Dockerfile', tag=None):
        self._reset_context(context_dir)
        dockerfile_location = os.path.join(context_dir, dockerfile)
        blueprint = self.parser.parse_from(dockerfile_location)
        for instruction in blueprint:
            print(instruction)
            self.previous_images.append(instruction.execute(self))
        cid = self.client.create_container(
            self.previous_image, self.default_command,
            **self.container_context()
        )
        self.previous_images.append(
            self.client.commit(cid, author=self.maintainer)['Id']
        )
        if tag is not None:
            self.client.tag(self.previous_image, tag)
        return self.previous_image

    @property
    def previous_image(self):
        return self.previous_images[-1]

    def container_context(self):
        return {
            'environment': self.__environment.copy(),
            'labels': self.__labels.copy(),
            'user': self.user,
            'working_dir': self.workdir,
            'stop_signal': self.stopsignal,
            'ports': list(self.__ports),
            'entrypoint': self.entrypoint
        }

    def variables(self):
        variables = self.__variables.copy()
        variables.update(self.__environment)
        return variables

    def update_labels(self, mapping):
        self.__labels.update(mapping)

    def update_variables(self, mapping):
        self.__variables.update(mapping)

    def update_environment(self, mapping):
        self.__environment.update(mapping)

    def expose_ports(self, ports):
        self.__ports = self.__ports.union(ports)

    def update_volumes(self, volumes):
        self.__volumes = self.__volumes.union(volumes)
