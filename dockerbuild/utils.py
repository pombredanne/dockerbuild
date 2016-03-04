import os
import tarfile
import tempfile


def tar(base_dir, paths, dest_subdir=None):
    fileobj = tempfile.NamedTemporaryFile()
    t = tarfile.open(mode='w', fileobj=fileobj)

    root = os.path.abspath(base_dir)

    for path in paths:

        if isinstance(path, tuple):
            origin = os.path.join(root, path[0])
            destination = path[1]
        else:
            origin = os.path.join(root, path)
            destination = path
        if dest_subdir is not None:
            destination = os.path.join(dest_subdir, destination)
        t.add(origin, arcname=destination, recursive=True)

    t.close()
    fileobj.seek(0)
    return fileobj
