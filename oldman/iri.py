from uuid import uuid1
from .exception import OMDataStoreError, OMRequiredHashlessIRIError


class IriGenerator(object):
    """An :class:`~oldman.iri.IriGenerator` object generates
    the IRIs of some new :class:`~oldman.resource.Resource` objects.
    """

    def __init__(self):
        pass

    def generate(self, **kwargs):
        """Generates an IRI.

        :return: Unique IRI (unicode string).
        """
        raise NotImplementedError()


class PrefixedUUIDIriGenerator(IriGenerator):
    """Uses a prefix, a fragment and a unique UUID1 number to generate IRIs.

    Recommended generator because UUID1 is robust and fast (no DB access).

    :param prefix: IRI prefix.
    :param fragment: IRI fragment to append to the hash-less IRI. Defaults to `None`.
    """

    def __init__(self, prefix, fragment=None):
        self._prefix = prefix
        self._fragment = fragment

    def generate(self, **kwargs):
        """See :func:`oldman.iri.IriGenerator.generate`."""
        partial_iri = _skolemize(prefix=self._prefix)
        if self._fragment is not None:
            return u"%s#%s" % (partial_iri, self._fragment)
        return partial_iri


class BlankNodeIriGenerator(PrefixedUUIDIriGenerator):
    """Generates skolem IRIs that denote blank nodes.

    :param hostname: Defaults to `"localhost"`.
    """

    def __init__(self, hostname=u"localhost"):
        prefix = u"http://%s/.well-known/genid/" % hostname
        PrefixedUUIDIriGenerator.__init__(self, prefix=prefix)


class IncrementalIriGenerator(IriGenerator):
    """Generates IRIs with short numbers.

    Beautiful but **slow** in concurrent settings. The number generation implies a critical section
    and a sequence of two SPARQL requests, which represents a significant bottleneck.

    :param prefix: IRI prefix.
    :param graph: :class:`rdflib.Graph` object where to store the counter.
    :param class_iri: IRI of the RDFS class of which new :class:`~oldman.resource.Resource` objects are instance of.
                      Usually corresponds to the class IRI of the :class:`~oldman.model.Model` object that
                      owns this generator.
    :param fragment: IRI fragment to append to the hash-less IRI. Defaults to `None`.
    """

    def __init__(self, prefix, data_store, class_iri, fragment=None):
        self._prefix = prefix
        self._data_store = data_store
        self._class_iri = class_iri
        self._fragment = fragment

        self._data_store.check_and_repair_counter(class_iri)

    def generate(self, **kwargs):
        """See :func:`oldman.iri.IriGenerator.generate`."""
        number = self._data_store.generate_instance_number(self._class_iri)

        partial_iri = u"%s%d" % (self._prefix, number)
        if self._fragment is not None:
            return u"%s#%s" % (partial_iri, self._fragment)
        return partial_iri

    def reset_counter(self):
        """
        For test purposes only
        """
        self._data_store.reset_instance_counter(self._class_iri)


class UUIDFragmentIriGenerator(IriGenerator):
    """Generates an hashed IRI from a hash-less IRI.

    Its fragment is a unique UUID1 number.
    """

    def generate(self, hashless_iri, **kwargs):
        """See :func:`oldman.iri.IriGenerator.generate`."""
        if hashless_iri is None:
            raise OMRequiredHashlessIRIError(u"Hash-less IRI is required to generate an IRI")
        if '#' in hashless_iri:
            raise OMRequiredHashlessIRIError(u"%s is not a valid hash-less IRI" % hashless_iri)
        return u"%s#%s" % (hashless_iri, uuid1().hex)


def _skolemize(prefix=u"http://localhost/.well-known/genid/"):
    return u"%s%s" % (prefix, uuid1().hex)
