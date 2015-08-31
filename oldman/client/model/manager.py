from oldman.client.hydra.operation import append_to_hydra_collection, append_to_hydra_paged_collection
from oldman.client.model.model import ClientModel
from oldman.core.model.ancestry import ClassAncestry
from oldman.core.model.manager import ModelManager
from oldman.core.vocabulary import HYDRA_COLLECTION_IRI, HTTP_POST, HYDRA_PAGED_COLLECTION_IRI


class ClientModelManager(ModelManager):
    """Client ModelManager.

    In charge of the conversion between and store and client models.
    """

    def __init__(self, oper_extractor, declare_default_operation_functions=True, **kwargs):
        ModelManager.__init__(self, **kwargs)

        self._operation_extractor = oper_extractor
        if declare_default_operation_functions:
            self.declare_operation_function(append_to_hydra_collection, HYDRA_COLLECTION_IRI, HTTP_POST)
            self.declare_operation_function(append_to_hydra_paged_collection, HYDRA_PAGED_COLLECTION_IRI, HTTP_POST)

    def import_model(self, store_model, is_default=False, store_schema_graph=None):
        """ Imports a store model. Creates the corresponding client model. """
        if is_default:
            # Default model
            client_model = self.get_model(None)
        else:
            schema_graph = self.schema_graph if self.schema_graph is not None else store_schema_graph
            if schema_graph is None:
                raise ValueError("No store_schema_graph given with no local schema_graph is available")

            ancestry = ClassAncestry(store_model.class_iri, schema_graph)
            operations = self._operation_extractor.extract(ancestry, schema_graph, self._operation_functions)

            client_model = ClientModel.copy_store_model(store_model, operations)
            # Hierarchy registration
            self._registry.register(client_model, is_default=False)
        return client_model

    def create_model(self, class_name_or_iri, context_iri_or_payload, untyped=False,
                     is_default=False, context_file_path=None, accept_new_blank_nodes=False):
        """TODO: describe """
        return self._create_model(class_name_or_iri, context_iri_or_payload, untyped=untyped,
                                  is_default=is_default, context_file_path=context_file_path,
                                  accept_new_blank_nodes=accept_new_blank_nodes)

    def _instantiate_model(self, class_name_or_iri, class_iri, ancestry, context_iri_or_payload, om_attributes,
                           local_context, accept_new_blank_nodes=False):
        operations = self._operation_extractor.extract(ancestry, self._schema_graph, self._operation_functions)

        return ClientModel(class_name_or_iri, class_iri, ancestry.bottom_up,
                           context_iri_or_payload, om_attributes, operations=operations,
                           local_context=local_context, accept_new_blank_nodes=accept_new_blank_nodes)


