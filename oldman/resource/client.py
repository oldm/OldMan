from rdflib import URIRef, RDF
from oldman.resource.resource import Resource, is_blank_node


class ClientResource(Resource):
    """ClientResource: resource manipulated by the end-user.

    Has access to the `resource_mediator`.

    Is not serializable.
    """

    def __init__(self, resource_mediator, **kwargs):
        Resource.__init__(self, resource_mediator.model_manager, **kwargs)
        self._resource_mediator = resource_mediator

    @classmethod
    def load_from_graph(cls, mediator, model_manager, id, subgraph, is_new=True, collection_iri=None):
        """Loads a new :class:`~oldman.resource.ClientResource` object from a sub-graph.

        TODO: update the comments.

        :param mediator: :class:`~oldman.resource.mediator.Mediator` object.
        :param id: IRI of the resource.
        :param subgraph: :class:`rdflib.Graph` object containing triples about the resource.
        :param is_new: When is `True` and `id` given, checks that the IRI is not already existing in the
                       `union_graph`. Defaults to `True`.
        :return: The :class:`~oldman.resource.Resource` object created.
        """
        types = list({unicode(t) for t in subgraph.objects(URIRef(id), RDF.type)})
        instance = cls(mediator, model_manager, id=id, types=types, is_new=is_new, collection_iri=collection_iri)
        instance.update_from_graph(subgraph, is_end_user=True, save=False, initial=True)
        return instance

    def get_related_resource(self, id):
        """ Gets a related `ClientResource` through the resource manager. """
        resource = self._resource_mediator.get(id=id)
        if resource is None:
            return id
        return resource

    def save(self, is_end_user=True):
        """Saves it into the `data_store` and its `resource_cache`.

        Raises an :class:`oldman.exception.OMEditError` exception if invalid.

        :param is_end_user: `False` when an authorized user (not a regular end-user)
                             wants to force some rights. Defaults to `True`.
                             See :func:`~oldman.attribute.OMAttribute.check_validity` for further details.
        :return: The :class:`~oldman.resource.resource.Resource` object itself."""
        attributes = self._extract_attribute_list()
        for attr in attributes:
            attr.check_validity(self, is_end_user)

        # The ID may be updated (if was a temporary IRI before)
        self._id = self._resource_mediator.save_resource(self, is_end_user)

        # Clears former values
        self._former_types = self._types
        # Clears former values
        for attr in attributes:
            attr.receive_storage_ack(self)
        self._is_new = False

        return self

    def delete(self):
        """Removes the resource from the `data_store` and its `resource_cache`.

        TODO: update this comment

        Cascade deletion is done for related resources satisfying the test
        :func:`~oldman.resource.resource.should_delete_resource`.
        """

        self._resource_mediator.delete_resource(self)

        # Clears former values
        self._former_types = self._types
        # Clears values
        for attr in self._extract_attribute_list():
            setattr(self, attr.name, None)
            attr.receive_storage_ack(self)
        self._is_new = False

    def __getstate__(self):
        """Cannot be pickled."""
        #TODO: find the appropriate exception
        raise Exception("A ClientResource is not serializable.")

    def __setstate__(self, state):
        """Cannot be pickled."""
        #TODO: find the appropriate exception
        raise Exception("A ClientResource is not serializable.")

    def _filter_objects_to_delete(self, ids):
        """TODO: consider other cases than blank nodes """
        return [self._resource_mediator.get(id=id) for id in ids
                if id is not None and is_blank_node(id)]
