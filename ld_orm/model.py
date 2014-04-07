import json
from urlparse import urlparse
from exceptions import Exception
from weakref import WeakKeyDictionary
from rdflib import Graph
import logging

logger = logging.getLogger("ld_orm")
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
logger.addHandler(ch)


def default_model_generator():
    from ld_orm.extraction.attribute import AttributeExtractor
    attr_extractor = AttributeExtractor()
    return ModelGenerator(attr_extractor)


class UnknownClassNameError(Exception):
    """ When a local (file://) URL has been deduced from the class name.
        This happens when the class name is not defined in the context
    """
    pass


class Model(object):
    pass

    # class __metaclass__(type):
    #     def __new__(mcs, name, bases, attributes):
    #         #if "__slots__" not in attributes:
    #         #    attributes.update(__slots__=[])
    #         if name != "Model":
    #             if "class_uri" not in attributes:
    #                 raise NoClassUriError("Please give a class_uri attribute for the class %s" % name)
    #
    #         mcs.plop()
    #
    #         print bases
    #
    #         cls = type.__new__(mcs, name, bases, attributes)
    #         return cls
    #
    #     @classmethod
    #     def plop(cls):
    #         print "Plop"


class ModelGenerator(object):

    def __init__(self, attr_manager):
        self.attr_manager = attr_manager

    def generate(self, class_name, context, graph):
        """
            Generates a model class
        """
        class_uri = self._extract_class_uri(class_name, context)
        attributes = self.attr_manager.extract(class_uri, context, graph)
        attributes.update({"class_uri": class_uri,
                           "context": context,
                           "graph": graph})
        return type(class_name, (Model,), attributes)

    def _extract_class_uri(self, class_name, context):
        """
            Extracts the class URI as the type of a blank node
        """
        g = Graph().parse(data=json.dumps({"@type": class_name}),
                            context=context, format="json-ld")
        class_uri = str(g.objects().next())

        # Check the URI
        result = urlparse(class_uri)
        if result.scheme == "file":
            raise UnknownClassNameError("Deduced URI %s is not a valid HTTP URL" % class_uri)
        return class_uri
