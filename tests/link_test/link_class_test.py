from unittest import TestCase
from os.path import join, dirname

from rdflib import Graph

from oldman import SparqlStoreProxy
from oldman.storage.hydra.schema_adapter import HydraSchemaAdapter


class LinkClassTest(TestCase):

    def setUp(self):
        self.schema_graph = Graph().parse(join(dirname(__file__), "vocab.jsonld"), format="json-ld")
        # print self.schema_graph.serialize(format="turtle")
        #self.store = SPARQLDataStore(Graph(), schema_graph=self.schema_graph)

    def test(self):
        hydra_adapter = HydraSchemaAdapter()
        self.schema_graph = hydra_adapter.update_schema_graph(self.schema_graph)
        print self.schema_graph.serialize(format="turtle")

        self.assertTrue(self.schema_graph.query(
            """ASK {
                ?c rdfs:subClassOf <http://www.w3.org/ns/hydra/core#Collection> ;
                   <http://www.w3.org/ns/hydra/core#supportedOperation> ?op .
            }"""))

        self.store = SparqlStoreProxy(Graph(), schema_graph=self.schema_graph)
