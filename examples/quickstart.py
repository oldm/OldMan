# -*- coding: utf-8 -*-
from rdflib import ConjunctiveGraph
from oldman import create_dataset

# In-memory main graph that will be divided into named sub-graphs
default_graph = ConjunctiveGraph()
# Graph containing all the schema RDF triples
schema_graph = default_graph.get_context("http://localhost/schema")

# Load the schema
schema_graph.parse("https://gitlab.bcgl.fr/benjamin/oldman/raw/master/examples/quickstart_schema.ttl", format="turtle")

context_iri = "https://gitlab.bcgl.fr/benjamin/oldman/raw/master/examples/quickstart_context.jsonld"

#Domain (will generate the model classes)
dataset = create_dataset(schema_graph, default_graph)

#LocalPerson model
lp_model = dataset.create_model("LocalPerson", context_iri, iri_prefix="http://localhost/persons/",
                               iri_fragment="me", incremental_iri=True)

# First object stored in the graph
alice = lp_model.objects.create(name="Alice", emails={"alice@example.org"}, short_bio_en="I am ...")
# Generated IRI
alice_iri = alice.id
print alice.id
print alice.name

# Second object
bob = lp_model.new(name="Bob", blog="http://blog.example.com/", short_bio_fr=u"J'ai grandi en ... .")
print bob.is_valid()
bob.emails = {"bob@localhost", "bob@example.org"}
print bob.is_valid()
bob.save()

# Declare friendship
alice.friends = {bob}
bob.friends = {alice}
alice.save()
bob.save()

#data_graph = default_graph
#data_graph = default_graph.default_context
#print data_graph.serialize(format="trig")

john_iri = "http://example.org/john#me"
john = lp_model.objects.create(id=john_iri, name="John", emails={"john@example.org"})
print john.id

#Clear the cache
#LocalPerson.objects.clear_cache()

#Reloads for the datastore
# First person found named Bob
bob = lp_model.objects.get(name="Bob")
alice = lp_model.objects.get(id=alice_iri)

# Or retrieve it as the unique friend of Bob
alice = list(bob.friends)[0]
print alice.name

print alice.to_json()
print alice.to_jsonld()
print bob.to_rdf("turtle")


# Validation (commented because generate errors)
# Email is required
#LocalPerson.objects.create(name="Jack")

#bob.emails = {'bad email address'}

# Schema
print schema_graph.serialize(format="turtle")

# Context (JSON-LD)
#TODO: get it