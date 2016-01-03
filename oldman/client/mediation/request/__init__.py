class Request(object):
    pass


class GetRequest(Request):
    """
    TODO: explain

    Gets all the types

    :param iri: IRI of the object
    :param rdf_properties: TODO: explain
    :param required_types: for validation purposes. May also have other types. Optional.

    """

    def __init__(self, iri, expected_properties, required_types=None):
        self._iri = iri
        self._required_types = required_types
        self._rdf_properties = expected_properties

    @property
    def iri(self):
        return self._iri

    @property
    def required_types(self):
        return list(self._required_types)

    @property
    def expected_properties(self):
        return list(self._rdf_properties)

    def to_sparql_select(self):
        # TODO: deal with lists
        return u"SELECT ?s ?p ?o " + self._get_sparql_body()

    def to_sparql_construct(self):
        # TODO: deal with lists
        return u"CONSTRUCT { ?s ?p ?o } " + self._get_sparql_body()

    def _get_where_clause(self):
        # TODO: get the list items

        direct_properties = {"%s" % p.iri for p in self._rdf_properties
                             if not p.is_reversed}
        reversed_properties = [p for p in self._rdf_properties
                               if p.is_reversed]

        if len(reversed_properties) == 0:
            return """\n WHERE {
                  ?s ?p ?o .
                  VALUES ?s { ?subject }
                  VALUES ?p { rdf:type ?direct_properties }
            }""".replace(
                "?subject", "<%s>" % self._iri).replace(
                "?direct_properties", " ".join(direct_properties)
            )
        else:
            return """\n WHERE {
               {
                  ?s ?p ?o .
                  VALUES ?s { ?subject }
                  VALUES ?p { ?direct_properties }
               }
               UNION
               {
                 ?s ?p ?o .
                 VALUES ?o { ?subject }
                 VALUES ?p { ?reverse_properties }
               }
            }""".replace(
                "?subject", "<%s>" % self._iri).replace(
                "?direct_properties", " ".join(direct_properties)
            ).replace(
                "?reversed_properties", " ".join(reversed_properties)
            )




