#!/usr/bin/env python

import os
import sys
import shutil
import platform
import subprocess
import glob
from pprint import pprint

import pyalpm

from pycman_config import PacmanConfig
from mlargparser.mlargparser import MLArgParser

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
  
  argDesc = {
    "package_name": "Name of a package to mirror to the local repository",
    "repo_name": "Name of the repostiory from which to retreive the package",
    "ignore_deps": "Do not mirror dependency packages",
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

  def __update_localrepo_metadata__ (self):
    p = subprocess.run([self.pac_tools['repo-add'], os.path.join(PacOptions.cachedir, "repo.db.tar.gz")] + glob.glob(os.path.join(PacOptions.cachedir, "*.pkg.*")))
    p.check_returncode()

  def __init__ (self):
    PacRepoMirror.__setup_filesystem__()
    self.__check_tooling__()
    self.alpmcfg = PacmanConfig(conf=PacRepoMirror.conf_file)
    self.handle = self.alpmcfg.initialize_alpm()
    self.repos = dict()

    for db in self.handle.get_syncdbs():
      self.repos[db.name] = db

    super().__init__()

  def mirror_package (self, repo_name:str, package_name:str, ignore_deps=True):
    """ Mirror a package from the specified repository to the local repository """

    if repo_name not in self.repos:
      sys.stderr.write(f"ERROR: {repo_name} is not a configured repository\n")
      sys.exit(1)

    # Update the repo package metadata
    repo = self.repos[repo_name]
    repo.update(True)

    # Prepare and execute the transaction to mirror the package
    transaction = self.handle.init_transaction(downloadonly=True, nodeps=ignore_deps)
    transaction.add_pkg(repo.get_pkg(package_name))
    transaction.prepare()
    transaction.commit()

    # Update the local repo metadata
    self.__update_localrepo_metadata__()

if __name__ == '__main__':
  PacRepoMirror()
