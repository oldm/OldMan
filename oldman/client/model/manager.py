from rdflib import RDF, URIRef

from oldman.client.hydra.operation import append_to_hydra_collection, append_to_hydra_paged_collection
from oldman.client.model.model import ClientModel
from oldman.core.model.manager import ModelManager, extract_class_iri
from oldman.core.vocabulary import HYDRA_COLLECTION_IRI, HTTP_POST, HYDRA_PAGED_COLLECTION_IRI

DEFAULT_MODEL_NAME = "Default_Client"


class ClientModelManager(ModelManager):
    """Client ModelManager.

    In charge of the conversion between and store and client models.
    """

    def __init__(self, schema_graph, contexts, oper_extractor, declare_default_operation_functions=True, **kwargs):
        ModelManager.__init__(self, **kwargs)

        self._operation_extractor = oper_extractor
        if declare_default_operation_functions:
            self.declare_operation_function(append_to_hydra_collection, HYDRA_COLLECTION_IRI, HTTP_POST)
            self.declare_operation_function(append_to_hydra_paged_collection, HYDRA_PAGED_COLLECTION_IRI, HTTP_POST)

        class_iris = extract_class_iris(schema_graph)
        class_names = index_class_names_by_iri(contexts)

        # TODO: make sure that _create_model also receive the class_iri
        for class_iri in class_iris:
            class_name_or_iri = class_names[class_iri]
            self._create_model(class_name_or_iri, contexts[class_name_or_iri], schema_graph)

        # Default model
        # TODO: remove it?
        self.create_model(DEFAULT_MODEL_NAME, {u"@context": {}}, untyped=True, is_default=True,
                          accept_new_blank_nodes=True)

    # def import_model(self, store_model, is_default=False, store_schema_graph=None):
    #     """ Imports a store model. Creates the corresponding client model. """
    #     if is_default:
    #         # Default model
    #         client_model = self.get_model(None)
    #     else:
    #         schema_graph = self.schema_graph if self.schema_graph is not None else store_schema_graph
    #         if schema_graph is None:
    #             raise ValueError("No store_schema_graph given with no local schema_graph is available")
    #
    #         ancestry = ClassAncestry(store_model.class_iri, schema_graph)
    #         operations = self._operation_extractor.extract(ancestry, schema_graph, self._operation_functions)
    #
    #         client_model = ClientModel.copy_store_model(store_model, operations)
    #         # Hierarchy registration
    #         self._registry.register(client_model, is_default=False)
    #     return client_model

    def create_model(self, class_name_or_iri, context, schema_graph=None, untyped=False,
                     is_default=False, accept_new_blank_nodes=False):
        """TODO: describe """
        return self._create_model(class_name_or_iri, context, schema_graph, untyped=untyped,
                                  is_default=is_default, accept_new_blank_nodes=accept_new_blank_nodes)

    def _instantiate_model(self, class_name_or_iri, class_iri, schema_graph, ancestry, context,
                           om_attributes, accept_new_blank_nodes=False):
        operations = self._operation_extractor.extract(ancestry, schema_graph, self._operation_functions)

        return ClientModel(class_name_or_iri, class_iri, ancestry.bottom_up,context, om_attributes,
                           operations=operations, accept_new_blank_nodes=accept_new_blank_nodes)


def extract_class_iris(schema_graph):
    return [unicode(c) for c in schema_graph.subjects(RDF["type"], URIRef("http://www.w3.org/ns/hydra/core#Class"))]


def index_class_names_by_iri(contexts):
    # TODO: make is more efficient
    return {
        extract_class_iri(class_iri_or_name, context): class_iri_or_name
        for class_iri_or_name, context in contexts.iteritems()
        }

