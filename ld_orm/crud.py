_JSON_TYPES = ["application/json", "json"]
_JSON_LD_TYPES = ["application/ld+json", "json-ld"]


class CRUDController(object):
    """


        TODO: implement a PATCH method
    """

    def __init__(self, registry):
        self._registry = registry

    def get(self, base_uri, content_type="text/turtle"):
        """
            HTTP GET.
            May raise an ObjectNotFoundError
        """
        obj_uri = self._registry.find_object_from_base_uri(base_uri)
        obj = self._registry.find_object(obj_uri)

        if content_type in _JSON_TYPES:
            return obj.to_json()
        elif content_type in _JSON_LD_TYPES:
            return obj.to_jsonld()
        # Try as a RDF mime-type (may not be supported)
        else:
            return obj.to_rdf(content_type)

    def delete(self, base_uri):
        for obj_iri in self._registry.find_object_iris(base_uri):
            obj = self._registry.find_object(obj_iri)
            if obj is not None:
                obj.delete()

    def put(self, base_uri, new_document, content_type):
        raise NotImplementedError("TODO: implement it")

    def append(self, base_uri, new_document, content_type):
        raise NotImplementedError("TODO: implement it")