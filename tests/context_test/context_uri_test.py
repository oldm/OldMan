import json
from unittest import TestCase
from os import path
from rdflib import Graph
from oldman import ClientResourceManager, parse_graph_safely, SPARQLDataStore

schema_graph = Graph()
my_class_def = {
    "@context": {
            "hydra": "http://www.w3.org/ns/hydra/core#",
    },
    "@id": "urn:test:vocab:MyClass",
    "@type": "hydra:Class",
    "hydra:supportedProperty": [
        {
            "hydra:property": "urn:test:vocab:isWorking"
        }
    ]

}
parse_graph_safely(schema_graph, data=json.dumps(my_class_def), format="json-ld")

context_file_path = path.join(path.dirname(__file__), "basic_context.jsonld")
context_iri = "/contexts/context.jsonld"

store = SPARQLDataStore(Graph(), schema_graph=schema_graph)
store.create_model("MyClass", context_iri, context_file_path=context_file_path)

client_manager = ClientResourceManager(store)
client_manager.import_store_models()
model = client_manager.get_model("MyClass")


class ContextUriTest(TestCase):

    def test_context_uri(self):
        obj = model.new(is_working=True)
        self.assertEquals(obj.context, context_iri)
        self.assertTrue(obj.is_working)
        print obj.to_dict()



