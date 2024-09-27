# Commands and Channels

The mxcubecore provides a hardware object level abstraction
for communicating using various flavors of control systems protocols.
A hardware object can utilize instances of `Command` and `Channel` objects.
These objects provide a uniform API for accessing specific control system.
Mxcubecore provides support for using protocols such as _tango_, _EPICS_, _exporter_ and more.

The `Command` and `Channel` objects can be created using `add_command()` and `add_channel()` methods of hardware objects.
Another option is to specify them in the hardware object's configuration file.
If `Command` and `Channel` are specified in the configuration file,
the specified objects will be automatically created during hardware object initialization.

## Configuration files format

The general format for specifying `Command` and `Channel` objects is as follows:

```yaml
class: MegaCommunicator
<protocol>:                      # protocol in use, tango / exporter / epics / etc
  <end-point>:                   # tango device / exporter address / EPICS prefix / etc
    commands:
      <command-1-name>:          # command's MXCuBE name
        <config-prop-1>: <val-1>
        <config-prop-2>: <val-2>
    channels:
      <channel-1-name>:          # channel's MXCuBE Name
        <config-prop-1>: <val-1>
        <config-prop-2>: <val-2>
```

The `Command` and `Channel` specification are grouped by the protocol they are using.
Each protocol have its own dedicated section in the configuration file.
The semantics for the protocol are simular but protocol specific, see below for details.

### Tango

The format for specifying _tango_ `Command` and `Channel` objects is as follows:

```yaml
class: TangoCommunicator
tango:
  <tango-device-name>:
    commands:
      <command-1-name>:
        <config-prop-1>: <val-1>
        <config-prop-2>: <val-2>
      <command-2-name>:
        <config-prop-1>: <val-1>
    channels:
      <channel-1-name>:
        <config-prop-1>: <val-1>
        <config-prop-2>: <val-2>
      <channel-2-name>:
        <config-prop-1>: <val-1>
```

`<tango-device-name>` specifies the tango device to use.
Multiple `<tango-device-name>` sections can be specified, in order to use different tango devices.
Each `<tango-device-name>` contains optional `commands` and `channels` sections.
These sections specify `Command` and `Channel` object to create using the `<tango-device-name>` tango device.

#### Commands

`commands` is a dictionary where each key specifies a `Command` object.
The key defines the MXCuBE name for the command.
The values specify an optional dictionary with configuration properties for the `Command` object.
Following configuration properties are supported:

| property | purpose            | default             |
|----------|--------------------|---------------------|
| name     | tango command name | MXCuBE command name |

#### Channels

`channels` is a dictionary where each key specifies a `Channel` object.
The key defines the MXCuBE name for the channel.
The values specify an optional dictionary with configuration properties for the `Channel` object.
Following configuration properties are supported:

| property  | purpose                           | default             |
|-----------|-----------------------------------|---------------------|
| attribute | tango attribute name              | MXCuBE channel name |
| poll      | polling periodicity, milliseconds | polling is disabled |

By default, a tango `Channel` object will use tango attribute change event, in order to receive new attribute values.
For this to work, the tango device must send the change events for the attribute.
For cases where such events are not sent, the attribute polling can be enabled.
If `polling` property is specified, MXCuBE will poll the tango attribute with specified periodicity.

#### Example

Below is an example of hardware object that specifies tango commands and channels.

```yaml
class: MyTango
tango:
  some/tango/device:
    commands:
      Open:
      Close:
      Reset:
        name: Reboot
    channels:
      State:
      Volume:
          attribute: currentVolume
          poll: 1024
```

In the above example commands `Open`, `Close` and `Reset` as well as `State` and `Volume` channels are configured.
All command and channel objects a bound to commands and attributes of the `some/tango/device` tango device.

`Open` and `Close` commands are bound to _Open_ and _Close_ tango commands.
The `Reset` have a configuration property that binds it to _Reboot_ tango command.

The `State` channel will be mapped to _State_ attribute of the tango device.
It's value will be updated via tango change events.

The `Volume` channel will be mapped to _currentVolume_ attribute of the tango device.
The _currentVolume_ attribute's value will be polled each 1024 millisecond.
