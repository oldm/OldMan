from threading import Lock
from uuid import uuid1
from .exception import OMDataStoreError, OMRequiredBaseIRIError


class IriGenerator(object):

    def __init__(self, **kwargs):
        pass

    def generate(self, **kwargs):
        raise NotImplementedError()


class RandomPrefixedIriGenerator(IriGenerator):

    def __init__(self, prefix, fragment=None):
        self._prefix = prefix
        self._fragment = fragment

    def generate(self, **kwargs):
        partial_iri = skolemize(prefix=self._prefix)
        if self._fragment is not None:
            return u"%s#%s" % (partial_iri, self._fragment)
        return partial_iri


class BlankNodeIriGenerator(RandomPrefixedIriGenerator):

    def __init__(self, hostname=u"localhost"):
        prefix = u"http://%s/.well-known/genid/" % hostname
        RandomPrefixedIriGenerator.__init__(self, prefix=prefix)


class IncrementalIriGenerator(IriGenerator):
    """
        Generates IRIs with short numbers.

        Slow in concurrent settings: number generation implies a critical section
        of two SPARQL requests. It is a significant bottleneck.
    """

    mutex = Lock()

    def __init__(self, prefix, graph, class_iri, fragment=None):
        self._prefix = prefix
        self._graph = graph
        self._class_iri = class_iri
        self._fragment = fragment

        self._counter_query_req = u"""
            prefix ldorm: <http://localhost/ldorm#>
            SELECT ?number
            WHERE {
                ?class_uri ldorm:nextNumber ?number .
            }""".replace("?class_uri", u"<%s>" % self._class_iri)

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
            }""".replace("?class_uri", "<%s>" % self._class_iri)

        numbers = list(self._graph.query(self._counter_query_req))
        # Inits if no counter
        if len(numbers) == 0:
            self.reset_counter()
        elif len(numbers) > 1:
            raise OMDataStoreError(u"Multiple counter for class %s" % self._class_iri)

    def reset_counter(self):
        self._graph.update(u"""
            prefix ldorm: <http://localhost/ldorm#>
            INSERT {
                <%s> ldorm:nextNumber 0 .
                } WHERE {}""" % self._class_iri)

    def generate(self, **kwargs):
        # Critical section
        self.mutex.acquire()
        try:
            self._graph.update(self._counter_update_req)
            numbers = [int(r) for r, in self._graph.query(self._counter_query_req)]
        finally:
            self.mutex.release()

        if len(numbers) == 0:
            raise OMDataStoreError(u"No counter for class %s (has disappeared)" % self._class_iri)
        elif len(numbers) > 1:
            raise OMDataStoreError(u"Multiple counter for class %s" % self._class_iri)

        partial_iri = u"%s%d" % (self._prefix, numbers[0])
        if self._fragment is not None:
            return u"%s#%s" % (partial_iri, self._fragment)
        return partial_iri


class RandomFragmentIriGenerator(IriGenerator):

    def generate(self, base_iri):
        if base_iri is None:
            raise OMRequiredBaseIRIError(u"Base IRI is required to generate an IRI")
        if '#' in base_iri:
            raise OMRequiredBaseIRIError(u"%s is not a valid base IRI" % base_iri)
        return u"%s#%s" % (base_iri, uuid1().hex)


def skolemize(prefix=u"http://localhost/.well-known/genid/"):
    return u"%s%s" % (prefix, uuid1().hex)
