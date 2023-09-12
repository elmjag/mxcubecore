# HWR.beamline.sample_changer

Provides an interface to control the sample changing robot.
This is typically a robot arm that can fetch samples from the dewar and mount them on the diffractometer.
Commonly the robot arm and sample storage dewar is tightly integrated into one common system.
The API for `sample_changer` hardware object treats the arm and the dewar as one unit.

An implementation of `sample_changer` hardware object must support:
 *  listing of available samples in the dewar
 * provide methods to transfer samples to and from diffractometer

_required interfaces_

| interface                                 | purpose                      |
|-------------------------------------------|------------------------------|
| [Container](sample_changer_container.md)  | available samples management |

_required methods_

| signature               | returns |
|-------------------------|---------|
| get_loaded_sample(self) |         |
| get_status(self)        | str     |

_expected signals_

| name         | payload                        |
|--------------|--------------------------------|
| stateChanged | tuple(state: int, unused: Any) |


## Samples Management

A `sample_changer` object must provide an API that will be used to query presence of the samples in the dewar.
The `sample_changer` object is expected to implement the API defined by
[mxcubecore.HardwareObjects.abstract.sample_changer.Container.Container](sample_changer_container.md) class.

The samples are expected to be stored in a hierarchy of containers.
For example each sample will be stored in a samples container, like a uni-puck.
A number of uni-pucks will be stored in sample changer's dewar.
Note that in principle the hierarchy of container can be arranged differently.
A sample changer may have multiple dewars, or the dewar maybe divided into sections.

The `sample_changer` object must be the top-level container.
The hierarchy of containers must end with a container of sample objects.
Sample objects must implement API defined by
[mxcubecore.HardwareObjects.abstract.sample_changer.Sample.Sample](sample_changer_sample.md) class.

## Methods

### get_status(self) -> str

Shall return a string representing sample changer current status.
Expected strings are as follows:

 * "Disabled" - sample changer is disabled, it can't be used to transfer samples
 * "Ready" - sample changer is ready to transfer samples

