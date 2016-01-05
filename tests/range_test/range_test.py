from copy import deepcopy
from unittest import TestCase
from os.path import dirname, join

from rdflib import Graph

from oldman import SparqlStoreProxy, create_mediator, Context
from oldman.core.exception import OMAttributeTypeCheckError, OMAlreadyDeclaredDatatypeError

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
        self.store_proxy = SparqlStoreProxy(Graph(), schema_graph=self.schema_graph)

    def test_no_property_context(self):
        context = Context(NO_PROPERTY_CONTEXT_DICT)
        mediator = create_mediator(self.schema_graph, {"MyClass": context})
        model = mediator.get_model("MyClass")

        self.store_proxy.create_model("MyClass", context)
        mediator.bind_store(self.store_proxy, model)

        session = mediator.create_session()
        obj = model.new(session, test_hasX=2)

        with self.assertRaises(OMAttributeTypeCheckError):
            obj.test_hasX = "not a number"

    def test_no_datatype_context(self):
        context_payload = deepcopy(NO_PROPERTY_CONTEXT_DICT)
        context_payload["@context"]["hasX"] = "test:hasX"
        context = Context(context_payload)

        self.store_proxy.create_model("MyClass", context)
        mediator = create_mediator(self.schema_graph, {"MyClass": context})
        model = mediator.get_model("MyClass")

        session = mediator.create_session()
        obj = model.new(session, hasX=2)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.hasX = "not a number"

    def test_conflicting_datatype_context(self):
        context_payload = deepcopy(NO_PROPERTY_CONTEXT_DICT)
        context_payload["@context"]["hasX"] = {
            "@id": "test:hasX",
            # Not an int
            "@type": "xsd:string"
        }
        with self.assertRaises(OMAlreadyDeclaredDatatypeError):
            self.store_proxy.create_model("MyClass", Context(context_payload))

    def test_complete_context(self):
        context_payload = deepcopy(NO_PROPERTY_CONTEXT_DICT)
        context_payload["@context"]["hasX"] = {
            "@id": "test:hasX",
            "@type": "xsd:int"
        }
        context = Context(context_payload)
        self.store_proxy.create_model("MyClass", context)
        mediator = create_mediator(self.schema_graph, {"MyClass": context})
        model = mediator.get_model("MyClass")

        session = mediator.create_session()
        obj = model.new(session, hasX=2)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.hasX = "not a number"






