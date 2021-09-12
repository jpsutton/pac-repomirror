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
By default, a standard set of ArchLinux repositories are configured (core, extra, community, multilib).

## How to Use
Note: The examples in this section assume you've installed the application in `/opt/pac-repomirror`, so be sure to adjust paths as needed if you installed it elsewhere.

Since the application creates a local Pacman repository, you'll want to add a block like the following to `/etc/pacman.conf`:
  ```
  [arch-upstream]
  SigLevel = Optional TrustAll
  Server = file:///opt/pac-repomirror/alpmcache
  ```
  
Individual packages can be added to the local repository like so:
  ```
  python repomirror.py add -p <package_name> -r <repo_name>
  ```
  
So, if you were running a Manjaro and wanted to install linux-zen (which is available in the ArchLinux but not Manjaro respositories), you'd do run the following:
  ```
  python repomirror.py add -p linux-zen -r extra
  sudo pacman -Sys linux-zen
  ```
Once you've added a package to the local repo, it will be tracked for future updates during `sync` operations. I suggest adding the following shell script into `/etc/cron.daily` in order to make sure your system will receive updates in a timely fashion:
  ```
  #!/bin/bash
  
  cd /opt/pac-repomirror
  source venv/bin/activate
  python repomirror.py sync
  ```
  
