# Sane

Sane is Makefile for humans.

## Key Concepts

- Recipes are python functions with recipe/file/hook dependencies.

- Recipe dependencies are satisfied in the same fashion as Makefiles: if recipe
A depends on file F1 and recipe B, and recipe B depends on file F2, then A is
only ran if F1 is older than F2.

- Recipes with no dependencies are always ran.

- Hooks are a way to tag dependencies. Recipes depending on a hook depend on all
recipes with that hook.

- Everything else is standard Python.

## Getting Started

All of `Sane` is contained in `sane.py`.

With this file in your `PYTHONPATH` or the same directory:

```python
# make.py

from sane import *

# ... Recipe definitions ...

sane_run(default_recipe)
```

then `python make.py` runs the default recipe. Call `python make.py --help` for
more information.

## Example

```python
import subprocess as sp
from os import makedirs
from glob import glob

from sane import *

CC = "gcc"
EXE = "main"

c_sources = glob("src/*.c")

# Define a recipe for each of the C source files...
for sourcefile in c_sources:
    objectfile = f"{sourcefile}.o"

    @recipe(
        name=f"compile_{sourcefile}",
        hooks=["compilation"],
        file_deps=[sourcefile, objectfile])
    def compile():
        makedirs("obj/", exist_ok=True)
        sp.run(f"{CC} -c {sourcefile} -o {sourcefile}.o", shell=True)

# All compilation recipes have the compilation hook, so the linking
# recipe simply depends on this hook

@recipe(hook_deps=["compilation"])
def link():
    obj_files = ' '.join(glob("src/*.o"))
    sp.run(f"{CC} -o {EXE} {obj_files}", shell=True)

sane_run(link)

```

## License

This tool is licensed under an MIT license.
See LICENSE for details.

## Support

💕 If you liked quik, consider [buying me a coffee](https://www.paypal.me/miguelmurca/2.50).
