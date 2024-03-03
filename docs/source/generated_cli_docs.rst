``<root>``
========================================

Tool for interfacing with CircuitPython devices.

.. rubric:: Syntax

.. parsed-literal::

   circuitpython-tool <root> [OPTIONS] COMMAND


.. rubric:: Options
.. option:: --log-level log_level, -l log_level

   Only display logs at or above ths level.

.. option:: --fake-device-config fake_device_config, -f fake_device_config

   Path to TOML configuration file for fake devices. For use in tests and demos.

.. option:: --version version, -v version

   Show the version and exit.

``clean``
========================================

Deletes all files on the target device, and creates an empty boot.py and code.py on it.

.. rubric:: Syntax

.. parsed-literal::

   circuitpython-tool clean DEVICE

``completion``
========================================

Output shell commands needed for auto-completion.

    Evaluating the output of this command will allow auto-completion of this
    program's arguments. This can be done as a one-off using:

    eval "$(circuitpython-tool completion)"

    or by putting the following line in your shell config file (e.g. ~/.bashrc):

    source "$(circuitpython-tool completion)"
    

.. rubric:: Syntax

.. parsed-literal::

   circuitpython-tool completion

``connect``
========================================

Connect to a device's serial terminal.

.. rubric:: Syntax

.. parsed-literal::

   circuitpython-tool connect DEVICE

``devices``
========================================

List all connected CircuitPython devices.

    If QUERY is specified, only devices matching that query are listed.

.. rubric:: Syntax

.. parsed-literal::

   circuitpython-tool devices [OPTIONS] [QUERY]


.. rubric:: Options
.. option:: --save fake_device_save_path, -s fake_device_save_path

   If set, save devices to a TOML file for later recall using the --fake-devices flag.

``mount``
========================================

Mounts the specified device if needed, and prints the mountpoint.

.. rubric:: Syntax

.. parsed-literal::

   circuitpython-tool mount DEVICE

``uf2``
========================================

Search and download CircuitPython UF2 binaries.

.. rubric:: Syntax

.. parsed-literal::

   circuitpython-tool uf2 COMMAND

``uf2 analyze``
========================================

Print details of each block in a UF2 image.

    If run in an interactive terminal, you can use arrow keys to browse blocks.
    If not run in an interactive context, the information about every block is
    printed.
    

.. rubric:: Syntax

.. parsed-literal::

   circuitpython-tool uf2 analyze IMAGE_PATH

``uf2 boot-info``
========================================

Lookup UF2 bootloader info of the specified CircuitPython device.

.. rubric:: Syntax

.. parsed-literal::

   circuitpython-tool uf2 boot-info DEVICE

``uf2 devices``
========================================

List connected devices that are in UF2 bootloader mode.

.. rubric:: Syntax

.. parsed-literal::

   circuitpython-tool uf2 devices

``uf2 download``
========================================

Download CircuitPython image for the requested board.

    If DESTINATION is not provided, the file is downloaded to the current directory.
    If DESTINATION is a directory, the filename is automatically generated.
    

.. rubric:: Syntax

.. parsed-literal::

   circuitpython-tool uf2 download [OPTIONS] BOARD [DESTINATION]


.. rubric:: Options
.. option:: --locale locale

   Locale for CircuitPython install.

.. option:: --offline offline

   If true, just print the download URL without actually downloading.

``uf2 enter``
========================================

Restart selected device into UF2 bootloader.

.. rubric:: Syntax

.. parsed-literal::

   circuitpython-tool uf2 enter DEVICE

``uf2 exit``
========================================

Restart given UF2 bootloader device into normal application code.

.. rubric:: Syntax

.. parsed-literal::

   circuitpython-tool uf2 exit

``uf2 install``
========================================

Install a UF2 image onto a connected UF2 bootloader device.

    If a CircuitPython device is specified with `--device`, then we restart that
    device into its UF2 bootloader and install the image onto it. If `--device`
    is not specified, we assume there is already a connected UF2 bootloader device.
    

.. rubric:: Syntax

.. parsed-literal::

   circuitpython-tool uf2 install [OPTIONS]


.. rubric:: Options
.. option:: --image_path image_path, -i image_path

   If specified, install this already-existing UF2 image.

.. option:: --board board, -b board

   If specified, automatically download and install appropriate CircuitPython UF2 image for this board ID.

.. option:: --device query, -d query

   If specified, this device will be restarted into its UF2 bootloader and be used as the target device for installing the image.

.. option:: --locale locale

   Locale for CircuitPython install. Not used if an explicit image is given using --image_path.

.. option:: --delete-download delete_download

   Delete any downloaded UF2 images on exit.

``uf2 mount``
========================================

Mount connected UF2 bootloader device if needed and print the mountpoint.

.. rubric:: Syntax

.. parsed-literal::

   circuitpython-tool uf2 mount

``uf2 nuke``
========================================

Clear out flash memory on UF2 bootloader device.

.. rubric:: Syntax

.. parsed-literal::

   circuitpython-tool uf2 nuke

``uf2 unmount``
========================================

Unmount connected UF2 bootloader device if needed.

.. rubric:: Syntax

.. parsed-literal::

   circuitpython-tool uf2 unmount

``uf2 versions``
========================================

List available CircuitPython boards.

.. rubric:: Syntax

.. parsed-literal::

   circuitpython-tool uf2 versions

``unmount``
========================================

Unmounts the specified device if needed.

.. rubric:: Syntax

.. parsed-literal::

   circuitpython-tool unmount DEVICE

``upload``
========================================

Continuously upload code to device in response to source file changes.

    The contents of the specified source directory will be copied onto the given
    CircuitPython device.

    If `--mode` is "single-shot", then the code is uploaded and then the command exits.

    If `--mode` is "watch", then this commnd will perform one upload, and then
    will continue running. The command will wait for filesystem events from all
    paths and descendant paths of the source tree, and will re-upload code to
    the device on each event.
    

.. rubric:: Syntax

.. parsed-literal::

   circuitpython-tool upload [OPTIONS] DEVICE


.. rubric:: Options
.. option:: --dir source_dir, -d source_dir

   Path containing source code to upload. If not specified, the source directory is guessed by searching the current directory and its descendants for user code (e.g. code.py).

.. option:: --circup circup

   If true, use `circup` to automatically install library dependencies on the target device.

.. option:: --mode mode

   Whether to upload code once, or continuously.

.. option:: --batch-period batch_period

   Batch filesystem events that happen within this period. This reduces spurious uploads when files update in quick succession. Unit: seconds

