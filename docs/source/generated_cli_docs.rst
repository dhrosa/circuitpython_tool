``<root>``
========================================

Syntax
   .. parsed-literal::

      circuitpython-tool <root> [OPTIONS] COMMAND

Description
   Tool for interfacing with CircuitPython devices.


.. rubric:: Options
.. option:: --log-level log_level, -l log_level

   Only display logs at or above ths level.

.. option:: --fake-device-config fake_device_config, -f fake_device_config

   Path to TOML configuration file for fake devices. For use in tests and demos.

.. option:: --version version, -v version

   Show the version and exit.




----

``clean``
========================================

Syntax
   .. parsed-literal::

      circuitpython-tool clean DEVICE

Description
   Deletes all files on the target device, and creates an empty boot.py and code.py on it.




----

``completion``
========================================

Syntax
   .. parsed-literal::

      circuitpython-tool completion

Description

   Output shell commands needed for auto-completion.

   Evaluating the output of this command will allow auto-completion of this
   program's arguments. This can be done as a one-off using::

     eval "$(circuitpython-tool completion)"

   or by putting the following line in your shell config file (e.g. ``~/.bashrc``)::

     source "$(circuitpython-tool completion)"





----

``connect``
========================================

Syntax
   .. parsed-literal::

      circuitpython-tool connect DEVICE

Description
   Connect to a device's serial terminal.




----

``devices``
========================================

Syntax
   .. parsed-literal::

      circuitpython-tool devices [OPTIONS] [QUERY]

Description

   List all connected CircuitPython devices.

   If ``QUERY`` is specified, only devices matching that query are listed.


.. rubric:: Options
.. option:: --save fake_device_save_path, -s fake_device_save_path

   If set, save devices to a TOML file for later recall using the ``--fake-devices`` flag.




----

``mount``
========================================

Syntax
   .. parsed-literal::

      circuitpython-tool mount DEVICE

Description
   Mounts the specified device if needed, and prints the mountpoint.




----

``uf2``
========================================

Syntax
   .. parsed-literal::

      circuitpython-tool uf2 COMMAND

Description
   Search and download CircuitPython UF2 binaries.




----

``uf2 analyze``
========================================

Syntax
   .. parsed-literal::

      circuitpython-tool uf2 analyze IMAGE_PATH

Description

   Print details of each block in a UF2 image.

   If run in an interactive terminal, you can use arrow keys to browse blocks.
   If not run in an interactive context, the information about every block is
   printed.





----

``uf2 boot-info``
========================================

Syntax
   .. parsed-literal::

      circuitpython-tool uf2 boot-info DEVICE

Description
   Lookup UF2 bootloader info of the specified CircuitPython device.




----

``uf2 devices``
========================================

Syntax
   .. parsed-literal::

      circuitpython-tool uf2 devices

Description
   List connected devices that are in UF2 bootloader mode.




----

``uf2 download``
========================================

Syntax
   .. parsed-literal::

      circuitpython-tool uf2 download [OPTIONS] BOARD [DESTINATION]

Description

   Download CircuitPython image for the requested board.

   If ``DESTINATION`` is not provided, the file is downloaded to the current directory.

   If ``DESTINATION`` is a directory, the filename is automatically generated.



.. rubric:: Options
.. option:: --locale locale

   Locale for CircuitPython install.

.. option:: --offline offline

   If true, just print the download URL without actually downloading.




----

``uf2 enter``
========================================

Syntax
   .. parsed-literal::

      circuitpython-tool uf2 enter DEVICE

Description
   Restart selected device into UF2 bootloader.




----

``uf2 exit``
========================================

Syntax
   .. parsed-literal::

      circuitpython-tool uf2 exit

Description
   Restart given UF2 bootloader device into normal application code.




----

``uf2 install``
========================================

Syntax
   .. parsed-literal::

      circuitpython-tool uf2 install [OPTIONS]

Description

   Install a UF2 image onto a connected UF2 bootloader device.

   If a CircuitPython device is specified with ``--device``, then we restart that
   device into its UF2 bootloader and install the image onto it. If ``--device``
   is not specified, we assume there is already a connected UF2 bootloader device.



.. rubric:: Options
.. option:: --image_path image_path, -i image_path

   If specified, install this already-existing UF2 image.

.. option:: --board board, -b board

   If specified, automatically download and install appropriate CircuitPython UF2 image for this board ID.

.. option:: --device query, -d query

   If specified, this device will be restarted into its UF2 bootloader and be used as the target device for installing the image.

.. option:: --locale locale

   Locale for CircuitPython install. Not used if an explicit image is given using ``--image_path``.

.. option:: --delete-download delete_download

   Delete any downloaded UF2 images on exit.




----

``uf2 mount``
========================================

Syntax
   .. parsed-literal::

      circuitpython-tool uf2 mount

Description
   Mount connected UF2 bootloader device if needed and print the mountpoint.




----

``uf2 nuke``
========================================

Syntax
   .. parsed-literal::

      circuitpython-tool uf2 nuke

Description
   Clear out flash memory on UF2 bootloader device.




----

``uf2 unmount``
========================================

Syntax
   .. parsed-literal::

      circuitpython-tool uf2 unmount

Description
   Unmount connected UF2 bootloader device if needed.




----

``uf2 versions``
========================================

Syntax
   .. parsed-literal::

      circuitpython-tool uf2 versions

Description
   List available CircuitPython boards.




----

``unmount``
========================================

Syntax
   .. parsed-literal::

      circuitpython-tool unmount DEVICE

Description
   Unmounts the specified device if needed.




----

``upload``
========================================

Syntax
   .. parsed-literal::

      circuitpython-tool upload [OPTIONS] DEVICE

Description

   Continuously upload code to device in response to source file changes.

   The contents of the specified source directory will be copied onto the given
   CircuitPython device.

   If ``--mode`` is ``single-shot``, then the code is uploaded and then the command exits.

   If ``--mode`` is ``watch``, then this commnd will perform one upload, and then
   will continue running. The command will wait for filesystem events from all
   paths and descendant paths of the source tree, and will re-upload code to
   the device on each event.



.. rubric:: Options
.. option:: --dir source_dir, -d source_dir

   Path containing source code to upload. If not specified, the source directory is guessed by searching the current directory and its descendants for user code (e.g. ``code.py``).

.. option:: --circup circup

   If true, use `circup` to automatically install library dependencies on the target device.

.. option:: --mode mode

   Whether to upload code once, or continuously.

.. option:: --batch-period batch_period

   Batch filesystem events that happen within this period. This reduces spurious uploads when files update in quick succession. Unit: seconds


