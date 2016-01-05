from os import path
from unittest import TestCase
from rdflib import Graph
from oldman import HttpStoreProxy, create_mediator, parse_graph_safely, Context

directory = path.dirname(__file__)
schema_graph = parse_graph_safely(Graph(), path.join(directory, 'api_schema.ttl'), format="turtle")
schema_graph.namespace_manager.bind("hydra", "http://www.w3.org/ns/hydra/core#")

context = Context(path.join(directory, 'api_documentation.json'))

mediator = create_mediator(schema_graph, {'ApiDocumentation': context})
doc_model = mediator.get_model('ApiDocumentation')

store_proxy = HttpStoreProxy(schema_graph=schema_graph)
store_proxy.create_model('ApiDocumentation', context)

mediator.bind_store(store_proxy, doc_model)


class HttpStoreTest(TestCase):
    def test_get(self):
        iri = u"http://www.markus-lanthaler.com/hydra/api-demo/vocab"

        session = mediator.create_session()

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
