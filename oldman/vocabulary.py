"""
    oldman.vocabulary
    ~~~~~~~~~~~~~~~~~

    RDF vocabulary used by OldMan. Some of it is specific to OldMan.

    TODO: replace these URNs by URLs.

    .. admonition:: Parent model prioritization

        In RDF, a class is often the child of multiple classes. When the code inherited
        from these classes (common practise in Object-Oriented Programming) is conflicting,
        arbitration is necessary.

        In this library, we provide a RDF vocabulary to declare priorities for each parent
        of a given child class. A priority statement is declared as follows: ::

            ?cls <urn:oldman:model:ordering:hasPriority> [
                <urn:oldman:model:ordering:class> ?parent1 ;
                <urn:oldman:model:ordering:priority> 2
            ].

        By default, when no priority is declared for a pair (child, parent),
        its priority value is set to 0.
"""

MODEL_HAS_PRIORITY_IRI = "urn:oldman:model:ordering:hasPriority"
MODEL_PRIORITY_CLASS_IRI = "urn:oldman:model:ordering:class"
MODEL_PRIORITY_IRI = "urn:oldman:model:ordering:priority"

OLDM_SHORTNAME = "urn:oldman:shortname"

#: Used to increment IRIs.
NEXT_NUMBER_IRI = "urn:oldman:nextNumber"

HYDRA_COLLECTION_IRI = "http://www.w3.org/ns/hydra/core#Collection"
HYDRA_PAGED_COLLECTION_IRI = "http://www.w3.org/ns/hydra/core#PagedCollection"
HYDRA_MEMBER_IRI = "http://www.w3.org/ns/hydra/core#member"

HYDRA_SUPPORTED_OPERATION = "http://www.w3.org/ns/hydra/core#supportedOperation"
HYDRA_METHOD = "http://www.w3.org/ns/hydra/core#method"
HYDRA_EXCEPTS = "http://www.w3.org/ns/hydra/core#expects"
HYDRA_RETURNS = "http://www.w3.org/ns/hydra/core#returns"


HTTP_POST = "POST"