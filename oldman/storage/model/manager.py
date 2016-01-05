from oldman.core.exception import OMInternalError
from oldman.storage.id_generation import IncrementalIriGenerator, PrefixedUUIDPermanentIDGenerator, \
    BlankNodePermanentIDGenerator
from oldman.core.model.manager import ModelManager
from oldman.storage.model.model import StoreModel


class StoreModelManager(ModelManager):

    def create_model(self, class_name_or_iri, context, store, schema_graph, iri_prefix=None,
                     iri_fragment=None, iri_generator=None, untyped=False, incremental_iri=False,
                     is_default=False):
        """Creates a :class:`~oldman.model.store.StoreModel` object.

        TODO: remove data_store from the constructor!

        To create it, they are three elements to consider:

          1. Its class IRI which can be retrieved from `class_name_or_iri`;
          2. Its JSON-LD context for mapping :class:`~oldman.attribute.OMAttribute` values to RDF triples;
          3. The :class:`~oldman.iri.IriGenerator` object that generates IRIs from new
             :class:`~oldman.resource.Resource` objects.

        The :class:`~oldman.iri.IriGenerator` object is either:

          * directly given: `iri_generator`;
          * created from the parameters `iri_prefix`, `iri_fragment` and `incremental_iri`.

        :param class_name_or_iri: IRI or JSON-LD term of a RDFS class.
        :param context: `dict`, `list` or `IRI` that represents the JSON-LD context .
        :param iri_generator: :class:`~oldman.iri.IriGenerator` object. If given, other `iri_*` parameters are
               ignored.
        :param iri_prefix: Prefix of generated IRIs. Defaults to `None`.
               If is `None` and no `iri_generator` is given, a :class:`~oldman.iri.BlankNodeIriGenerator` is created.
        :param iri_fragment: IRI fragment that is added at the end of generated IRIs. For instance, `"me"`
               adds `"#me"` at the end of the new IRI. Defaults to `None`. Has no effect if `iri_prefix` is not given.
        :param incremental_iri: If `True` an :class:`~oldman.iri.IncrementalIriGenerator` is created instead of a
               :class:`~oldman.iri.RandomPrefixedIriGenerator`. Defaults to `False`.
               Has no effect if `iri_prefix` is not given.
        :param context_file_path: TODO: describe.
        """

        return self._create_model(class_name_or_iri, context, schema_graph, iri_prefix=iri_prefix,
                                  iri_fragment=iri_fragment, iri_generator=iri_generator, untyped=untyped,
                                  incremental_iri=incremental_iri, is_default=is_default, store=store)

    def _instantiate_model(self, class_name_or_iri, class_iri, schema_graph, ancestry, context,
                           om_attributes, iri_fragment=None, iri_prefix=None, iri_generator=None,
                           incremental_iri=False, store=None):

        if store is None:
            raise OMInternalError("Store is required")

        if iri_generator is not None:
            id_generator = iri_generator
        elif iri_prefix is not None:
            if incremental_iri:
                id_generator = IncrementalIriGenerator(iri_prefix, store, class_iri, fragment=iri_fragment)
            else:
                id_generator = PrefixedUUIDPermanentIDGenerator(iri_prefix, fragment=iri_fragment)
        else:
            id_generator = BlankNodePermanentIDGenerator()

        return StoreModel(class_name_or_iri, class_iri, ancestry.bottom_up, context,
                          om_attributes, id_generator)
