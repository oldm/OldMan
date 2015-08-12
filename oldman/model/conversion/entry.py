from oldman.common import OBJECT_PROPERTY
from oldman.model.attribute import get_iris, Entry


class EntryCloner(object):
    """TODO: explain"""

    def clone(self, attribute, entry):
        if attribute.om_property.type == OBJECT_PROPERTY:
            return self._clone_object_entry(entry)
        else:
            return self._clone_literal_entry(entry)

    @staticmethod
    def _clone_literal_entry(entry):
        return entry.clone()

    def _clone_object_entry(self, source_entry):
        """Creates target objects for some source objects found.

            TODO: further explain.
        """
        # Converts the source resources into target resources
        target_current_values = self._convert_object_values(source_entry.current_value)

        # If has changed, retrieves at the previous values
        if source_entry.has_changed():
            source_previous_values, _ = source_entry.diff()

            # Previous values: only IRIs
            target_previous_values = get_iris(source_previous_values)

            target_entry = Entry(target_previous_values)
            target_entry.current_value = target_current_values
            return target_entry
        else:
            return Entry(target_current_values)

    def _convert_object_values(self, values):
        """For object entries only"""
        if isinstance(values, list):
            return [self._convert_object_value(v) for v in values]
        elif isinstance(values, set):
            return {self._convert_object_value(v) for v in values}
        elif isinstance(values, dict):
            raise NotImplementedError(u"Should we implement it?")
        elif values is not None:
            # A Resource object or an IRI
            v = values
            return self._convert_object_value(v)
        else:
            return None

    def _convert_object_value(self, value):
        raise NotImplementedError("To be implemented by a sub-class")


class ClientToStoreEntryCloner(EntryCloner):

    def __init__(self, conversion_manager, store):
        self._conversion_manager = conversion_manager
        self._store = store

    def _convert_object_value(self, value):
        if isinstance(value, basestring):
            return value

        # Otherwise, presumed to be a Resource
        client_resource = value
        store_resource = self._conversion_manager.convert_client_to_store_resource(client_resource, self._store)
        return store_resource


class StoreToClientEntryCloner(EntryCloner):

    def __init__(self, conversion_manager, resource_mediator):
        self._conversion_manager = conversion_manager
        self._resource_mediator = resource_mediator

    def _convert_object_value(self, value):
        if isinstance(value, basestring):
            return value

        # Otherwise, presumed to be a Resource
        store_resource = value
        client_resource = self._conversion_manager.convert_store_to_client_resource(store_resource,
                                                                                    self._resource_mediator)
        return client_resource