import subprocess as sp
from os import makedirs
from glob import glob

from sane import *

CC = "gcc"
EXE = "main"

c_sources = glob("src/*.c")

for sourcefile in c_sources:
    @recipe(
        name=f"compile_{sourcefile}",
        hooks=["compilation"],
        file_deps=[sourcefile, f"{sourcefile}.o"])
    def compile():
        makedirs("obj/", exist_ok=True)
        sp.run(f"{CC} -c {sourcefile} -o {sourcefile}.o", shell=True)

@recipe(hook_deps=["compilation"])
def link():
    obj_files = ' '.join(glob("src/*.o"))
    sp.run(f"{CC} -o {EXE} {obj_files}", shell=True)

sane_run(link)
