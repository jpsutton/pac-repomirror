# pac-repomirror
This application makes it possible to create a local Pacman repository which simply mirrors individual packages from other Pacman repositories.

## Introduction
The primary use case is to make it easier to cherry-pick packages from one distribution's repositories for use in another. For example, one might wish to install individual packages from ArchLinux's official repositories on a system which has Manjaro installed (or vice versa).

## Installation
 git clone https://github.com/jpsutton/pac-repomirror
 git submodule init
 git submodule update --remote
 
