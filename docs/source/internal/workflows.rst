##################
Internal Workflows
##################

.. rubric :: Python Code Development

Automatically run formatters, linters, and tests on any Python change:

.. code:: shell

   find . -type f -iname '*.py*' | entr -c -s 'hatch run style:all && hatch run test:all'


.. rubric :: Documentation Development

Automatically run formatters, linters, and rebuild docs on any Python change:

.. code:: shell

   find src docs -type f | egrep "\.(py|rst)$" | egrep -v "undo|generated" | entr -c -s 'hatch run style:all && hatch run docs:sphinx'

   
.. rubric :: Publish PyPI package

.. code:: shell
          
   git clean -dfx
   hatch publish -u __token__ -a $(cat ~/.pypi/circuitpython-tool.token)
