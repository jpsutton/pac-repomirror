# pac-repomirror
This application makes it possible to create a local Pacman repository which simply mirrors individual packages from other Pacman repositories.

## Introduction
The primary use case is to make it easier to cherry-pick packages from one distribution's repositories for use in another. For example, one might wish to install individual packages from ArchLinux's official repositories on a system which has Manjaro installed (or vice versa).

## Installation
  Execute the following to get a working application environment:
  ```
  git clone https://github.com/jpsutton/pac-repomirror
  cd pac-repomirror
  git submodule init
  git submodule update --remote
  virtualenv venv
  source venv/bin/activate
  pip install -r packages.txt
  ```
For the moment, the application stores the application state in the application directory. These are the files/folders that store the app/repo state (and they are created as needed):
  ```
  alpmcache/
  alpmdb/
  alpmroot/
  tracked.json
  ```
