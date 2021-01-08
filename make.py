import subprocess as sp
from glob import glob
from sane import *

RM = "rm -r"
VERSIONFILE = "VERSION"

@recipe()
def clean():
    sp.run(f"{RM} build/ dist/ sane_build.egg-info", shell=True)

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
    with open(VERSIONFILE, 'r') as version_file:
        current_version = int(version_file.read())
    next_version = current_version + 1
    with open(VERSIONFILE, 'w') as version_file:
        version_file.write(f'{next_version}')

    # Build
    sp.run("python3 setup.py sdist bdist_wheel", shell=True)

@recipe(recipe_deps=[clean, build])
def release():
    sp.run("twine upload dist/*", shell=True)

sane_run()
