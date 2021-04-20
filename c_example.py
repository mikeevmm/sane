"""make.py

Exists in the root of a C project folder, with the following structure

<root>
   └ make.py
   └ sane.py
   │
   └ src
      └ *.c (source files)

The `build` recipe will build an executable at the root.
"""

import os
from subprocess import run
from glob import glob

from sane import *
from sane import _Help as Help

CC = "gcc"
EXE = "main"
SRC_DIR = "src"
OBJ_DIR = "obj"

COMPILE_FLAGS = '-g -O2'

# Ensure source and objects directories exist
os.makedirs(SRC_DIR, exist_ok=True)
os.makedirs(OBJ_DIR, exist_ok=True)

sources = glob(f'{SRC_DIR}/*.c')

# Define a compile recipe for each source file in SRC_DIR

def make_recipe(source_file):
    basename = os.path.basename(source_file)
    obj_file = f'{OBJ_DIR}/{basename}.o'
    objects_older_than_source = (
        Help.file_condition(sources=[source_file], targets=[obj_file]))
    
    @recipe(name=source_file,
            conditions=[objects_older_than_source],
            hooks=['compile'],
            info=f'Compiles the file \'{source_file}\'')
    def compile():
        run(f'{CC} {COMPILE_FLAGS} -c {source_file} -o {obj_file}', shell=True)

for source_file in sources:
    make_recipe(source_file)
    # Why not define the recipe here directly? Because Python loops don't create
    # new scope. See stackoverflow:2295290 for more information.

# Define a linking recipe
@recipe(hook_deps=['compile'],
        info='Links the executable.')
def link():
    obj_files = glob(f'{OBJ_DIR}/*.o')
    run(f'{CC} {" ".join(obj_files)} -o {EXE}', shell=True)

# Define a run recipe
@recipe(recipe_deps=[link],
        info='Runs the compiled executable.')
def run_exe():
    run(f'./{EXE}', shell=True)

sane_run(run_exe)
