from uuid import uuid1


class UriGenerator(object):

    def __init__(self, **kwargs):
        pass

    def generate(self):
        raise NotImplementedError()


class RandomPrefixedUriGenerator(UriGenerator):

    def __init__(self, **kwargs):
        self.prefix = kwargs["prefix"]

    def generate(self):
        return "%s%s" % (self.prefix, uuid1().hex)


class RandomUriGenerator(RandomPrefixedUriGenerator):

    def __init__(self, **kwargs):
        hostname = kwargs.get("hostname", "localhost")
        prefix = "http://%s/.well-known/genid/" % hostname
        RandomPrefixedUriGenerator.__init__(self, prefix=prefix)