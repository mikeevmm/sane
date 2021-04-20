import setuptools
import subprocess as sp
from glob import glob
from sane import *
from sane import _Sane, _Help as Help

VERSION = _Sane.VERSION
RM = "rm -r"

with open('README.md', 'r') as readme:
    readme = readme.read().replace('"""', r'\"\"\"')

new_sources = Help.file_condition(
    targets=[
        *glob("build/*"),
        *glob("dist/*"),
        "sane_build.egg-info"],
    sources=[
        "sane.py",
        *glob("tests/*")])


@recipe(info="Delete everything that build produces.")
def clean():
    sp.run(f"{RM} build/ dist/ sane_build.egg-info", shell=True)

@recipe(
    conditions=[new_sources],
    info="Build the PyPi distributable with setuptools.")
def build():
    if new_sources():
        sane_run(clean, cli=False)

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

@recipe(
        recipe_deps=[clean, build],
        info="Upload the built package to PyPi.")
def release():
    sp.run("twine upload dist/*", shell=True)

for testfile in glob('tests/test_*.py'):
    @recipe(name=testfile, hooks=['test'], info=f'Runs test \'{testfile}\'.')
    def run_test():
        out = sp.run(f'python \'{testfile}\'', shell=True, capture_output=True)
        if out.returncode != 0:
            Help.warn(f'{testfile} failed!')
            Help.warn('Stdout:')
            Help.warn(out.stdout.decode('utf-8'))
            Help.warn('Stderr:')
            Help.warn(out.stderr.decode('utf-8'))
        else:
            Help.log(f'\'{testfile}\' passed.')

@recipe(hook_deps=['test'], info="Run the unit tests in tests/")
def test():
    Help.log('Finished tests.')

@recipe(
        recipe_deps=[build],
        conditions=[lambda: True],
        info="Build and install the current source.")
def install():
    sp.run("pip install .", shell=True)


sane_run()
