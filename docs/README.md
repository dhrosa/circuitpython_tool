# circuitpython-tool

`circuitpython-tool` is a command-line utility for conveniently addressing and
uploading code to CircuitPython devices in a consistent way. Especially when
multiple devices are connected to the same computer.

This tool is designed for a workflow where instead of editing files directly on
the CircuitPython device, you edit files on your computer and sync the code over
to the device.

## Usage

![`circuitpython-tool --help`](images/usage.svg)

### Terminology

- **Query**: `vendor:model:serial` string. Each component string is searched for in the respective attribute. Empty strings are allowed, e.g. `Adafruit::` matches all devices with the vendor *Adafruit*.
- **Device Label**: User-chosen aliases for queries.
- **Source Tree**: List of directories to copy to the device.

### List devices

![`circuitpython-tool devices`](images/devices.svg)

### Label commands

- `label list`
- `label add`
- `label remove`

### Source Tree commands

- `tree list`
- `tree add`
- `tree remove`

### Serial connection

`connect`

### Single-shot code upload

`upload`

### Automatic continuous code upload

`watch`
