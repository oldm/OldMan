# -*- coding: utf-8 -*-
""" Additional test on containers

No cache.
"""

from unittest import TestCase
from os import path
import json
from copy import copy

from rdflib import ConjunctiveGraph, URIRef

from oldman import create_mediator, parse_graph_safely, SparqlStore
from oldman.core.exception import OMRequiredPropertyError, OMAttributeTypeCheckError

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

data_store = SparqlStore(data_graph, schema_graph=schema_graph)
data_store.create_model("LocalClass", context, iri_prefix="http://localhost/objects/")
user_mediator = create_mediator(data_store)
user_mediator.import_store_models()
model = user_mediator.get_client_model("LocalClass")
default_list_en = ["w1", "w2"]


class ContainerTest(TestCase):

    def tearDown(self):
        """ Clears the data graph """
        data_graph.update("CLEAR DEFAULT")

    def create_object(self, session):
        obj = model.new(session, list_en=default_list_en)
        session.flush()
        return obj

    def test_basic_list(self):
        session1 = user_mediator.create_session()
        obj = self.create_object(session1)
        uri = obj.id.iri
        lst = ["Hello", "hi", "hi", "Hello"]
        backup_list = copy(lst)
        obj.primary_list = lst
        session1.flush()
        session1.close()

        session2 = user_mediator.create_session()
        obj2 = model.get(session2, iri=uri)
        self.assertEquals(lst, backup_list)
        self.assertEquals(obj2.primary_list, lst)
        self.assertNotEquals(obj2.primary_list, list(set(lst)))
        session2.close()

    def test_localized_lists(self):
        session1 = user_mediator.create_session()
        obj = model.new(session1)
        list_fr = ["Salut", "Bonjour"]
        list_en = ["Hi", "Hello"]
        obj.list_fr = copy(list_fr)
        obj.list_en = copy(list_en)
        session1.flush()
        uri = obj.id.iri
        session1.close()

        session2 = user_mediator.create_session()
        obj2 = model.get(session2, iri=uri)
        self.assertEquals(obj2.list_fr, list_fr)
        self.assertEquals(obj2.list_en, list_en)
        session2.close()

    def test_required_list(self):
        session = user_mediator.create_session()
        obj = model.new(session)
        with self.assertRaises(OMRequiredPropertyError):
            session.flush()
        obj.list_fr = []
        with self.assertRaises(OMRequiredPropertyError):
            session.flush()
        session.close()

    def test_undeclared_set(self):
        session = user_mediator.create_session()
        obj = self.create_object(session)
        uri = obj.id.iri
        lst = ["Hello", "hi", "hi", "Hello"]
        # No declaration -> implicit set or unique value
        # (lists and dict are not accepted)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.undeclared_set = lst
        obj.undeclared_set = set(lst)
        session.flush()
        # Unique values are also supported
        obj.undeclared_set = "unique value"
        session.flush()
        session.close()

    def test_change_attribute_of_required_property(self):
        session = user_mediator.create_session()
        obj = model.new(session)
        list_fr = ["Salut", "Bonjour"]
        list_en = ["Hi", "Hello"]
        obj.list_en = list_en
        session.flush()
        obj.list_en = None
        self.assertFalse(obj.is_valid())
        obj.list_fr = list_fr
        session.flush()
        session.close()

    def test_bool_list(self):
        session1 = user_mediator.create_session()
        obj = self.create_object(session1)
        uri = obj.id.iri
        lst = [True, False, True, False]
        obj.bool_list = lst
        self.assertEquals(obj.bool_list, lst)
        session1.flush()
        session1.close()

        session2 = user_mediator.create_session()
        obj2 = model.get(session2, iri=uri)
        self.assertEquals(obj2.bool_list, lst)
        obj2.bool_list = [True]
        session2.flush()
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.bool_list = ["Wrong"]
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.bool_list = [True, None, False]
        session2.close()

    def test_bool_set(self):
        session1 = user_mediator.create_session()
        obj1 = self.create_object(session1)
        uri = obj1.id.iri
        bools = {False, True}
        obj1.bool_set = bools
        session1.flush()

        session2 = user_mediator.create_session()
        obj2 = model.get(session2, iri=uri)
        self.assertEquals(obj2.bool_set, bools)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.bool_set = [True]
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.bool_set = {True, "Should not be there"}

    def test_lang_map(self):
        session1 = user_mediator.create_session()
        obj1 = self.create_object(session1)
        uri = obj1.id.iri
        values = {'fr': u"Hé, salut!",
                  'en': u"What's up?"}
        obj1.lang_map = values
        session1.flush()
        session2 = user_mediator.create_session()
        obj2 = model.get(session2, iri=uri)
        self.assertEquals(obj2.lang_map, values)

        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.lang_map = ["Not a map"]
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.lang_map = {"Not a map"}
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.lang_map = "Not a map"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.lang_map = {"en": {"key": "should not support level-2 map"}}
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.lang_map = {"en": 2}
        obj2.lang_map = {"en": "ok",
                         "fr": "ok aussi"}


