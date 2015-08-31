# -*- coding: utf-8 -*-
from rdflib import Graph
from oldman import create_user_mediator, parse_graph_safely, SparqlStore

# In-memory RDFLIB store
rdflib_store = "default"

# from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore
# rdflib_store = SPARQLUpdateStore(queryEndpoint="http://localhost:3030/test/query",
#                           update_endpoint="http://localhost:3030/test/update")

# Graph containing all the schema RDF triples
schema_graph = Graph(rdflib_store)

# Load the schema
schema_url = "https://raw.githubusercontent.com/oldm/OldMan/master/examples/quickstart_schema.ttl"
parse_graph_safely(schema_graph, schema_url, format="turtle")

ctx_iri = "https://raw.githubusercontent.com/oldm/OldMan/master/examples/quickstart_context.jsonld"

data_graph = Graph()
store = SparqlStore(data_graph, schema_graph=schema_graph)
# Only for SPARQL data stores
store.extract_prefixes(schema_graph)

#LocalPerson store model
store.create_model("LocalPerson", ctx_iri, iri_prefix="http://localhost/persons/",
                   iri_fragment="me", incremental_iri=True)

#User Mediator
user_mediator = create_user_mediator(store)
user_mediator.import_store_models()

lp_model = user_mediator.get_client_model("LocalPerson")

session1 = user_mediator.create_session()

alice = lp_model.new(session1, name="Alice", emails={"alice@example.org"},
                     short_bio_en="I am ...")
bob = lp_model.new(session1, name="Bob",
                   blog="http://blog.example.com/",
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

session2 = user_mediator.create_session()

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
