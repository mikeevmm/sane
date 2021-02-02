import subprocess as sp
from glob import glob
from sane import *
import setuptools


VERSION = "4.2"
RM = "rm -r"

with open('README.md', 'r') as readme:
    readme = readme.read()

@recipe()
def clean():
    sp.run(f"{RM} build/ dist/ sane_build.egg-info", shell=True)

def read_version():
    major, minor = VERSION.split('.')
    return (int(major), int(minor))

@recipe(
        target_files=[
            *glob("build/*"),
            *glob("dist/*"),
            "sane_build.egg-info"],
        file_deps=[
            "sane.py",
            *glob("tests/*")])
def build():
    # Build
    with open('setup.py', 'w') as setup:
        setup.write(f"""\
import setuptools
setuptools.setup(
    name="sane-build",
    version={VERSION},
    author="Miguel Murça",
    author_email="miguel.murca+pypi@gmail.com",
    description="Make, but Sane",
    long_description=r\"\"\"{readme}\"\"\",
    long_description_content_type="text/markdown",
    license="MIT",
    keywords="make makefiles cmd utility cli",
    url="https://github.com/mikeevmm/sane",
    py_modules=["sane"],
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
    ],
    python_requires='>=3.6',
)""")
    sp.run("python3 setup.py sdist bdist_wheel", shell=True)

@recipe(recipe_deps=[clean, build])
def release():
    sp.run("twine upload dist/*", shell=True)

sane_run()
