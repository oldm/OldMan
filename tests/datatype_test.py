# -*- coding: utf-8 -*-
"""
    Additional test on datatypes
"""

from unittest import TestCase
from os import path
from rdflib import ConjunctiveGraph, URIRef
import json
from decimal import Decimal
from copy import copy
from datetime import date, datetime, time
from oldman import create_user_mediator, parse_graph_safely, SPARQLDataStore
from oldman.exception import OMAttributeTypeCheckError

default_graph = ConjunctiveGraph()
schema_graph = default_graph.get_context(URIRef("http://localhost/schema"))
data_graph = default_graph.get_context(URIRef("http://localhost/data"))

EXAMPLE = "http://localhost/vocab#"

local_class_def = {
    "@context": [
        {
            "ex": EXAMPLE,
            "schema": "http://schema.org/",
            "foaf": "http://xmlns.com/foaf/0.1/"
        },
        #"http://www.w3.org/ns/hydra/core"
        json.load(open(path.join(path.dirname(__file__), "hydra_core.jsonld")))["@context"]
    ],
    "@id": "ex:LocalClass",
    "@type": "hydra:Class",
    "supportedProperty": [
        {
            "property": "ex:singleBool"
        }, {
            "property": "ex:date"
        }, {
            "property": "ex:dateTime"
        }, {
            "property": "ex:time"
        }, {
            "property": "ex:int"
        }, {
            "property": "ex:integer"
        }, {
            "property": "ex:short"
        }, {
            "property": "ex:positiveInt"
        }, {
            "property": "ex:negativeInt"
        }, {
            "property": "ex:nonPositiveInt"
        }, {
            "property": "ex:nonNegativeInt"
        }, {
            "property": "ex:decimal"
        }, {
            "property": "ex:float"
        }, {
            "property": "ex:double"
        }, {
            "property": "foaf:mbox"
        }, {
            "property": "schema:email"
        }
    ]
}
parse_graph_safely(schema_graph, data=json.dumps(local_class_def), format="json-ld")

context = {
    "@context": {
        "ex": EXAMPLE,
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "foaf": "http://xmlns.com/foaf/0.1/",
        "schema": "http://schema.org/",
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
        },
        "datetime": {
            "@id": "ex:dateTime",
            "@type": "xsd:dateTime"
        },
        "time": {
            "@id": "ex:time",
            "@type": "xsd:time"
        },
        "int": {
            "@id": "ex:int",
            "@type": "xsd:int"
        },
        "integer": {
            "@id": "ex:integer",
            "@type": "xsd:integer"
        },
        "short": {
            "@id": "ex:short",
            "@type": "xsd:short"
        },
        "positiveInt": {
            "@id": "ex:positiveInt",
            "@type": "xsd:positiveInteger"
        },
        "negativeInt": {
            "@id": "ex:negativeInt",
            "@type": "xsd:negativeInteger"
        },
        "nonPositiveInt": {
            "@id": "ex:nonPositiveInt",
            "@type": "xsd:nonPositiveInteger"
        },
        "nonNegativeInt": {
            "@id": "ex:nonNegativeInt",
            "@type": "xsd:nonNegativeInteger"
        },
        "decimal": {
            "@id": "ex:decimal",
            "@type": "xsd:decimal"
        },
        "float": {
            "@id": "ex:float",
            "@type": "xsd:float"
        },
        "double": {
            "@id": "ex:double",
            "@type": "xsd:double"
        },
        "mbox": {
            # foaf:mbox should have priority
            "@id": "foaf:mbox",
            "@type": "xsd:string"
        },
        "email": {
            # schema:email should have priority
            "@id": "schema:email",
            "@type": "xsd:string"
        }
    }
}

data_store = SPARQLDataStore(data_graph, schema_graph=schema_graph)
data_store.create_model("LocalClass", context, iri_prefix="http://localhost/objects/")

user_mediator = create_user_mediator(data_store)
user_mediator.import_store_models()
lc_model = user_mediator.get_client_model("LocalClass")
default_list_en = ["w1", "w2"]


class DatatypeTest(TestCase):

    def tearDown(self):
        """ Clears the data graph """
        data_graph.update("CLEAR DEFAULT")

    def create_object(self):
        return lc_model.create()

    def test_single_bool(self):
        obj = self.create_object()
        uri = obj.id
        obj.single_bool = True
        obj.save()
        obj = lc_model.get(id=uri)
        self.assertEquals(obj.single_bool, True)

        obj.single_bool = None
        obj.save()
        obj = lc_model.get(id=uri)
        self.assertEquals(obj.single_bool, None)

        obj.single_bool = False
        obj.save()
        obj = lc_model.get(id=uri)
        self.assertEquals(obj.single_bool, False)

    def test_single_date(self):
        obj = self.create_object()
        uri = obj.id
        d = date(2009, 11, 2)
        obj.date = copy(d)
        obj.save()
        obj = lc_model.get(id=uri)
        self.assertEquals(obj.date, d)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.date = "not a date object"

    def test_single_datetime(self):
        obj = self.create_object()
        uri = obj.id
        d = datetime.now()
        obj.datetime = copy(d)
        obj.save()
        obj = lc_model.get(id=uri)
        self.assertEquals(obj.datetime, d)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.datetime = "not a date time object"

    def test_single_time(self):
        obj = self.create_object()
        uri = obj.id
        t = time(12, 55, 30)
        obj.time = copy(t)
        obj.save()
        obj = lc_model.get(id=uri)
        self.assertEquals(obj.time, t)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.time = "not a time object"

    def test_int(self):
        obj = self.create_object()
        uri = obj.id
        value = -5
        obj.int = value
        obj.save()
        obj = lc_model.get(id=uri)
        self.assertEquals(obj.int, value)
        obj.int = 0
        obj.int = 5
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.int = "not a number"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.int = 5.5

    def test_integer(self):
        obj = self.create_object()
        uri = obj.id
        value = 5
        obj.integer = value
        obj.save()
        obj = lc_model.get(id=uri)
        self.assertEquals(obj.integer, value)
        obj.integer = 0
        obj.integer = -5
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.integer = "not a number"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.integer = 5.5

    def test_short(self):
        obj = self.create_object()
        uri = obj.id
        value = -5
        obj.short = value
        obj.save()
        obj = lc_model.get(id=uri)
        self.assertEquals(obj.short, value)
        obj.short = 0
        obj.short = 5
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.short = "not a number"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.short = 5.5

    def test_positive_int(self):
        obj = self.create_object()
        uri = obj.id
        value = 5
        obj.positiveInt = value
        obj.save()
        obj = lc_model.get(id=uri)
        self.assertEquals(obj.positiveInt, value)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.positiveInt = -1
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.positiveInt = "not a number"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.positiveInt = 5.5
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.positiveInt = 0

    def test_negative_int(self):
        obj = self.create_object()
        uri = obj.id
        value = -5
        obj.negativeInt = value
        obj.save()
        obj = lc_model.get(id=uri)
        self.assertEquals(obj.negativeInt, value)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.negativeInt = 1
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.negativeInt = "not a number"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.negativeInt = - 5.5
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.negativeInt = 0

    def test_non_positive_int(self):
        obj = self.create_object()
        uri = obj.id
        value = -5
        obj.nonPositiveInt = value
        obj.save()
        obj = lc_model.get(id=uri)
        self.assertEquals(obj.nonPositiveInt, value)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.nonPositiveInt = 1
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.nonPositiveInt = "not a number"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.nonPositiveInt = - 5.5
        obj.nonPositiveInt = 0

    def test_non_negative_int(self):
        obj = self.create_object()
        uri = obj.id
        value = 5
        obj.nonNegativeInt = value
        obj.save()
        obj = lc_model.get(id=uri)
        self.assertEquals(obj.nonNegativeInt, value)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.nonNegativeInt = -1
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.nonNegativeInt = "not a number"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.nonNegativeInt = 5.5
        obj.nonNegativeInt = 0
    
    def test_decimal(self):
        obj = self.create_object()
        uri = obj.id
        value = Decimal(23.05)
        obj.decimal = value
        obj.save()
        obj = lc_model.get(id=uri)
        self.assertEquals(obj.decimal, value)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.decimal = "not a number"
        obj.decimal = -2.433
        obj.decimal = 0

    def test_double(self):
        obj = self.create_object()
        uri = obj.id
        value = Decimal(23.05)
        obj.double = value
        obj.save()
        obj = lc_model.get(id=uri)
        self.assertEquals(obj.double, value)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.double = "not a number"
        obj.double = -2.433
        obj.double = 0
        
    def test_float(self):
        obj = self.create_object()
        uri = obj.id
        value = Decimal(23.05)
        obj.float = value
        obj.save()
        obj = lc_model.get(id=uri)
        self.assertEquals(obj.float, value)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.float = "not a number"
        obj.float = -2.433
        obj.float = 0

    def test_mbox(self):
        obj = self.create_object()
        uri = obj.id
        mail = "john.doe@example.org"
        obj.mbox = mail
        obj.save()
        obj = lc_model.get(id=uri)
        self.assertEquals(obj.mbox, mail)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.mbox = "john@somewhere@nowhereindeed.org"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.mbox = "john"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.mbox = 5
        obj.mbox = "john+spam@example.org"

    def test_email(self):
        obj = self.create_object()
        uri = obj.id
        mail = "john.doe@example.org"
        obj.email = mail
        obj.save()
        obj = lc_model.get(id=uri)
        self.assertEquals(obj.email, mail)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.email = "john@somewhere@nowhereindeed.org"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.email = "john"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.email = 5
        obj.email = "john+spam@example.org"
