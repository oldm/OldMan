# coding=utf-8
import logging


class ResourceCache(object):
    """A :class:`~oldman.management.cache.ResourceCache` object caches
    :class:`~oldman.resource.Resource` objects.

    It interfaces a :class:`dogpile.cache.region.CacheRegion` front-end object.
    If not `None`, `cache_region` must be already configured, i.e. mapped to a back-end
    (like `Memcache <http://memcached.org/>`_ or `Redis <http://redis.io/>`_).
    See `the official list of back-ends
    <http://dogpilecache.readthedocs.org/en/latest/api.html#module-dogpile.cache.backends.memory>`_ supported
    by `dogpile.cache <https://bitbucket.org/zzzeek/dogpile.cache>`_.

    When `cache_region` is None, no effective caching is done.
    However, methods :func:`~oldman.management.cache.ResourceCache.get_resource`,
    :func:`~oldman.management.cache.ResourceCache.set_resource`
    and :func:`~oldman.management.cache.ResourceCache.remove_resource` can still safely be
    called. They just have no effect.

    :param cache_region: :class:`dogpile.cache.region.CacheRegion` object.
                         This object must already be configured.
                         Defaults to None (no cache).
    """

    def __init__(self, cache_region):
        self._region = cache_region
        self._logger = logging.getLogger(__name__)

    @property
    def cache_region(self):
        """:class:`dogpile.cache.region.CacheRegion` object. May be `None`."""
        return self._region

    def is_active(self):
        """:return: `True` if the `cache_region` is active."""
        return self._region is not None

    def change_cache_region(self, cache_region):
        """Replaces the `cache_region` attribute.

        :param cache_region: :class:`dogpile.cache.region.CacheRegion` object.
                              May be `None`.
        """
        self._region = cache_region

    def get_resource(self, id):
        """Gets a :class:`~oldman.resource.Resource` object from the cache.

        :param id: IRI of the resource.
        :return: :class:`~oldman.resource.Resource` object or `None` if not found.
        """
        if id is None or self._region is None:
            return None
        resource = self._region.get(unicode(id))
        if resource:
            self._logger.debug(u"%s found in the cache." % resource.id)
            return resource
        return None

    def set_resource(self, resource):
        """Adds or updates a :class:`~oldman.resource.Resource` object in the cache.

        Its key is its `ìd`.

        :param resource: :class:`~oldman.resource.Resource` object to add to the cache (or update).
        """
        if self._region is not None:
            self._region.set(unicode(resource.id), resource)
            self._logger.debug(u"%s cached." % resource.id)

    def remove_resource(self, resource):
        """Removes a :class:`~oldman.resource.Resource` object from the cache.

        Indempotent (no problem if the :class:`~oldman.resource.Resource` object is not the
        cache). Does nothing if `cache_region` is `None`.

        :param resource: :class:`~oldman.resource.Resource` object to remove from the cache."""
        if self._region is not None:
            self._region.delete(unicode(resource.id))
            self._logger.debug(u"%s removed from the cache." % resource.id)

    def remove_resource_from_id(self, id):
        """:func:`~oldman.management.cache.ResourceCache.remove_resource` is usually preferred.

        Indempotent and does nothing if `cache_region` is `None`.

        :param id: IRI of the resource to remove from the cache.
        """
        if self._region is not None:
            self._region.delete(unicode(id))
            self._logger.debug(u"%s removed from the cache." % id)

    def invalidate_cache(self):
        """See :func:`dogpile.cache.region.CacheRegion.invalidate`.

        .. admonition:: Warning

            Please note that this method is not supported by some :class:`dogpile.cache.api.CacheBackend`
            objects. In such a case, this method has no effect so entries must be removed **explicitly**
            from their keys.
        """
        if self._region is not None:
            self._region.invalidate()