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
    """
    Encapsulates the operation required to strip the "root." string from the
    start of a module name when needed.

    Provides "strip" method to do the work.
    """

    def __init__(self, value):

        self.value = value

    def strip(self, name):
        """
        Remove the first instance of self.value from the string and return the
        result.
        """

        return name.replace(self.value, "", 1)

class NullStripper(object):
    """
    Stripper class that does not strip anything
    """

    def strip(self, name):
        "Return name without stripping anything"
        return name

class Loader(object):

    def __init__(self, path, stripper):

        self.path = path
        self.stripper = stripper

    def load_module(self, module_name):
        """
        Uses the imp module find_module and load_module methods to do as
        standard a module load as possible.

        Returns the newly imported module
        """

        module_name = self.stripper.strip(module_name)
        file, pathname, description = imp.find_module(module_name, [self.path])

        return imp.load_module(module_name, file, pathname, description)

class RootLoader(object):

    def load_module(self, module_name):
        """
        Creates a new module in memory to represent the "root" module concept
        and registers it with sys.modules.

        Returns new module
        """

        module = imp.new_module(module_name)

        # Add required attributes. __path__ in particular is necessary for
        # Python to handle modules "in" this abstract package appropriately.
        module.__file__ = "abstract"
        module.__loader__ = self
        module.__path__ = []

        # Register with sys.modules
        sys.modules[module_name] = module

        return module

class Porter(object):

    def __init__(self, path_map):

        self.path_map = path_map

    def find_module(self, module_name, package_path):
        """
        Returns Loader instance if module_name is found in our path_map,
        otherwise None is returned to signal that the standard Python import
        mechansim should be used.
        """

        try:
            return Loader(self.path_map[module_name], NullStripper())
        except KeyError:
            pass

        return None


class RootPorter(object):
    """
    Import hook with known root namespace. Finds modules that start with the
    given root path. For example, if root is set to "root" and the path_map
    points to modules called ham and spam, you will be able to do:

        import root.ham
        from root import spam
    """

    def __init__(self, root, path_map):

        self.root = root
        self.root_dot = "%s." % root
        self.path_map = path_map

    def find_module(self, module_name, package_path):
        """
        Check module_name and returns a RootLoader instance if it matches the
        specified root, or a Loader instance if it starts with "root.".

        Return None if the module_name after "root." is not found in the
        path_map, this allows the standard Python import mechanism is take
        over.
        """

        if module_name == self.root:
            return RootLoader()

        if module_name.startswith(self.root_dot):

            try:
                # Strip "root." from start
                key = module_name.replace(self.root_dot, "", 1)
                path = self.path_map[key]
                return Loader(path, Stripper(self.root_dot))
            except KeyError:
                pass

        return None


def from_string(value, entry_split=":", key_value_split="=", module_value_split=",", root=""):
    """
    Parses the given string value based on the split characters provided and
    returns an appropriate import hook taking into account the value of "root".

    No error handling code to handle malformed strings at this point.
    """

    entries = value.split(entry_split)
    path_map = {}
    for entry in entries:
        key, path = entry.split(key_value_split)

        modules = key.split(module_value_split)
        for module in modules:
            path_map[module] = path

    if root:
        return RootPorter(root, path_map)

    return Porter(path_map)


def from_env(env_var, entry_split=":", key_value_split="=", module_value_split=",", root=""):
    """
    Looks up the named environment variable and uses from_string to handle the
    contents.

    Raises PorterEnvVarNotFound if the environment variable is not in the
    os.environ dictionary.

    Return the result of from_string which should be the import hook object
    """

    try:
        value = os.environ[env_var]
    except KeyError:
        raise PorterEnvVarNotFound("Failed to find '%s' in environment" % env_var)

    return from_string(
            value,
            entry_split=entry_split,
            key_value_split=key_value_split,
            module_value_split=module_value_split,
            root=root
            )

if __name__ == "__main__":
    import doctest
    doctest.testmod()

