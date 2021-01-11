import subprocess as sp
from glob import glob
from sane import *

RM = "rm -r"
VERSIONFILE = "VERSION"

@recipe()
def clean():
    sp.run(f"{RM} build/ dist/ sane_build.egg-info", shell=True)

def read_version():
    with open(VERSIONFILE, 'r') as version_file:
        major = version_file.readline() or '1'
        minor = version_file.readline() or '0'
    return (int(major), int(minor))

def write_version(major, minor):
    with open(VERSIONFILE, 'w') as version_file:
        version_file.write(f'{major}\n')
        version_file.write(f'{minor}\n')

@recipe()
def increment_major():
    major, minor = read_version()
    write_version(major + 1, 0)

@recipe(
        target_files=[
            *glob("build/*"),
            *glob("dist/*"),
            "sane_build.egg-info"],
        file_deps=[
            "sane.py",
            "setup.py",
            *glob("tests/*")])
def build():
    # Increment the version
    major, minor = read_version()
    write_version(major, minor + 1)

    # Build
    sp.run("python3 setup.py sdist bdist_wheel", shell=True)

@recipe(recipe_deps=[clean, build])
def release():
    sp.run("twine upload dist/*", shell=True)

sane_run()
