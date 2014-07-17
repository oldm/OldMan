.. _foreword:

========
Foreword
========

OldMan is a Python *Object Linked Data Mapper* (OLDM).

An OLDM let you create, retrieve and update RDF representations of Web Resources by manipulating them
as Python objects.

OldMan, in its core, is based on two W3C standards:

 1. `RDF (the Resource Description Framework) <http://www.w3.org/TR/rdf11-concepts/>`_ as data model;
 2. `JSON-LD context <http://www.w3.org/TR/json-ld/#the-context>`_ for mapping objects and RDF graphs.


It is designed to support multiple protocols for interacting with data stores hosting these resources.
Currently, only `SPARQL <http://www.w3.org/TR/sparql11-overview/>`_ is officially supported.


OldMan relies on the `RDFlib <https://github.com/RDFLib/rdflib/>`_ Python library.


Why a new term?
===============

Some similar projects employ the term *Object RDF Mapper* for denoting the mapping between objects
and **RDF graphs**. This terminology uses the same initials than the well-known notion of *Object Relational
Mapper* (ORM) that consider *table rows* instead of *RDF graphs*.

The *Object Linked Data Mapper* (OLDM) term avoids this confusion.
It also emphasizes that the manipulated resources are supposed to be **on the Web**,
not just in a local database. It should lead users to interact with data stores
on which they not always have full control (e.g. a tiers Web API).


Mission
=======

OldMan has one main objective: help you to **declare your models using RDF triples and JSON-LD contexts** instead
of programming Python model classes yourself.

However, OldMan does not force you to express all your domain logic in a declarative style.
OldMan makes easy for you to add dynamically plain-old Python methods to resource objects.

By adopting a declarative style:

 1. You can provide both RDF and JSON data to your clients.
 2. Your schema (including validation constraints) can be published and reused by **hypermedia-driven** Web clients.
 3. Your declared domain logic becomes independent of Python and its frameworks.

It also acknowledges that IRIs or `compact URIs (CURIEs) <http://www.w3.org/TR/curie/>`_ -like strings
are not always pleasant to use: arbitrary short names and objects are usually more user-friendly.
However, you can still manipulate IRIs when it is relevant for you to do so. Everything remains mapped to IRIs.


Current core features
=====================
 * Resource-centric validation based on RDF vocabularies:

     - `Hydra`_: `hydra:required`_ , `hydra:readonly`_ and `hydra:writeonly`_;
     - Literal validation for common XSD types;
     - Literal validation for arbitrary property (e.g. `foaf:mbox <http://xmlns.com/foaf/spec/#term_mbox>`_);
     - `JSON-LD collections <http://www.w3.org/TR/json-ld/#sets-and-lists>`_ (set, list and language maps);
 * IRI generation for new resources (objects);
 * Inheritance (attributes and Python methods);
 * An attribute can require its value to be a collection (a set, a list or a language map);
 * Arbitrary attribute names (e.g. plural names for collections);
 * Extensibility to various sorts of data stores (not just SPARQL endpoints);
 * Optional resource cache relying on the popular `dogpile.cache <https://bitbucket.org/zzzeek/dogpile.cache>`_ library.

.. _Hydra: http://www.hydra-cg.com/spec/latest/core/
.. _hydra:required: http://www.hydra-cg.com/spec/latest/core/#hydra:required
.. _hydra:readonly: http://www.hydra-cg.com/spec/latest/core/#hydra:readonly
.. _hydra:writeonly: http://www.hydra-cg.com/spec/latest/core/#hydra:writeonly


Status
======

OldMan is a young project **under active development** started in April 2014.
Feel free to `join us on Github <https://github.com/oldm/OldMan>`_ and to subscribe
to our mailing list `oldman AT librelist.com`.

Only Python 2.7 is currently supported, but support for Python 3.x is of course something we would like to consider.


Planned features
================
See `our issue tracker <https://github.com/oldm/OldMan/issues>`_.

Continue to :ref:`installation <installation>` or the :ref:`quickstart <quickstart>`.