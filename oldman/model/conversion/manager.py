import types
from oldman.resource.client import ClientResource
from oldman.resource.store import StoreResource


class ModelConversionManager(object):
    """TODO: describe and find a better name."""

    def __init__(self):
        # { (client_model, data_store): store_model }
        self._client_to_store_models = {}
        # { store_model: client_model
        self._store_to_client_models = {}
        # { (client_model, store_model): converter}
        self._converters = {}

    def register_model_converter(self, client_model, store_model, data_store, model_converter):
        self._client_to_store_models[(client_model, data_store)] = store_model
        self._store_to_client_models[store_model] = client_model
        self._converters[(client_model, store_model)] = model_converter

    def convert_store_to_client_resources(self, store_resources, resource_finder, resource_factory):
        """TODO: describe """
        if isinstance(store_resources, types.GeneratorType):
            return (self.convert_store_to_client_resource(r, resource_factory, client_tracker=resource_finder)
                    for r in store_resources)
        # Otherwise, returns a list
        return [self.convert_store_to_client_resource(r, resource_factory, client_tracker=resource_finder)
                for r in store_resources]

    def convert_store_to_client_resource(self, store_resource, client_factory, client_tracker,
                                         update_local_client_resource=False):
        """
        :param store_resource:
        :param client_factory:
        :param client_tracker:
        :param update_local_client_resource: FOR OTHER updates than the IRI!
        :return:
        """
        client_former_types, client_new_types = self._extract_types_from_store_resource(store_resource)

        iri = store_resource.id.iri
        client_resource = None
        # Looks first for a local client resource
        if client_tracker is not None:
            client_resource = client_tracker.find(iri)
            if client_resource is not None:
                if not update_local_client_resource:
                    return client_resource
                else:
                    raise NotImplementedError("TODO: analyze what we should update local client resources after"
                                              "calling a filter")

        # If no local client resource
        if client_resource is None:
            # Mutable
            client_resource = client_factory.new_resource(iri=iri, types=client_new_types,
                                                            is_new=store_resource.is_new,
                                                            former_types=client_former_types)

        store = store_resource.store

        # Client models from the most general to the more specific
        client_models = list(client_resource.models)
        client_models.reverse()
        for client_model in client_models:
            # Corresponding store model
            store_model = self._client_to_store_models.get((client_model, store))
            if store_model is None:
                # TODO: find a better exception
                raise Exception("No store model associate to %s" % client_model.name)

            converter = self._converters[(client_model, store_model)]

            # Update the client resource according to the model properties
            converter.from_store_to_client(store_resource, client_resource, self, client_tracker, client_factory)

        return client_resource

    def convert_client_to_store_resource(self, client_resource, store, xstore_session):
        """TODO: explain """
        store_former_types, store_new_types = self._extract_types_from_client_resource(client_resource, store)

        client_id = client_resource.id
        store_resource = xstore_session.new(client_id, store, types=store_new_types, is_new=client_resource.is_new,
                                            former_types=store_former_types)

        # From the most general to the more specific
        store_models = list(store_resource.models)
        store_models.reverse()

        for store_model in store_models:
            client_model = self._store_to_client_models.get(store_model)
            if client_model is None:
                # TODO: find a better exception
                raise Exception("No client model associate to %s" % store_model.name)

            converter = self._converters[(client_model, store_model)]

            # Update the client resource according to the model properties
            converter.from_client_to_store(client_resource, store_resource, self, xstore_session)

        return store_resource

    def _extract_types_from_store_resource(self, store_resource):
        # Non model types
        new_types = set(store_resource.non_model_types)
        former_types = set(store_resource.former_non_model_types)

        for store_model in store_resource.models:
            client_model = self._store_to_client_models.get(store_model)
            if client_model is None:
                # TODO: See if relevant and find a better name
                raise Exception("No client model corresponding to %s" % store_model.name)

            client_model_type = client_model.class_iri
            if store_model.class_iri in store_resource.former_types:
                former_types.add(client_model_type)
            if client_model_type is not None:
                new_types.add(client_model_type)

        return former_types, new_types

    def _extract_types_from_client_resource(self, client_resource, store):
        # Non model types
        new_types = set(client_resource.non_model_types)
        former_types = set(client_resource.former_non_model_types)

        # Types corresponding to models
        for client_model in client_resource.models:
            store_model = self._client_to_store_models.get((client_model, store))
            if store_model is None:
                # TODO: See if relevant and find a better name
                raise Exception("No store model corresponding to %s" % client_model.name)

            store_model_type = store_model.class_iri
            if client_model.class_iri in client_resource.former_types:
                former_types.add(store_model_type)
            new_types.add(store_model_type)

        return former_types, new_types
