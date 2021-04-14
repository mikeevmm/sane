import os
from subprocess import run
from glob import glob

from sane import *

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
for source_file in sources:
    basename = os.path.basename(source_file)
    obj_file = f'{OBJ_DIR}/{basename}.o'
    objects_older_than_source = (
        sane_file_condition(sources=[source_file], targets=[obj_file]))
    
    @recipe(name=source_file,
            conditions=[objects_older_than_source],
            hooks=['compile'],
            info=f'Compiles the file \'{source_file}\'')
    def compile():
        run(f'{CC} {COMPILE_FLAGS} -c {source_file} -o {obj_file}', shell=True)

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
