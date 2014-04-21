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


class StringValueFormat(ValueFormat):

    def check_value(self, value):
        if not isinstance(value, (str, unicode)):
            raise ValueFormatError(u"%s is not a string" % value)


class BooleanValueFormat(ValueFormat):

    def check_value(self, value):
        if not isinstance(value, bool):
            raise ValueFormatError(u"%s is not a bool" % value)


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
