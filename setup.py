from setuptools import setup
setup(name="OldMan",
      author="Benjamin Cogrel",
      author_email="benjamin.cogrel@bcgl.fr",
      url="https://github.com/oldm/oldman",
      version="0.1",
      description="Object Linked Data Mapper",
      long_description=open('README.rst').read(),
      packages=['oldman',
                'oldman.management',
                'oldman.parsing',
                'oldman.parsing.schema',
                'oldman.rest',
                'oldman.utils',
                'oldman.validation'
      ],
      include_package_data=True,
      #zip_safe = False,
      install_requires=['rdflib',
                        'SPARQLWrapper',
                        'validate_email',
                        'dogpile.cache'
      ],
      license="BSD",
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: BSD License',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Topic :: Software Development :: Libraries',
      ]
      )
