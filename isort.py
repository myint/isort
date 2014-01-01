#!/usr/bin/env python

"""isort.py.

Exposes a simple library to sort through imports within Python code

usage:
    SortImports(file_name)
or:
    sorted = SortImports(file_contents=file_contents).output

Copyright (C) 2013  Timothy Edmund Crosley

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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import codecs
import copy
import io
import itertools
import os
import os.path
import sys
from collections import namedtuple
from difflib import unified_diff
from sys import path as PYTHONPATH
from sys import stderr
from sys import stdout

__version__ = '2.6.0'


SECTION_NAMES = ('FUTURE', 'STDLIB', 'THIRDPARTY', 'FIRSTPARTY', 'LOCALFOLDER')
SECTIONS = namedtuple('Sections', SECTION_NAMES)(*range(len(SECTION_NAMES)))

WrapModes = (
    'GRID',
    'VERTICAL',
    'HANGING_INDENT',
    'VERTICAL_HANGING_INDENT',
    'VERTICAL_GRID',
    'VERTICAL_GRID_GROUPED')
WrapModes = namedtuple('WrapModes', WrapModes)(*range(len(WrapModes)))

# Note that none of these lists must be complete as they are simply
# fallbacks for when included auto-detection fails.
default = {'force_to_top': [],
           'skip': ['__init__.py', ],
           'line_length': 80,
           'known_standard_library': [
               'abc', 'anydbm', 'argparse', 'array', 'asynchat', 'asyncore',
               'atexit', 'base64', 'BaseHTTPServer', 'bisect', 'bz2',
               'calendar', 'cgitb', 'cmd', 'codecs', 'collections', 'commands',
               'compileall', 'ConfigParser', 'contextlib', 'Cookie', 'copy',
               'cPickle', 'cProfile', 'cStringIO', 'csv', 'datetime', 'dbhash',
               'dbm', 'decimal', 'difflib', 'dircache', 'dis', 'doctest',
               'dumbdbm', 'EasyDialogs', 'errno', 'exceptions', 'filecmp',
               'fileinput', 'fnmatch', 'fractions', 'functools', 'gc', 'gdbm',
               'getopt', 'getpass', 'gettext', 'glob', 'grp', 'gzip',
               'hashlib', 'heapq', 'hmac', 'imaplib', 'imp', 'inspect',
               'itertools', 'json', 'linecache', 'locale', 'logging',
               'mailbox', 'math', 'mhlib', 'mmap', 'multiprocessing',
               'operator', 'optparse', 'os', 'pdb', 'pickle', 'pipes',
               'pkgutil', 'platform', 'plistlib', 'pprint', 'profile',
               'pstats', 'pwd', 'pyclbr', 'pydoc', 'Queue', 'random', 're',
               'readline', 'resource', 'rlcompleter', 'robotparser', 'sched',
               'select', 'shelve', 'shlex', 'shutil', 'signal',
               'SimpleXMLRPCServer', 'site', 'sitecustomize', 'smtpd',
               'smtplib', 'socket', 'SocketServer', 'sqlite3', 'string',
               'StringIO', 'struct', 'subprocess', 'sys', 'sysconfig',
               'tabnanny', 'tarfile', 'tempfile', 'textwrap', 'threading',
               'time', 'timeit', 'trace', 'traceback', 'unittest', 'urllib',
               'urllib2', 'urlparse', 'usercustomize', 'uuid', 'warnings',
               'weakref', 'webbrowser', 'whichdb', 'xml', 'xmlrpclib',
               'zipfile', 'zipimport', 'zlib'],
           'known_third_party': ['google.appengine.api'],
           'known_first_party': [],
           'multi_line_output': WrapModes.GRID,
           'forced_separate': [],
           'indent': ' ' * 4,
           'length_sort': False,
           'add_imports': [],
           'remove_imports': [],
           'default_section': 'FIRSTPARTY'}


class SortImports(object):
    config = default
    incorrectly_sorted = False

    def __init__(self, file_path=None, file_contents=None,
                 write_to_stdout=False, check=False, show_diff=False,
                 **setting_overrides):
        if setting_overrides:
            self.config = default.copy()
            self.config.update(setting_overrides)

        file_name = file_path
        self.file_path = file_path or ''
        if file_path:
            file_path = os.path.abspath(file_path)
            if '/' in file_name:
                file_name = file_name[file_name.rfind('/') + 1:]
            if file_name in self.config['skip']:
                print(
                    "WARNING: {0} was skipped as it's listed in 'skip' "
                    "setting".format(file_path),
                    file=stderr)
                file_contents = None
            else:
                self.file_path = file_path
                with io.open(file_path,
                             encoding='utf-8') as file_to_import_sort:
                    file_contents = file_to_import_sort.read()

        if file_contents is None or ('isort:' + 'skip_file') in file_contents:
            return

        self.in_lines = file_contents.split('\n')
        self.original_length = len(self.in_lines)
        for add_import in self.config['add_imports']:
            self.in_lines.append(add_import)
        self.number_of_lines = len(self.in_lines)

        self.out_lines = []
        self.imports = {}
        self.as_map = {}
        for section in itertools.chain(SECTIONS,
                                       self.config['forced_separate']):
            self.imports[section] = {'straight': set(), 'from': {}}

        self.index = 0
        self.import_index = -1
        self._parse()
        if self.import_index != -1:
            self._add_formatted_imports()

        self.length_change = len(self.out_lines) - self.original_length
        while self.out_lines and self.out_lines[-1].strip() == '':
            self.out_lines.pop(-1)
        self.out_lines.append('')

        self.output = '\n'.join(self.out_lines)
        if check:
            if self.output == file_contents:
                print(
                    'SUCCESS: {0} Everything Looks Good!'.format(
                        self.file_path))
            else:
                print(
                    'ERROR: {0} Imports are incorrectly sorted.'.format(
                        self.file_path),
                    file=stderr)
                self.incorrectly_sorted = True
            return

        if show_diff:
            for line in unified_diff(
                    file_contents.splitlines(1), self.output.splitlines(1),
                    fromfile=self.file_path + ':before',
                    tofile=self.file_path + ':after'):
                stdout.write(line)
        elif write_to_stdout:
            stdout.write(self.output)
        elif file_name:
            with codecs.open(self.file_path, encoding='utf-8', mode='w') as output_file:
                output_file.write(self.output)

    def place_module(self, moduleName):
        """Tries to determine if a module is a python std import,
           third party import, or project code:
           if it can't determine - it assumes it is project code
        """
        if moduleName.startswith('.'):
            return SECTIONS.LOCALFOLDER

        index = moduleName.find('.')
        if index:
            firstPart = moduleName[:index]
        else:
            firstPart = None

        for forced_separate in self.config['forced_separate']:
            if moduleName.startswith(forced_separate):
                return forced_separate

        if moduleName == '__future__' or (firstPart == '__future__'):
            return SECTIONS.FUTURE
        elif moduleName in self.config['known_standard_library'] or \
                (firstPart in self.config['known_standard_library']):
            return SECTIONS.STDLIB
        elif ((moduleName in self.config['known_third_party']) or
              (firstPart in self.config['known_third_party'])):
            return SECTIONS.THIRDPARTY
        elif ((moduleName in self.config['known_first_party']) or
              (firstPart in self.config['known_first_party'])):
            return SECTIONS.FIRSTPARTY

        for prefix in PYTHONPATH:
            module_path = '/'.join((prefix, moduleName.replace('.', '/')))
            package_path = '/'.join((prefix, moduleName.split('.')[0]))
            if (os.path.exists(module_path + '.py') or
                os.path.exists(module_path + '.so') or
                (os.path.exists(package_path) and
                 os.path.isdir(package_path))):
                if 'site-packages' in prefix or 'dist-packages' in prefix:
                    return SECTIONS.THIRDPARTY
                elif 'python2' in prefix.lower() or 'python3' in prefix.lower():
                    return SECTIONS.STDLIB
                else:
                    return SECTIONS.FIRSTPARTY

        return SECTION_NAMES.index(self.config['default_section'])

    def _get_line(self):
        """Returns the current line from the file while incrementing the
        index."""
        line = self.in_lines[self.index]
        self.index += 1
        return line

    def _at_end(self):
        """returns True if we are at the end of the file."""
        return self.index == self.number_of_lines

    def _add_formatted_imports(self):
        """Adds the imports back to the file.

        (at the index of the first import) sorted alphabetically and
        split between groups

        """
        output = []
        for section in itertools.chain(SECTIONS, self.config['forced_separate']):
            straight_modules = list(self.imports[section]['straight'])
            straight_modules = sorted(
                straight_modules,
                key=lambda key: _module_key(
                    key,
                    self.config))

            for module in straight_modules:
                if module in self.config['remove_imports']:
                    continue

                if module in self.as_map:
                    output.append(
                        'import {0} as {1}'.format(module, self.as_map[module]))
                else:
                    output.append('import {0}'.format(module))

            from_modules = list(self.imports[section]['from'].keys())
            from_modules = sorted(
                from_modules,
                key=lambda key: _module_key(
                    key,
                    self.config))
            for module in from_modules:
                if module in self.config['remove_imports']:
                    continue

                import_start = 'from {0} import '.format(module)
                from_imports = list(self.imports[section]['from'][module])
                from_imports = sorted(
                    from_imports,
                    key=lambda key: _module_key(
                        key,
                        self.config))
                if self.config['remove_imports']:
                    from_imports = [line for line in from_imports if not '{0}.{1}'.format(module, line) in
                                    self.config['remove_imports']]

                for from_import in copy.copy(from_imports):
                    import_as = self.as_map.get(
                        module +
                        '.' +
                        from_import,
                        False)
                    if import_as:
                        output.append(
                            import_start +
                            '{0} as {1}'.format(
                                from_import,
                                import_as))
                        from_imports.remove(from_import)

                if from_imports:
                    if '*' in from_imports:
                        import_statement = '{0}*'.format(import_start)
                    else:
                        import_statement = import_start + from_imports.pop(0)
                        for from_import in from_imports:
                            import_statement += '\n{0}{1}'.format(import_start,
                                                                  from_import)

                    output.append(import_statement)

            if straight_modules or from_modules:
                output.append('')

        while [character.strip() for character in output[-1:]] == ['']:
            output.pop()

        self.out_lines[self.import_index:0] = output

        imports_tail = self.import_index + len(output)
        while [character.strip() for character in self.out_lines[imports_tail: imports_tail + 1]] == ['']:
            self.out_lines.pop(imports_tail)

        if len(self.out_lines) > imports_tail:
            next_construct = self.out_lines[imports_tail]
            if next_construct.startswith('def') or next_construct.startswith('class') or \
               next_construct.startswith('@'):
                self.out_lines[imports_tail:0] = ['', '']
            else:
                self.out_lines[imports_tail:0] = ['']

    def _parse(self):
        """Parses a python file taking out and categorizing imports."""
        in_quote = False
        while not self._at_end():
            line = self._get_line()
            skip_line = in_quote
            if '"' in line or "'" in line:
                index = 0
                while index < len(line):
                    if line[index] == '\\':
                        index += 1
                    elif in_quote:
                        if line[index:index + len(in_quote)] == in_quote:
                            in_quote = False
                    elif line[index] in ("'", '"'):
                        long_quote = line[index:index + 3]
                        if long_quote in ('"""', "'''"):
                            in_quote = long_quote
                            index += 2
                        else:
                            in_quote = line[index]
                    elif line[index] == '#':
                        break
                    index += 1

            import_type = _import_type(line)
            if not import_type or skip_line:
                self.out_lines.append(line)
                continue

            if self.import_index == -1:
                self.import_index = self.index - 1

            import_string = _strip_comments(line)
            if '(' in line and not self._at_end():
                while not line.strip().endswith(')') and not self._at_end():
                    line = _strip_comments(self._get_line())
                    import_string += '\n' + line
            else:
                while line.strip().endswith('\\'):
                    line = _strip_comments(self._get_line())
                    import_string += '\n' + line

            import_string = import_string.replace('_import', '[[i]]')
            for remove_syntax in ['\\', '(', ')', ',', 'from ', 'import ']:
                import_string = import_string.replace(remove_syntax, ' ')
            import_string = import_string.replace('[[i]]', '_import')

            imports = import_string.split()
            if 'as' in imports and (imports.index('as') + 1) < len(imports):
                while 'as' in imports:
                    index = imports.index('as')
                    if import_type == 'from':
                        self.as_map[imports[0] + '.' +
                                    imports[index - 1]] = imports[index + 1]
                    else:
                        self.as_map[imports[index - 1]] = imports[index + 1]
                    del imports[index:index + 2]
            if import_type == 'from':
                import_from = imports.pop(0)
                root = self.imports[
                    self.place_module(
                        import_from)][
                    import_type]
                if root.get(import_from, False):
                    root[import_from].update(imports)
                else:
                    root[import_from] = set(imports)
            else:
                for module in imports:
                    self.imports[
                        self.place_module(module)][import_type].add(module)


def _import_type(line):
    """If the current line is an import line it will return its type (from
    or straight)"""
    if 'isort:skip' in line:
        return
    elif line.startswith('import '):
        return 'straight'
    elif line.startswith('from ') and 'import' in line:
        return 'from'


def _module_key(module_name, config):
    module_name = str(module_name).lower()
    return '{0}{1}'.format(module_name in config['force_to_top'] and 'A' or 'B',
                           config['length_sort'] and (str(len(module_name)) + ':' + module_name) or module_name)


def _output_grid(statement, imports, white_space, indent, line_length):
    statement += '(' + imports.pop(0)
    while imports:
        next_import = imports.pop(0)
        next_statement = statement + ', ' + next_import
        if len(next_statement.split('\n')[-1]) + 1 > line_length:
            next_statement = '{0},\n{1}{2}'.format(
                statement,
                white_space,
                next_import)
        statement = next_statement
    return statement + ')'


def _output_vertical(statement, imports, white_space, indent, line_length):
    return (
        '{0}({1})'.format(statement, (',\n' + white_space).join(imports))
    )


def _output_hanging_indent(
        statement, imports, white_space, indent, line_length):
    statement += ' ' + imports.pop(0)
    while imports:
        next_import = imports.pop(0)
        next_statement = statement + ', ' + next_import
        if len(next_statement.split('\n')[-1]) + 3 > line_length:
            next_statement = '{0}, \\\n{1}{2}'.format(
                statement,
                indent,
                next_import)
        statement = next_statement
    return statement


def _output_vertical_hanging_indent(
        statement, imports, white_space, indent, line_length):
    return (
        '{0}(\n{1}{2}\n)'.format(
            statement,
            indent,
            (',\n' + indent).join(imports))
    )


def _output_vertical_grid_common(
        statement, imports, white_space, indent, line_length):
    statement += '(\n' + indent + imports.pop(0)
    while imports:
        next_import = imports.pop(0)
        next_statement = '{0}, {1}'.format(statement, next_import)
        if len(next_statement.split('\n')[-1]) + 1 > line_length:
            next_statement = '{0},\n{1}{2}'.format(
                statement,
                indent,
                next_import)
        statement = next_statement
    return statement


def _output_vertical_grid(
        statement, imports, white_space, indent, line_length):
    return _output_vertical_grid_common(
            statement,
            imports,
            white_space,
            indent,
            line_length) + ')'


def _output_vertical_grid_grouped(
        statement, imports, white_space, indent, line_length):
    return _output_vertical_grid_common(
            statement,
            imports,
            white_space,
            indent,
            line_length) + '\n)'


def _strip_comments(line):
    """Removes comments from import line."""
    comment_start = line.find('#')
    if comment_start != -1:
        print(
            'Removing comment(%s) so imports can be sorted correctly' %
            line[comment_start:], file=stderr)
        line = line[:comment_start]

    return line


def main():
    parser = argparse.ArgumentParser(
        description='Sort Python import definitions alphabetically within logical sections.')
    parser.add_argument(
        'files',
        nargs='+',
        help='One or more Python source files that need their imports sorted.')
    parser.add_argument(
        '-l', '--lines', help='The max length of an import line (used for wrapping long imports).',
        dest='line_length', type=int)
    parser.add_argument(
        '-s',
        '--skip',
        help='Files that sort imports should skip over.',
        dest='skip',
        action='append')
    parser.add_argument(
        '-t', '--top', help='Force specific imports to the top of their appropriate section.',
        dest='force_to_top', action='append')
    parser.add_argument(
        '-b', '--builtin', dest='known_standard_library', action='append',
        help='Force sortImports to recognize a module as part of the python standard library.')
    parser.add_argument(
        '-o', '--thirdparty', dest='known_third_party', action='append',
        help='Force sortImports to recognize a module as being part of a third party library.')
    parser.add_argument(
        '-p', '--project', dest='known_first_party', action='append',
        help='Force sortImports to recognize a module as being part of the current python project.')
    parser.add_argument(
        '-m', '--multi_line', dest='multi_line_output', type=int, choices=[0, 1, 2, 3, 4, 5],
        help='Multi line output (0-grid, 1-vertical, 2-hanging, 3-vert-hanging, 4-vert-grid, '
        '5-vert-grid-grouped).')
    parser.add_argument(
        '--indent', help='String to place for indents defaults to "    " (4 spaces).',
        dest='indent', type=str)
    parser.add_argument(
        '-a', '--add_import', dest='add_imports', action='append',
        help='Adds the specified import line to all files, automatically determining correct placement.')
    parser.add_argument(
        '-r', '--remove_import', dest='remove_imports', action='append',
        help='Removes the specified import from all files.')
    parser.add_argument(
        '-ls', '--length_sort', help='Sort imports by their string length.',
        dest='length_sort', action='store_true', default=False)
    parser.add_argument(
        '-d', '--stdout', help='Force resulting output to stdout, instead of in-place.',
        dest='write_to_stdout', action='store_true')
    parser.add_argument(
        '-c', '--check-only', action='store_true', default=False, dest='check',
        help='Checks the file for unsorted imports and prints them to the command line without modifying '
        'the file.')
    parser.add_argument('-sd', '--section-default', dest='default_section',
                        help='Sets the default section for imports (by default FIRSTPARTY) options: ' + str(SECTION_NAMES))
    parser.add_argument(
        '-i', '--in-place', dest='show_diff', default=True, action='store_false',
        help='Write change in place.')
    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version='isort {0}'.format(__version__))

    arguments = dict((key, value)
                     for (key, value) in vars(parser.parse_args()).items() if value)
    file_names = arguments.pop('files', [])

    if file_names == ['-']:
        SortImports(
            file_contents=sys.stdin.read(),
            write_to_stdout=True,
            **arguments)
    else:
        wrong_sorted_files = False
        for file_name in file_names:
            incorrectly_sorted = SortImports(
                file_name,
                **arguments).incorrectly_sorted
            if arguments.get('check', False) and incorrectly_sorted:
                wrong_sorted_files = True
        if wrong_sorted_files:
            return 1


if __name__ == '__main__':
    sys.exit(main())
