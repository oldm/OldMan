_JSON_TYPES = ["application/json", "json"]
_JSON_LD_TYPES = ["application/ld+json", "json-ld"]


class CRUDController(object):

    def __init__(self, registry):
        self._registry = registry

    def get(self, base_uri, mime_type="text/turtle"):
        """
            HTTP GET.
            May raise an ObjectNotFoundError
        """
        obj_uri = self._registry.find_object_from_base_uri(base_uri)
        obj = self._registry.find_object(obj_uri)

        if mime_type in _JSON_TYPES:
            return obj.to_json()
        elif mime_type in _JSON_LD_TYPES:
            return obj.to_jsonld()
        # Try as a RDF mime-type (may not be supported)
        else:
            return obj.to_rdf(mime_type)