"""Utility methods for flake8."""
import fnmatch as _fnmatch
import inspect
import io
import os
import sys
import tokenize


def parse_comma_separated_list(value):
    # type: (Union[Sequence[str], str]) -> List[str]
    """Parse a comma-separated list.

    :param value:
        String or list of strings to be parsed and normalized.
    :returns:
        List of values with whitespace stripped.
    :rtype:
        list
    """
    if not value:
        return []

    if not isinstance(value, (list, tuple)):
        value = value.split(',')

    return [item.strip() for item in value]


def normalize_paths(paths, parent=os.curdir):
    # type: (Union[Sequence[str], str], str) -> List[str]
    """Parse a comma-separated list of paths.

    :returns:
        The normalized paths.
    :rtype:
        [str]
    """
    return [normalize_path(p, parent)
            for p in parse_comma_separated_list(paths)]


def normalize_path(path, parent=os.curdir):
    # type: (str, str) -> str
    """Normalize a single-path.

    :returns:
        The normalized path.
    :rtype:
        str
    """
    if '/' in path:
        path = os.path.abspath(os.path.join(parent, path))
    return path.rstrip('/')


def stdin_get_value():
    # type: () -> str
    """Get and cache it so plugins can use it."""
    cached_value = getattr(stdin_get_value, 'cached_stdin', None)
    if cached_value is None:
        stdin_value = sys.stdin.read()
        if sys.version_info < (3, 0):
            cached_type = io.BytesIO
        else:
            cached_type = io.StringIO
        stdin_get_value.cached_stdin = cached_type(stdin_value)
    return cached_value.getvalue()


def is_windows():
    # type: () -> bool
    """Determine if we're running on Windows.

    :returns:
        True if running on Windows, otherwise False
    :rtype:
        bool
    """
    return os.name == 'nt'


def is_using_stdin(paths):
    # type: (List[str]) -> bool
    """Determine if we're going to read from stdin.

    :param list paths:
        The paths that we're going to check.
    :returns:
        True if stdin (-) is in the path, otherwise False
    :rtype:
        bool
    """
    return '-' in paths


def _default_predicate(*args):
    return False


def filenames_from(arg, predicate=None):
    # type: (str, callable) -> Generator
    """Generate filenames from an argument.

    :param str arg:
        Parameter from the command-line.
    :param callable predicate:
        Predicate to use to filter out filenames. If the predicate
        returns ``True`` we will exclude the filename, otherwise we
        will yield it. By default, we include every filename
        generated.
    :returns:
        Generator of paths
    """
    if predicate is None:
        predicate = _default_predicate
    if os.path.isdir(arg):
        for root, sub_directories, files in os.walk(arg):
            for filename in files:
                joined = os.path.join(root, filename)
                if predicate(filename) or predicate(joined):
                    continue
                yield joined
            # NOTE(sigmavirus24): os.walk() will skip a directory if you
            # remove it from the list of sub-directories.
            for directory in sub_directories:
                if predicate(directory):
                    sub_directories.remove(directory)
    else:
        yield arg


def fnmatch(filename, patterns, default=True):
    # type: (str, List[str], bool) -> bool
    """Wrap :func:`fnmatch.fnmatch` to add some functionality.

    :param str filename:
        Name of the file we're trying to match.
    :param list patterns:
        Patterns we're using to try to match the filename.
    :param bool default:
        The default value if patterns is empty
    :returns:
        True if a pattern matches the filename, False if it doesn't.
        ``default`` if patterns is empty.
    """
    if not patterns:
        return default
    return any(_fnmatch.fnmatch(filename, pattern) for pattern in patterns)


def parameters_for(plugin):
    # type: (flake8.plugins.manager.Plugin) -> List[str]
    """Return the parameters for the plugin.

    This will inspect the plugin and return either the function parameters
    if the plugin is a function or the parameters for ``__init__`` after
    ``self`` if the plugin is a class.

    :param plugin:
        The internal plugin object.
    :type plugin:
        flake8.plugins.manager.Plugin
    :returns:
        Parameters to the plugin.
    :rtype:
        list(str)
    """
    func = plugin.plugin
    is_class = not inspect.isfunction(func)
    if is_class:  # The plugin is a class
        func = plugin.plugin.__init__

    if sys.version_info < (3, 3):
        parameters = inspect.getargspec(func)[0]
    else:
        parameters = [
            parameter.name
            for parameter in inspect.signature(func).parameters.values()
            if parameter.kind == parameter.POSITIONAL_OR_KEYWORD
        ]

    if is_class:
        parameters.remove('self')

    return parameters

NEWLINE = frozenset([tokenize.NL, tokenize.NEWLINE])
# Work around Python < 2.6 behaviour, which does not generate NL after
# a comment which is on a line by itself.
COMMENT_WITH_NL = tokenize.generate_tokens(['#\n'].pop).send(None)[1] == '#\n'


def is_eol_token(token):
    """Check if the token is an end-of-line token."""
    return token[0] in NEWLINE or token[4][token[3][1]:].lstrip() == '\\\n'

if COMMENT_WITH_NL:  # If on Python 2.6
    def is_eol_token(token, _is_eol_token=is_eol_token):
        """Check if the token is an end-of-line token."""
        return (_is_eol_token(token) or
                (token[0] == tokenize.COMMENT and token[1] == token[4]))


def is_multiline_string(token):
    """Check if this is a multiline string."""
    return token[0] == tokenize.STRING and '\n' in token[1]
