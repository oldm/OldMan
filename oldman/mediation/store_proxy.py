from oldman.session.tracker import BasicResourceTracker


class StoreProxy(object):
    """TODO: find a better name """

    def get(self, resource_factory, iri, types=None, eager_with_reversed_attributes=True):
        """TODO: explain

            :return a ClientResource
        """
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def filter(self, resource_tracker, resource_factory, types=None, hashless_iri=None, limit=None, eager=False,
               pre_cache_properties=None, **kwargs):
        """TODO: explain

            :return list of ClientResource ?
        """
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def first(self, resource_finder, resource_factory, types=None, hashless_iri=None, pre_cache_properties=None,
              eager_with_reversed_attributes=True, **kwargs):
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def sparql_filter(self, resource_finder, resource_factory, query):
        """TODO: explain

            :return list of ClientResource ?
        """
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def flush(self, resource_factory, client_resources_to_update, client_resources_to_delete, is_end_user):
        """TODO: explain

            :return list of the updated ClientResource ?
        """
        raise NotImplementedError("Should be implemented by a concrete implementation.")


class DefaultStoreProxy(StoreProxy):

    def __init__(self, store_selector, conversion_manager):
        self._store_selector = store_selector
        self._conversion_manager = conversion_manager

    def get(self, client_tracker, resource_factory, iri, types=None, eager_with_reversed_attributes=True):
        """TODO: explain

            TODO: also consider the client resource tracker.

            :return a ClientResource
        """
        for store in self._store_selector.select_stores(iri=iri, types=types):
            store_resource = store.get(iri, types=types, eager_with_reversed_attributes=eager_with_reversed_attributes)

            if store_resource is not None:
                return self._conversion_manager.convert_store_to_client_resource(store_resource, resource_factory,
                                                                                 client_tracker)
        return None

    def filter(self, resource_finder, resource_factory, types=None, hashless_iri=None, limit=None, eager=True,
               pre_cache_properties=None, **kwargs):
        """TODO: explain

            :return list of ClientResource ?
        """
        store_resources = [r for store in self._store_selector.select_stores(types=types, hashless_iri=hashless_iri,
                                                                             pre_cache_properties=pre_cache_properties,
                                                                             **kwargs)
                           for r in store.filter(types=types, hashless_iri=hashless_iri, limit=limit, eager=eager,
                                                 pre_cache_properties=pre_cache_properties, **kwargs)]
        client_resources = self._conversion_manager.convert_store_to_client_resources(store_resources, resource_finder,
                                                                                      resource_factory)
        return client_resources

    def first(self, client_tracker, resource_factory, types=None, hashless_iri=None, pre_cache_properties=None,
              eager_with_reversed_attributes=True, **kwargs):
        for store in self._store_selector.select_stores(types=types, hashless_iri=hashless_iri,
                                                        pre_cache_properties=pre_cache_properties, **kwargs):

            store_resource = store.first(types=types, hashless_iri=hashless_iri,
                                         pre_cache_properties=pre_cache_properties,
                                         eager_with_reversed_attributes=eager_with_reversed_attributes, **kwargs)
            if store_resource is not None:
                return self._conversion_manager.convert_store_to_client_resource(store_resource, resource_factory,
                                                                                 client_tracker=client_tracker)
        return None

    def sparql_filter(self, client_tracker, resource_factory, query):
        """TODO: explain

            :return list of ClientResource ?
        """
        store_resources = [r for store in self._store_selector.select_sparql_stores(query)
                           for r in store.sparql_filter(query)]
        client_resources = self._conversion_manager.convert_store_to_client_resources(store_resources, client_tracker,
                                                                                      resource_factory)
        return client_resources

    def flush(self, resource_factory, client_resources_to_update, client_resources_to_delete, is_end_user):
        """TODO: explain

            :return list of the new ClientResource ?
        """
        store_tracker = BasicResourceTracker()

        for resource in client_resources_to_delete:
            self._delete_resource(resource, store_tracker)

        for resource in client_resources_to_update:
            self._save_resource(resource, is_end_user, store_tracker)

        # TODO: return the new resources
        return []

    def _save_resource(self, client_resource, is_end_user, store_tracker):
        """TODO: refactor"""
        store = self._store_selector.select_store(client_resource, types=client_resource.types)
        store_resource = self._conversion_manager.convert_client_to_store_resource(client_resource, store,
                                                                                   store_tracker)
        store_resource.save(is_end_user)
        # previous_id = client_resource.id
        new_id = store_resource.id

        # Keeps track of the temporary IRI replacement
        # if previous_id != new_id:
        #    self._updated_iris[previous_id] = new_id
        client_resource.receive_storage_ack(new_id)

    def _delete_resource(self, client_resource, store_tracker):
        """TODO: refactor"""
        store = self._store_selector.select_store(client_resource, types=client_resource.types)
        store_resource = self._conversion_manager.convert_client_to_store_resource(client_resource, store,
                                                                                   store_tracker)
        store_resource.delete()
        client_resource.receive_deletion_notification_from_store()
