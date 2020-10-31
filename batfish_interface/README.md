# Config2Text - Automatic Network Policy Inference

## 1. Setting up Batfish/Minesweeper

__Important__: The additions work with Batfish at [commit 73946b2f1bdea5f1146e4db4f2586e071da752df](https://github.com/batfish/batfish/tree/73946b2f1bdea5f1146e4db4f2586e071da752df)

A snapshot of the Batfish code at that commit is also available in
[batfish_repo.zip](batfish_repo.zip).

After you obtained the Batfish code, you need to add the Config2Spec
specific modifications.

To that end, use the `setup.sh` script. It copies all the necessary
files into the batfish repository such that you can just build the
entire project with [Maven](https://maven.apache.org/).

Use the script as follows:

```bash
$ bash setup.sh <GitHub path> <repo name> <Config2Spec path>
```

#### Arguments

* __GitHub path__ - Specify the full path to the directory in which you
want to clone the repository.

* __repo name__ - Specify the name of the directory in which you have cloned batfish (e.g., c2s_batfish).

* __Config2Spec path__ - Specify the full path of the Config2Spec repository.

#### Example

```bash
$ bash setup.sh new /home/user/GitHub c2s_batfish /home/user/GitHub/config2spec
```

## 2. Installing Prerequisites

Install all the prerequisites described in the
[Batfish installation guide](https://github.com/batfish/batfish/wiki/Building-and-running-Batfish-service)
(Java, Maven, etc.).

Then, install Z3. All the other steps in the guide can be skipped.
Depending on your operating system, you might have to build Z3 from its
[source](https://github.com/Z3Prover/z3).
In that case, make sure to use the `--java` command line flag with the
`mk_make.py` script to enable building the Java bindings.

## Build Batfish/Minesweeper

Once, you have installed all the prerequisites, you can
enter the projects directory within the Batfish repository and run:

```bash
$ cd projects/
$ mvn package
```

You should then find all the `.jar`-files in the `target` directory of
all the module directories. The `backend-bundle-0.36.0.jar` is the file
that contains all the dependencies and can be run using:

```bash
$ cd backend/target/
$ java -cp backend-bundle-0.36.0.jar org.batfish.backend.Backend
```
