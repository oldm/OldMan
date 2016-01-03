class ExpectedProperty(object):

    def __init__(self, property_iri, is_reversed, is_contained_in_list):
        self._is_contained_in_list = is_contained_in_list
        self._is_reversed = is_reversed
        self._property_iri = property_iri

        if is_reversed and is_contained_in_list:
            raise ValueError("List are not supported for reversed properties")

    @property
    def is_contained_in_list(self):
        return self._is_contained_in_list

    @property
    def is_reversed(self):
        return self._is_reversed

    @property
    def iri(self):
        return self._property_iri
