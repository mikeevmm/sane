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
import builtins
import atexit
import concurrent.futures
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
        self.check_on_exit()

    def initialize_properties(self):
        self.finalized = False
        self.default = None
        self.cmds = {}
        self.tasks = {}
        self.tags = {}
        self.ignore_when = False
        self.operation = {}
        self.incidence = {}
        self.jobs = 1

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
            sane_args = list(args[:cmd_arg_limit])
            cmd_args = tuple(args[cmd_arg_limit + 1:])
        else:
            sane_args = list(args)
            cmd_args = None

        if '--help' in sane_args or '-h' in sane_args:
            print(self.get_long_usage())
            self.run_main = False
            sys.exit(0)

        if '--no-color' in sane_args and '--color' in sane_args:
            self.usage_error()
            sys.exit(1)

        if '--verbose' in sane_args:
            sane_args.remove('--verbose')
            self.verbose = True
        if '--no-color' in sane_args:
            sane_args.remove('--no-color')
            self.color = False
        if '--color' in sane_args:
            sane_args.remove('--color')
            self.color = True
        if '--ignore-when' in sane_args:
            sane_args.remove('--ignore-when')
            self.ignore_when = True

        if '--list' in sane_args:
            if cmd_args is not None or len(sane_args) != 1:
                self.usage_error()
            self.operation = {'mode': 'list'}
        else:
            jobs = self.get_keyword_value(sane_args, '--jobs')
            if jobs is not None:
                try:
                    self.jobs = int(jobs)
                    if self.jobs == 0:
                        self.jobs = None
                except ValueError:
                    self.error('--jobs must be a number.')
                    self.usage_error()

            if len(sane_args) > 0:
                if len(sane_args) != 1:
                    self.usage_error()
                cmd = sane_args.pop()
                if cmd.startswith('-'):
                    self.usage_error()
            else:
                cmd = None

            if cmd_args is None:
                cmd_args = ()

            self.operation = {
                'mode': 'cmd',
                'cmd': cmd,
                'args': cmd_args,
            }

    def get_keyword_value(self, args, name):
        for i in range(len(args)):
            arg = args[i]
            if arg.startswith(name):
                remaining = arg.removeprefix(name)
                if remaining.startswith('='):
                    args.remove(arg)
                    return remaining.removeprefix('=')
                elif len(remaining) == 0:
                    if i < len(args) - 1:
                        value = args[i+1]
                        args.remove(arg)
                        args.remove(value)
                        return value

    def usage_error(self):
        print(self.get_short_usage(), file=sys.stderr)
        sys.exit(1)

    def get_short_usage(self):
        main = self.get_main_name()
        return (f'Usage: {main} --version\n'
                f'       {main} [--no-color | --color] --list\n'
                f'       {main} [--no-color | --color] [--verbose] [--ignore-when] [--jobs=<n>] [cmd] [-- ...args]')

    def get_long_usage(self):
        return ('Sane, Make for humans.\n'
                f'{self.get_short_usage()}\n\n'
                'Options:\n'
                '  --version      Print the current sane version.\n'
                '  --verbose      Show verbose logs.\n'
                '  --color        Enables ANSI color codes even in non-console terminals.\n'
                '  --no-color     Disable ANSI color codes in the output.\n'
                '  --ignore-when  Ignore @when attributes when running @tasks and @cmds.\n'
                '  --jobs         Maximum number of tasks to perform concurrently.\n'
                '\n'
                'Arguments given after \'--\' are passed to the provided @cmd.\n'
                'If no command is given, the @default @cmd is ran, if it exists.')

    def get_main_name(self):
        main = sys.modules['__main__']
        if hasattr(main, '__file__'):
            return os.path.basename(main.__file__)
        else:
            return 'script'

    def check_on_exit(self):
        def check_if_finalized():
            if not self.finalized:
                self.warn('Sane was never ran!')
                self.hint('(Are you missing a sane() call?)')
        atexit.register(check_if_finalized)

    def cmd_decorator(self, *args, **kwargs):
        context = _Sane.get_context()

        if self.finalized:
            self.error('@cmd cannot appear after sane().')
            self.show_context(context)
            self.hint('(Move sane() to the end of the file.)')

        if len(args) > 1 or len(kwargs) > 0:
            self.error('@cmd does not take arguments.')
            self.show_context(context, 'error')
            self.hint('(To specify other properties, use @tag or @depends.)')
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
            if not self.finalized:
                context = _Sane.get_context()
                self.warn('Calling a @cmd from outside other @cmds or @tasks '
                          'ignores @depends and @when.')
                self.show_context(context, 'warn')
                return func(*args)
            else:
                return self.run_tree(func, args)

        cmd.__dict__['__sane__'] = {'type': 'wrapper', 'inner': func}
        self.cmds[func.__name__] = func
        return cmd

    def task_decorator(self, *args, **kwargs):
        context = _Sane.get_context()

        if self.finalized:
            self.error('@task cannot appear after sane().')
            self.show_context(context)
            self.hint('(Move sane() to the end of the file.)')

        if len(args) > 1 or len(kwargs) > 0:
            self.error('@task does not take arguments.')
            self.show_context(context, 'error')
            self.hint('(To specify other properties, use @tag or @depends.)')
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
            if not self.finalized:
                context = _Sane.get_context()
                self.warn('Calling a @task from outside other @cmds or @tasks '
                          'ignores @depends and @when.')
                self.show_context(context, 'warn')
                return func()
            else:
                return self.run_tree(func, ())

        task.__dict__['__sane__'] = {'type': 'wrapper', 'inner': func}
        self.tasks.setdefault(func.__name__, []).append(func)
        return task

    def depends_decorator(self, *pargs, **args):
        context = _Sane.get_context()

        if len(pargs) > 0:
            self.error('@depends takes keyword arguments only.')
            self.show_context(context, 'error')
            self.hint('(Use on_tag=, on_cmd=, or on_task=.)')

        given = list(arg for arg in ('on_tag', 'on_cmd',
                     'on_task') if arg in args.keys())
        if len(given) != 1:
            self.error(
                '@depends must take a single on_tag=, on_cmd=, or on_task=.')
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

            if given == 'on_tag':
                return self.depends_on_tag(context, func, **args)
            elif given == 'on_cmd':
                return self.depends_on_cmd(context, func, **args)
            else:
                return self.depends_on_task(context, func, **args)

        return specific_decorator

    def depends_on_tag(self, context, func, **args):
        if len(args) != 1:
            self.error('@depends(on_tag=...) does not take other arguments.')
            self.show_context(context)
            sys.exit(1)

        tag = []
        arg = args['on_tag']
        if type(arg) is str:
            tag.append(_Sane.Depends(arg, context))
        elif hasattr(arg, '__iter__'):
            if type(arg) not in (tuple, list, set):
                if type(arg) is dict:
                    self.warn('on_tag= argument is a dictionary, which, although iterable, '
                              'is ambiguous, since only the values (and not the keys) will '
                              'be considered. The values will still be considered, but '
                              'this may be unexpected.')
                else:
                    self.warn('on_tag= argument is not a collection, although it is iterable. '
                              'The elements in this iterator will still be considered, '
                              'but exhaustion of the iterator may produce unexpected results.')
                self.show_context(context, 'warn')
                self.hint(
                    '(To silence this warning, convert the argument to a collection type.)')

            for element in arg:
                if type(element) is str:
                    tag.append(_Sane.Depends(element, context))
                else:
                    self.error('on_tag= argument must be iterable of string.')
                    self.show_context(context, 'error')
                    sys.exit(1)
        else:
            self.error(
                'on_tag= argument must be string or iterable of string.')
            self.show_context(context, 'error')
            sys.exit(1)

        props = self.get_props(func)
        props['depends']['tag'].extend(tag)

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
        args = args['args']

        if type(args) not in (tuple, list):
            if type(args) is str:
                self.error('The args= argument must be a tuple or list.')
                self.show_context(context, 'error')
                self.hint(f'Write args=["{args}"] instead.')
            elif hasattr(args, '__iter__'):
                if type(args) is dict:
                    self.warn('The args= argument is a dictionary, which, although iterable, '
                              'is ambiguous, since only the values (and not the keys) will '
                              'be considered. The values will still be considered, but '
                              'this may be unexpected.')
                else:
                    self.warn('The args= argument is not a collection, although it is iterable. '
                              'The elements in this iterator will still be considered, '
                              'but exhaustion of the iterator may produce unexpected results.')
                self.show_context(context, 'warn')
                self.hint(
                    '(To silence this warning, convert the argument to a collection type.)')
                args = list(args)
            else:
                self.error('The args= argument must be a tuple or list.')
                self.show_context(context, 'error')

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
            _Sane.Depends((cmd, args), context))

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

    def tag_decorator(self, *args, **kwargs):
        context = _Sane.get_context()

        invalid_args = (len(kwargs) > 0 or
                        len(args) > 1)
        if invalid_args:
            self.error('@tag takes a single positional argument.')
            self.show_context(context, 'error')
            self.hint('(For example, @tag(\'quo\').)')
            sys.exit(1)

        tag = args[0]
        if type(tag) is not str:
            self.error('@tag must be a string.')
            self.show_context(context, 'error')
            self.hint('(For example, @tag(\'quo\').)')
            sys.exit(1)

        def specific_decorator(func):
            if self.is_task_or_cmd(func):
                self.error('@tag cannot come before @cmd or @task.')
                self.show_context(context, 'error')
                sys.exit(1)
            props = self.get_props(func)
            self.tags.setdefault(tag, []).append(func)
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
            self.hint('(To specify other properties, use @tag or @depends.)')
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
        if self.finalized:
            return
        self.finalized = True

        op_mode = self.operation['mode']
        if op_mode == 'list':
            self.list_cmds()
        elif op_mode == 'cmd':
            cmd = self.operation['cmd']
            args = self.operation['args']

            if cmd is None:
                if self.default is None:
                    self.error(
                        'No @cmd given, and no @default @cmd exists.')
                    self.hint(
                        '(Add @default to a @cmd to run it when no @cmd is specified.)')
                    sys.exit(1)
                cmd = self.default.func
            else:
                if cmd not in self.cmds:
                    self.error(f'No @cmd named {cmd}.')
                    self.hint('(Use --list to see all available @cmds.)')
                    sys.exit(1)
                cmd = self.cmds[cmd]

            self.run_tree(cmd, args)
        else:
            raise ValueError(op_mode)

    def list_cmds(self):
        for cmd_name, cmd in self.cmds.items():
            self.print(f'\x1b[1m{cmd_name}\x1b[0m', end='')

            if self.verbose:
                cmd_args = inspect.signature(cmd).parameters.keys()
                if len(cmd_args) > 0:
                    comma_sep_args = ', '.join(cmd_args)
                    self.print(f'\x1b[2m({comma_sep_args})\x1b[0m')
                else:
                    self.print('\n  \x1b[2m(No arguments.)\x1b[0m')

                if hasattr(cmd, '__doc__') and cmd.__doc__:
                    doc = cmd.__doc__
                    for line in doc.splitlines():
                        self.print(f'\x1b[2m  {line}\x1b[0m')
                else:
                    self.print('  \x1b[2mNo information given.\x1b[0m')
            else:
                self.print('\n', end='')

    def run_tree(self, func, args):
        self.update_graph(func, args)
        toposort = self.get_toposort(func, args)
        for slice_ in toposort[:-1]:
            if self.jobs == 1:
                for func, args in slice_:
                    if self.verbose:
                        str_func = self.get_name(func)
                        str_args = ', '.join(str(x) for x in args)
                        self.log(f'Running {str_func}({str_args})')
                    func.__call__(*args)
            else:
                if self.verbose:
                    str_jobs = []
                    for func, args in slice_:
                        str_func = self.get_name(func)
                        str_args = ', '.join(str(x) for x in args)
                        str_jobs.append(f'{str_func}({str_args})')
                    if len(str_jobs) > 1:
                        str_jobs = ', '.join(str_jobs[:-1]) + ', and ' + str_jobs[-1]
                        self.log(f'Simultaneously running {str_jobs}.')
                    else:
                        str_jobs = str_jobs[0]
                        self.log(f'Running {str_jobs}.')

                with concurrent.futures.ThreadPoolExecutor(max_workers=self.jobs) as exe:
                    futures = ((exe.submit(func, *args), func)
                               for func, args in slice_)
                    for future, func in futures:
                        future.result()

        if self.verbose:
            str_func = self.get_name(func)
            str_args = ', '.join(str(x) for x in args)
            self.log(f'Running {str_func}({str_args})')

        func, args = toposort[-1][0]
        return func.__call__(*args)

    def update_graph(self, func, args):
        visiting = set()
        stack = [('visit', (func, args))]
        while len(stack) > 0:
            op, item = stack.pop()
            func, args = item
            if op == 'visit':
                if item in visiting:
                    trace = self.get_trace(stack)
                    self.report_loop(trace)

                visiting.add(item)
                stack.append(('seal', item))

                props = self.get_props(func)
                self.resolve_depends(props)
                for cmd_item, _context in props['depends']['cmd']:
                    if cmd_item in self.incidence:
                        self.incidence[cmd_item] += 1
                    else:
                        stack.append(('visit', cmd_item))
                        self.incidence[cmd_item] = 1
                for task, _context in props['depends']['task']:
                    task_item = (task, ())
                    if task_item in self.incidence:
                        self.incidence[task_item] += 1
                    else:
                        stack.append(('visit', task_item))
                        self.incidence[task_item] = 1
            elif op == 'seal':
                visiting.remove(item)
            else:
                raise ValueError(op)

    def get_toposort(self, func, args):
        toposort = []

        roots = [(func, args)]
        incidence = self.incidence.copy()

        while len(roots) > 0:
            toposort.append(roots)
            next_roots = []
            for func, args in roots:
                props = self.get_props(func)
                for cmd_item, _context in props['depends']['cmd']:
                    incidence[cmd_item] -= 1
                    if incidence[cmd_item] == 0:
                        next_roots.append(cmd_item)
                for task, _context in props['depends']['task']:
                    task_item = (task, ())
                    incidence[task_item] -= 1
                    if incidence[task_item] == 0:
                        next_roots.append(task_item)
            roots = next_roots

        toposort.reverse()
        return toposort

    def resolve_depends(self, props):
        if props['depends']['resolved']:
            return

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
                        '(Alternatively, use @tag, and @depends(on_tag=...).)')
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
                self.ensure_signature_compatible(resolved, cmd_args, context)
                props['depends']['cmd'][i] = ((resolved, cmd_args), context)

        props['depends']['resolved'] = True

    def ensure_signature_compatible(self, func, args, context):
        signature = inspect.signature(func)
        mandatory_arg_count = 0
        optional_arg_count = 0
        for arg in signature.parameters.values():
            if arg.default is inspect.Parameter.empty:
                mandatory_arg_count += 1
            else:
                optional_arg_count += 1
        wrong_number_of_args = (len(args) < mandatory_arg_count or
                                len(args) > mandatory_arg_count + optional_arg_count)
        if wrong_number_of_args:
            self.error(
                'Arguments given in @depends are incompatible with the function signature.')
            self.show_context(context, 'error')
            sys.exit(1)

    def get_trace(self, stack):
        trace = []
        while len(stack) > 0:
            op, item = stack.pop()
            if op != 'seal':
                continue
            trace.append(item)
        return trace

    def report_loop(self, trace):
        lines = ['Dependency loop.\n']
        for element in reversed(trace):
            func, args = element
            name = self.get_name(func)
            str_args = ', '.join(str(arg) for arg in args)
            context = func.__sane__['context']
            lines.append(f'* {name}({str_args})\n')
            for line in self.format_context(context).splitlines():
                lines.append(f'| {line}\n')
            lines.append('|\n')

        loop_func, loop_args = trace[-1]
        loop_str_args = ', '.join(str(arg) for arg in args)
        loop_name = self.get_name(loop_func)
        loop_context = func.__sane__['context']
        lines.append(f'* {loop_name}({loop_str_args})')

        self.error(''.join(lines))
        sys.exit(1)
    
    def get_name(self, func):
        if hasattr(func, '__name__'):
            return func.__name__
        else:
            assert func.__sane__['type'] == 'task'
            return f'(Anonymous Task @ {hex(id(func))})'

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
                    'tag': [],
                    'cmd': [],
                    'task': [],
                },
                'incidence': None,
            }

        return func.__dict__['__sane__']

    def print(self, *args, **kwargs):
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
sane = _sane.main
cmd = _sane.cmd_decorator
task = _sane.task_decorator
depends = _sane.depends_decorator
tag = _sane.tag_decorator
when = _sane.when_decorator
default = _sane.default_decorator

if __name__ == '__main__':
    _stateful.log(f'Sane v{_Sane.VERSION}, by Miguel Murça.\n'
                  'Sane should be imported from other files, '
                  'not ran directly.\n'
                  'Refer to the [Github page] for more information.\n'
                  'https://github.com/mikeevmm/sane')
