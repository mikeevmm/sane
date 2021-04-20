# Sane

`sane` is a command runner made simple.

![Bit depressing, eh?](demo.gif)

## What

`sane` is:

- A *single* *Python* file, providing
- A decorator (`@recipe`), and a function (`sane_run`)

`sane` does **not**:

- Have its own domain specific language,
- Have an install process,
- Require anything other than `python3`,
- Restrict your Python code.

## Why

- More portable

At ~600 lines of code in a single file, `sane` is extremely portable, being made to be distributed alongside your code base. Being pure Python makes it cross-platform and with an extremely low adoption barrier. `sane` does not parse Python, or do otherwise "meta" operations, improving its future-proofness. `sane` aims to do only as much as reasonably documentable in a single README, and aims to have the minimum amount of gotchas, while preserving maximum flexibility.

- More readable

Its simple syntax and operation make it easy to understand and modify your recipe files. Everything is just Python, meaning neither you nor your users have to learn yet another domain specific language. 

- More flexible

You are free to keep state as you see fit, and all correct Python is valid. `sane` can function as a build system or as a command runner.

## Example

Below is a sane recipes file to compile a C executable (`Makefile` style).

```python
"""make.py

Exists in the root of a C project folder, with the following structure

<root>
   └ make.py
   └ sane.py
   │
   └ src
      └ *.c (source files)

The `build` recipe will build an executable at the root.
The executable can be launched with `python make.py`.
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
```

## The Flow of Recipes

`sane` uses **recipes**, **conditions** and **hooks**.

**Recipe:** A python function, with dependencies (on either/both other recipes and hooks), hooks, and conditions.

**Conditions:** Argument-less functions returning True or False.

**Hook:** A non-unique indentifier for a recipe. When a recipe depends on a hook, it depends on every recipe tagged with that hook.

The dependency tree of a given recipe is built and ran with `sane_run(recipe)`.
This is done according to a simple recursive algorithm:

0. Starting with the root recipe,
1. If the current recipe has no conditions or dependencies, register it as active
2. Otherwise, if any of the conditions is satisfied or dependency recipes is active, register it as active.
3. Sort the active recipes in descending depth and order of enumeration,
4. Run the recipes in order.

In concrete terms, this means that if

- Recipe `A` depends on `B`
- `B` has some conditions and depends on `C`
- `C` has some conditions

then

- If any of `B`'s conditions is satisfied, but none of `C`'s are, `B` is called and then `A` is called
- If any of `C`'s conditions is satisfied, `C`, `B`, `A` are called in that order
- Otherwise, nothing is ran.

## The `@recipe` decorator

Recipes are defined by decorating an argument-less function with `@recipe`:

```python
@recipe(name='...',
        hooks=['...'],
        recipe_deps=['...'],
        hook_deps=['...'],
        conditions=[...],
        info='...')
def my_recipe():
    # ...
    pass
```

**name:** The name ('str') of the recipe. If unspecified or `None`, it is inferred from the `__name__` attribute of the recipe function. However, recipe names must be unique, so dynamically created recipes (from, e.g., within a loop) typically require this argument.

**hooks:** `list` of `str`ings defining hooks for this recipe.

**recipe_deps:** `list` of `str`ing names that this recipe depends on. If an element of the list is not a string, a `name` is inferred from the `__name__` attribute, but this may cause an error if it does not match the given `name`.

**hook_deps:** `list` of `str`ing hooks that this recipe depends on. This means that the recipe implicitly depends on any recipe tagged with one of these hooks.

**conditions:** `list` of callables with signature `() -> bool`. If any of these is `True`, the recipe is considered active (see [The Flow of Recipes](#the-flow-of-recipes) for more information).

**info:** a description `str`ing to display when recipes are listed with `--list`.

## `sane_run`

```python
sane_run(default=None, cli=True)
```

This function should be called at the end of a recipes file, which will
trigger command-line arguments parsing, and run either the command-line
provided recipe, or, if none is specified, the defined `default` recipe.
(If neither are defined, an error is reported, and the program exits.)

(There are exceptions to this: `--help`, `--list` and similars will simply output the request information and exit.)

By default, `sane_run` runs in "CLI mode" (`cli=True`).
However, `sane_run` can also be called in "programmatic mode" (`cli=False`).
In this mode, command-line arguments will be ignored, and the `default`
recipe will be ran (observing dependencies, like in CLI mode).
This is useful if you wish to programmatically call upon a recipe (and its
subtree).

To see the available options and syntax when calling a recipes file (e.g., `make.py`), call

```bash
python make.py --help
```

## Installation

**It is recommended to just include sane.py in the same directory as your project.** You can do this easily with `curl`

```bash
curl 'https://raw.githubusercontent.com/mikeevmm/sane/master/sane.py' > sane.py
```

However, because it's convenient, `sane` is also available to install from PyPi with

```bash
pip install sane-build
```

## Miscelaneous

### `_Help`

`sane` provides a few helper functions that are not included by default. These are contained in a `Help` class and can be imported with

```python
from sane import _Help as Help
```

#### `Help.file_condition`

```python
Help.file_condition(sources=['...'],
                    targets=['...'])
```

Returns a callable that is `True` if the newest file in `sources` is older than the oldest files in `targets`, or if any of the files in `targets` does not exist.

**sources:** `list` of `str`ing path to files.

**targets:** `list` of `str`ing path to files.

#### Logging

The `sane` logging functions are exposed in `Help` as `log`, `warn`, `error`. These take a single string as a message, and the `error` function terminates the program with `exit(1)`.

### Concurrency

Recipes at the same depth are ran concurrently with a [ThreadPoolExecutor](https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.ThreadPoolExecutor). You can specify the number of threads to use with `--threads` (as of version 7.0). By default a single thread is used.

### Calling `python ...` is Gruesome

I suggest defining the following alias

```bash
alias sane='python3 make.py'
```

## License

This tool is licensed under an MIT license.
See LICENSE for details.
The LICENSE is included at the top of `sane.py`, so you may redistribute this file alone freely.

## Support

💕 If you liked sane, consider [buying me a coffee](https://www.paypal.me/miguelmurca/2.50).
