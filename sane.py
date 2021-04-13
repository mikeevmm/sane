import os
import argparse
import inspect
import bisect
import difflib


class _Sane:
    VERSION = '6.0'

    ### State ###

    def __init__(self):
        self.verbose = 0
        self.use_ansi = True
        self.graph = {}
        self.recipes = []
        self.hooks = []
        self.recipe_calls = []

    #### Reporting ####

    class AnsiColor:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKCYAN = '\033[96m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        ENDBOLD = '\033[22m'
        UNDERLINE = '\033[4m'

    class VerboseLevel:
        NONE = 0
        VERBOSE = 1
        VERY_VERBOSE = 2

    INDENT_LEADER = '  '
    LOG_PLATE = '[LOG] '
    WARN_PLATE = '[WARN] '
    ERROR_PLATE = '[ERROR] '

    @staticmethod
    def indent(message, leader):
        if type(leader) is int:
            leader = _Sane.INDENT_LEADER * leader
        return '\n'.join(leader + line for line in message.split('\n'))

    @staticmethod
    def trace(frame):
        line_call_str = f'{frame.filename}: {frame.lineno}'
        line_indicator = ('>  ' if i == frame.index else '|  '
                          for i in range(len(frame.code_context)))
        line_ctx_str = ''.join(f'{indicator}{line}'
                               for line, indicator in 
                               zip(frame.code_context, line_indicator))
        return (f'{line_call_str}\n'
                f'{line_ctx_str}')

    def bold(self, message):
        if self.use_ansi:
            return f'{_Sane.AnsiColor.BOLD}{message}{_Sane.AnsiColor.ENDBOLD}'
        return message

    def log(self, message, min_level=VerboseLevel.NONE):
        if self.verbose < min_level:
            return
        message = _Sane.indent(message, ' ' * len(_Sane.LOG_PLATE))
        # Suppress the plate spacing of the first line
        message = message[len(_Sane.LOG_PLATE):]
        if self.use_ansi:
            print(f'{_Sane.AnsiColor.OKBLUE}{_Sane.LOG_PLATE}'
                  f'{message}{_Sane.AnsiColor.ENDC}')
        else:
            print(f'{_Sane.LOG_PLATE}{message}')

    def warn(self, message, min_level=VerboseLevel.NONE):
        if self.verbose < min_level:
            return
        message = _Sane.indent(message, ' ' * len(_Sane.WARN_PLATE))
        # Suppress the plate spacing of the first line
        message = message[len(_Sane.WARN_PLATE):]
        if self.use_ansi:
            print(f'{_Sane.AnsiColor.WARNING}{_Sane.WARN_PLATE}'
                  f'{message}{_Sane.AnsiColor.ENDC}')
        else:
            print(f'{_Sane.WARN_PLATE}{message}')

    def error(self, message):
        message = _Sane.indent(message, ' ' * len(_Sane.ERROR_PLATE))
        # Suppress the plate spacing of the first line
        message = message[len(_Sane.ERROR_PLATE):]
        if self.use_ansi:
            print(f'{_Sane.AnsiColor.FAIL}{_Sane.ERROR_PLATE}'
                  f'{message}{_Sane.AnsiColor.ENDC}')
        else:
            print(f'{_Sane.ERROR_PLATE}{message}')
        exit(1)

    def set_verbose(self, verbose_level):
        self.verbose = verbose_level

    def set_ansi(self, use_ansi):
        self.use_ansi = use_ansi

    ### Dependency Graph ###

    class Node:
        HOOK = 0
        RECIPE = 1

        def __init__(self, type_, connections=[], meta={}):
            self.type = type_
            self.connections = connections
            self.meta = meta

        def is_always_active(self):
            if self.type == _Sane.Node.HOOK:
                # A hook is only active if any of its children are active
                return False
            elif self.type == _Sane.Node.RECIPE:
                conds = self.meta['conditions']
                return ((len(self.connections) == 0) and
                        (len(conds) == 0 or any(x() for x in conds)))
            else:
                raise ValueError(f'Unknown node type \'{self.type}\'.')

    @staticmethod
    def get_unique_name(name, type_):
        if type_ == _Sane.Node.HOOK:
            return f'hook-{name}'
        elif type_ == _Sane.Node.RECIPE:
            return f'recipe-{name}'
        else:
            raise ValueError(f'Unimplemented type \'{type_}\'')

    @staticmethod
    def split_unique_name(unique_name):
        if unique_name.startswith('hook-'):
            return _Sane.Node.HOOK, unique_name[len('hook-'):]
        elif unique_name.startswith('recipe-'):
            return _Sane.Node.RECIPE, unique_name[len('recipe-'):]
        else:
            raise ValueError(f'Unknown type of unique name \'{unique_name}\'')

    @staticmethod
    def human_format_unique_name(unique_name):
        type_, name = _Sane.split_unique_name(unique_name)
        if type_ == _Sane.Node.RECIPE:
            return f'\'{name}\' (Recipe)'
        elif type_ == _Sane.Node.HOOK:
            return f'\'{name}\' (Hook)'
        else:
            raise ValueError(f'Unknown type \'{type_}\'.')

    def recipe_exists(self, recipe):
        i = bisect.bisect_left(self.recipes, recipe)
        return (i < len(self.recipes) and self.recipes[i] == recipe)

    def hook_exists(self, hook):
        i = bisect.bisect_left(self.hooks, hook)
        return (i < len(self.hooks) and self.hooks[i] == hook)

    def list_recipes(self):
        for recipe_name in self.recipes:
            recipe_unique_name = _Sane.get_unique_name(
                recipe_name, _Sane.Node.RECIPE)
            recipe_node = self.graph[recipe_unique_name]
            print(f' -- {recipe_name}')
            if recipe_node.meta.get('info', None) is not None:
                print(_Sane.indent(recipe_node.meta['info'], 3))
            else:
                print(_Sane.indent('[no information given]', 3))

    def report_unknown(self, unknown_recipe, from_, traceback):
        error_message = (f'Recipe \'{from_}\' depends on an undefined '
                         f'recipe \'{unknown_recipe}\':\n'
                         f'{traceback}')
        # Fuzz the unknown recipe. If there's another recipe name
        # that matches more than 80%, suggest that.
        closest_i = (
            bisect.bisect_left(self.recipes, unknown_recipe) - 1)
        if closest_i >= 0:
            closest = self.recipes[closest_i]
            diff = difflib.ndiff(closest, unknown_recipe)
            common = 0
            total = 0
            for change in diff:
                if change[0] == ' ':
                    common += 1
                total += 1
            if common/total >= 0.80:
                error_message += f'\nDid you mean \'{closest}\'?'
        self.error(error_message)

    def report_cyclic(self, from_, traceback):
        self.error(f'Recipe \'{from_}\' has cyclic dependencies:\n'
                   f'{traceback}')

    ### Registration ###

    def register_recipe(self, fn, name, hooks, recipe_deps,
                        hook_deps, conditions, info):
        for hook in hooks:
            hook_node = \
                self.graph.setdefault(
                    _Sane.get_unique_name(hook, _Sane.Node.HOOK),
                    _Sane.Node(_Sane.Node.HOOK))
            hook_node.connections.append(
                _Sane.get_unique_name(name, _Sane.Node.RECIPE))
            i = bisect.bisect_left(self.hooks, hook)
            if not (i < len(self.hooks) and self.hooks[i] == hook):
                self.hooks.insert(i, hook)

        connections = \
            [_Sane.get_unique_name(recipe, _Sane.Node.RECIPE)
             for recipe in recipe_deps] + \
            [_Sane.get_unique_name(hook, _Sane.Node.HOOK)
             for hook in hook_deps]

        unique_name = _Sane.get_unique_name(name, _Sane.Node.RECIPE)
        self.graph[unique_name] = \
            _Sane.Node(
                _Sane.Node.RECIPE,
                connections,
                {
                    'fn': fn,
                    'conditions': conditions,  # unique names
                    'info': info  # string
                })

        # Recipes are inserted sorted by name, so as to be able to
        # perform fuzzing later.
        i = bisect.bisect_left(self.recipes, name)
        if not (i < len(self.recipes) and self.recipes[i] == name):
            self.recipes.insert(i, name)

    def register_decorator_call(self, frame, *args, **kwargs):
        # @recipe parsing is done after parsing of command line arguments.
        # During the @recipe calls a (args, kwargs, frame) object is stored.
        self.recipe_calls.append((args, kwargs, frame))

    def parse_decorator_calls(self):
        self.recipe_calls.reverse()
        while len(self.recipe_calls) > 0:
            args, kwargs, frame = self.recipe_calls.pop()

            # "Unwrap" expected kwargs
            name = kwargs['name']
            hooks = kwargs['hooks']
            recipe_deps = kwargs['recipe_deps']
            hook_deps = kwargs['hook_deps']
            conditions = kwargs['conditions']
            info = kwargs['info']
            fn = kwargs['fn']
            del kwargs['fn'], kwargs['name'], kwargs['hooks'], \
                kwargs['recipe_deps'], kwargs['hook_deps'], \
                kwargs['conditions'], kwargs['info']

            # Often, the user will wrongly decorate the function with `@recipe`,
            # instead of `@recipe()`, if they intend all the arguments to take
            # their default values. It would be possible to "switch modes"
            # depending on whether other arguments are specified, but for the
            # sake of being less error prone, an error is reported (with the
            # above suggestion).
            if len(args) > 0:
                quoted_args = (f'\'{arg}\'' for arg in args)
                error_msg = ('Got unexpected argument in recipe decorator at\n'
                             f'{_Sane.trace(frame)}\n'
                             'Unrecognized arguments are: '
                             f'{", ".join(quoted_args)}.')
                if len(args) == 1 and hasattr(args[0], '__call__'):
                    error_msg += '\nAre you missing a `()` after `@recipe`?'
                self.error(error_msg)

            # Deprecated and unrecognized keyword arguments
            # - file_deps and target_files
            file_deps_present = ('file_deps' in kwargs)
            target_files_present = ('target_files' in kwargs)
            if file_deps_present or target_files_present:
                sample_code = (
                        self.bold(
                            'conditions=[ sane_file_condition('
                            'file_deps=[...], target_files=[...]) ]'))
                self.warn(f'In recipe \'{name}\':\n'
                          '`file_deps` and `target_files` are deprecated '
                          'arguments. \n'
                          f'Use\n'
                          f' {sample_code}\n'
                          'instead.\n'
                          'This condition has been automatically inserted, '
                          'but may be ignored or fail in the future.')
                conditions.append(
                    sane_file_condition(
                        file_deps=kwargs.get('file_deps', []),
                        target_files=kwargs.get('target_files', [])))
                if file_deps_present:
                    del kwargs['file_deps']
                if target_files_present:
                    del kwargs['target_files']

            # - Unknown keyword arguments
            if len(kwargs) > 0:
                self.error('Got unexpected keyword arguments in recipe '
                           'decorator at\n'
                           f'{_Sane.trace(frame)}\n'
                           'Unrecognized keyword arguments are: '
                           f'{", ".join(kwargs)}.')

            # Check if the decorator is wrapping a callable object
            if not hasattr(fn, '__call__'):
                self.error(f'Cannot decorate non-callable object \'{fn}\' '
                           'as recipe.\n'
                           f'At {_Sane.trace(frame)}')

            # Check if name inference is needed
            if name is None:
                name_inferred = True
                name = fn.__name__
                self.log(
                    f'Inferred name \'{name}\' for function \'{fn}\'.',
                    _Sane.VerboseLevel.VERY_VERBOSE)
            else:
                name_inferred = False

            # Check if recipe name is a duplicate
            if self.recipe_exists(name):
                error_msg = 'Duplicate recipe of name \'{name}\'.'
                if name_inferred:
                    error_msg += (
                            'The name was inferred from the function name;\n'
                            'consider giving the recipe a unique name, with\n')
                    error_msg += _Sane.indent('@recipe(name=\'...\', ...)', 3)
                self.error(error_msg)

            # Type checking
            if type(name) is not str:
                self.error(f'`name` for recipe \'{name}\' is not string.\n'
                           f'At {_Sane.trace(frame)}')
            if type(hooks) not in (list, tuple):
                self.error(
                        f'`hooks` for recipe \'{name}\' is not list or tuple.\n'
                        f'At {_Sane.trace(frame)}')
            if type(recipe_deps) not in (list, tuple):
                self.error(
                        f'`recipe_deps` for recipe \'{name}\' is not list or '
                        'tuple.\n'
                        f'At {_Sane.trace(frame)}')
            if type(hook_deps) not in (list, tuple):
                self.error(
                        f'`hook_deps` for recipe \'{name}\' is not list or '
                        'tuple.\n'
                        f'At {_Sane.trace(frame)}')
            if type(conditions) not in (list, tuple):
                self.error(
                        f'`conditions` for recipe \'{name}\' is not list or '
                        'tuple.\n'
                        f'At {_Sane.trace(frame)}')
            if info is not None and type(info) is not str:
                self.error(f'`info` for recipe \'{name}\' is not string.\n'
                           f'At {_Sane.trace(frame)}')

            # Recipe dependency sanitizing
            # - Recipe dependency
            for i, recipe_dep in enumerate(recipe_deps):
                if type(recipe_dep) is not str:
                    if not hasattr(recipe_dep, '__name__'):
                        self.error(
                                f'Invalid object \'{recipe_dep}\' under recipe '
                                f'dependencies of recipe named \'{name}\'.\n'
                                f'At {_Sane.trace(frame)}')
                    recipe_deps[i] = recipe_dep.__name__
            self.log(
                f'Recipe dependencies of recipe \'{name}\':\n'
                f'{chr(10).join(recipe_deps)}',
                _Sane.VerboseLevel.VERY_VERBOSE)

            # - Hook dependency
            for hook in hook_deps:
                if type(hook) is not str:
                    self.error(f'Hooks must be strings, but got \'{hook}\' '
                               f'as a hook dependency of recipe \'{name}\'.\n'
                               f'At {_Sane.trace(frame)}')
            self.log(
                f'Hooks of recipe \'{name}\':\n{chr(10).join(hook_deps)}',
                _Sane.VerboseLevel.VERY_VERBOSE)

            # - Condition dependency
            for condition in conditions:
                if not hasattr(condition, '__call__'):
                    self.error(
                            'Conditions must be callables, but got '
                            f'\'{condition}\' as a condition of recipe '
                            f'\'{name}\'.\n'
                            f'At {_Sane.trace(frame)}')
                cond_signature = inspect.signature(condition)
                if any(arg.default == inspect.Parameter.empty
                        for arg in cond_signature.parameters):
                    self.error(
                            f'Condition \'{condition}\' of recipe \'{name}\' '
                            'takes required parameters. This is not allowed; '
                            'conditions are called without arguments.')
            self.log(
                f'Conditions of recipe \'{name}\':\n'
                f'{chr(10).join(str(x) for x in conditions)}',
                _Sane.VerboseLevel.VERY_VERBOSE)

            # Register recipe
            self.log(
                f'Registring recipe \'{name}\' (-> \'{fn}\').',
                _Sane.VerboseLevel.VERY_VERBOSE)
            self.register_recipe(fn, name, hooks, recipe_deps, hook_deps,
                                 conditions, info)

            del frame

    ### Execution ###

    def run_recipe_graph(self, recipe_name, force=False):
        """
        This is perhaps the most "sensitive" part of `sane`,
        so below is a more comprehensive description of what
        the taken approach is.
        This should also allow to disambiguate the behaviour
        of `sane` for less clear dependency situations.
        First of all, these are the assumptions (enforced by
        the program either before this function was called or
        upon visiting a node) about the graph of dependencies:

         - Each node uniquely corresponds to either a recipe
            (function) or a hook.
         - The connections are directed (so it's a directed graph),
            from the recipes to their dependencies.
         - The graph is acyclic.

        At a high level, the algorithm consists of a depth-first
        search of the tree of dependencies (considering that hook
        dependencies are expanded to the recipes with that hook),
        recursively marking a recipe as to be ran if any node in
        its subtree corresponds to an active recipe.

        ```python
        def check_node(node):
          active = (any(condition() for condition in conditions)
                    or any(check_node(child) for child in connections))
          if is_recipe(node) and active:
              register_node_as_active
          register_node_as_visited

          return active
        ```

        The active recipes are then sorted by decreasing order in
        their depth in the tree, and ran in sorting order.
        Sorting of recipes at same depth is disambiguated by order
        of iteration in exploration of the tree (recipes found
        "earlier" are ran first).

        Each recipe is ran iff:

          - any of its conditions are satisfied
          - it depends on a ran recipe
          - it has no dependencies (recipes, hooks, or conditions)

        The recursive approach is "iterative"-ized by manually managing
        lists as stacks. The reason for this is two fold: to have more
        control over the amount of objects kept in memory in deep recursion,
        and to avoid hitting Python's limit recursion depth in more extreme
        cases.
        """
        root_name = recipe_name
        root_unique_name = \
            _Sane.get_unique_name(root_name, _Sane.Node.RECIPE)
        root_node = self.graph[root_unique_name]

        active = []
        active_ordering = []
        visited = []
        backtrack_names = [root_unique_name]
        backtrack_child_idx = [0]
        backtrack_active = [root_node.is_always_active() or force, False]
        depth = 0
        ord_ = 0
        while len(backtrack_names) > 0:
            unique_name = backtrack_names[-1]
            child_idx = backtrack_child_idx.pop()
            child_active = backtrack_active.pop()

            # Update self active state based on child
            backtrack_active[-1] |= child_active

            node = self.graph[unique_name]
            # Return
            if child_idx >= len(node.connections):
                unique_name = backtrack_names.pop()
                type_, name = _Sane.split_unique_name(unique_name)

                # Mark as visited
                element = (depth, unique_name)
                i = bisect.bisect_left(visited, element)
                visited.insert(i, element)

                # Register as active if appropriate
                self_active = backtrack_active[-1]
                if self_active:
                    i = bisect.bisect_left(active, element)
                    active.insert(i, element)
                    active_ordering.insert(i, (element[0], ord_))
                    # Ord is decreased so that sort+reverse results in
                    # first found first ran under same depth
                    ord_ -= 1
                else:
                    if type_ == _Sane.Node.RECIPE:
                        self.log(f'Skipping recipe \'{name}\'.',
                                 _Sane.VerboseLevel.VERBOSE)

                # Do not reduce depth for hooks and others
                if type_ == _Sane.Node.RECIPE:
                    depth -= 1

                continue

            child_unique_name = node.connections[child_idx]
            child_type, child_name = _Sane.split_unique_name(child_unique_name)
            if child_type == _Sane.Node.RECIPE:
                child_exists = self.recipe_exists(child_name)
            elif child_type == _Sane.Node.HOOK:
                child_exists = self.hook_exists(child_name)
            else:
                raise ValueError(f'Unknown child type \'{child_type}\'.')

            if not child_exists:
                _, name = _Sane.split_unique_name(unique_name)
                backtrack_names.append(child_unique_name)
                traceback = ' > '.join(
                    _Sane.human_format_unique_name(x) for x in backtrack_names)
                self.report_unknown(child_name, name, traceback)

            # When we return to this point in the stack, explore the next child
            backtrack_child_idx.append(child_idx + 1)

            # Check if child has been visited before (at specified depth)
            child_depth = (depth + 1 if child_type ==
                           _Sane.Node.RECIPE else depth)
            element = (child_depth, child_unique_name)
            i = bisect.bisect_left(visited, element)
            child_visited = (i < len(visited) and visited[i] == element)

            if child_visited:
                # The child subtree has been explored before
                # (presumably as a subtree of a different parent).
                i = bisect.bisect_left(active, element)
                child_active = (i < len(active) and active[i] == element)
                backtrack_active.append(child_active)
            else:
                # Explore the child's subtree.
                depth = child_depth
                backtrack_child_idx.append(0)
                backtrack_names.append(child_unique_name)

                child_node = self.graph[child_unique_name]
                child_active = (child_node.is_always_active() or force)
                backtrack_active.extend((child_active, False))

        # Sort the active recipes by depth, and then by order in which they were
        # encountered.
        sort_key = sorted(range(len(active_ordering)),
                          key=active_ordering.__getitem__)
        active_in_order = map(lambda i: active[i], reversed(sort_key))

        self.log('Finished building and sorting dependency tree of '
                 f'\'{root_name}\'.\n'
                 'Launching recipes.',
                 _Sane.VerboseLevel.VERY_VERBOSE)

        # Finally, run the recipes in order
        # Note that some of the elements in `active` will be hooks.
        for _depth, unique_name in active_in_order:
            type_, name = _Sane.split_unique_name(unique_name)
            if type_ != _Sane.Node.RECIPE:
                continue
            self.log(f'Running recipe \'{name}\'.', _Sane.VerboseLevel.VERBOSE)
            fn = self.graph[unique_name].meta['fn']
            fn()


_stateful = _Sane()

### Optionally Expose Logging Tools ###
# For consistency, this class is never to be inside this file,
# and logging should be done via `_stateful`.


class _Logging:
    def log(message): return _stateful.log(message)
    def warn(message): return _stateful.warn(message)
    def error(message): return _stateful.error(message)

### Recipe Tag ###


def recipe(*args, name=None, hooks=[], recipe_deps=[],
           hook_deps=[], conditions=[], info=None, **kwargs):
    frame = inspect.stack(context=3)[-1]
    # `frame` is disposed of once used

    def recipe_fn(fn):
        _stateful.register_decorator_call(*args, frame=frame, name=name,
                                          hooks=hooks, recipe_deps=recipe_deps,
                                          hook_deps=hook_deps,
                                          conditions=conditions,
                                          info=info, fn=fn, **kwargs)
        return fn
    return recipe_fn


### Conditions ###

def sane_file_condition(file_deps, target_files):
    frame = inspect.stack(context=3)[-1]
    if type(file_deps) not in (tuple, list):
        _stateful.error('`file_deps` is expected to be tuple or list, '
                        f'got {type(file_deps)} instead.\n'
                        f'At {_Sane.trace(frame)}')
    if type(target_files) not in (tuple, list):
        _stateful.error('`target_files` is expected to be tuple or list, '
                        f'got {type(target_files)} instead.\n'
                        f'At {_Sane.trace(frame)}')
    if len(file_deps) == 0:
        _stateful.error('File condition without `file_deps` is ambiguous.\n'
                        'Consider writing an explicit condition.\n'
                        f'At {_Sane.trace(frame)}')
    if len(target_files) == 0:
        _stateful.error('File condition without `target_files` is ambiguous.\n'
                        'Consider writing an explicit condition.\n'
                        f'At {_Sane.trace(frame)}')
    del frame

    file_deps = [
        os.path.abspath(os.path.expanduser(path)) for path in file_deps]
    target_files = [
        os.path.abspath(os.path.expanduser(path)) for path in target_files]

    def condition():
        # The oldest file in `target_files` cannot be older than newest file
        # in `file_deps`.
        oldest = None
        for target_file in target_files:
            # If a target file does not exist, assume it should be created
            if not os.path.exists(target_file):
                return True
            # Otherwise check the time
            epoch = os.stat(target_file).st_mtime
            if oldest is None or epoch < oldest:
                oldest = epoch
        newest = None
        for file_dep in file_deps:
            # Ignore dependencies that do not exist
            if not os.path.exists(file_dep):
                _stateful.warn(f'File dependency \'{file_dep}\' does not exist '
                               'and will be ignored.')
                continue
            epoch = os.stat(file_dep).st_mtime
            if newest is None or epoch > newest:
                newest = epoch

        return (oldest < newest)
    return condition


### Run Routine ###


def sane_run(default=None):
    parser = argparse.ArgumentParser(description='Make, but Sane')
    parser.add_argument('--version', action='version',
                        version=f'Sane {_Sane.VERSION}')
    parser.add_argument('--verbose', metavar='level', type=int, default=0,
                        help='Level of verbosity in logs. '
                        f'{_Sane.VerboseLevel.NONE} is not verbose, '
                        f'{_Sane.VerboseLevel.VERY_VERBOSE} is most verbose.')
    parser.add_argument('recipe', nargs='?', default=None,
                        help='The recipe to run. If none is given, the default recipe is ran.')
    parser.add_argument('--force', action='store_true',
                        help='Always run the recipe and all of its dependencies '
                        '(regardless of whether dependant recipes were ran or '
                        'conditions are True).')
    parser.add_argument('--list', action='store_true', default=False,
                        help='List the defined recipes.')
    parser.add_argument('--no-ansi', action='store_true', default=False,
                        help='Disable ANSI color characters in logging.')

    args = parser.parse_args()

    _stateful.set_verbose(args.verbose)
    _stateful.set_ansi(not args.no_ansi)

    _stateful.log('Parsing registered `@recipe` decorations.',
                  _Sane.VerboseLevel.VERY_VERBOSE)
    _stateful.parse_decorator_calls()

    if args.list:
        _stateful.list_recipes()
        exit(0)

    recipe = args.recipe

    if recipe is None:
        if default is None:
            _stateful.error('No recipe given and no default recipe, exiting.')
        else:
            if type(default) is not str:
                if not hasattr(default, '__name__'):
                    _stateful.error(
                            'Given default recipe not a string, and '
                            'the given object has no `__name__` attribute.\n'
                            f'Default recipe given is \'{default}\'.')

                if not _stateful.recipe_exists(default.__name__):
                    _stateful.error(
                            'Given default recipe not a string, and '
                            f'inferred name \'{default.__name__}\' is not '
                            'defined as a recipe.')

                recipe = default.__name__
            else:
                if not _stateful.recipe_exists(default):
                    _stateful.error('No recipe given, and default recipe '
                                    f'\'{default}\' is not defined as a recipe.')
                recipe = default
    else:
        if not _stateful.recipe_exists(recipe):
            _stateful.error(
                f'Given recipe \'{recipe}\' is not defined as a recipe.')

    _stateful.log(
        f'Launching graph of recipe \'{recipe}\'.',
        _Sane.VerboseLevel.VERY_VERBOSE)
    _stateful.run_recipe_graph(recipe, args.force)


if __name__ == '__main__':
    _stateful.log(f'Sane v{_Sane.VERSION}, by Miguel Murça.\n'
                  'Sane should be imported from other files, '
                  'not ran directly.\n'
                  'Refer to the README for more information.')
