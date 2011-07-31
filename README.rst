Porter
======

The aim of the project is to provide a map based lookup for Python modules
instead of the normal linear list.

Disclaimer
----------

I know just enough to write this but not to fully understand the consequences. I
think it is pretty cool, but if you read this and are aware of some serious
issues that this might cause I would love to know.

Background
----------

The standard method for importing modules involves ``PYTHONPATH`` which is used
to populate ``sys.path`` which is then searched in a linear fashion. For each
module there are multiple checks for potential file matches on disk at each
location in ``sys.path``. The ``strace`` output for the checks for a single
location on disk look something like this::

   ...
   stat("location/codecs", 0x7fff43247de0) = -1 ENOENT (No such file or directory)
   open("location/codecs.so", O_RDONLY) = -1 ENOENT (No such file or directory)
   open("location/codecsmodule.so", O_RDONLY) = -1 ENOENT (No such file or directory)
   open("location/codecs.py", O_RDONLY) = -1 ENOENT (No such file or directory)
   open("location/codecs.pyc", O_RDONLY) = -1 ENOENT (No such file or directory)
   ...

This can be costly when there are a large number of entries in ``sys.path``,
especially when the file lookups are done across a network.

Proposal
--------

In order to try to help this situation, it seems reasonable to encode more
information into the environment. ``PYTHONPATH`` is designed to take a list of
locations to search for modules but without any further information about where
individual modules might be found. It has the format::

   location[:location[:location[:...]]]

If we introduce a new environment variable with a format::

   name=location[:name=location[:name=location[:...]]]

Then instead of parsing this information into a list, we can parse it into a map
of key-value pairs when the key is the name of the module or package and the
value is the directory in which it can be found.

Then when we are importing a new module instead of linearly searching a list
with expensive disk checks, we can swiftly look up the location in the map and
only test one directory.

Implementation
--------------

We implement this approach as a custom Python import hook via the mechanism
described in PEP 302. We add the hook to the ``sys.meta_path`` which is tried
before the standard import mechanism is employed.

The environment variable is only parsed once per Python session, when the hook
is created, and then for every module that is imported we check our map to see
if the module name is one of our keys and if it is found we return a custom
loader object which is prepped with the correct location from the map.

We use the ``imp`` module to do a standard Python import from that location so
that the appropriate checks are done for ``.py`` files, ``.pyc`` files, packages
and c-extensions.

If the module is not found in the map then we return ``None`` to indicate that
the we should fall back to the default import mechanism.

How to use
----------

The basic usage requires the following three lines::

    >>> import sys
    >>> hook = porter.from_env("PORTER_MODULE_MAP")
    >>> sys.meta_path.append(hook)

This can be done on a per-script basis, which isn't terribly preferable or
instead setup in your ``site.py`` module as far as I understand it.

The environment variable can be called whatever you like as you're setting it
up. By default, the key-value pairs should be separated with ``:``'s and there
should be an ``=``'s between the key and the value. These symbols can be
customised with ``entry_split`` and ``key_value_split`` keyword arguments to the
``from_env`` function. For example, if you're environment variable was setup
with ``|``'s and ``:``'s like::

   name:location[|name:location[|name:location[|...]]]

You could run::

    hook = porter.from_env(
      "PORTER_MODULE_MAP",
      entry_split="|",
      key_value_split=":"
      )

Whatever you chose, it is best that they are not characters that appear in
directory names.

Extension
---------

As an additional feature, Porter supports the idea of a root namespace for all
of the modules specified in this key-value environment variable. This is a
slightly similar concept to the package-namespace provided by ``pkgutils``,
though my understanding of that system is limited.

The root namespace functionality allows you to have an environment variable
like::

    ROOT_MODULE_MAP="spam=/dir/of/spam:ham=/dir/of/ham:parrot=/dir/of/parrot"

And then register the hook with::

    hook = porter.from_env(
      "PORTER_MODULE_MAP",
      root="root"
      )

Then the ``spam``, ``ham`` and ``parrot`` modules will be available as if they
all resided in a package called ``root``. You can import them like::

   import root.spam
   import root.ham.eggs
   from root import parrot

In this case the ``root`` object is created as a module in memory and the child
modules are imported as normal.

The benefit of this, as with the functionality provided by ``pkgutils`` is that
you can have multiple modules or packages installed to multiple different
locations which all appear to be part of the single root package. This allows a
level of consistency for, say, a company's internal software, with the
flexibility of having different parts of the root packages managed as separate
entities.


