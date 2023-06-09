
'''Sane, Makefile for humans.

Copyright 2023 Miguel Murça

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the 'Software'), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import os
import sys
import re
import inspect
import atexit
import builtins
from typing import Literal
from collections import namedtuple


class _Sane:

    VERSION = '7.0'
    ANSI = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    Context = namedtuple(
        'Context', ('filename', 'lineno', 'code_context', 'index'))
    Depends = namedtuple('Depends', ('value', 'context'))
    Default = namedtuple('Default', ('func', 'context'))

    singleton = None

    @staticmethod
    def strip_ansi(text):
        return _Sane.ANSI.sub('', text)

    @staticmethod
    def get_context():
        stack = inspect.stack(context=4)
        for element in stack:
            if element.frame.f_globals['__name__'] != __name__:
                context = _Sane.Context(
                    element.filename, element.lineno, element.code_context, element.index)
                stack.clear()
                return context

    @staticmethod
    def get():
        if _Sane.singleton is None:
            _Sane.singleton = _Sane()
        return _Sane.singleton

    def __init__(self):
        if _Sane.singleton is not None:
            raise Exception()
        self.initialize_properties()
        self.setup_logging()
        self.read_arguments()
        self.run_on_exit()

    def initialize_properties(self):
        self.run_main = True
        self.default = None
        self.cmds = {}
        self.tasks = {}
        self.quid = {}
        self.graph = None
        self.graph_map = None
        self.args_edges = None
        self.ignore_when = False
        self.operation = {}

    def setup_logging(self):
        self.verbose = False
        if os.environ.get('NO_COLOR', False) or not sys.stdout.isatty():
            self.color = False
        else:
            self.color = True

    def read_arguments(self):
        args = sys.argv[1:]
        if '--' in args:
            cmd_arg_limit = args.index('--')
            if cmd_arg_limit == len(args):
                self.usage_error()
            sane_args = set(args[:cmd_arg_limit])
            cmd_args = tuple(args[cmd_arg_limit + 1:])
        else:
            sane_args = set(args)
            cmd_args = None

        if '--help' in sane_args or '-h' in sane_args:
            print(self.get_long_usage())
            self.run_main = False
            sys.exit(0)

        if '--verbose' in sane_args:
            sane_args.remove('--verbose')
            self.verbose = True
        if '--no-color' in sane_args and '--color' in sane_args:
            print(self.get_short_usage(), file=sys.stderr)
            sys.exit(1)
        if '--no-color' in sane_args:
            sane_args.remove('--no-color')
            self.color = False
        if '--color' in sane_args:
            sane_args.remove('--color')
            self.color = True
        if '--ignore-when' in sane_args:
            sane_args.remove('--ignore-when')
            self.ignore_when = True

        if len(sane_args) != 1:
            self.usage_error()

        if '--list' in sane_args:
            if cmd_args is not None:
                self.usage_error()
            self.operation = {'mode': 'list'}
        else:
            cmd = sane_args.pop()
            if cmd.startswith('-'):
                self.usage_error()

            self.operation = {
                'mode': 'cmd',
                'cmd': cmd,
                'args': cmd_args,
            }

    def usage_error(self):
        print(self.get_short_usage(), file=sys.stderr)
        sys.exit(1)


    def get_short_usage(self):
        main = self.get_main_name()
        return (f'Usage: {main} --version\n'
                f'       {main} [--no-color | --color] --list\n'
                f'       {main} [--no-color | --color] [--verbose] [--ignore-when] [cmd [-- ...args]]')

    def get_long_usage(self):
        return ('Sane, Make for humans.\n'
                f'{self.get_short_usage()}\n\n'
                'Options:\n'
                '  --version      Print the current sane version.\n'
                '  --verbose      Show verbose logs.\n'
                '  --color        Enables ANSI color codes even in non-console terminals.\n'
                '  --no-color     Disable ANSI color codes in the output.\n'
                '  --ignore-when  Ignore @when attributes when running @tasks and @cmds.\n'
                '\n'
                'Arguments given after \'--\' are passed to the provided @cmd.\n'
                'If no command is given, the @default @cmd is ran, if it exists.')

    def get_main_name(self):
        main = sys.modules['__main__']
        if hasattr(main, '__file__'):
            return os.path.basename(main.__file__)
        else:
            return 'script'

    def run_on_exit(self):
        self.exit_code = 0

        _sys_excepthook = sys.excepthook

        def save_and_except(type, value, traceback):
            self.exit_code = 1
            if _sys_excepthook:
                _sys_excepthook(type, value, traceback)
        sys.excepthook = save_and_except

        def save_and_exit(wraps):
            def _exit(code=0):
                self.exit_code = code
                return wraps(code)
            return _exit
        _sys_exit = sys.exit
        _builtins_exit = builtins.exit
        sys.exit = save_and_exit(_sys_exit)
        builtins.exit = save_and_exit(_builtins_exit)
        atexit.register(self.main)

    def cmd_decorator(self, *args, **kwargs):
        context = _Sane.get_context()

        if len(args) > 1 or len(kwargs) > 0:
            self.error('@cmd does not take arguments.')
            self.show_context(context, 'error')
            self.hint('(To specify other properties, use @quid or @depends.)')
            sys.exit(1)
        elif len(args) == 0:
            self.error('@cmd does not have parentheses.')
            self.show_context(context, 'error')
            self.hint('(Remove the parentheses.)')
            sys.exit(1)

        func = args[0]
        if not hasattr(func, '__call__'):
            self.error('@cmd must decorate a function.')
            self.show_context(context, 'error')
            sys.exit(1)

        self.ensure_positional_args_only(context, func)
        
        if not hasattr(func, '__name__'):
            self.error('A @cmd must have a name.')
            self.show_context(context, 'error')
            self.hint('(Use a @task instead.)')
            sys.exit(1)
        
        if func.__name__ in self.cmds:
            other_, other_context = self.cmds[func.__name__]
            self.error('@cmd names must be unique.')
            self.show_context(context, 'error')
            self.show_context(other_context, 'hint')
            self.hint('(Use a @task instead.)')
            sys.exit(1)

        props = self.get_props(func)
        if self.is_task_or_cmd(func):
            self.error('More than one @cmd or @task.')
            self.show_context(context, 'error')
            self.hint(
                '(A function can only have a single @cmd or @task decorator.)')
            sys.exit(1)
        props['type'] = 'cmd'
        props['context'] = context

        def cmd(*args, **kwargs):
            # TODO: Run the tree, not just the function.
            return func(*args, **kwargs)

        cmd.__dict__['__sane__'] = {'type': 'wrapper', 'inner': func}
        self.cmds[func.__name__] = func
        return cmd

    def task_decorator(self, *args, **kwargs):
        context = _Sane.get_context()

        if len(args) > 1 or len(kwargs) > 0:
            self.error('@task does not take arguments.')
            self.show_context(context, 'error')
            self.hint('(To specify other properties, use @quid or @depends.)')
            sys.exit(1)
        elif len(args) == 0:
            self.error('@task does not have parentheses.')
            self.show_context(context, 'error')
            self.hint('(Remove the parentheses.)')
            sys.exit(1)

        func = args[0]
        if not hasattr(func, '__call__'):
            self.error('@task must decorate a function.')
            self.show_context(context, 'error')
            sys.exit(1)

        self.ensure_no_args(context, func)

        props = self.get_props(func)
        if self.is_task_or_cmd(func):
            self.error('More than one @cmd or @task.')
            self.show_context(context, 'error')
            self.hint(
                '(A function can only have a single @cmd or @task decorator.)')
            sys.exit(1)
        props['type'] = 'task'
        props['context'] = context

        def task():
            # TODO: Run the tree, not just the function
            return func()

        task.__dict__['__sane__'] = {'type': 'wrapper', 'inner': func}
        self.tasks.setdefault(func.__name__, []).append(func)
        return task

    def depends_decorator(self, *pargs, **args):
        context = _Sane.get_context()

        if len(pargs) > 0:
            self.error('@depends takes keyword arguments only.')
            self.show_context(context, 'error')
            self.hint('(Use on_quid=, on_cmd=, or on_task=.)')

        given = list(arg for arg in ('on_quid', 'on_cmd',
                     'on_task') if arg in args.keys())
        if len(given) != 1:
            self.error(
                '@depends must take a single on_quid=, on_cmd=, or on_task=.')
            self.show_context(context, 'error')
            self.hint('(If you wish to have multiple dependencies, '
                      'use multiple @depends decorators.)')
            sys.exit(1)
        given = given[0]

        def specific_decorator(func):
            if self.is_task_or_cmd(func):
                self.error('@depends cannot come before @cmd or @task.')
                self.show_context(context, 'error')
                sys.exit(1)

            if given == 'on_quid':
                return self.depends_on_quid(context, func, **args)
            elif given == 'on_cmd':
                return self.depends_on_cmd(context, func, **args)
            else:
                return self.depends_on_task(context, func, **args)

        return specific_decorator

    def depends_on_quid(self, context, func, **args):
        if len(args) != 1:
            self.error('@depends(on_quid=...) does not take other arguments.')
            self.show_context(context)
            sys.exit(1)

        quid = []
        arg = args['on_quid']
        if type(arg) is str:
            quid.append(_Sane.Depends(arg, context))
        elif hasattr(arg, '__iter__'):
            if type(arg) not in (tuple, list, set):
                self.warn('on_quid= argument is not a collection, although it is iterable. '
                          'The elements in this iterator will still be considered, '
                          'but exhaustion of the iterator may produce unexpected results.')
                self.show_context(context, 'warn')
                self.hint(
                    '(To silence this warning, convert the argument to a collection type.)')

            for element in arg:
                if type(element) is str:
                    quid.append(_Sane.Depends(element, context))
                else:
                    self.error('on_quid= argument must be iterable of string.')
                    self.show_context(context, 'error')
                    sys.exit(1)
        else:
            self.error(
                'on_quid= argument must be string or iterable of string.')
            self.show_context(context, 'error')
            sys.exit(1)

        props = self.get_props(func)
        props['depends']['quid'].extend(quid)

        return func

    def depends_on_cmd(self, context, func, **args):
        malformed_args = (
            len(args) != 2 or
            set(args.keys()) != set(('on_cmd', 'args')))

        if malformed_args:
            self.error(
                '@depends(on_cmd=..., args=...) takes exactly these two arguments.')
            self.show_context(context, 'error')
            self.hint('(Did you mean @depends(on_task=...)?)')
            sys.exit(1)

        cmd = args['on_cmd']
        if type(cmd) is not str:
            if hasattr(cmd, '__call__'):
                if not hasattr(cmd, '__sane__'):
                    self.error('Given function is not a @cmd.')
                    self.show_context(context, 'error')
                    self.hint('(Is the referenced function missing a @cmd?)')
                    sys.exit(1)
                elif cmd.__sane__.get('type', None) != 'wrapper':
                    self.error('Given function is not decorated with @cmd.')
                    self.show_context(context, 'error')
                    self.hint('(Add a @cmd before the other decorators.)')
                    sys.exit(1)
                cmd = cmd.__sane__['inner']
                if cmd.__sane__['type'] != 'cmd':
                    self.error('Given function is not a @cmd.')
                    self.show_context(context, 'error')
                    self.hint('(Did you mean @depends(on_task=...)?)')
                    sys.exit(1)
            else:
                self.error(
                    'on_cmd= argument must be a cmd, or the name of a cmd.')
                self.show_context(context, 'error')
                sys.exit(1)

        props = self.get_props(func)
        props['depends']['cmd'].append(
            _Sane.Depends((cmd, args['args']), context))

        # Resolution of `cmd` and validation of `args` happens at graph build stage.

        return func

    def depends_on_task(self, context, func, **args):
        if len(args) != 1:
            if len(args) == 2 and 'args' in args:
                self.error('@depends(on_task=...) takes no args= parameter.')
                self.show_context(context, 'error')
                self.hint('(Did you mean @depends(on_cmd=..., args=...)?)')
                sys.exit(1)
            else:
                self.error('@depends(on_task=...) takes no other parameters.')
                self.show_context(context, 'error')
                sys.exit(1)

        task = args['on_task']
        if type(task) is not str:
            if hasattr(task, '__call__'):
                if not hasattr(task, '__sane__'):
                    self.error('Given function is not a @task.')
                    self.show_context(context, 'error')
                    self.hint('(Is the referenced function missing a @task?)')
                    sys.exit(1)
                elif task.__sane__.get('type', None) != 'wrapper':
                    self.error('Given function is not decorated with @task.')
                    self.show_context(context, 'error')
                    self.hint('(Add a @task before the other decorators.)')
                    sys.exit(1)
                task = task.__sane__['inner']
                if task.__sane__['type'] != 'task':
                    self.error('Given function is not a @task.')
                    self.show_context(context, 'error')
                    self.hint('(Did you mean @depends(on_cmd=...)?)')
                    sys.exit(1)
            else:
                self.error(
                    'on_task= argument must be a task, or the name of a task.')
                self.show_context(context, 'error')
                sys.exit(1)

        props = self.get_props(func)
        props['depends']['task'].append(_Sane.Depends(task, context))

        # Resolution of task happens at graph build stage.

        return func

    def quid_decorator(self, *args, **kwargs):
        context = _Sane.get_context()

        invalid_args = (len(kwargs) > 0 or
                        len(args) > 1)
        if invalid_args:
            self.error('@quid takes a single positional argument.')
            self.show_context(context, 'error')
            self.hint('(For example, @quid(\'quo\').)')
            sys.exit(1)

        quid = args[0]
        if type(quid) is not str:
            self.error('@quid must be a string.')
            self.show_context(context, 'error')
            self.hint('(For example, @quid(\'quo\').)')
            sys.exit(1)

        def specific_decorator(func):
            if self.is_task_or_cmd(func):
                self.error('@quid cannot come before @cmd or @task.')
                self.show_context(context, 'error')
                sys.exit(1)
            props = self.get_props(func)
            self.quid.setdefault(quid, []).append(func)
            return func

        return specific_decorator

    def when_decorator(self, *args, **kwargs):
        context = _Sane.get_context()

        if len(kwargs) > 0 or len(args) != 1:
            self.error('@when takes a single function, with no arguments.')
            self.show_context(context, 'error')
            sys.exit(1)

        condition = args[0]

        if not hasattr(condition, '__call__'):
            self.error('Argument is not a function.')
            self.show_context(context, 'error')
            self.hint('(Use @when(fn), not @when(fn()).)')
            sys.exit(1)

        def specific_decorator(func):
            if self.is_task_or_cmd(func):
                self.error('@when cannot come before @cmd or @task.')
                self.show_context(context, 'error')
                sys.exit(1)
            props = self.get_props(func)
            if props['when'] is not None:
                self.error(
                    'To avoid ambiguity, a @cmd or @task can only have one @when.')
                self.show_context(context, 'error')
                self.hint(
                    '(To define a conjunction, you can use @when(lambda: a() or b() or c()).)')
                sys.exit(1)
            props['when'] = condition
            return func
        return specific_decorator

    def default_decorator(self, *args, **kwargs):
        if len(args) > 1 or len(kwargs) > 0:
            self.error('@default does not take arguments.')
            self.show_context(context, 'error')
            self.hint('(To specify other properties, use @quid or @depends.)')
            sys.exit(1)
        elif len(args) == 0:
            self.error('@default does not have parentheses.')
            self.show_context(context, 'error')
            self.hint('(Remove the parentheses.)')
            sys.exit(1)

        context = _Sane.get_context()

        if self.default is not None:
            self.error('More than one @default.')
            self.show_context(context, 'error')
            self.hint('(Other @default found here:)')
            self.show_context(self.default.context, 'hint')
            sys.exit(1)

        func = args[0]

        if not hasattr(func, '__sane__'):
            self.error('@default must come before @cmd.')
            self.show_context(context, 'error')
            self.hint('(Add a @cmd decorator to this function, '
                      'or move @default to come before @cmd.)')
            sys.exit(1)

        type_ = func.__sane__['type']
        if type_ == 'cmd':
            self.error('@default must come before @cmd.')
            self.show_context(context, 'error')
            self.hint('(Move @default to be the first decorator.)')
            sys.exit(1)
        else:
            if type_ == 'wrapper':
                type_ = func.__sane__['inner'].__sane__['type']
            if type_ == 'task':
                self.error('@default cannot be used with @task.')
                self.show_context(context, 'error')
                self.hint('(Use a @cmd instead.)')
                sys.exit(1)
            elif type_ != 'cmd':
                raise ValueError(type_)

        self.default = _Sane.Default(func.__sane__['inner'], context)
        return func

    def main(self):
        if self.exit_code or not self.run_main:
            return
        self.run_main = False

        try:
            op_mode = self.operation['mode']
            if op_mode == 'list':
                self.list_cmds()
            elif op_mode == 'cmd':
                cmd = self.operation['cmd']
                args = self.operation['args']
                self.build_graph(root)
                # TODO
            else:
                raise ValueError(op_mode)
        except SystemExit as sys_exit:
            # TODO: Change exit code and exit cleanly.
            # This is currently apparently not possible.
            # See https://github.com/python/cpython/issues/103512
            # os._exit ignores other handlers and does not flush buffers.
            os._exit(sys_exit.code)
    
    def launch_cmd_tree(self, cmd):
        pass
    
    def list_cmds(self):
        for cmd_name, cmd in self.cmds.items():
            self.color_print(f'\x1b[1m{cmd_name}\x1b[0m', end='')
            
            if self.verbose:
                cmd_args = inspect.signature(cmd).parameters.keys()
                if len(cmd_args) > 0:
                    comma_sep_args = ', '.join(cmd_args)
                    self.color_print(f'\x1b[2m({comma_sep_args})\x1b[0m')
                else:
                    self.color_print('\n  \x1b[2m(No arguments.)\x1b[0m')

                if hasattr(cmd, '__doc__') and cmd.__doc__:
                    doc = cmd.__doc__
                    for line in doc.splitlines():
                        self.color_print(f'\x1b[2m  {line}\x1b[0m')
                else:
                    self.color_print('  \x1b[2mNo information given.\x1b[0m')
            else:
                self.color_print('\n', end='')

    def build_graph(self, root):
        graph = []
        graph_map = {}
        args_edges = {}
        stack = []

        stack.append(('visit', root))

        while len(stack) > 0:
            op, node = stack.pop()
            type_ = node.__sane__['type']
            state = node.__sane__.setdefault('graph', 'unmarked')
            if op == 'seal':
                node.__sane__['graph'] = 'permanent'
                graph.append(node)
                graph_map[node] = len(graph) - 1
            elif op == 'visit':
                if state == 'permanent':
                    continue
                if state == 'temporary':
                    self.report_loop(stack)

                self.resolve_depends(node)
                depends = node.__sane__['depends']
                node.__sane__['graph'] = 'temporary'

                stack.append(('seal', node))
                for quid in depends['quid']:
                    quid, context = quid
                    for element in self.quid.setdefault(quid, []):
                        stack.append(('visit', element))
                for cmd in depends['cmd']:
                    cmd_args, _context = cmd
                    cmd, args = cmd_args
                    args_edges[(node, cmd)] = cmd_args
                    stack.append(('visit', cmd))
                for task in depends['task']:
                    task, _context = task
                    stack.append(('visit', task))
            else:
                raise ValueError()

        self.graph = graph
        self.graph_map = graph_map
        self.args_edges = args_edges

    def resolve_depends(self, func):
        props = self.get_props(func)
        for i in range(len(props['depends']['task'])):
            task_depends, context = props['depends']['task'][i]
            if type(task_depends) is str:
                if task_depends not in self.tasks:
                    self.error(f'No @task named {task_depends}.')
                    self.show_context(context, 'error')
                    self.hint(
                        '(You can reference a function directly, instead of a string.)')
                    self.hint(
                        '(Are you missing a @task somewhere?)')
                    sys.exit(1)
                elif len(self.tasks[task_depends]) > 1:
                    self.error(
                        f'There\'s more than one @task named {task_depends}.')
                    self.show_context(context, 'error')
                    self.hint(
                        '(You can reference a function directly, instead of a string.)')
                    self.hint(
                        '(Alternatively, use @quid, and @depends(on_quid=...).)')
                    sys.exit(1)
                resolved = self.tasks[task_depends][0]
                props['depends']['task'][i] = (resolved, context)

        for i in range(len(props['depends']['cmd'])):
            value, context = props['depends']['cmd'][i]
            cmd_depends, cmd_args = value
            if type(cmd_depends) is str:
                if cmd_depends not in self.cmds:
                    self.error(f'No @cmd named {cmd_depends}.')
                    self.show_context(context, 'error')
                    self.hint(
                        '(You can reference a function directly, instead of a string.)')
                    self.hint(
                        '(Are you missing a @cmd somewhere?)')
                    sys.exit(1)

                resolved = self.cmds[cmd_depends]

                signature = inspect.signature(resolved)
                mandatory_arg_count = 0
                optional_arg_count = 0
                for arg in signature.parameters.values():
                    if arg.default is inspect.Parameter.empty:
                        mandatory_arg_count += 1
                    else:
                        optional_arg_count += 1
                wrong_number_of_args = (len(cmd_args) < mandatory_arg_count or
                                        len(cmd_args) > mandatory_arg_count + optional_arg_count)
                if wrong_number_of_args:
                    self.error(
                        'Arguments given in @depends are incompatible with the function signature.')
                    self.show_context(context, 'error')
                    sys.exit(1)

                props['depends']['cmd'][i] = ((resolved, cmd_args), context)

    def report_loop(self, stack):
        lines = ['Dependency loop.\n']
        for element in reversed(stack):
            op_, node = element
            name = node.__name__
            context = node.__sane__['context']
            lines.append(f'* {name}\n')
            for line in self.format_context(context).splitlines():
                lines.append('| ' + line + '\n')
            lines.append('|\n')

        loop_op_, loop_node = stack[-1]
        loop_name = loop_node.__name__
        loop_context = node.__sane__['context']
        lines.append(f'* {loop_name}')

        self.error(''.join(lines))
        sys.exit(1)

    def is_task_or_cmd(self, func):
        props = self.get_props(func)
        return props['type'] is not None

    def ensure_no_args(self, context: Context, func):
        signature = inspect.signature(func)
        if len(signature.parameters.values()) > 0:
            self.error('@task cannot have arguments.')
            self.show_context(context, 'error')
            self.hint('(Use a @cmd instead.)')
            sys.exit(1)

    def ensure_positional_args_only(self, context: Context, func):
        signature = inspect.signature(func)
        any_non_positional = any(
            arg.kind not in (inspect.Parameter.POSITIONAL_ONLY,
                             inspect.Parameter.POSITIONAL_OR_KEYWORD)
            for arg in signature.parameters.values())
        if any_non_positional:
            self.error('@cmd cannot have non-positional arguments.')
            self.show_context(context, 'error')
            sys.exit(1)

    def get_props(self, func):
        if '__sane__' not in func.__dict__:
            func.__dict__['__sane__'] = {
                'type': None,
                'context': None,
                'when': None,
                'depends': {
                    'resolved': False,
                    'quid': [],
                    'cmd': [],
                    'task': [],
                }
            }

        return func.__dict__['__sane__']

    def color_print(self, *args, **kwargs):
        if self.color:
            print(*args, **kwargs)
        else:
            print(*map(_Sane.strip_ansi, args), **kwargs)

    def log(self, message):
        header = '\x1b[2m[log]\x1b[0m'
        if not self.color:
            header = _Sane.strip_ansi(header)
        print(header, message, file=sys.stderr)

    def warn(self, message):
        header = '\x1b[33m[warn]\x1b[0m'
        if not self.color:
            header = _Sane.strip_ansi(header)
        print(header, message, file=sys.stderr)

    def error(self, message):
        if self.color:
            message = '\x1b[35m[error] ' + message + '\x1b[0m'
        print(message, file=sys.stderr)

    def hint(self, message):
        if self.color:
            message = '\x1b[2m' + message + '\x1b[0m'
        print(message, file=sys.stderr)

    def format_context(self, context: Context):
        line_ctx = f'\n{context.filename}: l.{context.lineno}'
        info = []
        if context.index < context.lineno:
            info.append('...\n')
        for i, code_line in enumerate(context.code_context):
            if i == context.index:
                info_line = '>  ' + code_line
            else:
                info_line = '   ' + code_line
            info.append(info_line)
        info = ''.join(info)
        return f'{line_ctx}\n{info}'

    def show_context(self, context: Context, style: Literal['log', 'warn', 'error', 'debug']):
        info = self.format_context(context)
        if self.color:
            if style == 'log':
                print(f'\x1b[2m{info}\x1b[0m', file=sys.stderr)
            elif style == 'warn':
                print(f'\x1b[33m{info}\x1b[0m', file=sys.stderr)
            elif style == 'error':
                print(f'\x1b[35m{info}\x1b[0m', file=sys.stderr)
            elif style == 'hint':
                print(f'\x1b[2m{info}\x1b[0m', file=sys.stderr)
            else:
                raise ValueError(
                    f'Expected \'{style}\' to be one of log, warn, error, hint.')
        else:
            print(info, file=sys.stderr)


_sane = _Sane.get()
cmd = _sane.cmd_decorator
task = _sane.task_decorator
depends = _sane.depends_decorator
quid = _sane.quid_decorator
when = _sane.when_decorator
default = _sane.default_decorator

if __name__ == '__main__':
    _stateful.log(f'Sane v{_Sane.VERSION}, by Miguel Murça.\n'
                  'Sane should be imported from other files, '
                  'not ran directly.\n'
                  'Refer to the [Github page] for more information.\n'
                  'https://github.com/mikeevmm/sane')
