import logging
"""
oldman.management.cache
~~~~~~~~~~~~~~~~~~~~~~~

TODO: document

"""


class ResourceCache(object):
    """TODO: document"""

    def __init__(self, cache_region):
        self._region = cache_region
        self._logger = logging.getLogger(__name__)

    @property
    def is_active(self):
        return self._region is not None

    @property
    def cache_region(self):
        self._region

    def change_cache_region(self, cache_region):
        """First usecase: testing"""
        self._region = cache_region

    def get_resource(self, id):
        if id is None or self._region is None:
            return None
        resource = self._region.get(unicode(id))
        if resource:
            self._logger.debug(u"%s found in the cache." % resource.id)
        return resource

    def set_resource(self, resource):
        if self._region is not None:
            self._region.set(unicode(resource.id), resource)
            self._logger.debug(u"%s cached." % resource.id)

    def remove_resource(self, resource):
        if self._region is not None:
            self._region.delete(unicode(resource.id))
            self._logger.debug(u"%s removed from the cache." % resource.id)

    def remove_resource_from_id(self, id):
        """:func:`~oldman.management.cache.ResourceCache.remove_resource` is usually preferred."""
        if self._region is not None:
            self._region.delete(unicode(id))
            self._logger.debug(u"%s removed from the cache." % id)

    def invalidate_cache(self):
        if self._region is not None:
            self._region.invalidate()