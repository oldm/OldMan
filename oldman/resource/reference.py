from oldman.common import is_temporary_blank_node
from oldman.resource.resource import Resource


class ResourceReference(object):
    """TODO: explain

        "Subject" and "object" adjectives can be ROUGHLY understood like "subject predicate object".

        By roughly, we mean that we ignore the effect of "inverse property" (an attribute roughly
        corresponds to a predicate even in practice it can refer to an inverse predicate; we don't
        make the distinction here).


    """
    
    def __init__(self, subject_resource, attribute, object_resource_or_iri):
        """TODO: deal with temporary IRIs (expected to be robust)"""

        if object_resource_or_iri is None:
            raise ValueError("target_resource_or_iri must be given")

        if subject_resource is None:
            raise ValueError("source_resource is required")

        if attribute is None:
            raise ValueError("attribute is required")

        self._subject_resource = subject_resource
        self._attribute = attribute

        if isinstance(object_resource_or_iri, Resource):
            self._object_resource = object_resource_or_iri

            if self._object_resource.id.is_permanent:
                self._permanent_object_iri = self._object_resource.id.iri
            else:
                self._permanent_object_iri = None

        elif is_temporary_blank_node(object_resource_or_iri):
            raise ValueError("Cannot directly assign an temporary skolemized IRI. "
                             "Please assign a Resource object instead.")
        else:
            self._object_resource = None
            self._permanent_object_iri = object_resource_or_iri

        self._is_attached = True

        self._register()

    @property
    def subject_resource(self):
        if not self._is_attached:
            # TODO: use a better exception
            raise Exception("The ResourceReference is not attached anymore")
        return self._subject_resource

    @property
    def attribute(self):
        return self._attribute

    @property
    def object_iri(self):
        if self._object_resource is not None:
            return self._object_resource.id.iri
        else:
            return self._permanent_object_iri

    @property
    def is_bound_to_object_resource(self):
        return self._object_resource is not None

    def get(self):
        if not self._is_attached:
            # TODO: use a better exception
            raise Exception("The ResourceReference is not attached anymore")
        if self._object_resource is None:
            self._object_resource = self._subject_resource.get_related_resource(self._permanent_object_iri)
            if self._object_resource is None:
                # TODO: give another type to this exception
                raise Exception("The target resource could not be fetch")

        return self._object_resource
    
    def detach(self):
        """TODO: explain"""
        if self._is_attached:
            self._is_attached = False
            self._unregister()

    def _register(self):
        if self._object_resource is not None:
            self._subject_resource.notify_reference(self, object_resource=self._object_resource)
        else:
            self._subject_resource.notify_reference(self, object_iri=self._permanent_object_iri)

    def _unregister(self):
        if self._object_resource is not None:
            self._subject_resource.notify_reference_removal(self, object_resource=self._object_resource)
        else:
            self._subject_resource.notify_reference_removal(self, object_iri=self._permanent_object_iri)
