# OpenSAFELY Reference Gateway

This repository contains code for (part of) a reference implementation for an OpenSAFELY Gateway component.
It currently implements job management, but does not handle released outputs.

That is, it performs part of the role of [Job Server](https://github.com/opensafely-core/job-server/).
However, it is much simpler:

* We deal with a single backend.
* Each project can only have a single workspace or repo.
* All users are authorized to do anything.
* Users can only run the whole pipeline and not individual actions.

## Screenshots

The index page lists all projects:

![All projects](docs/projects.png)

The page for a project lists all the runs of that project's code:

![All runs for a project](docs/project.png)

The page for a run shows all the run's actions:

![All actions for a run](docs/run.png)

## Developer docs

Please see the [additional information](DEVELOPERS.md).
