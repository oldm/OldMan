import logging
from rdflib_jsonld.context import Context, UNDEF


class OMAttributeMdExtractor(object):
    """An :class:`~oldman.parsing.schema.context.OMAttributeMdExtractor` object
    extracts :class:`~oldman.attribute.OMAttributeMetadata` tuples
    and transmits them to :class:`~oldman.property.OMProperty` objects.
    """

    def update(self, om_properties, context_js, schema_graph):
        """Updates the :class:`~oldman.property.OMProperty` objects by transmitting
        them extracted :class:`~oldman.attribute.OMAttributeMetadata` tuples.

        :param om_properties: `dict` of :class:`~oldman.property.OMProperty` objects indexed
                              by their IRIs.
        :param context_js: JSON-LD context.
        :param schema_graph: :class:`rdflib.graph.Graph` object.
        """
        raise NotImplementedError()


class JsonLdContextAttributeMdExtractor(OMAttributeMdExtractor):
    """:class:`~oldman.parsing.schema.context.OMAttributeMdExtractor` objects
    that extract attribute names and datatypes from the JSON-LD context.
    """

    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def update(self, om_properties, context_js, schema_graph):
        """See :func:`oldman.parsing.schema.context.OMAttributeMdExtractor.update`."""
        context = Context(context_js)

        for (property_iri, reversed), om_property in om_properties.iteritems():
            # Efficient search
            term = context.find_term(property_iri)
            if term:
                self._update_property(om_property, term)
            else:
                # May not have been found because of its type
                terms = [t for t in context.terms.values()
                         if t.id == property_iri]
                if len(terms) > 0:
                    for term in terms:
                        self._update_property(om_property, term)

                # Not declared (worst case)
                elif len(property_iri) == 0:
                    name = schema_graph.qname(property_iri).replace(":", "_")
                    self._logger.warn(u"No short name found for property %s. QName %s used instead"
                                      % (property_iri, name))
                    om_property.add_attribute_metadata(name)

    def _update_property(self, om_property, term):
        reversed = bool(term.reverse)
        if reversed is not om_property.reversed:
            self._logger.info(u"The term %s (reversed: %s) does not match with property %s (reversed: %s)"
                              % (term.name, reversed, om_property.iri, om_property.reversed))
            return

        kwargs = {'jsonld_type': term.type,
                  'language': term.language,
                  'container': term.container}
        clean_fct = lambda v: None if v == UNDEF else v
        kwargs = {k: clean_fct(v) for k, v in kwargs.iteritems()}
        om_property.add_attribute_metadata(term.name, reversed=reversed, **kwargs)