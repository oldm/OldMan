from os import path
from unittest import TestCase
from rdflib import Graph
from oldman import HttpStore, create_mediator, parse_graph_safely

directory = path.dirname(__file__)
schema_graph = parse_graph_safely(Graph(), path.join(directory, 'api_schema.ttl'), format="turtle")
schema_graph.namespace_manager.bind("hydra", "http://www.w3.org/ns/hydra/core#")

context_uri = path.join(directory, 'api_documentation.json')

data_store = HttpStore(schema_graph=schema_graph)
data_store.create_model('ApiDocumentation', context_uri)

user_mediator = create_mediator(data_store)
user_mediator.import_store_models()

doc_model = user_mediator.get_client_model('ApiDocumentation')


class HttpStoreTest(TestCase):
    def test_get(self):
        iri = u"http://www.markus-lanthaler.com/hydra/api-demo/vocab"

        session = user_mediator.create_session()

        doc = doc_model.get(session, iri=iri)
        self.assertTrue(doc is not None)
        self.assertEquals(doc.id.iri, iri)
        expected_classes = {u'http://www.markus-lanthaler.com/hydra/api-demo/vocab#User',
                            u'http://www.w3.org/ns/hydra/core#Collection',
                            u'http://www.w3.org/ns/hydra/core#Resource',
                            u'http://www.markus-lanthaler.com/hydra/api-demo/vocab#Comment',
                            u'http://www.markus-lanthaler.com/hydra/api-demo/vocab#EntryPoint',
                            u'http://www.markus-lanthaler.com/hydra/api-demo/vocab#Issue'}
        # Gets just the IRIs, not the Resource objects
        supported_classes = doc.get_lightly("supported_classes")
        for cls in expected_classes:
            self.assertIn(cls, supported_classes, "Unsupported class: %s (supported: %s)" % (cls, supported_classes))
