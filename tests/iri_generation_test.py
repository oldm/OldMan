from unittest import TestCase

from rdflib import ConjunctiveGraph, URIRef, RDF, BNode, Graph

from ld_orm import default_model_factory
from ld_orm.iri import RandomFragmentIriGenerator
from ld_orm.exceptions import RequiredBaseIRIError
from ld_orm.rest.crud import CRUDController


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

model_generator = default_model_factory(schema_graph, default_graph)
crud_controller = CRUDController(model_generator.registry)
MyClass = model_generator.generate("MyClass", context, data_graph,
                                   uri_generator=RandomFragmentIriGenerator())


class DatatypeTest(TestCase):

    def tearDown(self):
        """ Clears the data graph """
        data_graph.update("CLEAR DEFAULT")
        MyClass.objects.clear_cache()

    def test_generation(self):
        base_iri = "http://example.org/doc1"
        obj1 = MyClass(base_iri=base_iri)
        self.assertEquals(obj1.base_iri, base_iri)
        self.assertTrue(base_iri in obj1.id)

        obj2 = MyClass.objects.create(base_iri=base_iri)
        self.assertEquals(obj2.base_iri, base_iri)
        self.assertTrue(base_iri in obj2.id)
        self.assertNotEquals(obj1.id, obj2.id)

        with self.assertRaises(RequiredBaseIRIError):
            MyClass()
        with self.assertRaises(RequiredBaseIRIError):
            MyClass(base_iri="http://localhost/not#a-base-iri")

    def test_controller_put(self):
        base_iri = "http://example.org/doc2"
        g = Graph()
        g.add((BNode(), RDF.type, URIRef(EXAMPLE + "MyClass")))
        crud_controller.update(base_iri, g.serialize(format="turtle"), "turtle")

        obj_iri = model_generator.registry.find_object_from_base_uri(base_iri)
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
        obj_iri = model_generator.registry.find_object_from_base_uri(base_iri)
        self.assertEquals(obj_iri, base_iri + "#this")