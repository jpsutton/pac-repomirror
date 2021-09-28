#!/usr/bin/env python

# Python standard libs
import os
import sys
import glob
import json
import shutil
import platform
import subprocess
from pprint import pprint

# Third-party libs
import pyalpm

# Local libraries
from pycman_config import PacmanConfig # This one is taken from pyalpm's sample app called "pycman", but it's not provided by merely installing pyalpm
from mlargparser.mlargparser import MLArgParser

# Options for libalpm
class PacOptions:
  local_name = "arch-upstream"
  root = "./alpmroot"
  dbpath = "./alpmdb"
  cachedir = "./alpmcache"
  logfile = "./alpmroot/pac-repomirror.log"


class PacRepoMirror (MLArgParser):
  """ A selective repository mirroring tool for Pacman """

  # Configuration file read by pyalpm
  conf_file = os.path.join(PacOptions.root, "etc/pacman.conf")

  # External CLI tool dependencies
  pac_tools = {
    "repo-add": None
  }

  # A place to store tracked packages at runtime
  tracked = None

  # Descriptions for CLI arguments (for help output)
  argDesc = {
    "package_name": "Name of a package to mirror to the local repository",
    "repo_name": "Name of the repostiory from which to retreive the package",
    "no_sync": "Do not permform a repo sync after adding a new tracked package",
  }

  # Setup local directories and config files for our internal alpm environment
  @staticmethod
  def __setup_filesystem__():
    for dir in (PacOptions.root, PacOptions.dbpath, PacOptions.cachedir):
      os.makedirs(dir, exist_ok=True)

    if not os.path.exists(PacRepoMirror.conf_file):
      os.makedirs(os.path.dirname(PacRepoMirror.conf_file))
      shutil.copytree("root.sample/etc", f"{PacOptions.root}/etc", dirs_exist_ok=True)

  # Locate our external CLI tools
  def __check_tooling__(self):
    delim = ';' if platform.system() == "Windows" else ':'
    path_dirs = os.environ['PATH'].split(delim)

    for directory in path_dirs:
      if not os.path.exists(directory):
        continue

      for name in os.listdir(directory):
        if name not in self.pac_tools or self.pac_tools[name] is not None:
          continue

        self.pac_tools[name] = os.path.join(directory, name)

    for tool, full_path in self.pac_tools.items():
      if full_path is None:
        sys.stderr.write(f"ERROR: could not locate {tool} in the current path.\n")

  # Use the repo-add CLI tool to generate local repo metadata for any packages added during a sync
  def __update_localrepo_metadata__ (self, transaction):
    file_list = [ os.path.join(PacOptions.cachedir, package.filename) for package in transaction.to_add ]
    p = subprocess.run([self.pac_tools['repo-add'], "-R", os.path.join(PacOptions.cachedir, f"{PacOptions.local_name}.db.tar.gz")] + file_list)
    p.check_returncode()

  # Class initializer
  def __init__ (self):
    PacRepoMirror.__setup_filesystem__()
    self.__check_tooling__()
    self.alpmcfg = PacmanConfig(conf=PacRepoMirror.conf_file)
    self.handle = self.alpmcfg.initialize_alpm()
    self.repos = dict()

    for db in self.handle.get_syncdbs():
      self.repos[db.name] = db

    if self.tracked is None:
      self.__read_tracked__()

    super().__init__()

  # Save our tracked package list to disk
  def __save_tracked__ (self):
    if self.tracked is not None:
      with open("./tracked.json", "w") as outfile:
        outfile.write(json.dumps(self.tracked))

  # Read our tracked package list from disk (or start with an empty list)
  def __read_tracked__ (self):
    if os.path.exists("./tracked.json"):
      with open("./tracked.json", "r") as infile:
        self.tracked = json.loads(infile.read())
    else:
      self.tracked = list()

  # Perform a repository sync of all tracked packages
  def sync (self):
    """ Mirror any updates for tracked packages to local repository """

    # Update all remote repository metadata
    for name, repo in self.repos.items():
      repo.update(True)

    # Prepare a pyalpm transaction; download-only mode
    transaction = self.handle.init_transaction(downloadonly=True, nodeps=True)
    added_count = 0

    try:
      for record in self.tracked:
        # Locate the requested package in the remote repo data
        pkg = self.repos[record['repo']].get_pkg(record['name'])

        # Handle each possible case of (1) package doesn't exist (2) already Downloaded (3) needs to be sync'd to local repo
        if pkg is None:
          sys.stderr.write(f"WARNING: {record['name']} is no longer present in repo {record['repo']}\n")
        elif os.path.exists(os.path.join(PacOptions.cachedir, pkg.filename)):
          sys.stderr.write(f"DEBUG: {record['name']} is already downloaded. Skipping.\n")
        else:
          transaction.add_pkg(pkg)
          added_count += 1

      # If no packages were added to the transaction, then we don't need to move forward with the sync
      if not added_count:
        sys.stderr.write(f"DEBUG: no packages were added to sync transaction.\n")
        return

      # Perform the sync
      transaction.prepare()
      transaction.commit()

      # Update the local repo metadata
      self.__update_localrepo_metadata__(transaction)
    finally:
      # Gracefully finish the transaction
      transaction.release()

  # Add a package to the tracked list (and by default, perform a repo sync)
  def add (self, repo_name:str, package_name:str, no_sync:bool = False):
    """ Mirror a package from the specified repository to the local repository """

    # Check that the specified repo is configured
    if repo_name not in self.repos:
      sys.stderr.write(f"ERROR: {repo_name} is not a configured repository\n")
      sys.exit(1)

    # Update the repo package metadata
    repo = self.repos[repo_name]
    repo.update(True)

    # Lookup the package meta
    pkg = repo.get_pkg(package_name)

    # Make sure the package exists in the repo
    if pkg is None:
      sys.stderr.write(f"ERROR: {package_name} was not found in repo {repo_name}\n")
      sys.exit(2)

    # Add package to tracked list if it's not already present; save the tracked list to disk
    if not len(list(filter(lambda x: x['name'] == package_name, self.tracked))):
      self.tracked.append({
        "name": package_name,
        "repo": repo_name,
      })
    self.__save_tracked__()

    # Perform a package sync, unless the user said no
    if not no_sync:
      self.sync()

  # Remove a package from being tracked and from the local repo
  def remove (self, package_name:str):
    """ Remove a package from being tracked and from the local repository """

    # Get the tracked entry for the specified package
    tracked_entry = list(filter(lambda x: x['name'] == package_name, self.tracked))

    # Error out if there aren't any matching tracked packages
    if not(len(tracked_entry)):
      sys.stderr.write(f"ERROR: {package_name} is not a tracked package\n")
      sys.exit(3)

    # Extract the first entry
    tracked_entry = tracked_entry[0]

    # Get the package record from pyalpm
    pkg = self.repos[tracked_entry['repo']].get_pkg(package_name)

    # Delete the local package file
    try:
      os.unlink(os.path.join(PacOptions.cachedir, pkg.filename))
    except FileNotFoundError:
      pass

    # Delete existing repo metadata files (if you know a better way to remove a package from the metadata, please fix and submit a PR)
    for file in glob.glob(os.path.join(PacOptions.cachedir, PacOptions.local_name + "*")):
      os.unlink(file)

    # Remove the tracked entry for the specified package
    self.tracked.remove(tracked_entry)
    self.__save_tracked__()

    # Update the local repo metadata
    transaction = self.handle.init_transaction(downloadonly=True, nodeps=True)

    try:
      self.__update_localrepo_metadata__(transaction)
    finally:
      # Gracefully finish the transaction
      transaction.release()

if __name__ == '__main__':
  PacRepoMirror()
