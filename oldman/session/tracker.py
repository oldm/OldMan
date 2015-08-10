class SessionResourceTracker(object):

    def add(self, client_resource):
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def add_all(self, client_resources):
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def mark_to_delete(self, client_resource):
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def find(self, iri):
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def forget_resources_to_delete(self):
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    @property
    def resources_to_delete(self):
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    @property
    def modified_resources(self):
        """ TODO: explain
        Excludes resources to be deleted."""
        raise NotImplementedError("Should be implemented by a concrete implementation.")


class BasicSessionResourceTracker(SessionResourceTracker):

    def __init__(self):
        self._resources = set()
        self._resources_to_delete = set()
        # TODO: add an index

    def add(self, client_resource):
        self._resources.add(client_resource)

    def add_all(self, client_resources):
        for resource in client_resources:
            self.add(resource)

    def mark_to_delete(self, client_resource):
        self._resources_to_delete.add(client_resource)

    def find(self, iri):
        """TODO: re-implement """
        # TODO: use an index
        for resource in self._resources:
            if resource.id.iri == iri:
                return resource
        return None

    def forget_resources_to_delete(self):
        self._resources_to_delete = set()

    @property
    def resources_to_delete(self):
        return self._resources_to_delete

    @property
    def modified_resources(self):
        """TODO: re-implement it"""
        # TODO: only resources that we know they have been modified.
        return self._resources.difference(self._resources_to_delete)

