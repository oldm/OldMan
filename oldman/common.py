DATATYPE_PROPERTY = "datatype"
OBJECT_PROPERTY = "object"

TMP_IRI_PREFIX = "http://localhost/.well-known/oldman/tmp-uri/"


def is_temporary_iri(iri):
    return iri.startswith(TMP_IRI_PREFIX)
