# -*- coding: utf-8 -*-
from rdflib import ConjunctiveGraph
from oldman import default_model_factory

# In-memory main graph that will be divided into named sub-graphs
default_graph = ConjunctiveGraph()
# Graph containing all the schema RDF triples
schema_graph = default_graph.get_context("http://localhost/schema")
# Graph containing all the data RDF triples
data_graph = default_graph.get_context("http://localhost/data")

# Load the schema
schema_graph.parse("https://gitlab.bcgl.fr/benjamin/oldman/raw/master/examples/quickstart_schema.ttl", format="turtle")

context_iri = "https://gitlab.bcgl.fr/benjamin/oldman/raw/master/examples/quickstart_context.jsonld"

#Model factory (will generate the model classes)
model_factory = default_model_factory(schema_graph, default_graph)

# Model class
LocalPerson = model_factory.generate("LocalPerson", context_iri, data_graph,
                                     iri_prefix="http://localhost/persons/", iri_fragment="me",
                                     incremental_iri=False)

# First object stored in the graph
alice = LocalPerson.objects.create(name="Alice", emails={"alice@example.org"}, short_bio_en="I am ...")
# Generated IRI
alice_iri = alice.id
print alice.id

# Second object
bob = LocalPerson(name="Bob", blog="http://blog.example.com/", short_bio_fr=u"J'ai grandi en ... .")
print bob.is_valid()
bob.emails = {"bob@localhost", "bob@example.org"}
print bob.is_valid()
bob.save()

# Declare friendship
alice.friends = {bob}
bob.friends = {alice}
alice.save()
bob.save()

print data_graph.serialize(format="turtle")

john_iri = "http://example.org/john#me"
john = LocalPerson.objects.create(id=john_iri, name="John", emails={"john@example.org"})
print john.id


#Clear the cache
LocalPerson.objects.clear_cache()

#Reloads for the datastore
# First person found named Bob
bob = LocalPerson.objects.get(name="Bob")
alice = LocalPerson.objects.get(id=alice_iri)

# Or retrieve it as the unique friend of Bob
alice = list(bob.friends)[0]
print alice.name

print alice.to_json()
print alice.to_jsonld()
print bob.to_rdf("turtle")


# Validation (commented because generate errors)
# Email is required
#LocalPerson.objects.create(name="Jack")

#bob.emails = {'not an email address'}

# Schema
print schema_graph.serialize(format="turtle")

# Context (JSON-LD)
#TODO: get it