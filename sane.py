
"""Sane, Makefile for humans.

Copyright 2023 Miguel Murça

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
import sys
import re
import inspect
from typing import Literal
from collections import namedtuple


class _Sane:

    VERSION = '7.0'
    ANSI = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    Context = namedtuple(
        "Context", ("filename", "lineno", "code_context", "index"))

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

    def __init__(self):
        if os.environ.get('NO_COLOR', False):
            self.color = False
        else:
            self.color = True

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

        props = self.get_props(func)
        if self.is_task_or_cmd(func):
            self.error('More than one @cmd or @task.')
            self.show_context(context, 'error')
            self.hint(
                '(A function can only have a single @cmd or @task statement.)')
            exit(1)
        return self.make_cmd(func)

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

        props = self.get_props(func)
        if self.is_task_or_cmd(func):
            self.error('More than one @cmd or @task.')
            self.show_context(context, 'error')
            self.hint(
                '(A function can only have a single @cmd or @task statement.)')
            exit(1)
        return self.make_task(func)

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

        quid = set()
        arg = args['on_quid']
        if type(arg) is str:
            quid.add(arg)
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
                    quid.add(element)
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
        props['depends']['quid'].union(quid)

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
        props['depends']['cmd'].add((cmd, args['args']))

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
        props['depends']['task'].add(task)

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
            props['quid'].add(quid)
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
            props['when'].add(condition)
            return func
        return specific_decorator

    def make_cmd(self, func):
        def cmd(*args, **kwargs):
            # TODO
            return func(*args, **kwargs)

        cmd.__dict__['__sane__'] = {
            'type': 'cmd',
            'inner': func,
        }
        return cmd

    def make_task(self, func):
        def task():
            # TODO
            return func()

        task.__dict__['__sane__'] = {
            'type': 'task',
            'inner': func,
        }
        return task

    def is_task_or_cmd(self, func):
        props = self.get_props(func)
        return ('type' in props)

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

    def main_function(self):
        # TODO
        pass

    def get_props(self, func):
        if '__sane__' not in func.__dict__:
            func.__dict__['__sane__'] = {
                'when': set(),
                'quid': set(),
                'depends': {
                    'quid': set(),
                    'cmd': set(),
                    'task': set()
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
            else:
                print('\x1b[35m' + f'{line_ctx}\n{info}' +
                      '\x1b[0m', file=sys.stderr)
        else:
            print(f'{line_ctx}\n{info}', file=sys.stderr)


_sane = _Sane()
cmd = _sane.cmd_decorator
task = _sane.task_decorator
depends = _sane.depends_decorator
quid = _sane.quid_decorator
when = _sane.when_decorator
sane = _sane.main_function


if __name__ == '__main__':
    _stateful.log(f'Sane v{_Sane.VERSION}, by Miguel Murça.\n'
                  'Sane should be imported from other files, '
                  'not ran directly.\n'
                  'Refer to the [Github page] for more information.\n'
                  'https://github.com/mikeevmm/sane')
