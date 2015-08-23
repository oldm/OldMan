class Session(object):
    """TODO: explain """

    def get(self, iri, types=None, eager_with_reversed_attributes=True):
        """See :func:`oldman.store.datastore.DataStore.get`."""
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def delete(self, resource):
        """TODO: describe"""
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def flush(self, is_end_user=True):
        """TODO: describe """
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def close(self):
        """TODO: describe """
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def receive_reference(self, reference, object_resource=None, object_iri=None):
        """ Not for end-users!"""
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def receive_reference_removal_notification(self, reference):
        """ Not for end-users!"""
        raise NotImplementedError("Should be implemented by a concrete implementation.")