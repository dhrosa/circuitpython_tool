=================
Command Reference
=================

****************
Parameter Types
****************

.. _types.query:

``query``
   A ``vendor:model:serial`` string that specifies one or more connected USB CircuitPythonDevice. Each component string is searched for in the respective attribute. Empty strings are allowed in each component of the query. Example queries:

   * ``::`` matches ANY device.
   * ``Adafruit::`` matches any device whose vendor contains the string "Adafruit"
   * ``:Feather:`` matches any device whose model contains the string "Feather"
   * ``Adafruit:Feather:`` matches any device whose vendor contains the string "Adafruit" AND whose model contains the string "Feather"


.. _types.device:

``device``
   The same as the above ``query``, except that a ``device`` parameter is only allowed to match a single connected device, rather than any number.

.. _types.board_id:


``board_id``
   A string specifying Adafruit's identifier for a CircuitPython-supported board. This corresponds to the lowercase board names found in the URLs of the boards on the `CircuitPython Downloads <https://circuitpython.org/downloads>`_ page. For example, a ``board_id`` value of ``raspberry_pi_pico`` corresponds to the `Raspberry Pi Pico <https://circuitpython.org/board/raspberry_pi_pico/>`_ board.

   A full list of possible values can be seen using the :ref:`uf2 versions <uf2.versions.command>` command.

.. include:: generated.rst
           
