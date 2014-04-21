from rdflib_jsonld.context import Context, UNDEF


class LDAttributeMdExtractor(object):
    def update(self, properties, context_js, graph):
        """
            No property added, only attribute metadata
        """
        raise NotImplementedError()


class JsonLdContextAttributeMdExtractor(LDAttributeMdExtractor):
    """
        Extracts name and basic type (if available) from the context
    """

    def update(self, properties, context_js, graph):
        context = Context(context_js)

        for property_uri, property in properties.iteritems():
            # Efficient search
            term = context.find_term(property_uri)
            if term:
                self._update_property(property, term)
            else:
                # May not have been found because of its type
                terms = [t for t in context.terms.values()
                         if t.id == property_uri]
                if len(terms) > 0:
                    for term in terms:
                        self._update_property(property, term)

                # Not declared (worst case)
                elif len(property_uri) == 0:
                    name = graph.qname(property_uri).replace(":", "_")
                    print u"No short name found for property %s. QName %s used instead" % (property_uri, name)
                    property.add_attribute_metadata(name)

    def _update_property(self, property, term):
        kwargs = {'jsonld_type': term.type,
                  'language': term.language,
                  'container': term.container,
                  'reverse': term.reverse}
        clean_fct = lambda v: None if v == UNDEF else v
        kwargs = {k: clean_fct(v) for k, v in kwargs.iteritems()}
        property.add_attribute_metadata(term.name, **kwargs)