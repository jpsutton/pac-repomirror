#!/usr/bin/env python

import os
import sys
import shutil
import platform
import subprocess
import glob
import json
from pprint import pprint

import pyalpm

from pycman_config import PacmanConfig
from mlargparser.mlargparser import MLArgParser

import code

class PacOptions:
  root = "./alpmroot"
  dbpath = "./alpmdb"
  cachedir = "./alpmcache"
  logfile = "./alpmroot/pac-repomirror.log"


class PacRepoMirror (MLArgParser):
  """ A selective repository mirroring tool for Pacman """

  conf_file = os.path.join(PacOptions.root, "etc/pacman.conf")

  pac_tools = {
    "repo-add": None
  }

  tracked = None
  
  argDesc = {
    "package_name": "Name of a package to mirror to the local repository",
    "repo_name": "Name of the repostiory from which to retreive the package",
  }

  @staticmethod
  def __setup_filesystem__():
    for dir in (PacOptions.root, PacOptions.dbpath, PacOptions.cachedir):
      os.makedirs(dir, exist_ok=True)

    if not os.path.exists(PacRepoMirror.conf_file):
      os.makedirs(os.path.dirname(PacRepoMirror.conf_file))
      shutil.copytree("root.sample/etc", f"{PacOptions.root}/etc", dirs_exist_ok=True)

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

  def __update_localrepo_metadata__ (self, transaction):
    file_list = [ os.path.join(PacOptions.cachedir, package.filename) for package in transaction.to_add ]
    p = subprocess.run([self.pac_tools['repo-add'], "-R", os.path.join(PacOptions.cachedir, "repo.db.tar.gz")] + file_list)
    p.check_returncode()

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

  def __del__ (self):
    del self.handle

  def __save_tracked__ (self):
    if self.tracked and len(self.tracked):
      with open("./tracked.json", "w") as outfile:
        outfile.write(json.dumps(self.tracked))

  def __read_tracked__ (self):
    if os.path.exists("./tracked.json"):
      with open("./tracked.json", "r") as infile:
        self.tracked = json.loads(infile.read())
    else:
      self.tracked = list()

  def sync (self):
    for name, repo in self.repos.items():
      repo.update(True)

    # Prepare and execute the transaction to mirror the packages
    transaction = self.handle.init_transaction(downloadonly=True, nodeps=True)
    added_count = 0

    try:
      for record in self.tracked:
        pkg = self.repos[record['repo']].get_pkg(record['name'])

        if pkg is None:
          sys.stderr.write(f"WARNING: {record['name']} is no longer present in repo {record['repo']}\n")
        elif os.path.exists(os.path.join(PacOptions.cachedir, pkg.filename)):
          sys.stderr.write(f"DEBUG: {record['name']} is already downloaded. Skipping.\n")
        else:
          transaction.add_pkg(pkg)
          added_count += 1

      if not added_count:
        sys.stderr.write(f"DEBUG: no packages were added to sync transaction.\n")
        return

      transaction.prepare()
      transaction.commit()

      # Update the local repo metadata
      self.__update_localrepo_metadata__(transaction)
    finally:
      transaction.release()


  def add (self, repo_name:str, package_name:str, no_sync:bool = False):
    """ Mirror a package from the specified repository to the local repository """

    if repo_name not in self.repos:
      sys.stderr.write(f"ERROR: {repo_name} is not a configured repository\n")
      sys.exit(1)

    # Update the repo package metadata
    repo = self.repos[repo_name]
    repo.update(True)

    pkg = repo.get_pkg(package_name)

    # Make sure the package exists in the repo
    if pkg is None:
      sys.stderr.write(f"ERROR: {package_name} was not found in repo {repo_name}\n")
      sys.exit(2)

    if not len(list(filter(lambda x: x['name'] == package_name, self.tracked))):
      self.tracked.append({
        "name": package_name,
        "repo": repo_name,
      })

    self.__save_tracked__()

    if not no_sync:
      self.sync()

if __name__ == '__main__':
  PacRepoMirror()
