from weakref import WeakValueDictionary
from rdflib import URIRef, Graph
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.parser import ParseException
from .resource import Resource
from .exception import OMReservedAttributeNameError, OMClassInstanceError, OMSPARQLParseError
from .exception import OMAttributeAccessError
from oldman.utils.sparql import build_query_part


class Model(object):

    def __init__(self, name, class_iri, om_attributes, context, id_generator, class_types,
                 manager, methods=None):
        reserved_names = ["id", "base_iri", "_types", "types"]
        for field in reserved_names:
            if field in om_attributes:
                raise OMReservedAttributeNameError("%s is reserved" % field)

        self._context = clean_context(context)
        self._class_iri = class_iri
        self._om_attributes = om_attributes
        self._id_generator = id_generator
        self._class_types = class_types
        self._manager = manager
        self._methods = methods if methods else {}

        registry = manager.model_registry
        registry.register(self, name)

        #TODO: move cache management away from models
        self._cache = WeakValueDictionary()
        if class_iri:
            self._check_type_request = prepareQuery(u"ASK {?s a <%s> }" % class_iri)
        else:
            self._check_type_request = None

    @property
    def class_iri(self):
        return self._class_iri

    @property
    def class_types(self):
        return list(self._class_types)

    @property
    def om_attributes(self):
        return dict(self._om_attributes)

    @property
    def methods(self):
        return dict(self._methods)

    @property
    def context(self):
        return self._context

    def is_subclass_of(self, model):
        """
            rdfs:subClassOf test
        """
        if self == model:
            return True
        if not isinstance(model, Model):
            return False
        return model.class_iri in self.class_types

    def access_attribute(self, name):
        try:
            return self._om_attributes[name]
        except KeyError:
            raise OMAttributeAccessError("%s has no supported attribute %s" % (self, name))

    def generate_iri(self, **kwargs):
        return self._id_generator.generate(**kwargs)

    def reset_counter(self):
        """
            To be called after clearing the storage graph.
            For unittest purposes.
        """
        if hasattr(self._id_generator, "reset_counter"):
            self._id_generator.reset_counter()

    def new(self, **kwargs):
        types = list(self._class_types)
        if "types" in kwargs:
            #TODO: clarify the ordering
            new_types = kwargs.pop("types")
            types += [t for t in new_types if t not in types]

        return Resource(self._manager, types=types, **kwargs)

    def create(self, **kwargs):
        """
            Creates a new instance and saves it
        """
        return self.new(**kwargs).save()

    def clear_cache(self):
        """ Clears its cache """
        self._cache.clear()

    def filter(self, **kwargs):
        if "id" in kwargs:
            return self.get(**kwargs)

        lines = u""
        for name, value in kwargs.iteritems():
            # May raise a LDAttributeAccessError
            attr = self.access_attribute(name)
            value = kwargs[name]
            if value:
                lines += attr.serialize_values_into_lines(value)

        query = build_query_part(u"SELECT ?s WHERE", u"?s", lines)
        #print query
        try:
            results = self._manager.default_graph.query(query)
        except ParseException as e:
            raise OMSPARQLParseError(u"%s\n %s" % (query, e))

        # Generator expression
        return (self.get(id=str(r)) for r, in results)

    def get(self, id=None, **kwargs):
        if id:
            return self._get_by_id(id)

        # First found
        for instance in self.filter(**kwargs):
            return instance

        return None

    def _get_by_id(self, id):
        instance = self._cache.get(id)
        if instance:
            #print "%s found in the cache" % instance
            return instance
        instance_graph = Graph()
        iri = URIRef(id)
        instance_graph += self._manager.default_graph.triples((iri, None, None))
        if self._check_type_request and not self._manager.default_graph.query(self._check_type_request,
                                                                              initBindings={'s': iri}):
            raise OMClassInstanceError(u"%s is not an instance of %s" % (id, self.class_iri))
        return self._new_instance(id, instance_graph)

    def get_any(self, id):
        """ Finds a object from any model class """
        return self._manager.get(id=id)

    def _new_instance(self, id, instance_graph):
        #print "Instance graph: %s" % instance_graph.serialize(format="turtle")
        if len(instance_graph) == 0:
            instance = self.new(id=id)
        else:
            instance = Resource.load_from_graph(self._manager, id, instance_graph, is_new=False)
        self._cache[id] = instance
        return instance


def clean_context(context):
    """
        Context can be an IRI, a list or a dict
        TODO: - make sure "id": "@id" and "type": "@type" are in
    """
    if isinstance(context, dict) and "@context" in context.keys():
        context = context["@context"]
    return context