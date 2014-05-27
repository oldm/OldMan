from validate_email import validate_email


class ValueFormatError(Exception):
    """Invalid format detected."""
    pass


class ValueFormat(object):
    """A :class:`~oldman.validation.value_format.ValueFormat` object
    checks the values and converts `rdflib.term.Identifier` objects into
    Python objects.
    """

    def check_value(self, value):
        """Raises a :class:`~oldman.validation.value_format.ValueFormatError` exception
        if the value is wrongly formatted.

        :param value: Python value to check.
        """
        raise NotImplementedError(u"check_value must be overwritten")

    def to_python(self, rdf_term):
        """Converts a `rdflib.term.Identifier` object into
        a regular Python value.

        By default, uses the RDFlib `toPython()` method.

        :param rdf_term: `rdflib.term.Identifier` object.
        :return: Regular Python object.
        """
        return rdf_term.toPython()


class AnyValueFormat(ValueFormat):
    """Accepts any value."""

    def check_value(self, value):
        """Accepts any value."""
        pass


class TypedValueFormat(ValueFormat):

    def __init__(self, types):
        self._types = types

    def check_value(self, value):
        if not isinstance(value, self._types):
            raise ValueFormatError(u"%s is not a %s" % (value, self._types))


class IRIValueFormat(ValueFormat):

    def check_value(self, value):
        #TODO: to be implemented
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


class HexBinaryFormat(TypedValueFormat):
    """
        Numbers should ALREADY be encoded as hexadecimal strings
    """

    def __init__(self):
        TypedValueFormat.__init__(self, (str, unicode))

    def check_value(self, value):
        TypedValueFormat.check_value(self, value)
        try:
            int(value, 16)
        except ValueError:
            raise ValueFormatError(u"%s is not a hexadecimal value" % value)

    def to_python(self, rdf_term):
        """
            Returns an hexstring (not unhexlified bytes)
        """
        return unicode(rdf_term)


class EmailValueFormat(TypedValueFormat):

    def __init__(self):
        TypedValueFormat.__init__(self, (str, unicode))

    def check_value(self, value):
        # Check that it is a string
        TypedValueFormat.check_value(self, value)

        if not validate_email(value):
            raise ValueFormatError(u"%s is not a valid email (bad format)" % value)
