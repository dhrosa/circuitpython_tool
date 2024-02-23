# circuitpython-tool

`circuitpython-tool` is a command-line utility for conveniently using
CircuitPython devices from the terminal. Especially useful
when multiple devices are connected to the same computer.

Benefits:
- No need to manually mount `CIRCUITPY` drives, or even keep track of where its mounted. You can refer to the device by name instead.
- No need to figure out the name of the serial terminal (e.g. /dev/ttyACM1). You can refer to the device by name instead.
- No need to find the correct CircuitPython version, reset your device while holding BOOTSEL, or drag-and-drop the `.uf2` file into `RPI-RP2`. You can enter the UF2 bootloader with one command, and automatically download and install CircuitPython with another command.

This tool is designed for a workflow where instead of editing files directly on
the CircuitPython device, you edit files on your computer and sync the code over
to the device.

## Usage

![`circuitpython-tool --help`](images/usage.svg)

## Terminology

- **Query**: `vendor:model:serial` string that specifies one or more connected CircuitPython devices. Each component string is searched for in the respective attribute. Empty strings are allowed in each component of the query. Example queries:
  - `::` matches ANY device.
  - `Adafruit::` matches any device whose vendor contains the string "Adafruit"
  - `:Feather:` matches any device whose model contains the string "Feather"
  - `Adafruit:Feather:` matches any device whose vendor contains the string "Adafruit" AND whose model contains the string "Feather"
  
- **Device**: A CircuitPython device connected over USB. The device shows up as
  a removeable drive labeled `CIRCUITPY`. When the term "device" is referred to
  in a command-line argument, the device is specified as a query strong as
  above. An error is thrown if the given query matches multiple connected
  devices.
  
- **UF2 Device**: A device connected over USB that is in its UF2 bootloader. For
  RP2040-based devices, the device shows up as a removable drive labeled
  `RPI-RP2`. This is the default state for brand-new RP2040 devices. This is
  also the state entered when a device is reset with the BOOTSEL butten held
  down. This state can also be entered via the `uf2 restart` command.

## Example Commands

### List devices
List connected CircuitPython devices and their properties:

![`circuitpython-tool devices`](images/devices.svg)


### Connect to serial terminal

Open serial terminal to connected Raspberry Pi Pico (without needing to find the correct /dev/ttyACM path!):

```sh
circuitpython-tool connect :Pico:
```

### Upload code

Upload code to connected Raspberry Pi Pico (without needing to manually mount the device!):

```sh
circuitpython-tool upload --dir ~/mycode :Pico:`
```

or automatically upload code everytime a source file changes:

```sh
circuitpython-tool watch --dir ~/mycode :Pico:`
```

### Mount device
Mount Raspberry Pi Pico (if needed) and print the path to the mountpoint:
```sh
circuitpython-tool mount :Pico:
```

### Install CircuitPython

Automatically download and install the correct version of CircuitPython onto a connected Raspberry Pi Pico.

If the device isn't already in the UF2 bootloader:

```sh
circuitpython-tool uf2 restart :Pico:
```

Then download and install CircuitPython:
```sh
circuitpython-tool install --board raspberry_pi_pico`
```

### Wipe out flash memory

Wipe out flash memory to bring the device to a factory default state:
```sh
circuitpython-tool uf2 nuke
```

## Shell completion

The tool supports shell completion of all parameters, including device queries and board names!

Setup completion for your shell:

```sh
eval "$(circuitpython-tool completion)"
```

Device queries:
<!-- RICH-CODEX hide_command: true -->
![`python3 -m circuitpython_tool.tools.shell_completer 'upload :Pico'`](images/completion_upload.svg)

Adafruit board names:
<!-- RICH-CODEX hide_command: true -->
![`python3 -m circuitpython_tool.tools.shell_completer 'uf2 install --board rasp'`](images/completion_uf2_install.svg)

CircuitPython locales:
<!-- RICH-CODEX hide_command: true -->
![`python3 -m circuitpython_tool.tools.shell_completer 'uf2 install --locale en'`](images/completion_uf2_locales.svg)
