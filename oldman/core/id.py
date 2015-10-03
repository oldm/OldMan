from urlparse import urlparse
from uuid import uuid1

from oldman.core.common import is_blank_node, TEMPORARY_BNODE_PREFIX
from oldman.core.exception import OMRequiredHashlessIRIError, OMIriError, OMUnsupportedUserIRIError


class OMId:
    """TODO: explain why an ID object and not a simple IRI. An ID can be temporary.

       Immutable data structure.
    """
    def __init__(self, iri, is_permanent):
        parse_result = urlparse(iri)
        if parse_result.scheme == '' or parse_result.path == '':
            # TODO: find a better exception
            raise OMIriError(u"Only IRI with a scheme and a path are accepted (IRI given: %s)" % iri)
        self._iri = iri
        self._is_permanent = is_permanent
        self._is_bnode = is_blank_node(self._iri)

    @property
    def iri(self):
        return self._iri

    @property
    def is_permanent(self):
        return self._is_permanent

    @property
    def is_blank_node(self):
        """TODO: explain """
        return self._is_bnode

    @property
    def hashless_iri(self):
        """TODO: explain """
        split_index = self._iri.find('#')
        if split_index == -1:
            return self._iri
        return self._iri[:split_index]

    @property
    def fragment(self):
        """TODO: explain """
        split_index = self._iri.find('#')
        if split_index == -1:
            return ""
        return self._iri[split_index+1:]

    def __str__(self):
        return self._iri


class TemporaryId(OMId):
    """TODO: describe """
    def __init__(self, suggested_hashless_iri=None, suggested_iri_fragment=None, collection_iri=None,
                 can_remain_bnode=True):

        if suggested_hashless_iri is not None and collection_iri is not None:
            #TODO: find a better exception
            raise Exception("suggested_hashless_iri and collection_iri must not be given in the same time")

        # The temporary id must be blank node. In order to reuse the hashless iri,
        # it must correspond to a skolemized bnode.
        if suggested_hashless_iri is not None and is_blank_node(suggested_hashless_iri):
            hashless_iri = suggested_hashless_iri
        else:
            hashless_iri = None

        if suggested_iri_fragment is not None and hashless_iri is not None:
            iri = hashless_iri + "#" + suggested_iri_fragment

        elif hashless_iri is not None:
            iri = generate_iri_with_uuid_fragment(hashless_iri)
        else:
            iri = generate_uuid_iri(prefix=TEMPORARY_BNODE_PREFIX, fragment=suggested_iri_fragment)

        try:
            OMId.__init__(self, iri, False)
        except OMIriError, e:
            # Temporary Ids are only generated by the client side. More specific type returned.
            raise OMUnsupportedUserIRIError(e.message)

        self._can_remain_bnode = self._is_bnode and can_remain_bnode
        self._collection_iri = collection_iri

        self._suggested_hashless_iri = suggested_hashless_iri
        self._suggested_fragment = suggested_iri_fragment

    @property
    def suggested_hashless_iri(self):
        """TODO: explain """
        return self._suggested_hashless_iri

    @property
    def suggested_fragment(self):
        """TODO: explain """
        return self._suggested_fragment

    @property
    def collection_iri(self):
        return self._collection_iri

    @property
    def can_remain_bnode(self):
        """ Returns True if is currently a blank node
        and may remain it before being stored.
        """
        return self._can_remain_bnode


class PermanentId(OMId):
    """TODO: explain """
    def __init__(self, iri):
        OMId.__init__(self, iri, True)


def generate_iri_with_uuid_fragment(hashless_iri):
    """TODO: describe"""
    if hashless_iri is None:
        raise OMRequiredHashlessIRIError(u"Hash-less IRI is required to generate an IRI")
    if '#' in hashless_iri:
        raise OMRequiredHashlessIRIError(u"%s is not a valid hash-less IRI" % hashless_iri)
    return u"%s#%s" % (hashless_iri, uuid1().hex)


def generate_uuid_iri(prefix=u"http://localhost/.well-known/genid/", fragment=None):
    """TODO: describe"""
    hashless_iri = u"%s%s" % (prefix, uuid1().hex)
    if fragment is not None:
        return hashless_iri + "#" + fragment
    return hashless_iri