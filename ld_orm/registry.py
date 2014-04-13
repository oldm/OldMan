
class ModelRegistry(object):
    """
        All model classes are registered here
    """

    def __init__(self):
        self._model_classes = {}

    def register(self, model_class):
        self._model_classes[model_class.class_uri] = model_class

    def unregister(self, model_class):
        self._model_classes.pop(model_class.class_uri)

    def get_model_class(self, class_uri):
        return self._model_classes.get(class_uri)
