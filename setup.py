from setuptools import setup
setup(name="OldMan",
      author="Benjamin Cogrel",
      author_email="benjamin.cogrel@bcgl.fr",
      url="https://github.com/bcogrel/oldman",
      version="0.1",
      description="Object Linked Data Mapper",
      long_description=open('README.rst').read(),
      packages=['oldman'],
      include_package_data=True,
      #zip_safe = False,
      install_requires=['rdflib',
                        'validate_email',
                        'enum34',
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

