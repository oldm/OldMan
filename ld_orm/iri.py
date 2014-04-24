from uuid import uuid1
from rdflib.plugins.sparql import prepareQuery
from .exceptions import DataStoreError


class IriGenerator(object):

    def __init__(self, **kwargs):
        pass

    def generate(self):
        raise NotImplementedError()


class RandomPrefixedIriGenerator(IriGenerator):

    def __init__(self, **kwargs):
        self.prefix = kwargs["prefix"]

    def generate(self):
        return u"%s%s" % (self.prefix, uuid1().hex)


class RandomIriGenerator(RandomPrefixedIriGenerator):

    def __init__(self, **kwargs):
        hostname = kwargs.get("hostname", u"localhost")
        prefix = u"http://%s/.well-known/genid/" % hostname
        RandomPrefixedIriGenerator.__init__(self, prefix=prefix)


class IncrementalIriGenerator(IriGenerator):
    """
        Generates IRIs with short numbers.

        Warning: does not support concurrency!
        The risk of collision is important.
    """

    def __init__(self, **kwargs):
        try:
            self._prefix = kwargs["prefix"]
            self._graph = kwargs["graph"]
            self._class_uri = kwargs["class_uri"]
        except KeyError as e:
            raise TypeError(u"Missing argument:%s" % e)

        self._counter_query_req = prepareQuery(u"""
            prefix ldorm: <http://localhost/ldorm#>
            SELECT ?number
            WHERE {
                ?class_uri ldorm:nextNumber ?number .
            }""".replace("?class_uri", u"<%s>" % self._class_uri))

        self._counter_update_req = u"""
            prefix ldorm: <http://localhost/ldorm#>
            DELETE {
                ?class_uri ldorm:nextNumber ?current .
            }
            INSERT {
                ?class_uri ldorm:nextNumber ?next .
            }
            WHERE {
                ?class_uri ldorm:nextNumber ?current .
                BIND (?current+1 AS ?next)
            }""".replace("?class_uri", "<%s>" % self._class_uri)

        numbers = list(self._graph.query(self._counter_query_req))
        # Inits if no counter
        if len(numbers) == 0:
            self.reset_counter()
        elif len(numbers) > 1:
            raise DataStoreError(u"Multiple counter for class %s" % self._class_uri)

    def reset_counter(self):
        self._graph.update(u"""
            prefix ldorm: <http://localhost/ldorm#>
            INSERT {
                <%s> ldorm:nextNumber 0 .
                } WHERE {}""" % self._class_uri)

    def generate(self):
        self._graph.update(self._counter_update_req)
        numbers = [int(r) for r, in self._graph.query(self._counter_query_req)]
        if len(numbers) == 0:
            raise DataStoreError(u"No counter for class %s (has disappeared)" % self._class_uri)
        elif len(numbers) > 1:
            raise DataStoreError(u"Multiple counter for class %s" % self._class_uri)

        return u"%s%d" % (self._prefix, numbers[0])


