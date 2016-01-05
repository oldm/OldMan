# -*- coding: utf-8 -*-
from rdflib import Graph
from oldman import create_mediator, parse_graph_safely, SparqlStoreProxy, Context

# Graph containing all the schema RDF triples
schema_graph = Graph()

# Load the schema
schema_url = "https://raw.githubusercontent.com/oldm/OldMan/master/examples/quickstart_schema.ttl"
parse_graph_safely(schema_graph, schema_url, format="turtle")

context = Context("https://raw.githubusercontent.com/oldm/OldMan/master/examples/quickstart_context.jsonld")

# JSON-LD contexts for models
contexts = {
    "Person": context,
    "LocalPerson": context
}

# User Mediator (creates models declared in the schema_graph)
mediator = create_mediator(schema_graph, contexts)

# Model
#lp_model = mediator.create_model("LocalPerson", ctx_iri, schema_graph)
lp_model = mediator.get_model("LocalPerson")


# Storage concerns

rdflib_store = "default"

# from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore
# rdflib_store = SPARQLUpdateStore(queryEndpoint="http://localhost:3030/test/query",
#                           update_endpoint="http://localhost:3030/test/update")


# In-memory triple store
triplestore = Graph(rdflib_store)

# store_proxy = SparqlStoreProxy(triplestore)

# TODO: remove these lines
store_proxy = SparqlStoreProxy(triplestore, schema_graph=schema_graph)
store_proxy.extract_prefixes(schema_graph)
store_proxy.create_model("LocalPerson", context, iri_prefix="http://localhost/persons/",
                         iri_fragment="me", incremental_iri=True)

# store_proxy.add_id_generator("LocalPerson", context=ctx_iri, iri_prefix="http://localhost/persons/",
#                             iri_fragment="me", incremental_iri=True)
mediator.bind_store(store_proxy, lp_model)


session1 = mediator.create_session()

alice = lp_model.new(session1, name="Alice", emails={"alice@example.org"},
                     short_bio_en="I am ...")
bob = lp_model.new(session1, name="Bob",
                   # blog="http://blog.example.com/",
                   short_bio_fr=u"J'ai grandi en ... .")

print bob.is_valid()
bob.emails = {"bob@localhost", "bob@example.org"}
print bob.is_valid()

session1.flush()

alice.friends = {bob}
bob.friends = {alice}
session1.flush()

print alice.id.iri
print bob.id.iri
print bob.types

print alice.name
print bob.emails
print bob.short_bio_en
print bob.short_bio_fr

john_iri = "http://example.org/john#me"
john = lp_model.new(session1, iri=john_iri, name="John", emails={"john@example.org"})
session1.flush()
print john.id.iri

alice_iri = alice.id.iri

session2 = mediator.create_session()

# First person found named Bob
bob = lp_model.first(session2, name="Bob")
alice = lp_model.get(session2, alice_iri)
print alice.name

# Or retrieve her as the unique friend of Bob
alice = list(bob.friends)[0]
print alice.name

print set(lp_model.all(session2))
print set(lp_model.filter(session2))

print alice.to_json()
print john.to_jsonld()
print bob.to_rdf("turtle")

## Email is required
# lp_model.new(session1, name="Jack")
# session1.flush()

## Invalid email
# bob.emails = {'you_wont_email_me'}

## Not a set
# bob.emails = "bob@example.com"

##Invalid name
# bob.name = 5

session1.close()
session2.close()
