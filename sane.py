import os
import argparse
from inspect import getframeinfo, stack

#### Reporting ####

class _AnsiColor:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class _VerboseLevel:
    NONE = 0
    VERBOSE = 1
    VERY_VERBOSE = 2

_verbose = 0

def _log(message, min_level=_VerboseLevel.NONE):
    if _verbose < min_level:
        return
    print(f"{_AnsiColor.OKBLUE}[LOG] {message}{_AnsiColor.ENDC}")

def _warn(message, min_level=_VerboseLevel.NONE):
    if _verbose < min_level:
        return
    print(f"{_AnsiColor.WARNING}[WARN] {message}{_AnsiColor.ENDC}")

def _error(message):
    print(f"{_AnsiColor.FAIL}[ERROR] {message}{_AnsiColor.ENDC}")

#### Internal State ####

_recipes = {}
_hooks = {}
_file_dependencies = {}
_recipe_dependencies = {}
_hook_dependencies = {}
_target_files = {}
_info = {}

#### Recipe Decorator ####

def recipe(*args, name=None, hooks=[], file_deps=[], recipe_deps=[], hook_deps=[], target_files=[], info=None):
    if len(args) > 0:
        caller = getframeinfo(stack()[-1][0])
        call_info = f"{caller.filename}: {caller.lineno}"
        _warn("Got unexpected arguments in recipe decorator at\n"
                f"          {call_info}\n"
                "       Are you missing a ()?")

    def recipe_fn(fn):
        nonlocal name, hooks, file_deps, recipe_deps, hook_deps, target_files, info

        _log(f"Registering recipe {fn}", _VerboseLevel.VERY_VERBOSE)

        # Do we need to infer the recipe's name
        if name is None:
            name = fn.__name__
            _name_inferred = True
            _log(f"Inferred name {name} for fn {fn}",
                    _VerboseLevel.VERY_VERBOSE)
        else:
            _name_inferred = False
            _log(f"Given name {name} for fn {fn}",
                    _VerboseLevel.VERY_VERBOSE)

        # Is the recipe name a duplicate?
        if name in _recipes:
            _error(f"Duplicate named recipe '{name}'")
            if _name_inferred:
                _error(f"The name was inferred from the function name;")
                _error("Consider giving the recipe a unique name, with")
                _error("        @recipe(name='...', ...)")
            exit(1)

        # Type checking
        if type(name) is not str:
            _error(f"`name` for recipe '{fn}' is not string")
            exit(1)
        if type(hooks) not in (list, tuple):
            _error(f"`hooks` for recipe '{name}' is not list or tuple")
            exit(1)
        if type(file_deps) not in (list, tuple):
            _error(f"`file_deps` for recipe '{name}' is not list or tuple")
            exit(1)
        if type(recipe_deps) not in (list, tuple):
            _error(f"`recipe_deps` for recipe '{name}' is not list or tuple")
            exit(1)
        if type(hook_deps) not in (list, tuple):
            _error(f"`hook_deps` for recipe '{name}' is not list or tuple")
            exit(1)
        if type(target_files) not in (list, tuple):
            _error(f"`target_files` for recipe '{name}' is not list or tuple")
            exit(1)
        if info is not None and type(info) is not str:
            _error(f"`info` for recipe '{name}' is not string")
            exit(1)

        ## Save recipe by name, and information
        _recipes[name] = fn

        if info is not None:
            _info[name] = info

        ## Register the function's dependencies
        # Note that the dependence recipes might not yet be registered,
        # and that we tolerate dependencies on files that do not exist.
        # Sanitize first
        abs_file_deps = [os.path.abspath(path) for path in file_deps]
        abs_target_files = [os.path.abspath(path) for path in target_files]
        
        recipe_deps_buf = []
        for recipe_dep in recipe_deps:
            if type(recipe_dep) is not str:
                if "__name__" not in dir(recipe_dep):
                    _error(f"Invalid object '{recipe_rep}' under recipe "
                            f"dependencies of recipe '{name}'")
                    exit(1)
                recipe_dep = recipe_dep.__name__
            recipe_deps_buf.append(recipe_dep)
        recipe_deps = recipe_deps_buf
        for hook in hook_deps:
            if type(hook) is not str:
                _error(f"Hooks must be strings, got '{hook}' as a hook "
                        "dependency for recipe '{name}'")
                exit(1)

        _file_dependencies.setdefault(name, []).extend(abs_file_deps)
        _target_files.setdefault(name, []).extend(abs_target_files)

        if len(abs_target_files) == 0 and len(abs_file_deps) > 0:
            _warn(f"Recipe '{name}' has file dependencies, but no target files")

        _recipe_dependencies.setdefault(name, []).extend(recipe_deps)
        _hook_dependencies.setdefault(name, []).extend(hook_deps)

        _log(f"Saved dependencies for recipe '{name} ({fn}):'\n"
                "File dependencies:\n"
                '\n'.join(f"    - {path}" for path in abs_file_deps),
                _VerboseLevel.VERY_VERBOSE)

        ## Register the hooks
        for hook in hooks:
            if type(hook) is not str:
                _error(f"Hook '{hook}' of recipe '{name}' is not a string; "
                        "hooks must be strings")
                exit(1)
            
            _hooks.setdefault(hook, []).append(name)

        _log(f"Saved hooks for recipe '{name} ({fn})'",
                _VerboseLevel.VERY_VERBOSE)

        return fn
    return recipe_fn

#### Run Routine ####

def _check_recipe_deps():
    _log("Checking that dependence recipes are all defined",
            _VerboseLevel.VERY_VERBOSE)
    for base_recipe in _recipe_dependencies:
        for dependence in _recipe_dependencies[base_recipe]:
            if dependence not in _recipes:
                _error(f"Recipe dependency '{dependence}' on recipe "
                    f"'{base_recipe}' is not defined")
                exit(1)
    _log("All dependence recipes are defined", _VerboseLevel.VERY_VERBOSE)

def _check_cyclic(recipe):
    _log(f"Checking for cyclic dependencies on recipe '{recipe}'",
            _VerboseLevel.VERY_VERBOSE)
    
    class DepNode:
        RECIPE = 'recipe'
        HOOK = 'hook'

        def __init__(self, kind, name, parent):
            self.kind = kind
            self.name = name
            self.parent = parent

        def __repr__(self):
            if self.kind == DepNode.RECIPE:
                return f"Recipe({self.name})"
            if self.kind == DepNode.HOOK:
                return f"Hook({self.name})"
            return f"Unknown({self.name})"

        def __eq__(self, other):
            return str(self) == str(other)

    recipe_node = DepNode(DepNode.RECIPE, recipe, None)
    visited = []
    leaves = [recipe_node]
    leaf_buffer = []
    while len(leaves) > 0:
        for leaf in leaves:
            if leaf in visited:
                # Circular path!
                # Rebuild path
                path = [leaf]
                parent = leaf.parent
                while parent is not None:
                    path.append(parent)
                    parent = parent.parent
                path.reverse()
                # Report error
                _error(f"Circular dependency on recipe '{recipe}'\n" + \
                        (" > ".join(str(x) for x in path)))
                exit(1)

            # Now visited
            visited.append(leaf)

            if leaf.kind == DepNode.RECIPE:
                for recipe_dep in _recipe_dependencies.get(leaf.name, []):
                    dep_leaf = DepNode(DepNode.RECIPE, recipe_dep, leaf)
                    leaf_buffer.append(dep_leaf)
                for hook_dep in _hook_dependencies.get(leaf.name, []):
                    dep_hook = DepNode(DepNode.HOOK, hook_dep, leaf)
                    leaf_buffer.append(dep_hook)
            elif leaf.kind == DepNode.HOOK:
                for hooked_recipe in _hooks.get(leaf.name, []):
                    dep_leaf = DepNode(DepNode.RECIPE, hooked_recipe, leaf)
                    leaf_buffer.append(dep_leaf)
        leaves = leaf_buffer
        leaf_buffer = []
    
    _log(f"Finished checking for cyclic dependencies on recipe '{recipe}'",
            _VerboseLevel.VERY_VERBOSE)

def _run_recipe(recipe, force=False):
    # The Makefile approach:
    # Check the oldest file this depends on; if any
    # dependency of this is more recent, rerun.
    # Greater m_time means more recent modification
    dependencies = _recipe_dependencies.get(recipe, [])
    for hook in _hook_dependencies.get(recipe, []):
        dependencies.extend(_hooks.get(hook, []))
    _log(f"Found the following dependencies for recipe '{recipe}':\n" + \
            ('\n'.join(f"  - {dep}" for dep in dependencies)),
            _VerboseLevel.VERY_VERBOSE)

    any_ran = False
    for dependency in dependencies:
        ran = _run_recipe(dependency, force)
        if ran:
            any_ran = True

    run = any_ran
    if not any_ran:
        _log(f"Checking file dependencies of recipe '{recipe}'",
                _VerboseLevel.VERY_VERBOSE)
        dep_newest = None 
        for file_dep in _file_dependencies.get(recipe, []):
            if not os.path.exists(file_dep):
                dep_newest = None
                break
            modification_time = os.stat(file_dep).st_mtime
            if dep_newest is None or modification_time > dep_newest:
                dep_newest = modification_time
        _log(f"Newest dependency from {dep_newest}",
                _VerboseLevel.VERY_VERBOSE)

        target_oldest = None
        for target in _target_files.get(recipe, []):
            if not os.path.exists(target):
                target_oldest = None
                break
            modification_time = os.stat(target).st_mtime
            if target_oldest is None or modification_time < target_oldest:
                target_oldest = modification_time
        _log(f"Oldest target from {target_oldest}",
                _VerboseLevel.VERY_VERBOSE)

        if dep_newest is None \
                or target_oldest is None \
                or dep_newest > target_oldest:
            run = True

    if force or run:
        _log(f"Running recipe '{recipe}'", _VerboseLevel.VERBOSE)
        _recipes[recipe]()
        return True
    else:
        _log(f"Skipping recipe '{recipe}'", _VerboseLevel.NONE)
        return False

def sane_run(default=None):
    global _verbose

    parser = argparse.ArgumentParser(description="Make, but Sane")
    parser.add_argument('--version', action='version',
            version=f'Sane 5.0')
    parser.add_argument('--verbose', metavar='level', type=int, default=0, 
        help="Level of verbosity in logs. "
         f"{_VerboseLevel.NONE} is not verbose, "
         f"{_VerboseLevel.VERY_VERBOSE} is most verbose.")
    parser.add_argument("recipe", nargs='?', default=None,
        help="The recipe to run. If none is given, the default recipe is ran.")
    parser.add_argument("--force", action="store_true",
        help="Ignore the times of file dependencies when deciding "
         "what recipes to run (i.e., run all).")
    parser.add_argument("--list", action="store_true", default=False,
        help="List the defined recipes.")

    args = parser.parse_args()

    if args.list:
        for recipe in _recipes:
            print(f" -- {recipe}")
            if recipe in _info:
                print(f"  {_info[recipe]}")
            else:
                print(f"  [no information given]")
        exit(0)

    recipe = args.recipe
    _verbose = args.verbose
    
    if recipe is None:
        if default is None:
            _log("No recipe given and no default recipe, exiting")
            exit(0)
        else:
            if type(default) is not str:
                if "__name__" not in dir(default):
                    _error("Given `default` recipe not a string, and the given "
                            "object has no '__name__' property\n"
                            f"Got given as default recipe {default}")
                    exit(1)

                if default.__name__ not in _recipes:
                    _error("Given `default` recipe not a string, and the "
                            f"inferred name '{default.__name__}' was not "
                            "found as a recipe.")
                    exit(1)

                recipe = default.__name__
            else:
                if default not in _recipes:
                    _error("No recipe given, and `default` recipe "
                            f"'{default}' does not exist as a recipe.")
                    exit(1)
                recipe = default
    else:
        if recipe not in _recipes:
            _error(f"Given recipe {recipe} does not exist.")
            exit(1)

    _check_recipe_deps()
    _check_cyclic(recipe)

    _run_recipe(recipe, force=args.force)

