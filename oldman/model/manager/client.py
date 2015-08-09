from oldman.model.client import ClientModel
from oldman.model.manager.manager import ModelManager


class ClientModelManager(ModelManager):
    """Client ModelManager.

    In charge of the conversion between and store and client models.
    """

    def import_model(self, store_model, is_default=False):
        """ Imports a store model. Creates the corresponding client model. """
        if is_default:
            # Default model
            client_model = self.get_model(None)
        else:
            client_model = ClientModel.copy_store_model(store_model)
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
                           operations, local_context, accept_new_blank_nodes=False):
        return ClientModel(class_name_or_iri, class_iri, ancestry.bottom_up,
                           context_iri_or_payload, om_attributes, operations=operations,
                           local_context=local_context, accept_new_blank_nodes=accept_new_blank_nodes)


