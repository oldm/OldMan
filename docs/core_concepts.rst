=============
Core concepts
=============

THIS PAGE IS OUT-DATED. TODO: rewrite it.

Resource
--------
A :class:`~oldman.resource.resource.Resource` object represents a `Web resource <https://en.wikipedia.org/wiki/Web_resource>`_
identified by a regular `IRI (internationalized URI) <https://en.wikipedia.org/wiki/Internationalized_resource_identifier>`_ or
or a `skolem IRI <http://www.w3.org/TR/2014/REC-rdf11-concepts-20140225/#section-skolemization>`_ (if it should treated
as a `blank node <https://en.wikipedia.org/wiki/Blank_node>`_).

In OldMan, Web resources are described in conformance to the
`Resource Description Framework (RDF) <https://en.wikipedia.org/wiki/Resource_Description_Framework>`_.
A :class:`~oldman.resource.resource.Resource` object may have some attributes that provide the *predicate*
(also called property) and the *object* terms of RDF triples describing the resource.
The resource itself is the *subject* of the triple (expect if the property is reversed).
Its attributes have arbitrary short names as defined in the JSON-LD context.

A :class:`~oldman.resource.resource.Resource` object access to its attributes through the
:class:`~oldman.model.model.Model` objects to which it relates (through its :attr:`~oldman.resource.resource.Resource.types`).
Thus, if it has no *type* or its types that are not related to a :class:`~oldman.model.model.Model` object,
a :class:`~oldman.resource.resource.Resource` object has no "RDF" attribute.

In OldMan, the relation between :class:`~oldman.resource.resource.Resource` and :class:`~oldman.model.model.Model` objects
is *many-to-many*.
It differs from traditional ORMs where the relation is *one-to-many* (the resource is usually
an instance of the model and the latter is a Python class in these frameworks).
However, we expect that most :class:`~oldman.resource.resource.Resource` objects will relate to one
:class:`~oldman.model.model.Model` object, but this is not a requirement.
It is common for a resource in RDF to be instance of multiple RDFS classes so OldMan had to be ok with this practise.

Some inherited Python methods may also be provided by the :class:`~oldman.model.model.Model` objects.


Features
~~~~~~~~

1. Edit its properties::

    >>> # We assume that a model has been created for the RDFS class schema:Person.
    >>> alice = Resource(resource_manager, types=["http://schema.org/Person"])
    >>> alice.name = "Alice"
    >>> print alice.name
    Alice
    >>> print alice.id
    'http://localhost/person/3#me'
    >>> alice.add_type("http://schema.org/Researcher")
    >>> print alice.types
    [u'http://schema.org/Person', u'http://schema.org/Researcher']

2. Persist its new values in the triplestore::

    alice.save()

3. Call inherited methods::

    alice.do_that()

4. Serialize to JSON, JSON-LD or any other RDF format::

    >>> alice.to_jsonld()
    {
      "@context": "https://example.com/context.jsonld",
      "id": "http://localhost/person/3#me",
      "name": "Alice",
      "types": [
        "http://schema.org/Person",
        "http://schema.org/Researcher"
      ]
    }
    >>> alice.to_rdf(format="turtle")
    @prefix schema: <http://schema.org/> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

    <http://localhost/persons/3#me> a schema:Person, schema:Researcher ;
                foaf:name "Alice"^^xsd:string .

UserMediator
------------
TODO: update

A :class:`~oldman.mediation.mediator.UserMediator` object is the central object of OldMan.

It creates :class:`~oldman.model.model.Model` objects (:func:`~oldman.mediation.mediator.UserMediator.create_model`)
and retrieves :class:`~oldman.resource.resource.Resource` objects  (:func:`~oldman.mediation.mediator.UserMediator.get`,
:func:`~oldman.mediation.mediator.UserMediator.filter`
and :func:`~oldman.mediation.mediator.UserMediator.sparql_filter`).

It accepts Python method declarations if they happen before the creation of :class:`~oldman.model.model.Model` objects
(:func:`~oldman.mediation.mediator.UserMediator.declare_method`).

It also provide helper functions to create new :class:`~oldman.resource.resource.Resource` objects
(:func:`~oldman.management.manager.ResourceManager.create` and :func:`~oldman.mediation.mediator.UserMediator.new`)
but it is usually simpler to use those of a :class:`~oldman.model.model.Model` object.

For creating the :class:`~oldman.mediation.mediator.UserMediator` object, the schema graph
and the data store (:class:`~oldman.store.datastore.DataStore`) must be given.

Basically, the schema graph describes which properties should be expected for a given RDFS class, which are
required and what are the constraints.


Model
-----

In OldMan, models are not Python classes but :class:`~oldman.model.model.Model` objects.
However, on the RDF side, they correspond to `RDFS classes <https://en.wikipedia.org/wiki/RDFS>`_ (their
:attr:`~oldman.model.model.Model.class_iri` attributes).

Their main role is to provide attributes and methods to :class:`~oldman.resource.resource.Resource` objects, as explained
above.

:class:`~oldman.model.model.Model` objects are created by the :class:`~oldman.mediation.mediator.UserMediator` object.

A model provide some helpers above the :class:`~oldman.mediation.mediator.UserMediator` object (
:func:`~oldman.model.model.Model.get`, :func:`~oldman.model.model.Model.filter`, :func:`~oldman.model.model.Model.new` and
:func:`~oldman.model.model.Model.create`) that include the :attr:`~oldman.model.model.Model.class_iri` to the `types`
parameter of these methods.

DataStore
---------

A :class:`~oldman.store.datastore.DataStore` implements the CRUD operations on Web Resources exposed by the
:class:`~oldman.mediation.mediator.UserMediator` and :class:`~oldman.model.model.Model` objects.

The vision of OldMan is to include a large choice of data stores. But currently, only SPARQL endpoints
are supported.

Non-CRUD operations may also be introduced in the future (in discussion).

Any data store accepts a :class:`dogpile.cache.region.CacheRegion` object to enable its
:class:`~oldman.store.cache.ResourceCache` object.
By default the latter is disabled so it does not cache the :class:`~oldman.resource.resource.Resource` objects loaded
from and stored in the data store.

SPARQLDataStore
~~~~~~~~~~~~~~~

A :class:`~oldman.store.sparql.SPARQLDataStore` object relies on one or two RDF graphs (:class:`rdflib.graph.Graph`):
the data and default graphs.

The data graph is where regular resources are saved and loaded.

The default graph (:class:`rdflib.graph.ConjunctiveGraph` or :class:`rdflib.graph.Dataset`) may be
given as an optional second graph.
Its only constraint is to include the content of the data graph in its default graph.