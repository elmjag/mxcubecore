# Hardware Objects API

This documentation describes what roles different type of hardware object play in MxCube.
It describes the API each type of hardware object must implement.
The required methods, signals and data types are documented.

## Hardware Objects

* [HWR.beamline.sample_changer](sample_changer.md) - sample changer robot
* [HWR.beamline.sample_changer_maintenance](sample_changer_maintenance.md) - sample changer maintenance features
* [HWR.beamline.sample_view.camera](sample_view_camera.md) - video feed of the mounted sample

## Abstract Classes

Part of the API is defined using abstract classes.
In an essence an abstract class defines an interface expected by MxCube.
When implementing hardware object it's possible to extend an abstract class,
leveraging its partial implementation of the interface.

Abstract classes are defined inside `mxcubecore.HardwareObjects.abstract` package.

* [sample_changer.Sample](sample_changer_sample.md) - mountable sample
* [sample_changer.Container](sample_changer_container.md) - sample containers hierarchy
