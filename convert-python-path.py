#!/bin/env python

from zipfile import ZipFile, BadZipfile

import sys
import os

module_path = []

for entry in sys.path[1:]:

    print entry

    try:
        with ZipFile( entry, 'r' ) as zip_:
            # TODO: Handle zip files
            pass

    except BadZipfile as e:
        print "File, but not a zip", entry

    except IOError as e:
        # Probably a directory

        try:
            contents = os.listdir( entry )
        except OSError:
            # Directory doesn't exist
            continue

        modules = set()

        modules.update( set( [ x[:-4] for x in contents if x.endswith( ".pyc" ) ] ) )

        modules.update( set( [ x[:-3] for x in contents if x.endswith( ".py" ) ] ) )

        modules.update( set( [ x[:-3] for x in contents if x.endswith( ".so" ) ] ) )

        modules.update( set( [ x for x in contents if os.path.exists( "%s%s%s%s__init__.py" % ( entry, os.sep, x, os.sep ) ) ] ) )

        module_path.append( "%s=%s" % ( ",".join( modules ), entry ) )

print ":".join( module_path )



