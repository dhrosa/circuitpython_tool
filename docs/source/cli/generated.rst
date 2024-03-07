
----

.. _command:

********
Commands
********

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool [:ref:`OPTIONS <options>`] :ref:`COMMAND <arguments.command>`
.. rubric:: Description

Tool for interfacing with CircuitPython devices.

.. rubric:: Arguments

.. _arguments.command:

``COMMAND``
   Valid values:

   .. hlist::

      * :ref:`completion<completion.command>`
      * :ref:`devices<devices.command>`
      * :ref:`upload<upload.command>`
      * :ref:`clean<clean.command>`
      * :ref:`connect<connect.command>`
      * :ref:`mount<mount.command>`
      * :ref:`unmount<unmount.command>`
      * :ref:`uf2<uf2.command>`

.. _options:
.. rubric:: Options

--log-level log_level

   *Optional*. Only display logs at or above ths level.

   :Aliases: ``-l``
   :Environment Variable: ``LOG_LEVEL``
   :Choices: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``
   :Default: ``INFO``


--fake-device-config fake_device_config

   *Optional*. Path to TOML configuration file for fake devices. For use in tests and demos.

   :Aliases: ``-f``
   :Environment Variable: ``FAKE_DEVICE_CONFIG``
   :Type: file


--version

   *Optional*. Show the version and exit.

   :Aliases: ``-v``
   :Default: ``False``





----

.. _completion.command:

completion
==========

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool completion
.. rubric:: Description

Output shell commands needed for auto-completion.

Evaluating the output of this command will allow auto-completion of this
program's arguments. This can be done as a one-off using::

  eval "$(circuitpython-tool completion)"

or by putting the following line in your shell config file (e.g. ``~/.bashrc``)::

  source "$(circuitpython-tool completion)"



----

.. _devices.command:

devices
=======

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool devices [:ref:`OPTIONS <devices.options>`] [:ref:`QUERY <devices.arguments.query>`]
.. rubric:: Description

List all connected CircuitPython devices.

If ``QUERY`` is specified, only devices matching that query are listed.

*Linux-only*.

.. rubric:: Arguments

.. _devices.arguments.query:

``QUERY``
   :Required: False

   :Type: :ref:`types.query`

.. _devices.options:
.. rubric:: Options

--save fake_device_save_path

   *Optional*. If set, save devices to a TOML file for later recall using the ``--fake-devices`` flag.

   :Aliases: ``-s``
   :Type: file





----

.. _upload.command:

upload
======

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool upload [:ref:`OPTIONS <upload.options>`] :ref:`DEVICE <upload.arguments.device>`
.. rubric:: Description

Continuously upload code to device in response to source file changes.

The contents of the specified source directory will be copied onto the given
CircuitPython device.

If ``--mode`` is ``single-shot``, then the code is uploaded and then the command exits.

If ``--mode`` is ``watch``, then this commnd will perform one upload, and then
will continue running. The command will wait for filesystem events from all
paths and descendant paths of the source tree, and will re-upload code to
the device on each event.

*Linux-only*.

.. rubric:: Arguments

.. _upload.arguments.device:

``DEVICE``
   :Required: True

   :Type: :ref:`types.device`

.. _upload.options:
.. rubric:: Options

--dir source_dir

   *Optional*. Path containing source code to upload. If not specified, the source directory is guessed by searching the current directory and its descendants for user code (e.g. ``code.py``).

   :Aliases: ``-d``
   :Type: directory


--circup, --no-circup

   *Optional*. If ``True``, use ``circup`` to automatically install library dependencies on the target device.

   :Default: ``False``


--mode mode

   *Optional*. Whether to upload code once, or continuously.

   :Choices: ``single-shot``, ``watch``
   :Default: ``watch``


--batch-period batch_period

   *Optional*. Batch filesystem events that happen within this period. This reduces spurious uploads when files update in quick succession. Unit: seconds

   :Type: float
   :Default: ``0.25``





----

.. _clean.command:

clean
=====

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool clean :ref:`DEVICE <clean.arguments.device>`
.. rubric:: Description

Deletes all files on the target device, and creates an empty boot.py and code.py on it.

*Linux-only*.

.. rubric:: Arguments

.. _clean.arguments.device:

``DEVICE``
   :Required: True

   :Type: :ref:`types.device`



----

.. _connect.command:

connect
=======

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool connect :ref:`DEVICE <connect.arguments.device>`
.. rubric:: Description

Connect to a device's serial terminal.

*Linux-only*.

.. rubric:: Arguments

.. _connect.arguments.device:

``DEVICE``
   :Required: True

   :Type: :ref:`types.device`



----

.. _mount.command:

mount
=====

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool mount :ref:`DEVICE <mount.arguments.device>`
.. rubric:: Description

Mounts the specified device if needed, and prints the mountpoint.

*Linux-only*.

.. rubric:: Arguments

.. _mount.arguments.device:

``DEVICE``
   :Required: True

   :Type: :ref:`types.device`



----

.. _unmount.command:

unmount
=======

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool unmount :ref:`DEVICE <unmount.arguments.device>`
.. rubric:: Description

Unmounts the specified device if needed.

*Linux-only*.

.. rubric:: Arguments

.. _unmount.arguments.device:

``DEVICE``
   :Required: True

   :Type: :ref:`types.device`



----

.. _uf2.command:

uf2
===

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 :ref:`COMMAND <uf2.arguments.command>`
.. rubric:: Description

Search and download CircuitPython UF2 binaries.

.. rubric:: Arguments

.. _uf2.arguments.command:

``COMMAND``
   Valid values:

   .. hlist::

      * :ref:`versions<uf2.versions.command>`
      * :ref:`download<uf2.download.command>`
      * :ref:`devices<uf2.devices.command>`
      * :ref:`install<uf2.install.command>`
      * :ref:`enter<uf2.enter.command>`
      * :ref:`exit<uf2.exit.command>`
      * :ref:`boot-info<uf2.boot-info.command>`
      * :ref:`mount<uf2.mount.command>`
      * :ref:`unmount<uf2.unmount.command>`
      * :ref:`nuke<uf2.nuke.command>`
      * :ref:`analyze<uf2.analyze.command>`



----

.. _uf2.versions.command:

uf2 versions
------------

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 versions
.. rubric:: Description

List available CircuitPython boards.



----

.. _uf2.download.command:

uf2 download
------------

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 download [:ref:`OPTIONS <uf2.download.options>`] :ref:`BOARD <uf2.download.arguments.board>` [:ref:`DESTINATION <uf2.download.arguments.destination>`]
.. rubric:: Description

Download CircuitPython image for the requested board.

If ``DESTINATION`` is not provided, the file is downloaded to the current directory.

If ``DESTINATION`` is a directory, the filename is automatically generated.

.. rubric:: Arguments

.. _uf2.download.arguments.board:

``BOARD``
   :Required: True

   :Type: :ref:`types.board_id`

.. _uf2.download.arguments.destination:

``DESTINATION``
   :Required: False

   :Type: path

.. _uf2.download.options:
.. rubric:: Options

--locale locale

   *Optional*. Locale for CircuitPython install.

   :Type: locale
   :Default: ``en_US``


--offline, --no-offline

   *Optional*. If ``True``, just print the download URL without actually downloading.

   :Default: ``False``





----

.. _uf2.devices.command:

uf2 devices
-----------

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 devices
.. rubric:: Description

List connected devices that are in UF2 bootloader mode.

*Linux-only*.



----

.. _uf2.install.command:

uf2 install
-----------

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 install [:ref:`OPTIONS <uf2.install.options>`]
.. rubric:: Description

Install a UF2 image onto a connected UF2 bootloader device.

If a CircuitPython device is specified with ``--device``, then we restart that
device into its UF2 bootloader and install the image onto it. If ``--device``
is not specified, we assume there is already a connected UF2 bootloader device.

.. _uf2.install.options:
.. rubric:: Options

--image_path image_path

   *Optional*. If specified, install this already-existing UF2 image.

   :Aliases: ``-i``
   :Type: file


--board board

   *Optional*. If specified, automatically download and install appropriate CircuitPython UF2 image for this board ID.

   :Aliases: ``-b``
   :Type: board_id


--device query

   *Optional*. If specified, this device will be restarted into its UF2 bootloader and be used as the target device for installing the image.

   :Aliases: ``-d``
   :Type: query


--locale locale

   *Optional*. Locale for CircuitPython install. Not used if an explicit image is given using ``--image_path``.

   :Type: locale
   :Default: ``en_US``


--delete-download, --no-delete-download

   *Optional*. Delete any downloaded UF2 images on exit.

   :Default: ``True``





----

.. _uf2.enter.command:

uf2 enter
---------

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 enter :ref:`DEVICE <uf2.enter.arguments.device>`
.. rubric:: Description

Restart selected device into UF2 bootloader.

*Linux-only*.

.. rubric:: Arguments

.. _uf2.enter.arguments.device:

``DEVICE``
   :Required: True

   :Type: :ref:`types.device`



----

.. _uf2.exit.command:

uf2 exit
--------

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 exit
.. rubric:: Description

Restart given UF2 bootloader device into normal application code.

*Linux-only*.



----

.. _uf2.boot-info.command:

uf2 boot-info
-------------

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 boot-info :ref:`DEVICE <uf2.boot-info.arguments.device>`
.. rubric:: Description

Lookup UF2 bootloader info of the specified CircuitPython device.

*Linux-only*.

.. rubric:: Arguments

.. _uf2.boot-info.arguments.device:

``DEVICE``
   :Required: True

   :Type: :ref:`types.device`



----

.. _uf2.mount.command:

uf2 mount
---------

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 mount
.. rubric:: Description

Mount connected UF2 bootloader device if needed and print the mountpoint.

*Linux-only*.



----

.. _uf2.unmount.command:

uf2 unmount
-----------

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 unmount
.. rubric:: Description

Unmount connected UF2 bootloader device if needed.

*Linux-only*.



----

.. _uf2.nuke.command:

uf2 nuke
--------

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 nuke
.. rubric:: Description

Clear out flash memory on UF2 bootloader device.

*Linux-only*.



----

.. _uf2.analyze.command:

uf2 analyze
-----------

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 analyze :ref:`IMAGE_PATH <uf2.analyze.arguments.image_path>`
.. rubric:: Description

Print details of each block in a UF2 image.

If run in an interactive terminal, you can use arrow keys to browse blocks.
If not run in an interactive context, the information about every block is
printed.

.. rubric:: Arguments

.. _uf2.analyze.arguments.image_path:

``IMAGE_PATH``
   :Required: True

   :Type: file

