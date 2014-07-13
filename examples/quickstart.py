# -*- coding: utf-8 -*-
from rdflib import Dataset
from oldman import ResourceManager, parse_graph_safely, SPARQLDataStore

# In-memory store
store = "default"

# from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore
# store = SPARQLUpdateStore(queryEndpoint="http://localhost:3030/test/query",
#                           update_endpoint="http://localhost:3030/test/update")

# The dataset will contain the two named graphs
dataset = Dataset(store)

# Graph containing all the schema RDF triples
schema_graph = dataset.graph("http://localhost/schema")
data_graph = dataset.graph("http://localhost/data")

# Load the schema
parse_graph_safely(schema_graph, "https://raw.githubusercontent.com/oldm/OldMan/master/examples/quickstart_schema.ttl",
                   format="turtle")

context_iri = "https://raw.githubusercontent.com/oldm/OldMan/master/examples/quickstart_context.jsonld"

#Resource manager (will generate the model objects)
data_store = SPARQLDataStore(data_graph)
manager = ResourceManager(schema_graph, data_store)

#LocalPerson model
lp_model = manager.create_model("LocalPerson", context_iri, iri_prefix="http://localhost/persons/",
                                iri_fragment="me", incremental_iri=True)

alice = lp_model.create(name="Alice", emails={"alice@example.org"},
                        short_bio_en="I am ...")
bob = lp_model.new(name="Bob", blog="http://blog.example.com/",
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