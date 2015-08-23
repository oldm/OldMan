# -*- coding: utf-8 -*-
"""
    Test property inheritance, isinstance() and issubclass()
"""

from unittest import TestCase

from rdflib import Graph, RDFS, URIRef, BNode, Literal

from oldman.core.model.ancestry import ClassAncestry
from oldman.core.vocabulary import MODEL_PRIORITY_IRI, MODEL_HAS_PRIORITY_IRI, MODEL_PRIORITY_CLASS_IRI


EXAMPLE = "http://localhost/vocab#"

schema_ttl = """
@prefix ex: <{0}> .
@prefix hydra: <http://www.w3.org/ns/hydra/core#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:Branch1GrandParentClass a hydra:Class .

ex:Branch1ParentClass a hydra:Class ;
    rdfs:subClassOf ex:Branch1GrandParentClass .

ex:Branch2GrandParentClass a hydra:Class .

ex:Branch2ParentClass a hydra:Class ;
    rdfs:subClassOf ex:Branch2GrandParentClass .

ex:Branch3ParentClass a hydra:Class .

ex:ChildClass a hydra:Class ;
    rdfs:subClassOf ex:Branch1ParentClass, ex:Branch1GrandParentClass .
""".format(EXAMPLE)

CHILD_CLS = "ChildClass"
B1P_CLS = "Branch1ParentClass"
B1GP_CLS = "Branch1GrandParentClass"
B2P_CLS = "Branch2ParentClass"
B2GP_CLS = "Branch2GrandParentClass"
B3P_CLS = "Branch3ParentClass"

child_cls_iri = EXAMPLE + CHILD_CLS
b1p_cls_iri = EXAMPLE + B1P_CLS
b1gp_cls_iri = EXAMPLE + B1GP_CLS
b2p_cls_iri = EXAMPLE + B2P_CLS
b2gp_cls_iri = EXAMPLE + B2GP_CLS
b3p_cls_iri = EXAMPLE + B3P_CLS


class AncestryTest(TestCase):

    def setUp(self):
        self.schema_graph = Graph().parse(data=schema_ttl, format="turtle")

    def test_single_branch_ancestry(self):
        child_ancestry = ClassAncestry(child_cls_iri, self.schema_graph)
        self.assertEquals(child_ancestry.bottom_up, [child_cls_iri, b1p_cls_iri, b1gp_cls_iri])
        self.assertEquals(child_ancestry.child, child_cls_iri)
        self.assertEquals(child_ancestry.top_down, [b1gp_cls_iri, b1p_cls_iri, child_cls_iri])
        self.assertEquals(child_ancestry.parents(child_cls_iri), [b1p_cls_iri])
        self.assertEquals(child_ancestry.parents(b1p_cls_iri), [b1gp_cls_iri])
        self.assertEquals(child_ancestry.parents(b1gp_cls_iri), [])

    def test_two_branch_ancestry_without_priority(self):
        self.schema_graph.add((URIRef(child_cls_iri), RDFS.subClassOf, URIRef(b2p_cls_iri)))
        self.schema_graph.add((URIRef(child_cls_iri), RDFS.subClassOf, URIRef(b2gp_cls_iri)))
        child_ancestry = ClassAncestry(child_cls_iri, self.schema_graph)
        self.assertEquals(child_ancestry.bottom_up[0], child_cls_iri)
        self.assertEquals(set(child_ancestry.bottom_up[1:3]), {b1p_cls_iri, b2p_cls_iri})
        self.assertEquals(set(child_ancestry.bottom_up[3:]), {b1gp_cls_iri, b2gp_cls_iri})
        self.assertEquals(child_ancestry.child, child_cls_iri)
        self.assertEquals(set(child_ancestry.parents(child_cls_iri)), {b1p_cls_iri, b2p_cls_iri})
        self.assertEquals(child_ancestry.parents(b1p_cls_iri), [b1gp_cls_iri])
        self.assertEquals(child_ancestry.parents(b1gp_cls_iri), [])
        self.assertEquals(child_ancestry.parents(b2p_cls_iri), [b2gp_cls_iri])
        self.assertEquals(child_ancestry.parents(b2gp_cls_iri), [])

    def test_three_branch_ancestry_with_priority(self):
        child_ref = URIRef(child_cls_iri)
        self.schema_graph.add((child_ref, RDFS.subClassOf, URIRef(b2p_cls_iri)))
        self.schema_graph.add((child_ref, RDFS.subClassOf, URIRef(b2gp_cls_iri)))
        self.schema_graph.add((child_ref, RDFS.subClassOf, URIRef(b3p_cls_iri)))

        priority_b1 = BNode()
        self.schema_graph.add((child_ref, URIRef(MODEL_HAS_PRIORITY_IRI), priority_b1))
        self.schema_graph.add((priority_b1, URIRef(MODEL_PRIORITY_CLASS_IRI), URIRef(b1p_cls_iri)))
        self.schema_graph.add((priority_b1, URIRef(MODEL_PRIORITY_IRI), Literal(1)))

        priority_b2 = BNode()
        self.schema_graph.add((child_ref, URIRef(MODEL_HAS_PRIORITY_IRI), priority_b2))
        self.schema_graph.add((priority_b2, URIRef(MODEL_PRIORITY_CLASS_IRI), URIRef(b2p_cls_iri)))
        self.schema_graph.add((priority_b2, URIRef(MODEL_PRIORITY_IRI), Literal(2)))

        child_ancestry = ClassAncestry(child_cls_iri, self.schema_graph)

        self.assertEquals(child_ancestry.bottom_up[0], child_cls_iri)
        self.assertEquals(child_ancestry.bottom_up[1:3], [b2p_cls_iri, b2gp_cls_iri])
        self.assertEquals(child_ancestry.bottom_up[3:5], [b1p_cls_iri, b1gp_cls_iri])
        # b3p_cls_iri is the last because has no priority (nothing declared)
        self.assertEquals(child_ancestry.bottom_up[-1], b3p_cls_iri)
        self.assertEquals(child_ancestry.child, child_cls_iri)
        self.assertEquals(child_ancestry.parents(child_cls_iri), [b2p_cls_iri, b1p_cls_iri, b3p_cls_iri])
        self.assertEquals(child_ancestry.parents(b1p_cls_iri), [b1gp_cls_iri])
        self.assertEquals(child_ancestry.parents(b1gp_cls_iri), [])
        self.assertEquals(child_ancestry.parents(b2p_cls_iri), [b2gp_cls_iri])
        self.assertEquals(child_ancestry.parents(b2gp_cls_iri), [])
