# -*- coding: utf-8 -*-
"""
    Test property inheritance, isinstance() and issubclass()
"""

from unittest import TestCase
from rdflib import ConjunctiveGraph, URIRef
import json
from decimal import Decimal
from copy import copy
from datetime import date, datetime, time
from ld_orm import default_model_factory
from ld_orm.exceptions import RequiredPropertyError, LDAttributeTypeCheckError

default_graph = ConjunctiveGraph()
schema_graph = default_graph.get_context(URIRef("http://localhost/schema"))
data_graph = default_graph.get_context(URIRef("http://localhost/data"))

EXAMPLE = "http://localhost/vocab#"


#Turtle instead of JSON-LD because of a bug with the JSON-LD parser
schema_ttl = """
@prefix ex: <%s> .
@prefix hydra: <http://www.w3.org/ns/hydra/core#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:GrandParentClass a hydra:Class ;
    hydra:supportedProperty [
        hydra:property ex:oldProperty ;
        hydra:required false
    ] .

ex:ParentClass a hydra:Class ;
    rdfs:subClassOf ex:GrandParentClass ;
    hydra:supportedProperty [
        hydra:property ex:mediumProperty ;
        hydra:required false
    ] .

ex:ChildClass a hydra:Class ;
    rdfs:subClassOf ex:ParentClass, ex:GrandParentClass ;
    hydra:supportedProperty [
        hydra:property ex:newProperty ;
        hydra:required false
    ] .
""" % format(EXAMPLE)

# schema_def = {
#     "@context": [
#         {
#             "ex": EXAMPLE,
#         },
#         "http://www.w3.org/ns/hydra/core"
#     ],
#     "@graph": [
#         {
#             "@id": "ex:GrandParentClass",
#             "@type": "hydra:Class",
#             "supportedProperty": [
#                 {
#                     "property": "ex:oldProperty",
#                     "required": False
#                 }
#             ]
#         },
#         {
#             "@id": "ex:ParentClass",
#             "@type": "hydra:Class",
#             "subClassOf": "ex:GrandParentClass",
#             "supportedProperty": [
#                 {
#                     "property": "ex:mediumProperty",
#                     "required": False
#                 }
#             ]
#         },
#         {
#             "@id": "ex:ChildClass",
#             "@type": "hydra:Class",
#             # Saves inference
#             "subClassOf": ["ex:ParentClass", "ex:GrandParentClass"],
#             "supportedProperty": [
#                 {
#                     "property": "ex:newProperty",
#                     "required": False
#                 }
#             ]
#         }
#     ]
# }
#print json.dumps(schema_def)
#schema_graph.parse(data=json.dumps(schema_def), format="json-ld")

schema_graph.parse(data=schema_ttl, format="turtle")
#print schema_graph.serialize(format="n3")

context = {
    "@context": {
        "ex": EXAMPLE,
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "id": "@id",
        "type": "@type",
        "ChildClass": "ex:ChildClass",
        "ParentClass": "ex:ParentClass",
        "GrandParentClass": "ex:GrandParentClass",
        "old_number_value": {
            "@id": "ex:oldProperty",
            "@type": "xsd:int"
        },
        "mid_values": {
            "@id": "ex:mediumProperty",
            "@type": "xsd:string",
            "@container": "@set"
        },
        "new_value": {
            "@id": "ex:newProperty",
            "@type": "xsd:string"
        }
    }
}

model_generator = default_model_factory(schema_graph, default_graph)
# ChildClass is generated before the older!!
ChildClass = model_generator.generate("ChildClass", context, data_graph,
                                      uri_prefix="http://localhost/children/")
GrandParentClass = model_generator.generate("GrandParentClass", context, data_graph,
                                      uri_prefix="http://localhost/ancestors/")
ParentClass = model_generator.generate("ParentClass", context, data_graph,
                                       uri_prefix="http://localhost/parents/")


class DatatypeTest(TestCase):

    def tearDown(self):
        """ Clears the data graph """
        data_graph.update("CLEAR DEFAULT")
        ChildClass.objects.clear_cache()
        ParentClass.objects.clear_cache()
        GrandParentClass.objects.clear_cache()

    def test_ancestor_assignment(self):
        john = GrandParentClass()
        uri = john.id
        old_value = 5
        john.old_number_value = old_value
        # Not declared so will not be saved
        mid_values = {"not saved"}
        john.mid_values = mid_values
        new_value = "not saved (again)"
        john.new_value = new_value
        john.save()
        del john
        GrandParentClass.objects.clear_cache()
        john = GrandParentClass.objects.get(id=uri)
        self.assertEquals(john.old_number_value, old_value)
        with self.assertRaises(AttributeError):
            print john.mid_values
        with self.assertRaises(AttributeError):
            print john.new_value

    def test_parent_assignment(self):
        jack = ParentClass()
        uri = jack.id
        mid_values = { "Hello", "world" }
        jack.mid_values = mid_values
        old_value = 8
        jack.old_number_value = old_value
        new_value = "not saved"
        jack.new_value = new_value
        jack.save()
        del jack
        ParentClass.objects.clear_cache()
        jack = ParentClass.objects.get(id=uri)
        self.assertEquals(jack.mid_values, mid_values)
        self.assertEquals(jack.old_number_value, old_value)
        with self.assertRaises(AttributeError):
            print jack.new_value

    def test_child_assignment(self):
        tom = ChildClass()
        uri = tom.id
        mid_values = { "Hello", "world" }
        tom.mid_values = mid_values
        old_value = 10
        tom.old_number_value = old_value
        new_value = u"ok!"
        tom.new_value = new_value
        tom.save()
        del tom
        ChildClass.objects.clear_cache()
        tom = ChildClass.objects.get(id=uri)
        self.assertEquals(tom.new_value, new_value)
        self.assertEquals(tom.mid_values, mid_values)
        self.assertEquals(tom.old_number_value, old_value)