from types import GeneratorType
from rdflib import URIRef, RDF
from oldman.exception import OMInternalError
from oldman.iri.id import PermanentId
from oldman.resource.resource import Resource


class StoreResource(Resource):
    """StoreResource: resource manipulated by the data store.

     End-users should not manipulate it.

     Is serializable (pickable).

    :param previous_id: TODO: describe (maybe a temporary one).
    :param model_manager: :class:`~oldman.model.manager.ModelManager` object. Gives access to its models.
    :param store: :class:`~oldman.store.store.Store` object. Store that has authority on this resource.
    :param kwargs: Other parameters considered by the :class:`~oldman.resource.Resource` constructor
                   and values indexed by their attribute names.
    """

    def __init__(self, previous_id, model_manager, store, session, types=None, is_new=True, **kwargs):
        resource_id = previous_id
        Resource.__init__(self, resource_id, model_manager, session, types=types, is_new=is_new, **kwargs)
        self._store = store

    @classmethod
    def load_from_graph(cls, model_manager, store, session, iri, subgraph, is_new=True):
        """Loads a new :class:`~oldman.resource.StoreResource` object from a sub-graph.

        TODO: update the comments.

        :param model_manager: :class:`~oldman.model.manager.StoreModelManager` object.
        :param iri: IRI of the resource.
        :param subgraph: :class:`rdflib.Graph` object containing triples about the resource.
        :param is_new: When is `True` and `id` given, checks that the IRI is not already existing in the
                       `union_graph`. Defaults to `True`.
        :return: The :class:`~oldman.resource.store.StoreResource` object created.
        """
        types = list({unicode(t) for t in subgraph.objects(URIRef(iri), RDF.type)})
        instance = cls(PermanentId(iri), model_manager, store, session, types=types, is_new=is_new)
        instance.update_from_graph(subgraph, initial=True)
        return instance

    @property
    def store(self):
        return self._store

    def __getstate__(self):
        """Pickles this resource."""
        state = {name: getattr(self, name) for name in self._pickle_attribute_names}
        state["store_name"] = self._store.name

        # Reversed order so that important models can overwrite values
        reversed_models = self._models
        reversed_models.reverse()
        for model in reversed_models:
            for name, attr in model.om_attributes.iteritems():
                value = attr.get_lightly(self)
                if isinstance(value, GeneratorType):
                    if attr.container == "@list":
                        value = list(value)
                    else:
                        value = set(value)
                if value is not None:
                    state[name] = value
        return state

    def __setstate__(self, state):
        """Unpickles this resource from its serialized `state`."""
        required_fields = self._pickle_attribute_names + ["store_name"]
        for name in required_fields:
            if name not in state:
                #TODO: find a better exception (due to the cache)
                raise OMInternalError(u"Required field %s is missing in the cached state" % name)

        self._id = state["_id"]
        self._is_new = state["_is_new"]
        self._init_non_persistent_attributes(self._id)
        # Have to be re-attached
        self._session = None

        # Store
        from oldman.store.store import Store
        self._store = Store.get_store(state["store_name"])
        self._model_manager = self._store.model_manager

        # Models and types
        self._models, self._types = self._model_manager.find_models_and_types(state["_types"])
        self._former_types = set(self._types)

        # Attributes (Python attributes or OMAttributes)
        for name, value in state.iteritems():
            if name in ["store_name", "_id", "_types", "_is_new"]:
                continue
            elif name in self._special_attribute_names:
                setattr(self, name, value)
            # OMAttributes
            else:
                attribute = self._get_om_attribute(name)
                attribute.set(self, value)
                # Clears former values (allows modification)
                attribute.receive_storage_ack(self)

    def reattach(self, xstore_session):
        if self._session is None:
            self._session = xstore_session
        else:
            # TODO: find a better exception
            raise Exception("Already attached StoreResource %s" % self)

    def prepare_deletion(self):
        self._former_types = self._types
        self._types = []
        # Removes its attribute
        for attr in self.attributes:
            setattr(self, attr.name, None)

    # def save(self, is_end_user=True):
    #     """Saves it into the `data_store` and its `resource_cache`.
    #
    #     Raises an :class:`oldman.exception.OMEditError` exception if invalid.
    #
    #     :param is_end_user: `False` when an authorized user (not a regular end-user)
    #                          wants to force some rights. Defaults to `True`.
    #                          See :func:`~oldman.attribute.OMAttribute.check_validity` for further details.
    #     :return: The :class:`~oldman.resource.resource.Resource` object itself."""
    #
    #     # Checks
    #     attributes = self._extract_attribute_list()
    #     for attr in attributes:
    #         attr.check_validity(self, is_end_user)
    #
    #     # Find objects to delete
    #     objects_to_delete = []
    #     for attr in attributes:
    #         if not attr.has_changed(self):
    #             continue
    #
    #         # Some former objects may be deleted
    #         if attr.om_property.type == OBJECT_PROPERTY:
    #             former_refs, new_refs = attr.diff(self)
    #
    #             if isinstance(former_refs, dict):
    #                 raise NotImplementedError("Object dicts are not yet supported.")
    #             former_refs = former_refs if isinstance(former_refs, (set, list)) else [former_refs]
    #
    #             # Cache invalidation (because of possible reverse properties)
    #             resources_to_invalidate = set(new_refs) if isinstance(new_refs, (set, list)) else {new_refs}
    #             resources_to_invalidate.update(former_refs)
    #             for r in resources_to_invalidate:
    #                 if r is not None:
    #                     iri = r.id.iri if isinstance(r, Resource) else r
    #                     self._store.resource_cache.remove_resource_from_iri(iri)
    #
    #             objects_to_delete += self._filter_objects_to_delete(former_refs)
    #
    #     # Update literal values and receives the definitive id
    #     self.store.save(self, attributes, self._former_types, self._is_new)
    #
    #     # Delete the objects
    #     for obj in objects_to_delete:
    #         obj.delete()
    #
    #     # Clears former values
    #     self._former_types = self._types
    #     for attr in attributes:
    #         attr.receive_storage_ack(self)
    #
    #     return self
    #
    # def delete(self):
    #     """Removes the resource from the `data_store` and its `resource_cache`.
    #
    #     Cascade deletion is done for related resources satisfying the test
    #     :func:`~oldman.resource.resource.should_delete_resource`.
    #     """
    #     attributes = self._extract_attribute_list()
    #     for attr in attributes:
    #         # Delete blank nodes recursively
    #         if attr.om_property.type == OBJECT_PROPERTY:
    #             value = getattr(self, attr.name)
    #             if value is not None:
    #                 objs = value if isinstance(value, (list, set, GeneratorType)) else [value]
    #                 for obj in objs:
    #                     if should_delete_resource(obj):
    #                         self._logger.debug(u"%s deleted with %s" % (obj.id, self._id))
    #                         obj.delete()
    #                     else:
    #                         self._logger.debug(u"%s not deleted with %s" % (obj.id, self._id))
    #                         # Cache invalidation (because of possible reverse properties)
    #                         self._store.resource_cache.remove_resource(obj)
    #
    #         setattr(self, attr.name, None)
    #
    #     #Types
    #     self._change_types(set())
    #     self._store.delete(self, attributes, self._former_types)
    #
    #     # Clears former values
    #     for attr in attributes:
    #         attr.receive_storage_ack(self)
    #     self._is_new = False
    #
    # def _filter_objects_to_delete(self, refs):
    #     return [ref.get() for ref in refs
    #             if ref is not None and is_blank_node(ref.object_iri)]
