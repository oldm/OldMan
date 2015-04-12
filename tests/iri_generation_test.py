from unittest import TestCase

from rdflib import ConjunctiveGraph, URIRef, RDF, BNode, Graph

from oldman import create_user_mediator, SparqlStore
from oldman.iri.generator import UUIDFragmentIriGenerator
from oldman.exception import OMRequiredHashlessIRIError
from oldman.rest.crud import HashLessCRUDer


EXAMPLE = "http://localhost/vocab#"
HYDRA = "http://www.w3.org/ns/hydra/core#"

default_graph = ConjunctiveGraph()
schema_graph = default_graph.get_context(URIRef("http://localhost/schema"))
data_graph = default_graph.get_context(URIRef("http://localhost/data"))

# Declaration (no attribute)
schema_graph.add((URIRef(EXAMPLE + "MyClass"), RDF.type, URIRef(HYDRA + "Class")))

context = {
    "@context": {
        "ex": EXAMPLE,
        "id": "@id",
        "type": "@type",
        "MyClass": "ex:MyClass",
    }
}

data_store = SparqlStore(data_graph, schema_graph=schema_graph)
data_store.create_model("MyClass", context, iri_generator=UUIDFragmentIriGenerator())

user_mediator = create_user_mediator(data_store)
user_mediator.import_store_models()
crud_controller = HashLessCRUDer(user_mediator)
model = user_mediator.get_client_model("MyClass")


class HashlessIriTest(TestCase):

    def tearDown(self):
        """ Clears the data graph """
        data_graph.update("CLEAR DEFAULT")

    def test_generation(self):
        hashless_iri = "http://example.org/doc1"
        obj1 = model.create(hashless_iri=hashless_iri)
        self.assertEquals(obj1.hashless_iri, hashless_iri)
        self.assertTrue(hashless_iri in obj1.id)

        obj2 = model.create(hashless_iri=hashless_iri)
        self.assertEquals(obj2.hashless_iri, hashless_iri)
        self.assertTrue(hashless_iri in obj2.id)
        self.assertNotEquals(obj1.id, obj2.id)

        with self.assertRaises(OMRequiredHashlessIRIError):
            model.new()
        with self.assertRaises(OMRequiredHashlessIRIError):
            model.new(hashless_iri="http://localhost/not#a-base-iri")

    def test_controller_put(self):
        hashless_iri = "http://example.org/doc2"
        g = Graph()
        g.add((BNode(), RDF.type, URIRef(EXAMPLE + "MyClass")))
        crud_controller.update(hashless_iri, g.serialize(format="turtle"), "turtle")

        resource = user_mediator.get(hashless_iri=hashless_iri)
        self.assertTrue(resource is not None)
        self.assertTrue(hashless_iri in resource.id)
        self.assertTrue('#' in resource.id)

    def test_relative_iri(self):
        """
            No IRI generation here
        """
        ttl = """
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

        <#this> rdf:type <http://localhost/vocab#MyClass> .
        """
        hashless_iri = "http://example.org/doc3"
        crud_controller.update(hashless_iri, ttl, "turtle", allow_new_type=True)
        resource = user_mediator.get(hashless_iri=hashless_iri)
        self.assertEquals(resource.id, hashless_iri + "#this")