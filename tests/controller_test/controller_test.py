from os import path
import unittest

from rdflib import Graph

from oldman import SparqlStoreProxy, create_mediator, parse_graph_safely, Context
from oldman.client.rest.controller import HTTPController

schema_graph = Graph()
schema_file = path.join(path.dirname(__file__), "controller-schema.ttl")
schema_graph = parse_graph_safely(schema_graph, schema_file, format="turtle")

context = Context("file://" + path.join(path.dirname(__file__), "controller-context.jsonld"))
contexts = {
    "Collection": context,
    "Item": context
}

data_graph = Graph()

mediator = create_mediator(schema_graph, contexts)

collection_model = mediator.get_model("Collection")
item_model = mediator.get_model("Item")

# TODO: update these 3 lines
store_proxy = SparqlStoreProxy(data_graph, schema_graph=schema_graph)
store_proxy.create_model("Collection", context, iri_prefix="http://localhost/collections/",
                         incremental_iri=True)
store_proxy.create_model("Item", context, iri_prefix="http://localhost/items/")

mediator.bind_store(store_proxy, collection_model)
mediator.bind_store(store_proxy, item_model)

controller = HTTPController(mediator)

collection1_iri = u"http://localhost/collection1"


class ControllerTest(unittest.TestCase):

    def setUp(self):
        initial_session = mediator.create_session()
        collection_model.new(initial_session, iri=collection1_iri)
        initial_session.flush()
        initial_session.close()

    def tearDown(self):
        data_graph.update("CLEAR DEFAULT")

    def test_operation(self):
        """TODO: remove """
        session1 = mediator.create_session()
        collection1 = session1.get(collection1_iri)

        operation = collection1.get_operation("POST")
        self.assertTrue(operation is not None)

        title = u"First item"
        item = item_model.new(session1, title=title)
        session1.flush()

        #item_graph = Graph().parse(data=item.to_rdf(rdf_format="nt"), format="nt")
        #print item_graph.serialize(format="turtle")
        item_iri = item.id.iri
        operation(collection1, new_resources=[item])

        session1.flush()
        session1.close()

        print data_graph.serialize(format="turtle")

        session2 = mediator.create_session()
        item = session2.get(iri=item_iri)
        self.assertTrue(item is not None)
        self.assertEquals(item.title, title)
        session2.close()

    def test_normal_append_item(self):

        session1 = mediator.create_session()
        collection1 = session1.get(collection1_iri)

        #TODO: test mutiple formats

        title = u"Append test"
        item = item_model.new(session1, title=title)
        self.assertTrue(item.id.is_blank_node)

        payloads = {}
        payloads["application/ld+json"] = item.to_jsonld()
        payloads["application/json"] = item.to_json()
        payloads["text/turtle"] = item.to_rdf("turtle")

        for content_type in payloads:

            controller.post(collection1.id.iri, content_type, payloads[content_type])
            #TODO: retrieve the IRI of the newly created resource

            session2 = mediator.create_session()
            items = list(item_model.filter(session2, title=title))
            self.assertEquals(len(items), 1)
            retrieved_item = items[0]
            self.assertEquals(retrieved_item.title, title)
            self.assertFalse(retrieved_item.is_blank_node())
            print retrieved_item.id.iri

            #TODO: test the member part
            session2.delete(retrieved_item)
            session2.flush()
            session2.close()
        session1.close()

    def forbid_putting_new_resource_test(self):
        #TODO: implement it
        pass





