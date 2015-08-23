"""
TODO: explain
"""


class Operation(object):
    """ TODO: describe """

    def __init__(self, http_method, excepted_type, returned_type, function, name):
        self._http_method = http_method
        self._excepted_type = excepted_type
        self._returned_type = returned_type
        self._function = function
        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def expected_type(self):
        return self._excepted_type

    @property
    def returned_type(self):
        return self._returned_type

    def __call__(self, resource, **kwargs):
        return self._function(resource, **kwargs)


# ---------------------------------
# Pre-defined operation functions
# ---------------------------------


def not_implemented(resource, **kwargs):
    # TODO: find a better error
    raise NotImplementedError("This method is declared but not implemented.")