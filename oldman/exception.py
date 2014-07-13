class OMError(Exception):
    """Root of exceptions generated by the oldman package."""
    pass


class ModelGenerationError(OMError):
    """Error occured when generating a new model."""
    pass


class AlreadyAllocatedModelError(ModelGenerationError):
    """The class IRI or the short name of a new model is already allocated."""
    pass


class OMSchemaError(ModelGenerationError):
    """Error in the schema graph and/or the JSON-LD context."""
    pass


class OMPropertyDefError(OMSchemaError):
    """Inconsistency in the definition of a supported property."""
    pass


class OMPropertyDefTypeError(OMPropertyDefError):
    """A RDF property cannot be both an ObjectProperty and a DatatypeProperty."""
    pass


class OMAttributeDefError(OMSchemaError):
    """Inconsistency in the definition of a model class attribute."""
    pass


class OMAlreadyDeclaredDatatypeError(OMAttributeDefError):
    """At least two different datatypes for the same attribute.

    You may check the possible datatype inherited from the property (rdfs:range)
    and the one specified in the JSON-LD context.
    """
    pass


class OMReservedAttributeNameError(OMAttributeDefError):
    """Some attribute names are reserved and should not
        be included in the JSON-LD context."""
    pass


class OMUndeclaredClassNameError(ModelGenerationError):
    """The name of the model class should be defined in the JSON-LD context."""
    pass


class OMExpiredMethodDeclarationTimeSlotError(ModelGenerationError):
    """All methods must be declared before creating a first model."""
    pass


class OMUserError(OMError):
    """Error when accessing or editing objects."""
    pass


class OMEditError(OMUserError):
    """Runtime errors, occuring when editing or creating an object."""
    pass


class OMAttributeTypeCheckError(OMEditError):
    """The value assigned to the attribute has wrong type."""
    pass


class OMRequiredPropertyError(OMEditError):
    """A required property has no value."""
    pass


class OMReadOnlyAttributeError(OMEditError):
    """End-users are not allowed to edit this attribute."""
    pass


class OMUniquenessError(OMEditError):
    """Attribute uniqueness violation.

    Example: IRI illegal reusing.
    """
    pass


class OMWrongResourceError(OMEditError):
    """Not updating the right object."""
    pass


class OMDifferentHashlessIRIError(OMEditError):
    """When creating or updating an object with a different hashless IRI is forbidden.

        Blank nodes are not concerned.
    """
    pass


class OMForbiddenSkolemizedIRIError(OMEditError):
    """When updating a skolemized IRI from the local domain is forbidden."""
    pass


class OMRequiredHashlessIRIError(OMEditError):
    """No hash-less IRI has been given."""
    pass


class OMUnauthorizedTypeChangeError(OMEditError):
    """When updating a resource with new types without explicit authorization."""
    pass


class OMAccessError(OMUserError):
    """Error when accessing objects."""
    pass


class OMAttributeAccessError(OMAccessError):
    """When such an attribute cannot be identified
        (is not supported or no model has been found).
    """
    pass


class OMClassInstanceError(OMAccessError):
    """The object is not an instance of the expected RDFS class."""
    pass


class OMObjectNotFoundError(OMAccessError):
    """When the object is not found."""
    pass


class OMHashIriError(OMAccessError):
    """A hash IRI has been given instead of a hash-less IRI."""
    pass


class OMSPARQLError(OMAccessError):
    """Invalid SPARQL query given."""
    pass


class OMInternalError(OMError):
    """ Do not expect it. """
    pass


class OMSPARQLParseError(OMInternalError):
    """Invalid SPARQL request."""
    pass


class OMAlreadyGeneratedAttributeError(OMInternalError):
    """Attribute generation occurs only once per SupportedProperty.

    You should not try to add metadata or regenerate after that.
    """
    pass


class OMDataStoreError(OMError):
    """Error detected in the stored data."""
    pass


class UnsupportedDataStorageFeature(OMDataStoreError):
    """Feature not supported by the data store."""