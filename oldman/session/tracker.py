from collections import defaultdict


class ResourceFinder(object):
    """
        Interface without side-effect method.

        TODO: should we still keep distinct?
    """
    def find(self, iri):
        raise NotImplementedError("Should be implemented by a concrete implementation.")


class ResourceTracker(ResourceFinder):

    def find(self, iri):
        """ Inherited. See YYYY """
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def add(self, resource):
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def add_all(self, resources):
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def mark_to_delete(self, resource):
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def receive_reference(self, reference, object_resource=None, object_iri=None):
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


class BasicResourceTracker(ResourceTracker):

    def __init__(self):
        self._resources = set()
        self._resources_to_delete = set()
        # TODO: add an index for resources

        # { Source resource -> Reference }
        self._subject_references = defaultdict(list)
        # { Target resource -> Reference }
        self._object_references = defaultdict(list)
        # { Target permanent IRI -> Reference }
        self._object_iri_references = defaultdict(list)

    def add(self, resource):
        self._resources.add(resource)

    def add_all(self, resources):
        for resource in resources:
            self.add(resource)

    def mark_to_delete(self, resource):
        self._resources_to_delete.add(resource)
        # TODO: UPDATE the objects that refer to this resource.
        # TODO: see how to CASCADE.

    def receive_reference(self, reference, object_resource=None, object_iri=None):
        """TODO: better implement it """
        if object_resource is None and object_iri is None:
            raise ValueError("the target_resource OR the target_iri must be given")

        self._subject_references[reference.subject_resource].append(reference)
        if object_resource is not None:
            self._object_references[object_resource].append(reference)
        else:
            self._object_iri_references[object_iri].append(reference)

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

