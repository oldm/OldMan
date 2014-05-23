import logging
from rdflib import RDF, URIRef
from oldman.exception import AlreadyAllocatedModelError, OMInternalError


class ModelRegistry(object):
    """ A :class:`~oldman.management.registry.ModelRegistry` object registers
        the :class:`~oldman.model.Model` objects.

        Its main function is to find and order models from a set of class IRIs
        (this ordering is crucial when creating new :class:`~oldman.resource.Resource` objects).
        See :func:`~oldman.management.registry.ModelRegistry.find_models_and_types` for more details.

    """

    def __init__(self):
        self._model_classes = {}
        self._model_names = {}
        self._default_model_name = None
        #Only IRIs in this dict
        self._model_descendants = {}
        self._type_set_cache = {}
        self._logger = logging.getLogger(__name__)

    def register(self, model, is_default=False):
        """Registers a :class:`~oldman.model.Model` object.

        :param model: the :class:`~oldman.model.Model` object to register.
        :param is_default: If `True`, sets the model as the default model. Defaults to `False`.
        """
        class_iri = model.class_iri
        self._logger.info("Register model %s (%s)" % (model.name, class_iri))
        if class_iri in self._model_classes:
            raise AlreadyAllocatedModelError(u"%s is already allocated to %s" %
                                             (class_iri, self._model_classes[class_iri]))
        if model.name in self._model_names:
            raise AlreadyAllocatedModelError(u"%s is already allocated to %s" %
                                             (model.name, self._model_names[model.name].class_iri))
        sub_model_iris = set()
        # The new is not yet in this list
        for m in self._model_classes.values():
            if class_iri in m.ancestry_iris:
                sub_model_iris.add(m.class_iri)

        self._model_descendants[class_iri] = sub_model_iris
        self._model_classes[class_iri] = model
        self._model_names[model.name] = model
        # Clears the cache
        self._type_set_cache = {}

        if is_default:
            if self._default_model_name is not None:
                self._logger.warn(u"Default model name overwritten: %s" % model.name)
            self._default_model_name = model.name

    def unregister(self, model):
        """Un-registers a :class:`~oldman.model.Model` object.

        :param model: the :class:`~oldman.model.Model` object to remove from the registry.
        """
        self._model_classes.pop(model.class_iri)
        self._model_descendants.pop(model.class_iri)
        self._model_names.pop(model.name)
        # Clears the cache
        self._type_set_cache = {}

    def get_model(self, class_iri):
        """Gets a :class:`~oldman.model.Model` object.

        :param class_iri: IRI of a RDFS class
        :return: A :class:`~oldman.model.Model` object or `None` if not found
        """
        return self._model_classes.get(class_iri)

    def find_models_and_types(self, type_set):
        """Finds the leaf models from a set of class IRIs and orders them.
        Also returns an ordered list of the RDFS class IRIs that
        come from `type_set` or were deduced from it.

        Leaf model ordering is important because it determines:

           1. the IRI generator to use (the one of the first model);
           2. method inheritance priorities between leaf models.

        Resulting orderings are cached.

        :param type_set: Set of RDFS class IRIs.
        :return: An ordered list of leaf :class:`~oldman.model.Model` objects
                 and an ordered list of RDFS class IRIs.
        """
        if type_set is None or len(type_set) == 0:
            if self._default_model_name is None:
                raise OMInternalError(u"No default model defined!")

            return [self._model_names[self._default_model_name]], []

        if isinstance(type_set, list):
            type_set = set(type_set)
        cache_entry = self._type_set_cache.get(tuple(type_set))
        if cache_entry is not None:
            leaf_models, types = cache_entry
            # Protection against mutation
            return list(leaf_models), list(types)

        leaf_models = self._find_leaf_models(type_set)
        leaf_model_iris = [m.class_iri for m in leaf_models]
        ancestry_class_iris = {t for m in leaf_models for t in m.ancestry_iris}.difference(leaf_model_iris)
        independent_class_iris = type_set.difference(leaf_model_iris).difference(ancestry_class_iris)

        types = leaf_model_iris + list(independent_class_iris) + list(ancestry_class_iris)
        pair = (leaf_models, types)
        self._type_set_cache[tuple(type_set)] = pair
        # If type_set was not exhaustive
        self._type_set_cache[tuple(set(types))] = pair

        # Protection against mutation
        return list(leaf_models), list(types)

    def _find_leaf_models(self, type_set):
        leaf_models = []
        for type_iri in type_set:
            descendants = self._model_descendants.get(type_iri)
            if (descendants is not None) and (len(descendants.intersection(type_set)) == 0):
                model = self._model_classes[type_iri]
                assert(model.class_iri == type_iri)
                leaf_models.append(model)

        if len(leaf_models) == 0:
            return [self._model_names[self._default_model_name]]
        return self._sort_leaf_models(leaf_models)

    def _sort_leaf_models(self, leaf_models):
        """TODO: propose some vocabulary to give priorities."""
        if len(leaf_models) > 1:
            self._logger.warn(u"Arbitrary order between leaf models %s" % [m.name for m in leaf_models])
        return leaf_models