from ast import literal_eval


class ValueFormatError(Exception):
    pass


class ValueFormat(object):

    def check_value(self, value):
        """
            Raise a ValueFormatError if the value is wrongly formatted
        """
        raise NotImplementedError(u"check_value must be overwritten")

    def xsdify_value(self, value):
        """
            Reshapes the value as a XSD-like format.
            By default does nothing.
        """
        return value

    def to_python(self, value):
        """
            If the value cannot be converted, raises a ValueError
        """
        return value


class AnyValueFormat(ValueFormat):

    def check_value(self, value):
        pass


class IRIValueFormat(ValueFormat):
    """
        TODO:
            - implement it.
    """
    pass

    def check_value(self, value):
        """
            TODO: to be implemented
        """
        pass

    def to_python(self, value):
        """ TODO: check value """
        return unicode(value)


class StringValueFormat(ValueFormat):

    def check_value(self, value):
        if not isinstance(value, (str, unicode)):
            raise ValueFormatError(u"%s is not a string" % value)


class BooleanValueFormat(ValueFormat):

    def check_value(self, value):
        if not isinstance(value, bool):
            raise ValueFormatError(u"%s is not a bool" % value)

    def xsdify_value(self, value):
        return unicode(value).lower()

    def to_python(self, value):
        return literal_eval(value.capitalize())


class IntegerValueFormat(ValueFormat):
    """
        TODO: implement
    """
    pass


class DateValueFormat(ValueFormat):
    """ TODO: implement it """
    pass


class EmailValueFormat(ValueFormat):
    """ TODO: implement it """

    def check_value(self, value):
        raise NotImplementedError(u"TODO: implement it")
