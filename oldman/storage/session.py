from collections import defaultdict
import logging

import networkx as nx
from networkx.algorithms.dag import is_directed_acyclic_graph, topological_sort
from oldman.core.session.session import Session

from oldman.core.session.tracker import BasicResourceTracker
from oldman.storage.resource import StoreResource


class CrossStoreSession(Session):

    @property
    def tracker(self):
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def new(self, id, store, types=None, hashless_iri=None, collection_iri=None, is_new=True, former_types=None,
            **kwargs):
        """Creates a new :class:`~oldman.resource.Resource` object **without saving it** in the `data_store`.

        The `kwargs` dict can contains regular attribute key-values that will be assigned to
        :class:`~oldman.attribute.OMAttribute` objects.

        TODO: update this doc

        :param id: TODO: explain
        :param types: IRIs of RDFS classes the resource is instance of. Defaults to `None`.
                      Note that these IRIs are used to find the models of the resource
                      (see :func:`~oldman.resource.manager.ResourceManager.find_models_and_types` for more details).
        :param hashless_iri: hash-less IRI that MAY be considered when generating an IRI for the new resource.
                         Defaults to `None`. Ignored if `id` is given. Must be `None` if `collection_iri` is given.
        :param collection_iri: IRI of the controller to which this resource belongs. This information
                        is used to generate a new IRI if no `id` is given. The IRI generator may ignore it.
                        Defaults to `None`. Must be `None` if `hashless_iri` is given.
        :return: A new :class:`~oldman.resource.Resource` object.
        """
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def load_from_graph(self, id, resource_graph, store):
        raise NotImplementedError("Should be implemented by a concrete implementation.")


class DefaultCrossStoreSession(CrossStoreSession):
    """TODO: explain because the name can be counter-intuitive
    """

    def __init__(self, store_selector):
        self._store_selector = store_selector
        self._tracker = BasicResourceTracker()
        self._logger = logging.getLogger(__name__)

    @property
    def tracker(self):
        return self._tracker

    def flush(self, is_end_user=True):
        """TODO: re-implement it """

        all_resources_to_update = self._sort_resources_to_update(self._tracker.modified_resources)
        all_resources_to_delete = self._tracker.resources_to_delete
        store_cluster = cluster_by_store_and_status(all_resources_to_update, all_resources_to_delete)

        all_updated_resources = []
        all_deleted_resources = []
        for store in self._sort_stores(all_resources_to_update, all_resources_to_delete):
            resources_to_update, resources_to_delete = store_cluster[store]

            updated_resources, deleted_resources = store.flush(resources_to_update, resources_to_delete, is_end_user)
            all_updated_resources.extend(updated_resources)
            all_deleted_resources.extend(deleted_resources)

        # TODO: improve this
        self._tracker.add_all(all_updated_resources)
        self._tracker.forget_resources_to_delete()
        return all_updated_resources, all_deleted_resources

    def get(self, iri, types=None, eager_with_reversed_attributes=True):
        for store in self._store_selector.select_stores(iri=iri, types=types):
            store_resource = store.get(self, iri, types=types,
                                       eager_with_reversed_attributes=eager_with_reversed_attributes)
            if store_resource is not None:
                return store_resource
        return None

    def new(self, id, store, types=None, is_new=True, former_types=None, **kwargs):
        resource = StoreResource(id, store.model_manager, store, self, types=types, is_new=is_new,
                                 former_types=former_types)
        self._tracker.add(resource)
        return resource

    def load_from_graph(self, id, resource_graph, store):
        resource = StoreResource.load_from_graph(store.model_manager, store, self, id, resource_graph, is_new=False)
        self._tracker.add(resource)
        return resource

    def delete(self, store_resource):
        """TODO: describe.

            Wait for the next flush() to remove the resource
            from the store.
        """
        self._tracker.mark_to_delete(store_resource)
        store_resource.prepare_deletion()

    def receive_reference(self, reference, object_resource=None, object_iri=None):
        self._tracker.receive_reference(reference, object_resource=object_resource, object_iri=object_iri)

    def receive_reference_removal_notification(self, reference):
        self._tracker.receive_reference_removal_notification(reference)

    def close(self):
        """Does nothing"""
        pass

    def _sort_resources_to_update(self, resources_to_update):
        """ TODO: implement it seriously. Construct a dependency graph.

            The order is important when saving resources with temporary IDs.
        """
        if len(resources_to_update) == 1:
            return resources_to_update

        graph = nx.DiGraph()
        for resource in resources_to_update:
            if resource not in graph:
                graph.add_node(resource)
            dependencies = self._tracker.get_dependencies(resource)
            for dep_resource in dependencies:
                if dep_resource not in graph:
                    graph.add_node(dep_resource)
                # Inverse dependency edge
                graph.add_edge(dep_resource, resource)

        if is_directed_acyclic_graph(graph):
            return topological_sort(graph)
        else:
            self._logger.warn("Some resources are mutually dependent so cannot be sorted. \n"
                              "This may cause problems when flushing new resources (with temporary IDs)"
                              "to some stores.")
            return resources_to_update

    @staticmethod
    def _sort_stores(all_resources_to_update, all_resources_to_delete):
        """ TODO: explain.

            TODO: improve the implementation to throw an exception if the order
            cannot be enforced.
        """
        stores = []
        # Here the order matters
        for resource in all_resources_to_update:
            if resource.store not in stores:
                stores.append(resource.store)

        # Probably the order does not really matters here
        for resource in all_resources_to_delete:
            if resource.store not in stores:
                stores.append(resource.store)
        return stores


def cluster_by_store_and_status(resources_to_update, resources_to_delete):
    update_cluster = cluster_by_store(resources_to_update)
    delete_cluster = cluster_by_store(resources_to_delete)

    stores = update_cluster.keys() + delete_cluster.keys()

    return {store: (update_cluster[store], delete_cluster[store])
            for store in stores}


def cluster_by_store(resources):
    cluster = defaultdict(list)
    for resource in resources:
        cluster[resource.store].append(resource)
    return cluster
