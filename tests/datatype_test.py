# -*- coding: utf-8 -*-
"""
    Additional test on datatypes
"""

from unittest import TestCase
from rdflib import ConjunctiveGraph, URIRef
import json
from copy import copy
from datetime import date
from ld_orm import default_model_factory
from ld_orm.exceptions import RequiredPropertyError, LDAttributeTypeCheckError

default_graph = ConjunctiveGraph()
schema_graph = default_graph.get_context(URIRef("http://localhost/schema"))
data_graph = default_graph.get_context(URIRef("http://localhost/data"))

EXAMPLE = "http://localhost/vocab#"

local_person_def = {
    "@context": [
        {
            "ex": EXAMPLE
        },
        "http://www.w3.org/ns/hydra/core"
    ],
    "@id": "ex:LocalClass",
    "@type": "hydra:Class",
    "supportedProperty": [
        {
            "property": "ex:singleBool",
            "required": False,
            "readonly": False,
            "writeonly": False
        },
        {
            "property": "ex:date",
            "required": False,
            "readonly": False,
            "writeonly": False
        }
    ]
}
schema_graph.parse(data=json.dumps(local_person_def), format="json-ld")

context = {
    "@context": {
        "ex": EXAMPLE,
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "id": "@id",
        "type": "@type",
        "LocalClass": "ex:LocalClass",
        "single_bool": {
            "@id": "ex:singleBool",
            "@type": "xsd:boolean"
        },
        "date": {
            "@id": "ex:date",
            "@type": "xsd:date"
        }
    }
}

model_generator = default_model_factory(schema_graph, default_graph)
# Model class is generated here!
LocalClass = model_generator.generate("LocalClass", context, data_graph,
                                      uri_prefix="http://localhost/objects/")
default_list_en = ["w1", "w2"]


class ContainerTest(TestCase):

    def tearDown(self):
        """ Clears the data graph """
        data_graph.update("CLEAR DEFAULT")
        LocalClass.objects.clear_cache()

    def create_object(self):
        return LocalClass.objects.create()

    def test_single_bool(self):
        obj = self.create_object()
        uri = obj.id
        obj.single_bool = True
        obj.save()
        del obj
        LocalClass.objects.clear_cache()
        obj = LocalClass.objects.get(id=uri)
        self.assertEquals(obj.single_bool, True)

        obj.single_bool = None
        obj.save()
        del obj
        LocalClass.objects.clear_cache()
        obj = LocalClass.objects.get(id=uri)
        self.assertEquals(obj.single_bool, None)

        obj.single_bool = False
        obj.save()
        del obj
        LocalClass.objects.clear_cache()
        obj = LocalClass.objects.get(id=uri)
        self.assertEquals(obj.single_bool, False)

    def test_single_date(self):
        obj = self.create_object()
        uri = obj.id
        d = date(2009, 11, 2)
        obj.date = copy(d)
        obj.save()
        del obj
        LocalClass.objects.clear_cache()
        obj = LocalClass.objects.get(id=uri)
        self.assertEquals(obj.date, d)
        # with self.assertRaises(LDAttributeTypeCheckError):
        #     obj.date = "not a date"







