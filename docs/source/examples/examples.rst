========
Examples
========

#. Create a new folder for your source code, e.g. in ``~/Documents/test`` and
   change into that directory:

   .. code:: shell
          
      mkdir ~/Documents/test
      cd ~/Documents/test

#. In an editor, create a new file named ``code.py`` in the above folder with
   the following contents:

   .. literalinclude:: example.py
      :language: python

#. Enable shell completion to make the subsequent commands easier:

   .. code:: shell

      eval $(circuitpython-tool completion)

#. List connected CircuitPython devices to figure out the device naming:

   .. code:: shell

      circuitpython-tool devices

   The connected device has a ``model`` value of ``Pico_W``. To refer to this
   device in subsequent commands, we can use the :ref:`types.device` syntax of
   ``:Pico:``. Alternatively, if you only have one device connected to your
   computer, you can just use the wildcard ``::`` value.

#. Use ``circuitpython-tool`` to upload code:

   .. code:: shell
           
      circuitpython-tool upload :Pico: --mode=watch


   The ``:Pico:`` argument refers to the Raspberry Pi Pico W we found using. the
   ``circuitpython devices`` command. The ``--mode=watch`` option keeps the
   program continuously running and waiting for file changes. You can exit it at
   any time using :kbd:`Control-C`

#. Open a new terminal window and connect to your device's serial terminal:

   .. code:: shell

      circuitpython-tool connect :Pico:
