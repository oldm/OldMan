from copy import deepcopy
from unittest import TestCase
from os.path import dirname, join
from rdflib import Graph
from oldman import SPARQLDataStore, create_user_mediator
from oldman.exception import OMAttributeTypeCheckError, OMAlreadyDeclaredDatatypeError

NO_PROPERTY_CONTEXT_DICT = {
    "@context": {
        "test": "urn:test:vocab:",
        "hydra": "http://www.w3.org/ns/hydra/core#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "MyClass": "test:MyClass",
    }
}


class RangeTest(TestCase):

    def setUp(self):
        self.schema_graph = Graph().parse(join(dirname(__file__), "vocab.jsonld"), format="json-ld")
        print self.schema_graph.serialize(format="turtle")
        self.store = SPARQLDataStore(Graph(), schema_graph=self.schema_graph)

    def test_no_property_context(self):
        self.store.create_model("MyClass", NO_PROPERTY_CONTEXT_DICT)
        user_mediator = create_user_mediator(self.store)
        user_mediator.import_store_models()
        model = user_mediator.get_client_model("MyClass")

        obj = model.new(test_hasX=2)

        with self.assertRaises(OMAttributeTypeCheckError):
            obj.test_hasX = "not a number"

    def test_no_datatype_context(self):
        context = deepcopy(NO_PROPERTY_CONTEXT_DICT)
        context["@context"]["hasX"] = "test:hasX"
        self.store.create_model("MyClass", context)
        user_mediator = create_user_mediator(self.store)
        user_mediator.import_store_models()
        model = user_mediator.get_client_model("MyClass")

        obj = model.new(hasX=2)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.hasX = "not a number"

    def test_conflicting_datatype_context(self):
        context = deepcopy(NO_PROPERTY_CONTEXT_DICT)
        context["@context"]["hasX"] = {
            "@id": "test:hasX",
            # Not an int
            "@type": "xsd:string"
        }
        with self.assertRaises(OMAlreadyDeclaredDatatypeError):
            self.store.create_model("MyClass", context)

    def test_complete_context(self):
        context = deepcopy(NO_PROPERTY_CONTEXT_DICT)
        context["@context"]["hasX"] = {
            "@id": "test:hasX",
            "@type": "xsd:int"
        }
        self.store.create_model("MyClass", context)
        user_mediator = create_user_mediator(self.store)
        user_mediator.import_store_models()
        model = user_mediator.get_client_model("MyClass")

        obj = model.new(hasX=2)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.hasX = "not a number"






