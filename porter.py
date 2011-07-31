"""
This is an example usage of the porter module without a custom namespace.
Requires 'PYTHON_PATH_MAP' to be set to the value:

    spam=$DEV/modules:ham=$DEV/modules:shop=$DEV/modules

Where $DEV is the full path to the development directory for this module. ie.
the one that contains the modules directory with appropriate subfolders.

    >>> import sys
    >>> hook = from_env("PYTHON_PATH_MAP")
    >>> sys.meta_path.append(hook)

    >>> import spam
    >>> import ham.eggs
    >>> from shop import parrot

    >>> spam.spam()
    'Spam module'
    >>> ham.eggs.eggs()
    'Eggs module'
    >>> parrot.parrot()
    'Parrot module'

This is an example of using the porter module with a custom namespace:

    >>> hook = from_env("ROOT_PYTHON_PATH_MAP", root="root")
    >>> sys.meta_path.append(hook)

    >>> import root.spam
    >>> import root.ham.eggs
    >>> from root.shop import parrot
    >>> from root import lumberjack

    >>> root.spam.spam()
    'Spam module'
    >>> root.ham.eggs.eggs()
    'Eggs module'
    >>> parrot.parrot()
    'Parrot module'
    >>> lumberjack.lumberjack()
    'LumberJack module'

This is an example to test that the module fails appropriately when provided
with an environment variable that doesn't exist.

    >>> hook = from_env("FAKE_PYTHON_PATH_MAP")
    Traceback (most recent call last):
    PorterEnvVarNotFound: Failed to find 'FAKE_PYTHON_PATH_MAP' in environment

"""

import imp
import sys
import os

class PorterEnvVarNotFound(Exception):
    pass

class Stripper(object):

    def __init__(self, value):

        self.value = value

    def strip(self, name):

        return name.replace(self.value, "", 1)

class NullStripper(object):

    def strip(self, name):
        return name

class Loader(object):

    def __init__(self, path, stripper):

        self.path = path
        self.stripper = stripper

    def load_module(self, module_name):

        module_name = self.stripper.strip(module_name)
        file, pathname, description = imp.find_module(module_name, [self.path])

        return imp.load_module(module_name, file, pathname, description)

class RootLoader(object):

    def load_module(self, module_name):

        module = imp.new_module(module_name)
        module.__file__ = "abstract"
        module.__loader__ = self
        module.__path__ = []
        sys.modules[module_name] = module
        return module

class Porter(object):

    def __init__(self, path_map):

        self.path_map = path_map

    def find_module(self, module_name, package_path):

        try:
            return Loader(self.path_map[module_name], NullStripper())
        except KeyError:
            pass

        return None


class RootPorter(object):

    def __init__(self, root, path_map):

        self.root = root
        self.root_dot = "%s." % root
        self.path_map = path_map

    def find_module(self, module_name, package_path):

        if module_name == self.root:
            return RootLoader()

        if module_name.startswith(self.root_dot):

            try:
                key = module_name.replace(self.root_dot, "", 1)
                path = self.path_map[key]
                return Loader(path, Stripper(self.root_dot))
            except KeyError:
                pass

        return None


def from_string(value, entry_split=":", key_value_split="=", root=""):

    entries = value.split(entry_split)
    path_map = {}
    for entry in entries:
        name, path = entry.split(key_value_split)
        path_map[name] = path

    if root:
        return RootPorter(root, path_map)

    return Porter(path_map)


def from_env(env_var, entry_split=":", key_value_split="=", root=""):

    try:
        value = os.environ[env_var]
    except KeyError:
        raise PorterEnvVarNotFound("Failed to find '%s' in environment" % env_var)

    return from_string(
            value,
            entry_split=entry_split,
            key_value_split=key_value_split,
            root=root
            )

if __name__ == "__main__":
    import doctest
    doctest.testmod()

