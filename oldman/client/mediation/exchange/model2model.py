from oldman.client.mediation.exchange.broker import Broker
from oldman.storage.session import DefaultCrossStoreSession


class Model2ModelBroker(Broker):

    def __init__(self, store_selector, conversion_manager):
        self._store_selector = store_selector
        self._conversion_manager = conversion_manager

    def get(self, client_tracker, resource_factory, iri, types=None, eager_with_reversed_attributes=True):
        """TODO: explain

            TODO: also consider the client resource tracker.

            :return a ClientResource
        """
        xstore_session = self._create_session()
        store_resource = xstore_session.get(iri, types=types,
                                            eager_with_reversed_attributes=eager_with_reversed_attributes)
        if store_resource is not None:
            store_resource = self._conversion_manager.convert_store_to_client_resource(store_resource, resource_factory,
                                                                                       client_tracker)
        return store_resource

    def filter(self, resource_finder, resource_factory, types=None, hashless_iri=None, limit=None, eager=True,
               pre_cache_properties=None, **kwargs):
        """TODO: explain

            :return list of ClientResource ?
        """
        xstore_session = self._create_session()
        store_resources = [r for store in self._store_selector.select_stores(types=types, hashless_iri=hashless_iri,
                                                                             pre_cache_properties=pre_cache_properties,
                                                                             **kwargs)
                           for r in store.filter(xstore_session, types=types, hashless_iri=hashless_iri, limit=limit,
                                                 eager=eager, pre_cache_properties=pre_cache_properties, **kwargs)]
        client_resources = self._conversion_manager.convert_store_to_client_resources(store_resources, resource_finder,
                                                                                      resource_factory)
        xstore_session.close()
        return client_resources

    def first(self, client_tracker, resource_factory, types=None, hashless_iri=None, pre_cache_properties=None,
              eager_with_reversed_attributes=True, **kwargs):

        session = self._create_session()
        for store in self._store_selector.select_stores(types=types, hashless_iri=hashless_iri,
                                                        pre_cache_properties=pre_cache_properties, **kwargs):

            store_resource = store.first(session, types=types, hashless_iri=hashless_iri,
                                         pre_cache_properties=pre_cache_properties,
                                         eager_with_reversed_attributes=eager_with_reversed_attributes, **kwargs)
            if store_resource is not None:
                client_resource = self._conversion_manager.convert_store_to_client_resource(store_resource,
                                                                                            resource_factory,
                                                                                            client_tracker=client_tracker)
                session.close()
                return client_resource

        session.close()
        return None

    def sparql_filter(self, client_tracker, resource_factory, query):
        """TODO: explain

            :return list of ClientResource ?
        """
        store_session = self._create_session()
        store_resources = [r for store in self._store_selector.select_sparql_stores(query)
                           for r in store.sparql_filter(store_session, query)]
        client_resources = self._conversion_manager.convert_store_to_client_resources(store_resources, client_tracker,
                                                                                      resource_factory)
        store_session.close()
        return client_resources

    def flush(self, resource_factory, client_resources_to_update, client_resources_to_delete, is_end_user):
        """TODO: explain

            :return list of the new ClientResource ?
        """
        xstore_session = self._create_session()

        store_to_client_resources = {}

        for client_resource in client_resources_to_update:
            store = self._store_selector.select_store(client_resource, types=client_resource.types)
            # TODO: make sure the mapping between client and store resources are kept
            store_resource = self._conversion_manager.convert_client_to_store_resource(client_resource, store,
                                                                                       xstore_session)
            store_to_client_resources[store_resource] = client_resource

        store_resources_to_delete = []
        for client_resource in client_resources_to_delete:
            store = self._store_selector.select_store(client_resource, types=client_resource.types)
            store_resource = self._conversion_manager.convert_client_to_store_resource(client_resource, store,
                                                                                       xstore_session)
            store_resources_to_delete.append(store_resource)
            store_to_client_resources[store_resource] = client_resource

        for store_resource in store_resources_to_delete:
            # Mark as to be deleted
            xstore_session.delete(store_resource)

        updated_store_resources, deleted_store_resources = xstore_session.flush(is_end_user=is_end_user)
        updated_client_resources = self._update_client_resources(store_to_client_resources, updated_store_resources)
        deleted_client_resources = self._update_deleted_client_resources(store_to_client_resources,
                                                                         deleted_store_resources)

        # TODO: should we append it HERE to the client_tracker/client_session?
        return updated_client_resources, deleted_client_resources

    @staticmethod
    def _update_client_resources(store_to_client_resources, updated_store_resources):
        updated_client_resources = []
        for store_resource in updated_store_resources:
            client_resource = store_to_client_resources.get(store_resource)

            # New store resource
            if client_resource is None:
                raise NotImplementedError("TODO: retrieve the client_resource %s" % store_resource.id)
            if client_resource is not None:
                client_resource.receive_storage_ack(store_resource.id)
                updated_client_resources.append(client_resource)
        return updated_client_resources

    @staticmethod
    def _update_deleted_client_resources(store_to_client_resources, deleted_store_resources):
        """TODO: find a better name"""
        deleted_client_resources = []
        for store_resource in deleted_store_resources:
            client_resource = store_to_client_resources.get(store_resource)

            if client_resource is None:
                raise NotImplementedError("TODO: retrieve the client_resource")
            if client_resource is not None:
                client_resource.receive_deletion_notification_from_store()
                deleted_client_resources.append(client_resource)
        return deleted_client_resources

    # def _save_resource(self, client_resource, is_end_user, store_tracker):
    #     """TODO: refactor"""
    #     store = self._store_selector.select_store(client_resource, types=client_resource.types)
    #     store_resource = self._conversion_manager.convert_client_to_store_resource(client_resource, store,
    #                                                                                store_tracker)
    #     store_resource.save(is_end_user)
    #     # previous_id = client_resource.id
    #     new_id = store_resource.id
    #
    #     # Keeps track of the temporary IRI replacement
    #     # if previous_id != new_id:
    #     #    self._updated_iris[previous_id] = new_id
    #     client_resource.receive_storage_ack(new_id)
    #
    # def _delete_resource(self, client_resource, store_tracker):
    #     """TODO: refactor"""
    #     store = self._store_selector.select_store(client_resource, types=client_resource.types)
    #     store_resource = self._conversion_manager.convert_client_to_store_resource(client_resource, store,
    #                                                                                store_tracker)
    #     store_resource.delete()
    #     client_resource.receive_deletion_notification_from_store()

    def _create_session(self):
        # TODO: better understand the relation between the client and xstore sessions.
        return DefaultCrossStoreSession(self._store_selector)