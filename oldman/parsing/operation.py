from rdflib import URIRef
from oldman.vocabulary import HYDRA_SUPPORTED_OPERATION, HYDRA_METHOD, HYDRA_EXCEPTS
from oldman.vocabulary import HYDRA_RETURNS, OLDM_SHORTNAME
from oldman.resource import Resource
from oldman.operation import Operation
import logging


def get_operation_function(operation_functions, class_iri, ancestry, method):
    # The class first and its ancestors
    class_iris = [class_iri] + ancestry.parents(class_iri)
    for cls_iri in class_iris:
        method_functions = operation_functions.get(cls_iri, {})
        func = method_functions.get(method)
        if func is not None:
            return func
    return None


class OperationExtractor(object):
    """ TODO: describe
    """
    def extract(self, class_iri, ancestry, schema_graph,
                operation_implementations):
        """ TODO: describe
        """
        raise NotImplementedError("Abstract method")


class HydraOperationExtractor(OperationExtractor):
    """ TODO: describe
    """
    #
    # PREDEFINED_OPERATION_FUNCTIONS = {'DELETE': Resource.delete,
    #                                   'PUT': Resource.update_from_graph}

    def __init__(self):
        self._operation_iris = None
        self._logger = logging.getLogger(__name__)

    def extract(self, ancestry, schema_graph, operation_functions):
        """TODO: comment """
        return self._extract_hydra_operations(ancestry, schema_graph, operation_functions)

    def _extract_hydra_operations(self, ancestry, schema_graph,
                                  operation_functions):
        """ Extracts operations supported by Hydra classes. """

        # Extracts the IRIs of the operations if needed
        if self._operation_iris is None:
            self._extract_operation_iris(schema_graph)

        operations = {}
        # For each in the ancestry
        for class_iri in ancestry.bottom_up:
            cls_oper_iris = self._operation_iris.get(class_iri, [])

            # For each (operation + method), creates a new Operation object
            #  if there is no operation for this method yet.
            for oper_iri in cls_oper_iris:
                operations = self._extract_hydra_operation(class_iri, ancestry, oper_iri, schema_graph, operation_functions,
                                                           operations)

        return operations

    def _extract_operation_iris(self, schema_graph):
        self._operation_iris = {}

        for cls_iri, _, oper_iri in schema_graph.triples((None, URIRef(HYDRA_SUPPORTED_OPERATION), None)):
            class_iri = unicode(cls_iri)
            operation_iri = unicode(oper_iri)

            if class_iri not in self._operation_iris:
                self._operation_iris[class_iri] = []
            self._operation_iris[class_iri].append(operation_iri)

    def _extract_hydra_operation(self, class_iri, ancestry, operation_iri, schema_graph, operation_functions, operations):
        """
            TODO: describe
        """
        operation_ref = URIRef(operation_iri)

        # Looks for its method(s)
        http_methods = {unicode(o) for o in schema_graph.objects(operation_ref, URIRef(HYDRA_METHOD))}

        # Expected type
        expected_types = {unicode(o) for o in schema_graph.objects(operation_ref, URIRef(HYDRA_EXCEPTS))}
        if len(expected_types) == 0:
            self._logger.warn("No expected type for operation %s of %s" % (http_methods, class_iri))
            expected_type = None
        elif len(expected_types) > 1:
            #TODO: Check with the Hydra CG if it is a problem or not
            #TODO: find a better exception
            raise Exception("Multiple expected types for operation %s of %s" % (http_methods, class_iri))
        else:
            expected_type = list(expected_types)[0]

        # Returned type
        returned_types = {unicode(o) for o in schema_graph.objects(operation_ref, URIRef(HYDRA_RETURNS))}
        if len(returned_types) == 0:
            self._logger.warn("No returned type for operation %s of %s" % (http_methods, class_iri))
            returned_type = None
        elif len(returned_types) > 1:
            #TODO: Check with the Hydra CG if it is a problem or not
            #TODO: find a better exception
            raise Exception("Multiple returned types for operation %s of %s" % (http_methods, class_iri))
        else:
            returned_type = list(returned_types)[0]

        # Name (optional)
        short_names = {unicode(o) for o in schema_graph.objects(operation_ref, URIRef(OLDM_SHORTNAME))}
        if len(returned_types) == 0:
            shortname = None
        elif len(returned_types) > 1:
            #TODO: find a better exception
            raise Exception("Multiple short names for operation %s of %s" % (http_methods, class_iri))
        else:
            shortname = list(short_names)[0]

        # Only consider methods that are not already defined
        # (bottom-up first)
        for m in http_methods:
            method = m.upper()

            if not method in operations:

                # Get function
                func = get_operation_function(operation_functions, class_iri, ancestry, method)
                if func is None:
                    continue
                    # func = self.PREDEFINED_OPERATION_FUNCTIONS.get(method)
                    # if func is None:
                    #     continue

                # New operation
                operations[method] = Operation(method, expected_type, returned_type, func, shortname)

        return operations