isort
=====

isort your python imports for you so you don't have to.

isort is a Python utility / library to sort imports alphabetically, and
automatically separated into sections. It provides a command line
utility, Python library, Vim plugin, Sublime plugin, and Kate plugin to
quickly sort all your imports.

Before isort:

::

    from my_lib import Object

    print("Hey")

    import os

    from my_lib import Object3

    from my_lib import Object2

    import sys

    from third_party import lib15, lib1, lib2, lib3, lib4, lib5, lib6, lib7, lib8, lib9, lib10, lib11, lib12, lib13, lib14

    import sys

    from __future__ import absolute_import

    from third_party import lib3

    print("yo")

After isort:

::

    from __future__ import absolute_import

    import os
    import sys

    from third_party import (lib1, lib2, lib3, lib4, lib5, lib6, lib7, lib8,
                             lib9, lib10, lib11, lib12, lib13, lib14, lib15)

    from my_lib import Object, Object2, Object3

    print("Hey")
    print("yo")

Installing isort
================

Installing isort is as simple as::

    pip install git+https://github.com/myint/isort

Using isort
===========

from the command line::

    isort foo.py
