.. _dbpedia:

============================
DBpedia querying (read-only)
============================

`Source code <https://github.com/oldm/OldMan/blob/master/examples/dbpedia_film.py>`_

This example presents a use case where an OLDM produces a significant overhead that is important
to understand.

We want to query the  `DBpedia <https://en.wikipedia.org/wiki/Dbpedia>`_   which contains RDF statements
extracted from the info-boxes of Wikipedia.
DBpedia provides a public SPARQL endpoint powered by `Virtuoso <https://github.com/openlink/virtuoso-opensource>`_.

Inspired by `a gist of O. Berger <https://gist.github.com/olberger/c6ebd26bb389e270da72>`_, we will display:

 1. The 10 first French films found on DBpedia and the names of their actors;
 2. The films in which `Michel Piccoli <https://en.wikipedia.org/wiki/Michel_Piccoli>`_ had a role.


Direct SPARQL queries (without OldMan)
--------------------------------------

First, let's create a Graph to access the DBpedia SPARQL endpoint ::

    from rdflib import Graph
    from rdflib.plugins.stores.sparqlstore import SPARQLStore
    data_graph = Graph(SPARQLStore("http://dbpedia.org/sparql", context_aware=False))

Query 1
~~~~~~~
::

    import time
    q3_start_time = time.time()

    results = data_graph.query("""
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dbpo: <http://dbpedia.org/ontology/>

    SELECT ?film ?title_fr ?title_en ?actor ?actor_name_fr ?actor_name_en
    WHERE {
        {
         SELECT ?film
         WHERE {
            ?film a dbpo:Film ;
                  dcterms:subject <http://dbpedia.org/resource/Category:French_films> .
          }
          LIMIT 10
        }
        OPTIONAL {
           ?film rdfs:label ?title_en .
           FILTER langMatches( lang(?title_en), "EN" ) .
        }
        OPTIONAL {
           ?film rdfs:label ?title_fr .
           FILTER langMatches( lang(?title_fr), "FR" ) .
        }
        OPTIONAL {
          ?film dbpo:with ?actor .
          OPTIONAL {
            ?actor foaf:name ?actor_name_en .
            FILTER langMatches( lang(?actor_name_en), "EN" ) .
          }
          OPTIONAL {
            ?actor foaf:name ?actor_name_fr .
            FILTER langMatches( lang(?actor_name_fr), "FR" ) .
          }
        }
    }
    """)

Now we extract the film titles and the names of the actors::

    film_titles = {}
    film_actors = {}
    for film_iri, title_fr, title_en, actor_iri, actor_name_fr, actor_name_en in results:
        if film_iri not in film_titles:
            for t in [title_fr, title_en, film_iri]:
                if t is not None:
                    film_titles[film_iri] = unicode(t)
                    break
        for name in [actor_name_fr, actor_name_en, actor_iri]:
            if name is not None:
                if film_iri not in film_actors:
                    film_actors[film_iri] = [name]
                elif name not in film_actors[film_iri]:
                    film_actors[film_iri].append(unicode(name))
                break

and display them::

    >>> for film_iri in film_titles:
    ...     title = film_titles[film_iri]
    ...     if film_iri not in film_actors:
    ...         print "%s %s (no actor declared)" % (title, film_iri)
    ...     else:
    ...         actor_names = ", ".join(film_actors[film_iri])
    ...         print "%s with %s" % (title, actor_names)
    And Now... Ladies and Gentlemen with Patricia Kaas, Jeremy Irons, Thierry Lhermitte
    Un long dimanche de fiançailles (film) with Dominique Pinon, Marion Cotillard, Ticky Holgado, Audrey Tautou, Jodie Foster, Chantal Neuwirth, Gaspard Ulliel, André Dussollier, Andre Dussolier
    Charlotte et Véronique http://dbpedia.org/resource/All_the_Boys_Are_Called_Patrick (no actor declared)
    Toutes ces belles promesses with Jeanne Balibar, Bulle Ogier, Valerie Crunchant, http://dbpedia.org/resource/Renaud_B%C3%A9card
    Édith et Marcel with Évelyne Bouix, Evelyne Bouix, http://dbpedia.org/resource/Marcel_Cerdan_Jr
    Une robe d'été http://dbpedia.org/resource/A_Summer_Dress (no actor declared)
    9 semaines 1/2 with Kim Basinger, Mickey Rourke
    Tout sur ma mère with Penélope Cruz, Penélope Cruz Sánchez, Cecilia Roth, Antonia San Juan, Candela Pena, Marisa Paredes
    Artemisia (film) with Miki Manojlović, Predrag Miki Manojlovic, Michel Serrault, Valentina Cervi
    Two Days in Paris with Julie Delpy, Adam Goldberg, Daniel Bruhl
    >>> print "Done in %.3f seconds" % (time.time() - q3_start_time)
    Done in 0.252 seconds

Some names are missing in the DBpedia and are replaced by the URI.
The film URI is also displayed when the actors are unknown so that you can check with your browser
that this information is missing.

Query 2
~~~~~~~

::

    q4_start_time = time.time()
    results = data_graph.query("""
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dbpo: <http://dbpedia.org/ontology/>

    SELECT ?film ?title_fr ?title_en
    WHERE {
        ?film a dbpo:Film ;
              dbpo:with <http://dbpedia.org/resource/Michel_Piccoli> .
        OPTIONAL {
           ?film rdfs:label ?title_en .
           FILTER langMatches( lang(?title_en), "EN" ) .
        }
        OPTIONAL {
           ?film rdfs:label ?title_fr .
           FILTER langMatches( lang(?title_fr), "FR" ) .
        }
    }
    """)

::

    >>> for film_iri, title_fr, title_en in results:
    ...     if film_iri not in film_titles:
    ...         for t in [title_fr, title_en, film_iri]:
    ...             if t is not None:
    ...                 print t
    ...                 break
        La Diagonale du fou
        Le Journal d'une femme de chambre (film, 1964)
        La Grande Bouffe
        Max et les Ferrailleurs
        La Voie lactée (film, 1969)
        Les Demoiselles de Rochefort
        Le Saut dans le vide
        Belle toujours
        Boxes
        Des enfants gâtés
        Une étrange affaire
        Belle de Jour (film)
        Benjamin ou les Mémoires d'un puceau
        Le Mépris (film)
        Dillinger est mort
        Généalogies d'un crime
        Je rentre à la maison
        La Belle Noiseuse
        La Chamade (film)
        Le Prix du danger (film)
        Mauvais Sang (film)
        Milou en mai
        Passion (film, 1982)
        La Prophétie des grenouilles
        La Poussière du temps
        Le Fantôme de la liberté
        Compartiment tueurs
        Les Choses de la vie
        Themroc
        Une chambre en ville
        Vincent, François, Paul... et les autres
        Habemus papam (film)
        Les Noces rouges
        Les Cent et Une Nuits de Simon Cinéma
        La Décade prodigieuse
        Der Preis fürs Überleben
        Party (1996 film)
        The Distant Land
        Passion in the Desert
    >>> print "Done in %.3f seconds" % (time.time() - q4_start_time)
    Done in 0.180 seconds


With OldMan
-----------

Let's first create two :class:`~oldman.model.Model` objects: `film_model` and `person_model` from these
`context <https://raw.githubusercontent.com/oldm/OldMan/master/examples/dbpedia_film_context.jsonld>`_
and `schema <https://raw.githubusercontent.com/oldm/OldMan/master/examples/dbpedia_film_schema.ttl>`_::

    from oldman import create_user_mediator, SparqlStore
    from dogpile.cache import make_region

    schema_url = "https://raw.githubusercontent.com/oldm/OldMan/master/examples/dbpedia_film_schema.ttl"
    schema_graph = Graph().parse(schema_url, format="turtle")

    context_url = "https://raw.githubusercontent.com/oldm/OldMan/master/examples/dbpedia_film_context.jsonld"

    # Same data graph that before
    data_graph = Graph(SPARQLStore("http://dbpedia.org/sparql", context_aware=False))

    cache_region = make_region().configure('dogpile.cache.memory_pickle')

    # store: SPARQL-aware triple store, with two models
    store = SparqlStore(data_graph, schema_graph=schema_graph, cache_region=cache_region)
    store.create_model("http://dbpedia.org/ontology/Film", context_url)
    # JSON-LD terms can be used instead of IRIs
    store.create_model("Person", context_url)

    # Mediator for users
    user_mediator = create_user_mediator(store)
    # Re-uses the models of the data store
    user_mediator.use_all_store_models()
    film_model = user_mediator.get_client_model("http://dbpedia.org/ontology/Film")
    actor_model = user_mediator.get_client_model("Person")

Please note that we set up a resource cache and reused the `data_graph`.

We also declare two extraction functions::

    def extract_title(film):
        if len(film.titles) > 0:
            key = "fr" if "fr" in film.titles else film.titles.keys()[0]
            return "%s (%s version)" % (film.titles[key], key)
        return film.id

    def extract_name(person):
        if person.names is not None and len(person.names) > 0:
            for key in ["fr", "en"]:
                if key in person.names:
                    return person.names[key]
            return person.names.values()[0]
        return person.id

Query 1 (lazy)
~~~~~~~~~~~~~~
By default, OldMan behaves lazily::

    >>> q1_start_time = time.time()
    >>> for film in film_model.filter(subjects=["http://dbpedia.org/resource/Category:French_films"],
    ...                               limit=10):
    ...     title = extract_title(film)
    ...     if film.actors is None:
    ...         print "   %s %s (no actor declared)" % (title, film.id)
    ...     else:
    ...         actor_names = ", ".join([extract_name(a) for a in film.actors])
    ...         print "%s with %s" % (title, actor_names)
    Édith et Marcel (fr version) with http://dbpedia.org/resource/Marcel_Cerdan_Jr, Evelyne Bouix
    Two Days in Paris (fr version) with Julie Delpy, Adam Goldberg, Daniel Bruhl
    9 semaines 1/2 (fr version) with Kim Basinger, Mickey Rourke
    Une robe d'été (fr version) http://dbpedia.org/resource/A_Summer_Dress (no actor declared)
    Un long dimanche de fiançailles (film) (fr version) with Jodie Foster, Chantal Neuwirth, Marion Cotillard, Ticky Holgado, André Dussollier, Dominique Pinon, Audrey Tautou, Gaspard Ulliel
    Tout sur ma mère (fr version) with Cecilia Roth, Antonia San Juan, Marisa Paredes, Candela Pena, Penélope Cruz Sánchez
    Charlotte et Véronique (fr version) http://dbpedia.org/resource/All_the_Boys_Are_Called_Patrick (no actor declared)
    Toutes ces belles promesses (fr version) with Valerie Crunchant, Jeanne Balibar, Bulle Ogier, http://dbpedia.org/resource/Renaud_B%C3%A9card
    And Now... Ladies and Gentlemen (fr version) with Thierry Lhermitte, Jeremy Irons, Patricia Kaas
    Artemisia (film) (fr version) with Michel Serrault, Miki Manojlović, Valentina Cervi
    >>> print "Done in %.3f seconds" % (time.time() - q1_start_time)
    Done in 17.123 seconds

17s? Why is it so slow?  There are two reasons:

1. OldMan loads a :class:`~oldman.resource.Resource` object for each film or actor that is displayed.
   Loading a :class:`~oldman.resource.Resource` object implies to retrieve all the triples in which
   the resource is the subject. In DBpedia, entries like films and actors have often many triples. Some
   of them have long textual literal values (localized paragraphs from Wikipedia).
   For instance, see `<http://dbpedia.org/resource/Penelope_Cruz>`_.
   This approach retrieves much more information than we need for our specific query.
2. By default OldMan is lazy so it retrieves each a :class:`~oldman.resource.Resource` object at the last time,
   *one by one in sequence*. The execution of this long sequence of queries takes a long time, partly because of
   the network latency that is multiplied by the number of queries.

Query 1 (eager)
~~~~~~~~~~~~~~~

While this first phenomenon is something you should expect when using an OLDM, the second reason can avoided
by adopting an eager strategy::

    >>> q1_start_time = time.time()
    >>> for film in film_model.filter(subjects=["http://dbpedia.org/resource/Category:French_films"],
    ...                               limit=10, eager=True, 
    ...                               pre_cache_properties=["http://dbpedia.org/ontology/starring"]):
    ... # Code and results not shown
    >>> print "Done in %.3f seconds" % (time.time() - q1_start_time)
    Done in 2.518 seconds

The eager strategy makes one heavy SPARQL request that returns all the triples about the films but also about
the actors (thanks to the pre-cached property `dbpo:starring`).
The network latency is then almost minimal.

If we re-query it again lazily, thanks to the cache it makes just one lightweight SPARQL query::

    >>> q1_start_time = time.time()
    >>> for film in film_model.filter(subjects=["http://dbpedia.org/resource/Category:French_films"],
    ...                               limit=10):
    ... # Code and results not shown
    >>> print "Done in %.3f seconds" % (time.time() - q1_start_time)
    Done in 0.182 seconds

But if we re-query it eagerly, the heavy query will be sent again. The cache is then of little interest::

    >>> # Code and results not shown
    >>> print "Done in %.3f seconds" % (time.time() - q1_start_time)
    Done in 2.169 seconds


Query 2 (lazy)
~~~~~~~~~~~~~~

::

    >>> q2_start_time = time.time()
    >>> for film in film_model.filter(actors=["http://dbpedia.org/resource/Michel_Piccoli"]):
    ...     print extract_title(film)
    ... # Results not shown
    >>> print "Done in %.3f seconds" % (time.time() - q2_start_time)
    Done in 16.419 seconds

Query 2 (eager)
~~~~~~~~~~~~~~~
::

    >>> q2_start_time = time.time()
    >>> for film in film_model.filter(actors=["http://dbpedia.org/resource/Michel_Piccoli"],
                                      eager=True):
    ... # Code and results not shown
    >>> print "Done in %.3f seconds" % (time.time() - q2_start_time)
    Done in 1.503 seconds
