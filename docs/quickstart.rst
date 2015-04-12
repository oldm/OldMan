.. _quickstart:

==========
Quickstart
==========

Model creation
--------------

First, let's import some functions and classes::

    from rdflib import Graph
    from oldman import create_user_mediator, parse_graph_safely, SparqlStore

and create the RDF graph `schema_graph` that will contain our schema::

    schema_graph = Graph()

The role of the schema graph is to contain most of the domain logic necessary to build our models.
In this example, we load it
`from a RDF file <https://github.com/oldm/OldMan/blob/master/examples/quickstart_schema.ttl>`_::

    schema_url = "https://raw.githubusercontent.com/oldm/OldMan/master/examples/quickstart_schema.ttl"
    parse_graph_safely(schema_graph, schema_url, format="turtle")

Another main piece of the domain logic is found in
`the JSON-LD context <https://github.com/oldm/OldMan/blob/master/examples/quickstart_context.jsonld>`_.
Here, we just need its IRI::

    ctx_iri = "https://raw.githubusercontent.com/oldm/OldMan/master/examples/quickstart_context.jsonld"

We now have almost enough domain knowledge to create our store and its models.


Here, we consider an in-memory SPARQL endpoint as a store (:class:`~oldman.store.sparql.SparqlStore`)::

    # In-memory RDF graph
    data_graph = Graph()
    store = SparqlStore(data_graph, schema_graph=schema_graph)

We extract the prefix information from the schema graph::

    store.extract_prefixes(schema_graph)


We create a `LocalPerson` :class:`~oldman.model.model.Model` for the store.
For that, we need:
 * The IRI or a JSON-LD term of the RDFS class of the model. Here `"LocalPerson"` is an alias
   for `<http://example.org/myvoc#LocalPerson>`_ defined in the context file ;
 * The JSON-LD context;
 * A prefix for creating the IRI of new resources (optional) ;
 * An IRI fragment (optional);
 * To declare that we want to generate incremental IRIs with short numbers
   for new :class:`~oldman.resource.resource.Resource` objects. ::

    store.create_model("LocalPerson", ctx_iri, iri_prefix="http://localhost/persons/",
                            iri_fragment="me", incremental_iri=True)



Models of the store are not directly manipulated; the user is expected to use their relative client models instead.
Here, we instantiate a :class:`~oldman.mediation.mediator.UserMediator` object that (i) gives access to client models and (ii) offers convenient method to retrieve and create :class:`~oldman.resource.resource.Resource` objects::


    user_mediator = create_user_mediator(store)
    user_mediator.import_store_models()
    lp_model = user_mediator.get_client_model("LocalPerson")


Resource editing
----------------
Now that the domain logic has been declared, we can create :class:`~oldman.resource.resource.Resource` objects
for two persons, Alice and Bob::

    alice = lp_model.create(name="Alice", emails={"alice@example.org"},
                            short_bio_en="I am ...")
    bob = lp_model.new(name="Bob", blog="http://blog.example.com/",
                       short_bio_fr=u"J'ai grandi en ... .")

Alice is already stored in the `store` but not Bob.
Actually, it cannot be saved yet because some information is still missing: its email addresses.
This information is required by our domain logic. Let's satisfy this constraint and save Bob::

    >>> bob.is_valid()
    False
    >>> bob.emails = {"bob@localhost", "bob@example.org"}
    >>> bob.is_valid()
    True
    >>> bob.save()

Let's now declare that they are friends::

    alice.friends = {bob}
    bob.friends = {alice}
    alice.save()
    bob.save()

That's it. Have you seen many IRIs? Only one, for the blog.
Let's look at them::

    >>> alice.id
    "http://localhost/persons/1#me"
    >>> bob.id
    "http://localhost/persons/2#me"
    >>> bob.types
    [u'http://example.org/myvoc#LocalPerson', u'http://xmlns.com/foaf/0.1/Person']

and at some other attributes::

    >>> alice.name
    "Alice"
    >>> bob.emails
    set(['bob@example.org', 'bob@localhost'])
    >>> bob.short_bio_en
    None
    >>> bob.short_bio_fr
    u"J'ai grandi en ... ."

We can assign an IRI when creating a  :class:`~oldman.resource.resource.Resource` object::

    >>> john_iri = "http://example.org/john#me"
    >>> john = lp_model.create(id=john_iri, name="John", emails={"john@example.org"})
    >>> john.id
    "http://example.org/john#me"


Resource retrieval
------------------

By default, resource are not cached.
We can retrieve Alice and Bob from the data graph as follows::

    >>> alice_iri = alice.id
    >>> # First person found named Bob
    >>> bob = lp_model.get(name="Bob")
    >>> alice = lp_model.get(id=alice_iri)

    >>> # Or retrieve her as the unique friend of Bob
    >>> alice = list(bob.friends)[0]
    >>> alice.name
    "Alice"

Finds all the persons::

    >>> set(lp_model.all())
    set([Resource(<http://example.org/john#me>), Resource(<http://localhost/persons/2#me>), Resource(<http://localhost/persons/1#me>)])
    >>> # Equivalent to
    >>> set(lp_model.filter())
    set([Resource(<http://localhost/persons/1#me>), Resource(<http://localhost/persons/2#me>), Resource(<http://example.org/john#me>)])


Serialization
-------------
JSON::

    >>> print alice.to_json()
    {
      "emails": [
        "alice@example.org"
      ],
      "friends": [
        "http://localhost/persons/2#me"
      ],
      "id": "http://localhost/persons/1#me",
      "name": "Alice",
      "short_bio_en": "I am ...",
      "types": [
        "http://example.org/myvoc#LocalPerson",
        "http://xmlns.com/foaf/0.1/Person"
      ]
    }

JSON-LD::

    >>> print john.to_jsonld()
    {
      "@context": "https://raw.githubusercontent.com/oldm/OldMan/master/examples/quickstart_context.jsonld",
      "emails": [
        "john@example.org"
      ],
      "id": "http://example.org/john#me",
      "name": "John",
      "types": [
        "http://example.org/myvoc#LocalPerson",
        "http://xmlns.com/foaf/0.1/Person"
      ]
    }

Turtle::

    >>> print bob.to_rdf("turtle")
    @prefix bio: <http://purl.org/vocab/bio/0.1/> .
    @prefix foaf: <http://xmlns.com/foaf/0.1/> .
    @prefix myvoc: <http://example.org/myvoc#> .
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix xml: <http://www.w3.org/XML/1998/namespace> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

    <http://localhost/persons/2#me> a myvoc:LocalPerson,
            foaf:Person ;
        bio:olb "J'ai grandi en ... ."@fr ;
        foaf:knows <http://localhost/persons/1#me> ;
        foaf:mbox "bob@example.org"^^xsd:string,
            "bob@localhost"^^xsd:string ;
        foaf:name "Bob"^^xsd:string ;
        foaf:weblog <http://blog.example.com/> .

Validation
----------
Validation is also there::

    >>> # Email is required
    >>> lp_model.create(name="Jack")
    oldman.exception.OMRequiredPropertyError: emails

    >>> #Invalid email
    >>> bob.emails = {'you_wont_email_me'}
    oldman.exception.OMAttributeTypeCheckError: you_wont_email_me is not a valid email (bad format)

    >>> # Not a set
    >>> bob.emails = "bob@example.com"
    oldman.exception.OMAttributeTypeCheckError: A container (<type 'set'>) was expected instead of <type 'str'>

    >>> #Invalid name
    >>> bob.name = 5
    oldman.exception.OMAttributeTypeCheckError: 5 is not a (<type 'str'>, <type 'unicode'>)

Domain logic
------------

Here is the declared domain logic that we used:

JSON-LD context `<https://raw.githubusercontent.com/oldm/OldMan/master/examples/quickstart_context.jsonld>`_::

    {
      "@context": {
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "foaf": "http://xmlns.com/foaf/0.1/",
        "bio": "http://purl.org/vocab/bio/0.1/",
        "myvoc": "http://example.org/myvoc#",
        "Person": "foaf:Person",
        "LocalPerson": "myvoc:LocalPerson",
        "id": "@id",
        "types": "@type",
        "friends": {
          "@id": "foaf:knows",
          "@type": "@id",
          "@container": "@set"
        },
        "short_bio_fr": {
          "@id": "bio:olb",
          "@language": "fr"
        },
        "name": {
          "@id": "foaf:name",
          "@type": "xsd:string"
        },
        "emails": {
          "@id": "foaf:mbox",
          "@type": "xsd:string",
          "@container": "@set"
        },
        "blog": {
          "@id": "foaf:weblog",
          "@type": "@id"
        },
        "short_bio_en": {
          "@id": "bio:olb",
          "@language": "en"
        }
      }
    }


Schema (uses the Hydra vocabulary) `<https://raw.githubusercontent.com/oldm/OldMan/master/examples/quickstart_schema.ttl>`_::

    @prefix bio: <http://purl.org/vocab/bio/0.1/> .
    @prefix foaf: <http://xmlns.com/foaf/0.1/> .
    @prefix hydra: <http://www.w3.org/ns/hydra/core#> .
    @prefix myvoc: <http://example.org/myvoc#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

    # Properties that may be given to a foaf:Person (no requirement)
    foaf:Person a hydra:Class ;
        hydra:supportedProperty [ hydra:property foaf:mbox ],
            [ hydra:property foaf:weblog ],
            [ hydra:property foaf:name ],
            [ hydra:property bio:olb ],
            [ hydra:property foaf:knows ].

    # Local version of a Person with requirements
    myvoc:LocalPerson a hydra:Class ;
        rdfs:subClassOf foaf:Person ;
        hydra:supportedProperty [ hydra:property foaf:mbox ;
                hydra:required true ],
            [ hydra:property foaf:name ;
                hydra:required true ].

