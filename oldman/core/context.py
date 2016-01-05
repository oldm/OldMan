import rfc3987


class Context(object):

    def __init__(self, uncategorized_value=None, payload=None, iri=None, file_path=None):

        if uncategorized_value and (payload or iri or file_path):
            raise ValueError("Cannot have uncategorized and categorized context values at the same time.")

        if file_path and not iri:
            raise ValueError("A file_path argument cannot be given without an IRI.")

        if file_path and payload:
            raise ValueError("Conflict between the arguments file_path and payload. "
                             "Please only give one of the two.")

        if uncategorized_value:
            payload, iri = self._categorize(uncategorized_value)

        self._annotation = self._extract_annotation(iri, payload)
        self._value_to_load = self._extract_value_to_load(iri, file_path, payload)

    @property
    def annotation(self):
        """Value to include in JSON-LD serializations"""
        return self._annotation

    @property
    def value_to_load(self):
        """Value to give to the context parser"""
        return self._value_to_load

    @staticmethod
    def _categorize(uncategorized_value):
        if isinstance(uncategorized_value, dict):
            return uncategorized_value, None
        try:
            # Throw an exception if not an IRI
            rfc3987.parse(uncategorized_value, 'IRI')
            # Is an IRI
            return None, uncategorized_value
        except ValueError:
            # Otherwise is presumed to be a payload
            # TODO: check more
            return uncategorized_value, None


    @staticmethod
    def _extract_annotation(iri, payload):
        if iri is not None:
            return iri
        if payload is not None:
            return payload
        else:
            raise ValueError("No value given")

    @staticmethod
    def _extract_value_to_load(iri, file_path, payload):
        if payload is not None:
            return clean_payload(payload)
        elif file_path is not None:
            return file_path
        elif iri is not None:
            return iri
        else:
            raise ValueError("No value given")


def clean_payload(payload):
    """Cleans the context.

    Context can be an IRI, a `list` or a `dict`.
    """
    # TODO: - make sure "id": "@id" and "types": "@type" are in
    if isinstance(payload, dict) and "@context" in payload.keys():
        payload = payload["@context"]
    return payload