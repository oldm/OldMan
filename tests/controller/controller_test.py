from rdflib import Graph
from oldman import SPARQLDataStore, ResourceManager, parse_graph_safely
from os import path
import unittest

schema_graph = Graph()
schema_file = path.join(path.dirname(__file__), "controller-schema.ttl")
schema_graph = parse_graph_safely(schema_graph, schema_file , format="turtle")

context_file = path.join(path.dirname(__file__), "controller-context.jsonld")

data_graph = Graph()
data_store = SPARQLDataStore(data_graph)

manager = ResourceManager(schema_graph, data_store)

collection_model = manager.create_model("Collection", context_file, iri_prefix="http://localhost/collections/",
                                        incremental_iri=True)
item_model = manager.create_model("Item", context_file, iri_prefix="http://localhost/items/",
                                  incremental_iri=True)

collection1 = collection_model.create()


class ControllerTest(unittest.TestCase):

    def test_operation(self):
        operation = collection1.get_operation("POST")
        self.assertTrue(operation is not None)

        title = u"First item"
        item = item_model.new(title=title)
        item_graph = Graph().parse(data=item.to_rdf(rdf_format="nt"), format="nt")
        print item_graph.serialize(format="turtle")
        item_iri = item.id
        operation(collection1, graph=item_graph)

        print data_graph.serialize(format="turtle")

        item = manager.get(id=item_iri)
        self.assertTrue(item is not None)
        # We do not update existing objects like this (with already an IRI). TODO: improve this
        #self.assertEquals(item.title, None)