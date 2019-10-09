# Config2Spec: Mining Network Specifications from Network Configurations

This repository contains the code of the Config2Spec project: A system
to automatically learn a network's specification from its configuration.

[Config2Spec](https://nsg.ee.ethz.ch/fileadmin/user_upload/publications/config2spec-final.pdf)
has been published at [USENIX NSDI'20](https://www.usenix.org/conference/nsdi20).

The system relies on [Batfish](https://www.batfish.org/) and [Minesweeper](https://www.batfish.org/minesweeper/).

## Installation Guide

1. __Clone this repository__

2. __Build Batfish and Minesweeper__
Follow the steps described [here](batfish_interface/README.md)

3. __Create a virtualenv with all requirements__
    ```bash
    $ virtualenv -p python3 c2s_env
    $ source c2s_env/bin/activate
    $ pip install -r requirements.txt
    ```

4. __Install Config2Spec__
    ```bash
    $ pip install -e .
    ```

## Run Config2Spec

A set of configurations of a network is called scenario. We provide a
few sample scenarios in this repository. With the exception of
Internet2, the configs have been synthesized using [NetComplete](https://netcomplete.ethz.ch/).

If you want to analyze your own configuration, just follow the same
structure: Create a new directory for the scenario and within that
create a directory called `configs` that contains all the configuration
files to be analyzed. Also, make sure that the configuration files have
a `.cfg` file ending.

The [`run_c2s.py`](run_c2s.py) script contains the full pipeline as
described in the [paper](https://nsg.ee.ethz.ch/fileadmin/user_upload/publications/config2spec-final.pdf).

You can run it the following way:

```bash
$ python run_c2s.py <scenario path> <backend path> <temp batfish path> -mf <max failures>
```

#### Arguments

* __scenario path__ - The path to the directory containing the
scenario (e.g., `/home/user/config2spec/scenarios/bics`).

* __backend path__ - The path to the `.jar` of the Batfish backend
(e.g., `/home/user/batfish/projects/backend/target/backend-bundle-0.36.0.jar`).

* __temp batfish path__ - The path to an directory where batfish can
store some temporary data.

* __max failures__ - An int specifying the maximum number of failures
the specification should include (e.g., for up to 1 failure set `-mf 1`).

### Example

```bash
$ python run_c2s.py scenarios/bics ~/batfish-73946b2f1bdea5f1146e4db4f2586e071da752df/projects/backend/target/backend-bundle-0.36.0.jar ~/tmp -mf 1
```




