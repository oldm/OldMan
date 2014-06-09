===================
OldMan: Python OLDM
===================

.. image:: _static/wiseoldman_small.png
  :alt: Wise old man from https://openclipart.org/detail/190655/wise-old-man-by-j4p4n-190655

OldMan is a Python *Object Linked Data Mapper* (OLDM), an alternative name for *Object RDF Mapper*.
It relies on the popular `RDFlib <https://github.com/RDFLib/rdflib/>`_ Python library.
See the :ref:`foreword <foreword>` for further characteristics.


User's Guide
============

.. toctree::
   :maxdepth: 2

   foreword
   installation
   quickstart
   examples


API reference
=============

First, you may have a look to the three main classes that end-users manipulate:
the :class:`~oldman.management.manager.ResourceManager`, the :class:`~oldman.model.Model`
and the :class:`~oldman.resource.Resource`.

If you want to choose a specific :class:`~oldman.iri.IriGenerator` class, look at the :class:`oldman.iri` module.

The whole API is accessible from the :ref:`oldman <oldman>` package, the :ref:`modindex`, the  :ref:`genindex`
and the :ref:`search`.
