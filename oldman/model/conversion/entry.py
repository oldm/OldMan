from oldman.common import OBJECT_PROPERTY
from oldman.model.attribute import Entry
from oldman.resource.reference import ResourceReference


class EntryExchanger(object):
    """TODO: explain"""

    def __init__(self, client_resource, store_resource):
        self._client_subject_resource = client_resource
        self._store_subject_resource = store_resource

    @property
    def target_tracker(self):
        raise NotImplementedError("Must be implemented by a sub-class")

    @property
    def target_subject_resource(self):
        raise NotImplementedError("Must be implemented by a sub-class")

    def exchange(self, source_attribute, target_attribute):
        if source_attribute.om_property.type == OBJECT_PROPERTY:
            return self._convert_object_entry(source_attribute, target_attribute)
        else:
            return self._convert_literal_entry(source_attribute)

    def _convert_literal_entry(self, source_attribute):
        source_entry = self._extract_source_entry(source_attribute)
        return source_entry.clone()

    def _convert_object_entry(self, source_attribute, target_attribute):
        """Creates target objects for some source objects found.

            TODO: further explain.
        """
        source_entry = self._extract_source_entry(source_attribute)

        # Converts the source resources into target resources
        target_current_references = self._convert_references(source_entry.current_value, target_attribute)

        # If has changed, retrieves at the previous values
        if source_entry.has_changed():
            source_previous_references, _ = source_entry.diff()

            # TODO: maybe we could optimize it
            target_previous_references = self._convert_references(source_previous_references, target_attribute)

            target_entry = Entry(target_previous_references)
            target_entry.current_value = target_current_references
            return target_entry
        else:
            return Entry(target_current_references)

    def _convert_references(self, references, target_attribute):
        """For object entries only"""
        if isinstance(references, list):
            return [self._convert_reference(r, target_attribute) for r in references]
        elif isinstance(references, set):
            return {self._convert_reference(r, target_attribute) for r in references}
        elif isinstance(references, dict):
            raise NotImplementedError(u"Should we implement it?")
        elif references is not None:
            # A Resource object or an IRI
            r = references
            return self._convert_reference(r, target_attribute)
        else:
            return None

    def _convert_reference(self, source_reference, target_attribute):
        """

        Terminology:
        source and target attributes
        and subject and object resources of a given attributes

        """
        object_iri = source_reference.object_iri

        # First, try to fetch the store_resource in the store tracker
        target_object_resource = self.target_tracker.find(object_iri)
        if target_object_resource is not None:
            target_object_resource_or_iri = target_object_resource

        # If the client target resource is immediately available, convert it
        elif source_reference.is_bound_to_object_resource:
            source_object_resource = source_reference.get()
            target_object_resource = self._convert_object_resource(source_object_resource)
            target_object_resource_or_iri = target_object_resource
        else:
            target_object_resource_or_iri = object_iri

        return ResourceReference(self.target_subject_resource, target_attribute, target_object_resource_or_iri)

    def _extract_source_entry(self, source_attribute):
        raise NotImplementedError("Must be implemented by sub-classes")

    def _convert_object_resource(self, source_object_resource):
        raise NotImplementedError("Must be implemented by sub-classes")


class ClientToStoreEntryExchanger(EntryExchanger):

    def __init__(self, conversion_manager, store, client_resource, store_resource, store_tracker):
        EntryExchanger.__init__(self, client_resource, store_resource)
        self._conversion_manager = conversion_manager
        self._store = store
        self._store_tracker = store_tracker

    @property
    def target_tracker(self):
        return self._store_tracker

    @property
    def target_subject_resource(self):
        return self._store_subject_resource

    def _convert_object_resource(self, client_object_resource):
        return self._conversion_manager.convert_client_to_store_resource(client_object_resource, self._store,
                                                                         self._store_tracker)

    def _extract_source_entry(self, client_attribute):
        return client_attribute.get_entry(self._client_subject_resource)


class StoreToClientEntryExchanger(EntryExchanger):

    def __init__(self, conversion_manager, client_resource, store_resource, client_tracker, client_factory):
        EntryExchanger.__init__(self, client_resource, store_resource)
        self._conversion_manager = conversion_manager
        self._client_tracker = client_tracker
        self._client_factory = client_factory

    @property
    def target_tracker(self):
        return self._client_tracker

    @property
    def target_subject_resource(self):
        return self._client_subject_resource

    def _convert_object_resource(self, source_object_resource):
        # TODO: update the prototype
        return self._conversion_manager.convert_store_to_client_resource(source_object_resource, self._client_factory,
                                                                         self._client_tracker)

    def _extract_source_entry(self, store_attribute):
        return store_attribute.get_entry(self._store_subject_resource)
