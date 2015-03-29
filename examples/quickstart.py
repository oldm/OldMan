# -*- coding: utf-8 -*-
from rdflib import Graph
from oldman import create_user_mediator, parse_graph_safely, SPARQLDataStore

# In-memory store
store = "default"

# from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore
# store = SPARQLUpdateStore(queryEndpoint="http://localhost:3030/test/query",
#                           update_endpoint="http://localhost:3030/test/update")

# Graph containing all the schema RDF triples
schema_graph = Graph(store)

# Load the schema
schema_url = "https://raw.githubusercontent.com/oldm/OldMan/master/examples/quickstart_schema.ttl"
parse_graph_safely(schema_graph, schema_url, format="turtle")

ctx_iri = "https://raw.githubusercontent.com/oldm/OldMan/master/examples/quickstart_context.jsonld"

data_graph = Graph()
data_store = SPARQLDataStore(data_graph, schema_graph=schema_graph)
# Only for SPARQL data stores
data_store.extract_prefixes(schema_graph)

#LocalPerson store model
data_store.create_model("LocalPerson", ctx_iri, iri_prefix="http://localhost/persons/",
                        iri_fragment="me", incremental_iri=True)

#User Mediator
user_mediator = create_user_mediator(data_store)
user_mediator.import_store_models()

lp_model = user_mediator.get_client_model("LocalPerson")

alice = lp_model.create(name="Alice", emails={"alice@example.org"},
                        short_bio_en="I am ...")
bob = lp_model.new(name="Bob",
                   #blog="http://blog.example.com/",
                   short_bio_fr=u"J'ai grandi en ... .")

print bob.is_valid()
bob.emails = {"bob@localhost", "bob@example.org"}
print bob.is_valid()
bob.save()

alice.friends = {bob}
bob.friends = {alice}
alice.save()
bob.save()

print alice.id
print bob.id
print bob.types

print alice.name
print bob.emails
print bob.short_bio_en
print bob.short_bio_fr

john_iri = "http://example.org/john#me"
john = lp_model.create(id=john_iri, name="John", emails={"john@example.org"})
print john.id

alice_iri = alice.id
# First person found named Bob
bob = lp_model.get(name="Bob")
alice = lp_model.get(id=alice_iri)
print alice.name

# Or retrieve her as the unique friend of Bob
alice = list(bob.friends)[0]
print alice.name

print set(lp_model.all())
print set(lp_model.filter())

print alice.to_json()
print john.to_jsonld()
print bob.to_rdf("turtle")

## Email is required
#lp_model.create(name="Jack")

## Invalid email
#bob.emails = {'you_wont_email_me'}

## Not a set
#bob.emails = "bob@example.com"

##Invalid name
#bob.name = 5