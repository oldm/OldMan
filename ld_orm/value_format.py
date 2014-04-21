from rdflib import Literal

class ValueFormatError(Exception):
    pass


class ValueFormat(object):

    def check_value(self, value):
        """
            Raise a ValueFormatError if the value is wrongly formatted
        """
        raise NotImplementedError(u"check_value must be overwritten")


class AnyValueFormat(ValueFormat):

    def check_value(self, value):
        pass


class TypedValueFormat(ValueFormat):

    def __init__(self, types):
        self._types = types

    def check_value(self, value):
        if not isinstance(value, self._types):
            raise ValueFormatError(u"%s is not a %s" % (value, self._types))


class IRIValueFormat(ValueFormat):
    """
        TODO:
            - implement it.
    """

    def check_value(self, value):
        """
            TODO: to be implemented
        """
        pass


class PositiveTypedValueFormat(TypedValueFormat):

    def check_value(self, value):
        TypedValueFormat.check_value(self, value)
        if value <= 0:
            raise ValueFormatError(u"%s should be positive" % value)


class NegativeTypedValueFormat(TypedValueFormat):

    def check_value(self, value):
        TypedValueFormat.check_value(self, value)
        if value >= 0:
            raise ValueFormatError(u"%s should be negative" % value)


class NonPositiveTypedValueFormat(TypedValueFormat):

    def check_value(self, value):
        TypedValueFormat.check_value(self, value)
        if value > 0:
            raise ValueFormatError(u"%s should not be positive" % value)


class NonNegativeTypedValueFormat(TypedValueFormat):

    def check_value(self, value):
        TypedValueFormat.check_value(self, value)
        if value < 0:
            raise ValueFormatError(u"%s should not be negative" % value)


class EmailValueFormat(ValueFormat):
    """ TODO: implement it """

    def check_value(self, value):
        raise NotImplementedError(u"TODO: implement it")
