# dockerbuild

Python implementation of the docker builder.

## Installation

```bash
git clone https://github.com/shin-/dockerbuild
python setup.py install
```

## Usage

```python
import dockerbuild

builder = dockerbuild.Builder()
dockerfile_path = './Dockerfile'
image_id = builder.build(context_dir='.', dockerfile='Dockerfile', tag='myimage')
```
