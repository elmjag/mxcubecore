# HWR.beamline.sample_changer_maintenance

Implements maintenance commands for sample changer (SC).
Most notably populates SC commands buttons on the `equipment` tab in the UI.

_required methods_

| signature                     | returns                 |
|-------------------------------|-------------------------|
| \_\_init\_\_(self, name: str) |                         |
| get_cmd_info(self)            | list                    |
| send_command(self)            |                         |
| get_global_state(self)        | tuple(dict, dict, str) |

_expected signals_

| name               | payload                |
|--------------------|------------------------|
| globalStateChanged | tuple(dict, dict, str) |

## Methods

### \_\_init\_\_(self, name: str)

The object's will be created by invoking a constractor with above signature.

`name`: object's name in the configuration files

### get_cmd_info(self) -> lists

Should return commands provided by this object.
Each command shall have an id, button text and short help text.
The commands must be grouped into sections.
UI will render buttons for each command, grouped by specified sections.

The returned list must have the following structure:

    [
        [
            "<section_name>",
            [
                ["<command_id>", "<button_text>", "<command_help_text>"],
                ...
            ],
        ],
        ...
    ]

Below is an example implementation of `get_cmd_info()`:

    def get_cmd_info(self):
        return [
            [
                "Lid",
                [
                    ["openLid", "Open Lid", "Open Lid"],
                    ["closeLid", "Close Lid", "Close Lid"],
                ],
            ],
            [
                "Abort",
                [
                    ["abort", "Abort", "Abort running trajectory"]
                ]
            ],
        ]

In the above example, 3 commands are provided _Open Lid_, _Close Lid_ and _Abort_.
These commands are grouped into 2 sections _Lid_ and _Abort_.

### send_command(self, command_id: str, args=None)

Run the specified command on sample changer.
The `command_id` specifies the command to invoke, as denoted by return value of the `get_cmd_info()` method.

### get_global_state(self) -> tuple(dict, dict, str)

Must return a tuple representing the state of the sample changer.

First argument is the general state of the sample changer.

Second argument represents the state of provided command states.
For each command there must be an entry in the dictionary.
They key must be commands id, and value a boolean.
If the value is true, then the command can be run at the moment.
If the value is false, the command is not available.

Last argument represents a human-readable state message from the sample changer.
It will be displayed under equipment tab.

## Signals

### globalStateChanged

If state of commands or sample changer message changes, a `globalStateChanged` signal must be emitted.
The signal's payload must be a tuple, with the same structure as returned by `get_global_state(self)` method.
