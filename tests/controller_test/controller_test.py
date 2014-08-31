from rdflib import Graph
from oldman import SPARQLDataStore, ResourceManager, parse_graph_safely
from oldman.rest.controller import HTTPController
from os import path
import unittest

schema_graph = Graph()
schema_file = path.join(path.dirname(__file__), "controller-schema.ttl")
schema_graph = parse_graph_safely(schema_graph, schema_file , format="turtle")

context_file = path.join(path.dirname(__file__), "controller-context.jsonld")

data_graph = Graph()
data_store = SPARQLDataStore(data_graph)

manager = ResourceManager(schema_graph, data_store, manager_name="controller_test")

collection_model = manager.create_model("Collection", context_file, iri_prefix="http://localhost/collections/",
                                        incremental_iri=True)
item_model = manager.create_model("Item", context_file, iri_prefix="http://localhost/items/",
                                  incremental_iri=True)

collection1 = collection_model.create()

controller = HTTPController(manager)


class ControllerTest(unittest.TestCase):

    def test_operation(self):
        """TODO: remove """
        operation = collection1.get_operation("POST")
        self.assertTrue(operation is not None)

        title = u"First item"
        item = item_model.new(title=title)
        #item_graph = Graph().parse(data=item.to_rdf(rdf_format="nt"), format="nt")
        #print item_graph.serialize(format="turtle")
        item_iri = item.id
        operation(collection1, new_resources=[item])

        print data_graph.serialize(format="turtle")

        item = manager.get(id=item_iri)
        self.assertTrue(item is not None)
        self.assertEquals(item.title, title)

    def test_normal_append_item(self):

        #TODO: test mutiple formats

        title = u"Append test"
        # Skolem IRI that should not be serialized
        skolem_iri = "http://localhost/.well-known/genid/3832"
        item = item_model.new(id=skolem_iri, title=title)

        payloads = {}
        payloads["application/ld+json"] = item.to_jsonld()
        payloads["application/json"] = item.to_json()
        payloads["text/turtle"] = item.to_rdf("turtle")


        for content_type in payloads:

            controller.post(collection1.id, content_type, payloads[content_type])
            #TODO: retrieve the IRI of the newly created resource

            items = list(item_model.filter(title=title))
            self.assertEquals(len(items), 1)
            retrieved_item = items[0]
            self.assertEquals(retrieved_item.title, title)
            self.assertNotEquals(retrieved_item.id, skolem_iri)
            print retrieved_item.id

            #TODO: test the member part
            retrieved_item.delete()

    def forbid_putting_new_resource_test(self):
        #TODO: implement it
        pass





