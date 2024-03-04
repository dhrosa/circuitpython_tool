Command Reference
========================================

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool [OPTIONS] COMMAND

.. rubric:: Description

Tool for interfacing with CircuitPython devices.


.. rubric:: Options

--log-level log_level
   Only display logs at or above ths level.

   Aliases: ``-l``


--fake-device-config fake_device_config
   Path to TOML configuration file for fake devices. For use in tests and demos.

   Aliases: ``-f``


--version
   Show the version and exit.

   Aliases: ``-v``





----

clean
========================================

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool clean DEVICE

.. rubric:: Description

Deletes all files on the target device, and creates an empty boot.py and code.py on it.




----

completion
========================================

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

connect
========================================

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool connect DEVICE

.. rubric:: Description

Connect to a device's serial terminal.




----

devices
========================================

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool devices [OPTIONS] [QUERY]

.. rubric:: Description

List all connected CircuitPython devices.

If ``QUERY`` is specified, only devices matching that query are listed.


.. rubric:: Options

--save fake_device_save_path
   If set, save devices to a TOML file for later recall using the ``--fake-devices`` flag.

   Aliases: ``-s``





----

mount
========================================

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool mount DEVICE

.. rubric:: Description

Mounts the specified device if needed, and prints the mountpoint.




----

uf2
========================================

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 COMMAND

.. rubric:: Description

Search and download CircuitPython UF2 binaries.




----

uf2 analyze
========================================

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 analyze IMAGE_PATH

.. rubric:: Description

Print details of each block in a UF2 image.

If run in an interactive terminal, you can use arrow keys to browse blocks.
If not run in an interactive context, the information about every block is
printed.




----

uf2 boot-info
========================================

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 boot-info DEVICE

.. rubric:: Description

Lookup UF2 bootloader info of the specified CircuitPython device.




----

uf2 devices
========================================

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 devices

.. rubric:: Description

List connected devices that are in UF2 bootloader mode.




----

uf2 download
========================================

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 download [OPTIONS] BOARD [DESTINATION]

.. rubric:: Description

Download CircuitPython image for the requested board.

If ``DESTINATION`` is not provided, the file is downloaded to the current directory.

If ``DESTINATION`` is a directory, the filename is automatically generated.


.. rubric:: Options

--locale locale
   Locale for CircuitPython install.


--offline
   If true, just print the download URL without actually downloading.





----

uf2 enter
========================================

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 enter DEVICE

.. rubric:: Description

Restart selected device into UF2 bootloader.




----

uf2 exit
========================================

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 exit

.. rubric:: Description

Restart given UF2 bootloader device into normal application code.




----

uf2 install
========================================

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 install [OPTIONS]

.. rubric:: Description

Install a UF2 image onto a connected UF2 bootloader device.

If a CircuitPython device is specified with ``--device``, then we restart that
device into its UF2 bootloader and install the image onto it. If ``--device``
is not specified, we assume there is already a connected UF2 bootloader device.


.. rubric:: Options

--image_path image_path
   If specified, install this already-existing UF2 image.

   Aliases: ``-i``


--board board
   If specified, automatically download and install appropriate CircuitPython UF2 image for this board ID.

   Aliases: ``-b``


--device query
   If specified, this device will be restarted into its UF2 bootloader and be used as the target device for installing the image.

   Aliases: ``-d``


--locale locale
   Locale for CircuitPython install. Not used if an explicit image is given using ``--image_path``.


--delete-download
   Delete any downloaded UF2 images on exit.





----

uf2 mount
========================================

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 mount

.. rubric:: Description

Mount connected UF2 bootloader device if needed and print the mountpoint.




----

uf2 nuke
========================================

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 nuke

.. rubric:: Description

Clear out flash memory on UF2 bootloader device.




----

uf2 unmount
========================================

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 unmount

.. rubric:: Description

Unmount connected UF2 bootloader device if needed.




----

uf2 versions
========================================

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool uf2 versions

.. rubric:: Description

List available CircuitPython boards.




----

unmount
========================================

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool unmount DEVICE

.. rubric:: Description

Unmounts the specified device if needed.




----

upload
========================================

.. rubric:: Syntax
.. parsed-literal::

   circuitpython-tool upload [OPTIONS] DEVICE

.. rubric:: Description

Continuously upload code to device in response to source file changes.

The contents of the specified source directory will be copied onto the given
CircuitPython device.

If ``--mode`` is ``single-shot``, then the code is uploaded and then the command exits.

If ``--mode`` is ``watch``, then this commnd will perform one upload, and then
will continue running. The command will wait for filesystem events from all
paths and descendant paths of the source tree, and will re-upload code to
the device on each event.


.. rubric:: Options

--dir source_dir
   Path containing source code to upload. If not specified, the source directory is guessed by searching the current directory and its descendants for user code (e.g. ``code.py``).

   Aliases: ``-d``


--circup
   If true, use `circup` to automatically install library dependencies on the target device.


--mode mode
   Whether to upload code once, or continuously.


--batch-period batch_period
   Batch filesystem events that happen within this period. This reduces spurious uploads when files update in quick succession. Unit: seconds



