from unittest import TestCase

from rdflib import ConjunctiveGraph, URIRef, RDF, BNode, Graph

from oldman import create_dataset
from oldman.iri import RandomFragmentIriGenerator
from oldman.exception import OMRequiredBaseIRIError
from oldman.rest.crud import CRUDController


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

dataset = create_dataset(schema_graph, default_graph)
crud_controller = CRUDController(dataset)
model = dataset.create_model("MyClass", context, iri_generator=RandomFragmentIriGenerator())


class DatatypeTest(TestCase):

    def tearDown(self):
        """ Clears the data graph """
        data_graph.update("CLEAR DEFAULT")
        model.objects.clear_cache()

    def test_generation(self):
        base_iri = "http://example.org/doc1"
        obj1 = model.new(base_iri=base_iri)
        self.assertEquals(obj1.base_iri, base_iri)
        self.assertTrue(base_iri in obj1.id)

        obj2 = model.objects.create(base_iri=base_iri)
        self.assertEquals(obj2.base_iri, base_iri)
        self.assertTrue(base_iri in obj2.id)
        self.assertNotEquals(obj1.id, obj2.id)

        with self.assertRaises(OMRequiredBaseIRIError):
            model.new()
        with self.assertRaises(OMRequiredBaseIRIError):
            model.new(base_iri="http://localhost/not#a-base-iri")

    def test_controller_put(self):
        base_iri = "http://example.org/doc2"
        g = Graph()
        g.add((BNode(), RDF.type, URIRef(EXAMPLE + "MyClass")))
        crud_controller.update(base_iri, g.serialize(format="turtle"), "turtle")

        obj_iri = dataset.model_registry.find_object_from_base_uri(base_iri)
        self.assertTrue(obj_iri is not None)
        self.assertTrue(base_iri in obj_iri)
        self.assertTrue('#' in obj_iri)

    def test_relative_iri(self):
        """
            No IRI generation here
        """
        ttl = """
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

        <#this> rdf:type <http://localhost/vocab#MyClass> .
        """
        base_iri = "http://example.org/doc3"
        crud_controller.update(base_iri, ttl, "turtle")
        obj_iri = dataset.model_registry.find_object_from_base_uri(base_iri)
        self.assertEquals(obj_iri, base_iri + "#this")