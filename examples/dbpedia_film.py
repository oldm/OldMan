# Inspired by https://gist.github.com/olberger/c6ebd26bb389e270da72

from rdflib import Graph
from rdflib.plugins.stores.sparqlstore import SPARQLStore
from oldman import ResourceManager
import logging

logger = logging.getLogger('oldman')
logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)

schema_graph = Graph().parse("https://raw.githubusercontent.com/oldm/OldMan/master/examples/dbpedia_film_schema.ttl",
                             format="turtle")
data_graph = Graph(SPARQLStore("http://dbpedia.org/sparql", context_aware=False))

context_iri = "https://raw.githubusercontent.com/oldm/OldMan/master/examples/dbpedia_film_context.jsonld"


manager = ResourceManager(schema_graph, data_graph)
film_model = manager.create_model("http://dbpedia.org/ontology/Film", context_iri)
# JSON-LD terms can be used instead of IRIs
actor_model = manager.create_model("Person", context_iri)

french_film_iri = "http://dbpedia.org/resource/Category:French_films"

print "50 first French films on DBPedia"
print "--------------------------------"
for film in film_model.filter(subjects=[french_film_iri], limit=50):
    title = film.title_fr if film.title_fr else film.id
    if film.actors is None:
        print "   %s (no actor declared)" % title
    else:
        actor_names = [a.name if a.name else a.id for a in film.actors]
        print "   %s starring %s" %(title, ", ".join(actor_names))

print "Films starring Michel Piccoli"
print "-----------------------------"
for film in film_model.filter(actors={"http://dbpedia.org/resource/Michel_Piccoli"}):
    title = film.title_fr if film.title_fr else film.id
    print "   %s" % title
