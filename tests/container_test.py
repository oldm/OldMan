# -*- coding: utf-8 -*-
""" Additional test on containers

No cache.
"""

from unittest import TestCase
from os import path
from rdflib import ConjunctiveGraph, URIRef
import json
from copy import copy
from oldman import ClientResourceManager, parse_graph_safely, SPARQLDataStore
from oldman.exception import OMRequiredPropertyError, OMAttributeTypeCheckError

default_graph = ConjunctiveGraph()
schema_graph = default_graph.get_context(URIRef("http://localhost/schema"))
data_graph = default_graph.get_context(URIRef("http://localhost/data"))

EXAMPLE = "http://localhost/vocab#"

local_person_def = {
    "@context": [
        {
            "ex": EXAMPLE
        },
        #"http://www.w3.org/ns/hydra/core"
        json.load(open(path.join(path.dirname(__file__), "hydra_core.jsonld")))["@context"]
    ],
    "@id": "ex:LocalClass",
    "@type": "hydra:Class",
    "supportedProperty": [
        {
            "property": "ex:primaryList",
            "required": False,
            "readonly": False,
            "writeonly": False
        },
        {
            "property": "ex:localizedList",
            "required": True,
            "readonly": False,
            "writeonly": False
        },
        {
            "property": "ex:undeclaredSet",
            "required": False,
            "readonly": False,
            "writeonly": False
        },
        {
            "property": "ex:boolList",
            "required": False,
            "readonly": False,
            "writeonly": False
        },
        {
            "property": "ex:boolSet",
            "required": False,
            "readonly": False,
            "writeonly": False
        },
        {
            "property": "ex:localizedValue",
            "required": False,
            "readonly": False,
            "writeonly": False
        }

    ]
}
parse_graph_safely(schema_graph, data=json.dumps(local_person_def), format="json-ld")

context = {
    "@context": {
        "ex": EXAMPLE,
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "id": "@id",
        "type": "@type",
        "LocalClass": "ex:LocalClass",
        "primary_list": {
            "@id": "ex:primaryList",
            "@type": "xsd:string",
            "@container": "@list"
        },
        "list_en": {
            "@id": "ex:localizedList",
            "@type": "xsd:string",
            "@container": "@list",
            "@language": "en"
        },
        "list_fr": {
            "@id": "ex:localizedList",
            "@type": "xsd:string",
            "@container": "@list",
            "@language": "fr"
        },
        "undeclared_set": {
            "@id": "ex:undeclaredSet",
            "@type": "xsd:string"
        },
        "bool_list": {
            "@id": "ex:boolList",
            "@type": "xsd:boolean",
            "@container": "@list"
        },
        "bool_set": {
            "@id": "ex:boolSet",
            "@type": "xsd:boolean",
            "@container": "@set"
        },
        "lang_map": {
            "@id": "ex:localizedValue",
            "@type": "xsd:string",
            "@container": "@language"
        }
    }
}

data_store = SPARQLDataStore(data_graph, schema_graph=schema_graph)
data_store.create_model("LocalClass", context, iri_prefix="http://localhost/objects/")
client_manager = ClientResourceManager(data_store)
client_manager.import_store_models()
model = client_manager.get_model("LocalClass")
default_list_en = ["w1", "w2"]


class ContainerTest(TestCase):

    def tearDown(self):
        """ Clears the data graph """
        data_graph.update("CLEAR DEFAULT")

    def create_object(self):
        return model.create(list_en=default_list_en)

    def test_basic_list(self):
        obj = self.create_object()
        uri = obj.id
        lst = ["Hello", "hi", "hi", "Hello"]
        backup_list = copy(lst)
        obj.primary_list = lst
        obj.save()

        obj = model.get(id=uri)
        self.assertEquals(lst, backup_list)
        self.assertEquals(obj.primary_list, lst)
        self.assertNotEquals(obj.primary_list, list(set(lst)))

    def test_localized_lists(self):
        obj = model.new()
        uri = obj.id
        list_fr = ["Salut", "Bonjour"]
        list_en = ["Hi", "Hello"]
        obj.list_fr = copy(list_fr)
        obj.list_en = copy(list_en)
        obj.save()

        obj = model.get(id=uri)
        self.assertEquals(obj.list_fr, list_fr)
        self.assertEquals(obj.list_en, list_en)

    def test_required_list(self):
        obj = model.new()
        with self.assertRaises(OMRequiredPropertyError):
            obj.save()
        obj.list_fr = []
        with self.assertRaises(OMRequiredPropertyError):
            obj.save()

    def test_undeclared_set(self):
        obj = self.create_object()
        uri = obj.id
        lst = ["Hello", "hi", "hi", "Hello"]
        # No declaration -> implicit set or unique value
        # (lists and dict are not accepted)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.undeclared_set = lst
        obj.undeclared_set = set(lst)
        obj.save()
        # Unique values are also supported
        obj.undeclared_set = "unique value"
        obj.save()

    def test_change_attribute_of_required_property(self):
        obj = model.new()
        list_fr = ["Salut", "Bonjour"]
        list_en = ["Hi", "Hello"]
        obj.list_en = list_en
        obj.save()
        obj.list_en = None
        self.assertFalse(obj.is_valid())
        obj.list_fr = list_fr
        obj.save()

    def test_bool_list(self):
        obj = self.create_object()
        uri = obj.id
        lst = [True, False, True, False]
        obj.bool_list = lst
        self.assertEquals(obj.bool_list, lst)
        obj.save()
        obj = model.get(id=uri)
        self.assertEquals(obj.bool_list, lst)
        obj.bool_list = [True]
        obj.save()
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.bool_list = ["Wrong"]
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.bool_list = [True, None, False]

    def test_bool_set(self):
        obj = self.create_object()
        uri = obj.id
        bools = {False, True}
        obj.bool_set = bools
        obj.save()
        obj = model.get(id=uri)
        self.assertEquals(obj.bool_set, bools)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.bool_set = [True]
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.bool_set = {True, "Should not be there"}

    def test_lang_map(self):
        obj = self.create_object()
        uri = obj.id
        values = {'fr': u"Hé, salut!",
                  'en': u"What's up?"}
        obj.lang_map = values
        obj.save()
        obj = model.get(id=uri)
        self.assertEquals(obj.lang_map, values)

        with self.assertRaises(OMAttributeTypeCheckError):
            obj.lang_map = ["Not a map"]
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.lang_map = {"Not a map"}
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.lang_map = "Not a map"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.lang_map = {"en": {"key": "should not support level-2 map"}}
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.lang_map = {"en": 2}
        obj.lang_map = {"en": "ok",
                        "fr": "ok aussi"}


