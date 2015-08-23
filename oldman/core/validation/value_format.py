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
        """See :func:`oldman.validation.value_format.ValueFormat.check_value`."""
        pass


class TypedValueFormat(ValueFormat):
    """Checks that the value is of a given type.

    :param types: Supported Python types.
    """

    def __init__(self, types):
        self._types = types

    def check_value(self, value):
        """See :func:`oldman.validation.value_format.ValueFormat.check_value`."""
        if not isinstance(value, self._types):
            raise ValueFormatError(u"%s is not a %s" % (value, self._types))


class IRIValueFormat(ValueFormat):
    """Checks that the value is an IRI."""

    def check_value(self, value):
        """See :func:`oldman.validation.value_format.ValueFormat.check_value`."""
        #TODO: to be implemented
        pass


class PositiveTypedValueFormat(TypedValueFormat):
    """Checks that the value is a positive number."""

    def check_value(self, value):
        """See :func:`oldman.validation.value_format.ValueFormat.check_value`."""
        TypedValueFormat.check_value(self, value)
        if value <= 0:
            raise ValueFormatError(u"%s should be positive" % value)


class NegativeTypedValueFormat(TypedValueFormat):
    """Checks that the value is a negative number."""

    def check_value(self, value):
        """See :func:`oldman.validation.value_format.ValueFormat.check_value`."""
        TypedValueFormat.check_value(self, value)
        if value >= 0:
            raise ValueFormatError(u"%s should be negative" % value)


class NonPositiveTypedValueFormat(TypedValueFormat):
    """Checks that the value is a non-positive number."""

    def check_value(self, value):
        """See :func:`oldman.validation.value_format.ValueFormat.check_value`."""
        TypedValueFormat.check_value(self, value)
        if value > 0:
            raise ValueFormatError(u"%s should not be positive" % value)


class NonNegativeTypedValueFormat(TypedValueFormat):
    """Checks that the value is a non-negative number."""

    def check_value(self, value):
        """See :func:`oldman.validation.value_format.ValueFormat.check_value`."""
        TypedValueFormat.check_value(self, value)
        if value < 0:
            raise ValueFormatError(u"%s should not be negative" % value)


class HexBinaryFormat(TypedValueFormat):
    """Checks that the value is a hexadecimal string."""

    def __init__(self):
        TypedValueFormat.__init__(self, (str, unicode))

    def check_value(self, value):
        """See :func:`oldman.validation.value_format.ValueFormat.check_value`."""
        TypedValueFormat.check_value(self, value)
        try:
            int(value, 16)
        except ValueError:
            raise ValueFormatError(u"%s is not a hexadecimal value" % value)

    def to_python(self, rdf_term):
        """Returns a hexstring."""
        return unicode(rdf_term)


class EmailValueFormat(TypedValueFormat):
    """Checks that the value is an email address."""

    def __init__(self):
        TypedValueFormat.__init__(self, (str, unicode))

    def check_value(self, value):
        """See :func:`oldman.validation.value_format.ValueFormat.check_value`."""
        # Check that it is a string
        TypedValueFormat.check_value(self, value)

        if not validate_email(value):
            raise ValueFormatError(u"%s is not a valid email (bad format)" % value)