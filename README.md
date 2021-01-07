# Sane

Sane is Makefile for humans.

## Key Concepts

- Recipes are python functions with recipe/file/hook dependencies.

- Recipe dependencies are satisfied in the same fashion as Makefiles: if recipe
A depends on file F1 and recipe B, and recipe B depends on file F2, then A is
only ran if F1 is older than F2.

- Recipes are ran if its dependency files are newer than its target files (or if
either cannot be found).

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

for sourcefile in c_sources:
    objectfile = sourcefile + '.o'
    @recipe(
        name=f"compile_{sourcefile}",
        hooks=["compilation"],
        target_files=[objectfile],
        file_deps=[sourcefile])
    def compile():
        makedirs("obj/", exist_ok=True)
        sp.run(f"{CC} -c {sourcefile} -o {objectfile}", shell=True)

@recipe(hook_deps=["compilation"])
def link():
    obj_files = ' '.join(glob("src/*.o"))
    sp.run(f"{CC} -o {EXE} {obj_files}", shell=True)

sane_run(link)

```

## The `@recipe` Decorator

```python
@recipe(
    name="...",
    hooks=[...],
    file_deps=[...],
    target_files=[...],
    recipe_deps=[...],
    hook_deps=[...])
```

`name` - The name of the recipe (str). If none is given, the name is inferred
from the associated function's name. Two recipes cannot share the same name.

`hooks` - An array of hooks applicable to the recipe ([str]).

`file_deps` - The file dependencies of this recipe ([str]). This recipe is ran
if the newest of these files is newer that the oldest of the `target_files`.

`target_files` - Files to check against `file_deps` ([str]).

`recipe_deps` - The recipe dependencies of this recipe ([str or fn]); before
running this recipe, these are checked. If any is ran, this recipe is ran.

`hook_deps` - The hook dependencies of this recipe ([str]); before running this
recipe, all recipes with any of these hooks are checked. If any is ran, this
recipe is ran.

## License

This tool is licensed under an MIT license.
See LICENSE for details.

## Support

💕 If you liked quik, consider [buying me a coffee](https://www.paypal.me/miguelmurca/2.50).
