from oldman.model.model import Model


class StoreModel(Model):
    """
    :param name: Model name. Usually corresponds to a JSON-LD term or to a class IRI.
    :param class_iri: IRI of the RDFS class represented by this :class:`~oldman.model.Model` object.
    :param ancestry_iris: ancestry of the attribute `class_iri`.
                          Each instance of `class_iri` is also instance of these classes.
    :param context: An IRI, a `list` or a `dict` that describes the JSON-LD context.
                    See `<http://www.w3.org/TR/json-ld/#the-context>`_ for more details.
    :param om_attributes: `dict` of :class:`~oldman.model.attribute.OMAttribute` objects. Keys are their names.
    :param id_generator: :class:`~oldman.iri.IriGenerator` object that generates IRIs from new
                         :class:`~oldman.resource.Resource` objects.
    :param methods: `dict` of Python functions that takes as first argument a
                    :class:`~oldman.resource.Resource` object. Keys are the method names.
                    Defaults to `{}`. TODO: see if is still needed.
    :param operations: TODO: describe.
    :param local_context: TODO: describe.
    """

    def __init__(self, name, class_iri, ancestry_iris, context, om_attributes,
                 id_generator, operations=None, local_context=None):
        Model.__init__(self, name, class_iri, ancestry_iris, context, om_attributes,
                       id_generator.is_generating_blank_nodes, operations=operations,
                       local_context=local_context)
        self._id_generator = id_generator

    def generate_permanent_id(self, previous_id):
        """Generates a new OMId object.

        Used by the :class:`~oldman.resource.store.StoreResource` class but an end-user
        should not need to call it.

        :return: A new OMId object.
        """
        return self._id_generator.generate_permanent_id(previous_id)

    def reset_counter(self):
        """Resets the counter of the ID generator.

        Please use it only for test purposes.
        """
        if hasattr(self._id_generator, "reset_counter"):
            self._id_generator.reset_counter()