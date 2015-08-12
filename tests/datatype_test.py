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
from oldman import create_user_mediator, parse_graph_safely, SparqlStore
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

data_store = SparqlStore(data_graph, schema_graph=schema_graph)
data_store.create_model("LocalClass", context, iri_prefix="http://localhost/objects/")

user_mediator = create_user_mediator(data_store)
user_mediator.import_store_models()
lc_model = user_mediator.get_client_model("LocalClass")
default_list_en = ["w1", "w2"]


class DatatypeTest(TestCase):

    def tearDown(self):
        """ Clears the data graph """
        data_graph.update("CLEAR DEFAULT")

    def create_object(self, session):
        obj = lc_model.new(session)
        session.flush()
        return obj

    def test_single_bool(self):
        session1 = user_mediator.create_session()
        obj1 = self.create_object(session1)
        uri = obj1.id.iri
        obj1.single_bool = True
        session1.flush()
        session1.close()

        session2 = user_mediator.create_session()
        obj2 = lc_model.get(session2, iri=uri)
        self.assertEquals(obj2.single_bool, True)
        obj2.single_bool = None
        session2.flush()
        session2.close()

        session3 = user_mediator.create_session()
        obj3 = lc_model.get(session3, iri=uri)
        self.assertEquals(obj3.single_bool, None)

        obj3.single_bool = False
        session3.flush()
        session3.close()

        session4 = user_mediator.create_session()
        obj4 = lc_model.get(session4, iri=uri)
        self.assertEquals(obj4.single_bool, False)
        session4.close()

    def test_single_date(self):
        session1 = user_mediator.create_session()
        obj1 = self.create_object(session1)
        uri = obj1.id.iri
        d = date(2009, 11, 2)
        obj1.date = copy(d)
        session1.flush()
        session1.close()

        session2 = user_mediator.create_session()
        obj2 = lc_model.get(session2, iri=uri)
        self.assertEquals(obj2.date, d)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.date = "not a date object"
        session2.close()

    def test_single_datetime(self):
        session1 = user_mediator.create_session()
        obj1 = self.create_object(session1)
        uri = obj1.id.iri
        d = datetime.now()
        obj1.datetime = copy(d)
        session1.flush()
        session1.close()

        session2 = user_mediator.create_session()
        obj2 = lc_model.get(session2, iri=uri)
        self.assertEquals(obj2.datetime, d)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.datetime = "not a date time object"
        session2.close()

    def test_single_time(self):
        session1 = user_mediator.create_session()
        obj1 = self.create_object(session1)
        uri = obj1.id.iri
        t = time(12, 55, 30)
        obj1.time = copy(t)
        session1.flush()
        session1.close()

        session2 = user_mediator.create_session()
        obj2 = lc_model.get(session2, iri=uri)
        self.assertEquals(obj2.time, t)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.time = "not a time object"
        session2.close()

    def test_int(self):
        session1 = user_mediator.create_session()
        obj1 = self.create_object(session1)
        uri = obj1.id.iri
        value = -5
        obj1.int = value
        session1.flush()
        session1.close()

        session2 = user_mediator.create_session()
        obj2 = lc_model.get(session2, iri=uri)
        self.assertEquals(obj2.int, value)
        obj2.int = 0
        obj2.int = 5
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.int = "not a number"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.int = 5.5
        session2.close()

    def test_integer(self):
        session1 = user_mediator.create_session()
        obj1 = self.create_object(session1)
        uri = obj1.id.iri
        value = 5
        obj1.integer = value
        session1.flush()
        session1.close()

        session2 = user_mediator.create_session()
        obj2 = lc_model.get(session2, iri=uri)
        self.assertEquals(obj2.integer, value)
        obj2.integer = 0
        obj2.integer = -5
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.integer = "not a number"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.integer = 5.5
        session2.close()

    def test_short(self):
        session1 = user_mediator.create_session()
        obj1 = self.create_object(session1)
        uri = obj1.id.iri
        value = -5
        obj1.short = value
        session1.flush()
        session1.close()

        session2 = user_mediator.create_session()
        obj2 = lc_model.get(session2, iri=uri)
        self.assertEquals(obj2.short, value)
        obj2.short = 0
        obj2.short = 5
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.short = "not a number"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.short = 5.5
        session2.close()

    def test_positive_int(self):
        session1 = user_mediator.create_session()
        obj1 = self.create_object(session1)
        uri = obj1.id.iri
        value = 5
        obj1.positiveInt = value
        session1.flush()
        session1.close()

        session2 = user_mediator.create_session()
        obj2 = lc_model.get(session2, iri=uri)
        self.assertEquals(obj2.positiveInt, value)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.positiveInt = -1
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.positiveInt = "not a number"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.positiveInt = 5.5
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.positiveInt = 0
        session2.close()

    def test_negative_int(self):
        session1 = user_mediator.create_session()
        obj1 = self.create_object(session1)
        uri = obj1.id.iri
        value = -5
        obj1.negativeInt = value
        session1.flush()
        session1.close()

        session2 = user_mediator.create_session()
        obj2 = lc_model.get(session2, iri=uri)
        self.assertEquals(obj2.negativeInt, value)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.negativeInt = 1
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.negativeInt = "not a number"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.negativeInt = - 5.5
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.negativeInt = 0
        session2.close()

    def test_non_positive_int(self):
        session1 = user_mediator.create_session()
        obj = self.create_object(session1)
        uri = obj.id.iri
        value = -5
        obj.nonPositiveInt = value
        session1.flush()
        session1.close()

        session2 = user_mediator.create_session()
        obj = lc_model.get(session2, iri=uri)
        self.assertEquals(obj.nonPositiveInt, value)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.nonPositiveInt = 1
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.nonPositiveInt = "not a number"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.nonPositiveInt = - 5.5
        obj.nonPositiveInt = 0
        session2.close()

    def test_non_negative_int(self):
        session1 = user_mediator.create_session()
        obj1 = self.create_object(session1)
        uri = obj1.id.iri
        value = 5
        obj1.nonNegativeInt = value
        session1.flush()
        session1.close()

        session2 = user_mediator.create_session()
        obj2 = lc_model.get(session2, iri=uri)
        self.assertEquals(obj2.nonNegativeInt, value)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.nonNegativeInt = -1
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.nonNegativeInt = "not a number"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.nonNegativeInt = 5.5
        obj2.nonNegativeInt = 0
        session2.close()
    
    def test_decimal(self):
        session1 = user_mediator.create_session()
        obj1 = self.create_object(session1)
        uri = obj1.id.iri
        value = Decimal(23.05)
        obj1.decimal = value
        session1.flush()
        session1.close()

        session2 = user_mediator.create_session()
        obj2 = lc_model.get(session2, iri=uri)
        self.assertEquals(obj2.decimal, value)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.decimal = "not a number"
        obj2.decimal = -2.433
        obj2.decimal = 0
        session2.close()

    def test_double(self):
        session1 = user_mediator.create_session()
        obj1 = self.create_object(session1)
        uri = obj1.id.iri
        value = Decimal(23.05)
        obj1.double = value
        session1.flush()
        session1.close()

        session2 = user_mediator.create_session()
        obj2 = lc_model.get(session2, iri=uri)
        self.assertEquals(obj2.double, value)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.double = "not a number"
        obj2.double = -2.433
        obj2.double = 0
        session2.close()
        
    def test_float(self):
        session1 = user_mediator.create_session()
        obj1 = self.create_object(session1)
        uri = obj1.id.iri
        value = Decimal(23.05)
        obj1.float = value
        session1.flush()
        session1.close()

        session2 = user_mediator.create_session()
        obj = lc_model.get(session2, iri=uri)
        self.assertEquals(obj.float, value)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj.float = "not a number"
        obj.float = -2.433
        obj.float = 0
        session2.close()

    def test_mbox(self):
        session1 = user_mediator.create_session()
        obj1 = self.create_object(session1)
        uri = obj1.id.iri
        mail = "john.doe@example.org"
        obj1.mbox = mail
        session1.flush()
        session1.close()

        session2 = user_mediator.create_session()
        obj2 = lc_model.get(session2, iri=uri)
        self.assertEquals(obj2.mbox, mail)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.mbox = "john@somewhere@nowhereindeed.org"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.mbox = "john"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.mbox = 5
        obj2.mbox = "john+spam@example.org"
        session2.close()

    def test_email(self):
        session1 = user_mediator.create_session()
        obj1 = self.create_object(session1)
        uri = obj1.id.iri
        mail = "john.doe@example.org"
        obj1.email = mail
        session1.flush()
        session1.close()

        session2 = user_mediator.create_session()
        obj2 = lc_model.get(session2, iri=uri)
        self.assertEquals(obj2.email, mail)
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.email = "john@somewhere@nowhereindeed.org"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.email = "john"
        with self.assertRaises(OMAttributeTypeCheckError):
            obj2.email = 5
        obj2.email = "john+spam@example.org"
        session2.close()
