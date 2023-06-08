
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

    singleton = None

    @staticmethod
    def strip_ansi(text):
        return ANSI.sub('', text)

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
        self.setup_logging()
        self.run_on_exit()

        self.ran = False
        self.cmds = {}
        self.tasks = {}

    def setup_logging(self):
        if os.environ.get('NO_COLOR', False):
            self.color = False
        else:
            self.color = True

    def run_on_exit(self):
        self.exit_code = 0

        def save_and_exit(wraps):
            def _exit(code=0):
                self.exit_code = code
                return wraps(code)
            return _exit
        _sys_exit = sys.exit
        _builtins_exit = builtins.exit
        sys.exit = save_and_exit(_sys_exit)
        builtins.exit = save_and_exit(_builtins_exit)
        atexit.register(self.run)

    def cmd_decorator(self, *args, **kwargs):
        context = _Sane.get_context()

        if len(args) > 1 or len(kwargs) > 0:
            self.error('@cmd does not take arguments.')
            self.show_context(context, 'error')
            self.hint('(To specify other properties, use @quid or @depends.)')
            exit(1)
        elif len(args) == 0:
            self.error('@cmd does not have parentheses.')
            self.show_context(context, 'error')
            self.hint('(Remove the parentheses.)')
            exit(1)

        func = args[0]
        if not hasattr(func, '__call__'):
            self.error('@cmd must decorate a function.')
            self.show_context(context, 'error')
            exit(1)

        self.ensure_positional_args_only(context, func)

        props = self.get_props(func)
        if self.is_task_or_cmd(func):
            self.error('More than one @cmd or @task.')
            self.show_context(context, 'error')
            self.hint(
                '(A function can only have a single @cmd or @task statement.)')
            exit(1)
        props['type'] = 'cmd'
        props['context'] = context

        def cmd(*args, **kwargs):
            # TODO: Run the tree, not just the function.
            return func(*args, **kwargs)

        cmd.__dict__['__sane__'] = {'type': 'wrapper', 'inner': func}
        self.cmds.setdefault(func.__name__, []).append(func)
        return cmd

    def task_decorator(self, *args, **kwargs):
        context = _Sane.get_context()

        if len(args) > 1 or len(kwargs) > 0:
            self.error('@task does not take arguments.')
            self.show_context(context, 'error')
            self.hint('(To specify other properties, use @quid or @depends.)')
            exit(1)
        elif len(args) == 0:
            self.error('@task does not have parentheses.')
            self.show_context(context, 'error')
            self.hint('(Remove the parentheses.)')
            exit(1)

        func = args[0]
        if not hasattr(func, '__call__'):
            self.error('@task must decorate a function.')
            self.show_context(context, 'error')
            exit(1)

        self.ensure_no_args(context, func)

        props = self.get_props(func)
        if self.is_task_or_cmd(func):
            self.error('More than one @cmd or @task.')
            self.show_context(context, 'error')
            self.hint(
                '(A function can only have a single @cmd or @task statement.)')
            exit(1)
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
                      'use multiple @depends statements.)')
            exit(1)
        given = given[0]

        def specific_decorator(func):
            if self.is_task_or_cmd(func):
                self.error('@depends cannot come before @cmd or @task.')
                self.show_context(context, 'error')
                exit(1)

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
            exit(1)

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
                    exit(1)
        else:
            self.error(
                'on_quid= argument must be string or iterable of string.')
            self.show_context(context, 'error')
            exit(1)

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
            exit(1)

        cmd = args['on_cmd']
        if type(cmd) is not str:
            if hasattr(cmd, '__call__'):
                if not hasattr(cmd, '__sane__'):
                    self.error('Given function is not a cmd.')
                    self.show_context(context, 'error')
                    self.hint('(Is the referenced function missing a @cmd?)')
                    exit(1)
                elif cmd.__sane__.get('type', None) != 'cmd':
                    self.error('Given function is not a cmd.')
                    self.show_context(context, 'error')
                    self.hint('(Did you mean @depends(on_task=...)?)')
                    exit(1)
            else:
                self.error(
                    'on_cmd= argument must be a cmd, or the name of a cmd.')
                self.show_context(context, 'error')
                exit(1)

        props = self.get_props(func)
        props['depends']['cmd'].append(_Sane.Depends((cmd, args['args']), context))

        # Resolution of `cmd` and validation of `args` happens at graph build stage.

        return func

    def depends_on_task(self, context, func, **args):
        if len(args) != 1:
            if len(args) == 2 and 'args' in args:
                self.error('@depends(on_task=...) takes no args= parameter.')
                self.show_context(context, 'error')
                self.hint('(Did you mean @depends(on_cmd=..., args=...)?)')
                exit(1)
            else:
                self.error('@depends(on_task=...) takes no other parameters.')
                self.show_context(context, 'error')
                exit(1)

        task = args['on_task']
        if type(task) is not str:
            if hasattr(task, '__call__'):
                if not hasattr(task, '__sane__'):
                    self.error('Given function is not a task.')
                    self.show_context(context, 'error')
                    self.hint('(Is the referenced function missing a @task?)')
                    exit(1)
                elif cmd.__sane__.get('type', None) != 'task':
                    self.error('Given function is not a task.')
                    self.show_context(context, 'error')
                    self.hint('(Did you mean @depends(on_task=...)?)')
                    exit(1)
            else:
                self.error(
                    'on_task= argument must be a task, or the name of a task.')
                self.show_context(context, 'error')
                exit(1)

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
            exit(1)

        quid = args[0]
        if type(quid) is not str:
            self.error('@quid must be a string.')
            self.show_context(context, 'error')
            self.hint('(For example, @quid(\'quo\').)')
            exit(1)

        def specific_decorator(func):
            if self.is_task_or_cmd(func):
                self.error('@quid cannot come before @cmd or @task.')
                self.show_context(context, 'error')
                exit(1)
            props = self.get_props(func)
            props['quid'].append(quid)
            return func

        return specific_decorator

    def when_decorator(self, condition):
        context = _Sane.get_context()

        def specific_decorator(func):
            if self.is_task_or_cmd(func):
                self.error('@when cannot come before @cmd or @task.')
                self.show_context(context, 'error')
                exit(1)
            props = self.get_props(func)
            props['when'].append(condition)
            return func
        return specific_decorator

    def run(self):
        if self.exit_code or self.ran:
            return
        self.ran = True

        try:
            self._run()
        except SystemExit as sys_exit:
            # TODO: Change exit code and exit cleanly.
            # This is currently apparently not possible.
            # See https://github.com/python/cpython/issues/103512
            # os._exit ignores other handlers and does not flush buffers.
            os._exit(sys_exit.code)

    def _run(self):
        for cmd_name, cmd_list in self.cmds.items():
            for cmd in cmd_list:
                props = self.get_props(cmd)
                self.resolve_depends(props)

        for task_name, task_list in self.tasks.items():
            for task in task_list:
                props = self.get_props(cmd)
                self.resolve_depends(props)

    def resolve_depends(self, props):
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
                    exit(1)
                elif len(self.tasks[task_depends]) > 1:
                    self.error(
                        f'There\'s more than one @task named {task_depends}.')
                    self.show_context(context, 'error')
                    self.hint(
                        '(You can reference a function directly, instead of a string.)')
                    self.hint(
                        '(Alternatively, use @quid, and @depends(on_quid=...).)')
                    exit(1)
                resolved = self.tasks[task_depends][0]
                props['depends']['task'][i] = (resolved, context)

        for i in range(len(props['depends']['cmd'])):
            cmd_depends, context = props['depends']['cmd'][i]
            if type(cmd_depends) is str:
                if cmd_depends not in self.cmds:
                    self.error(f'No @cmd named {cmd_depends}.')
                    self.show_context(context, 'error')
                    self.hint(
                        '(You can reference a function directly, instead of a string.)')
                    self.hint(
                        '(Are you missing a @cmd somewhere?)')
                    exit(1)
                elif len(self.cmds[cmd_depends]) > 1:
                    self.error(
                        f'There\'s more than one @cmd named {cmd_depends}.')
                    self.show_context(context, 'error')
                    self.hint(
                        '(You can reference a function directly, instead of a string.)')
                    self.hint(
                        '(Alternatively, use @quid, and @depends(on_quid=...).)')
                    exit(1)
                resolved = self.cmds[cmd_depends][0]
                props['depends']['cmd'][i] = (resolved, context)

    def is_task_or_cmd(self, func):
        props = self.get_props(func)
        return props['type'] is not None

    def ensure_no_args(self, context: Context, func):
        signature = inspect.signature(func)
        if len(signature.parameters.values()) > 0:
            self.error('@task cannot have arguments.')
            self.show_context(context, 'error')
            self.hint('(Use a @cmd instead.)')
            exit(1)

    def ensure_positional_args_only(self, context: Context, func):
        signature = inspect.signature(func)
        any_non_positional = any(
            arg.kind not in (inspect.Parameter.POSITIONAL_ONLY,
                             inspect.Parameter.POSITIONAL_OR_KEYWORD)
            for arg in signature.parameters.values())
        if any_non_positional:
            self.error('@cmd cannot have non-positional arguments.')
            self.show_context(context, 'error')
            exit(1)

    def get_props(self, func):
        if '__sane__' not in func.__dict__:
            func.__dict__['__sane__'] = {
                'type': None,
                'when': [],
                'quid': [],
                'depends': {
                    'quid': [],
                    'cmd': [],
                    'task': [],
                }
            }

        return func.__dict__['__sane__']

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

    def show_context(self, context: Context, style: Literal['log', 'warn', 'error']):
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

        if self.color:
            if style == 'log':
                print('\x1b[2m' + f'{line_ctx}\n{info}' +
                      '\x1b[0m', file=sys.stderr)
            elif style == 'warn':
                print('\x1b[33m' + f'{line_ctx}\n{info}' +
                      '\x1b[0m', file=sys.stderr)
            elif style == 'error':
                print('\x1b[35m' + f'{line_ctx}\n{info}' +
                      '\x1b[0m', file=sys.stderr)
            elif style == 'hint':
                print('\x1b[2m' + f'{line_ctx}\n{info}' +
                      '\x1b[0m', file=sys.stderr)
            else:
                raise ValueError(
                    f'Expected \'{style}\' to be one of log, warn, error, hint.')
        else:
            print(f'{line_ctx}\n{info}', file=sys.stderr)


_sane = _Sane.get()
cmd = _sane.cmd_decorator
task = _sane.task_decorator
depends = _sane.depends_decorator
quid = _sane.quid_decorator
when = _sane.when_decorator

if __name__ == '__main__':
    _stateful.log(f'Sane v{_Sane.VERSION}, by Miguel Murça.\n'
                  'Sane should be imported from other files, '
                  'not ran directly.\n'
                  'Refer to the [Github page] for more information.\n'
                  'https://github.com/mikeevmm/sane')
