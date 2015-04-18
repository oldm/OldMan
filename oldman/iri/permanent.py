from uuid import uuid1
from oldman.exception import OMRequiredHashlessIRIError
from oldman.iri.id import generate_uuid_iri, PermanentId


class PermanentIDGenerator(object):
    """An :class:`~oldman.iri.permanent.PermanentIDGenerator` object generates
    the :class:`~oldman.iri.id.OMId`s of some new :class:`~oldman.resource.resource.Resource` objects.
    """

    def __init__(self, is_generating_blank_nodes):
        self._is_generating_blank_nodes = is_generating_blank_nodes

    @property
    def is_generating_blank_nodes(self):
        """TODO: remove"""
        return self._is_generating_blank_nodes

    def generate_permanent_id(self, temporary_id):
        """Generates an ID.

        :return: A PermanentID.
        """
        raise NotImplementedError()


class PrefixedUUIDPermanentIDGenerator(PermanentIDGenerator):
    """Uses a prefix, a fragment and a unique UUID1 number to generate IRIs.

    Recommended generator because UUID1 is robust and fast (no DB access).

    :param prefix: IRI prefix.
    :param fragment: IRI fragment to append to the hash-less IRI. Defaults to `None`.
    """

    def __init__(self, prefix, fragment=None, is_generating_blank_nodes=False):
        PermanentIDGenerator.__init__(self, is_generating_blank_nodes)
        self._prefix = prefix
        self._fragment = fragment

    def generate_permanent_id(self, ignored_tmp_id):
        """See :func:`oldman.iri.permanent.PermanentIDGenerator.generate_permanent_id`."""
        partial_iri = generate_uuid_iri(prefix=self._prefix)
        if self._fragment is not None:
            iri = u"%s#%s" % (partial_iri, self._fragment)
        else:
            iri = partial_iri
        return PermanentId(iri)


class BlankNodePermanentIDGenerator(PrefixedUUIDPermanentIDGenerator):
    """Generates skolem IRIs that denote blank nodes.

    :param hostname: Defaults to `"localhost"`.
    """

    def __init__(self, hostname=u"localhost"):
        prefix = u"http://%s/.well-known/genid/" % hostname
        PrefixedUUIDPermanentIDGenerator.__init__(self, prefix, is_generating_blank_nodes=True)


class IncrementalIriGenerator(PermanentIDGenerator):
    """Generates IRIs with short numbers.

    Beautiful but **slow** in concurrent settings. The number generation implies a critical section
    and a sequence of two SPARQL requests, which represents a significant bottleneck.

    :param prefix: IRI prefix.
    :param store: TODO: describe.
    :param graph: :class:`rdflib.Graph` object where to store the counter.
    :param class_iri: IRI of the RDFS class of which new :class:`~oldman.resource.Resource` objects are instance of.
                      Usually corresponds to the class IRI of the :class:`~oldman.model.Model` object that
                      owns this generator.
    :param fragment: IRI fragment to append to the hash-less IRI. Defaults to `None`.
    """

    def __init__(self, prefix, store, class_iri, fragment=None):
        PermanentIDGenerator.__init__(self, is_generating_blank_nodes=False)
        self._prefix = prefix
        self._store = store
        self._class_iri = class_iri
        self._fragment = fragment

        self._store.check_and_repair_counter(class_iri)

    def generate_permanent_id(self, ignored_tmp_id):
        """See :func:`oldman.iri.permanent.PermanentIDGenerator.generate_permanent_id`."""
        number = self._store.generate_instance_number(self._class_iri)

        partial_iri = u"%s%d" % (self._prefix, number)
        if self._fragment is not None:
            iri = u"%s#%s" % (partial_iri, self._fragment)
        else:
            iri = partial_iri
        return PermanentId(iri)

    def reset_counter(self):
        """
        For test purposes only
        """
        self._store.reset_instance_counter(self._class_iri)


class UUIDFragmentPermanentIDGenerator(PermanentIDGenerator):
    """Generates an hashed IRI from a hash-less IRI.

    Its fragment is a unique UUID1 number.
    """
    def __init__(self):
        PermanentIDGenerator.__init__(self, is_generating_blank_nodes=False)

    def generate_permanent_id(self, temporary_id):
        """See :func:`oldman.iri.permanent.PermanentIDGenerator.generate_permanent_id`."""
        hashless_iri = temporary_id.suggested_hashless_iri
        if hashless_iri is None:
            raise OMRequiredHashlessIRIError(u"A suggested hash-less IRI is required to generate an IRI")
        if '#' in hashless_iri:
            raise OMRequiredHashlessIRIError(u"%s is not a valid hash-less IRI" % hashless_iri)
        return PermanentId(u"%s#%s" % (hashless_iri, uuid1().hex))
