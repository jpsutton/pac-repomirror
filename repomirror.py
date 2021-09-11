#!/usr/bin/env python

import os
import sys
import shutil
import pyalpm
from pprint import pprint
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

  def __init__ (self):
    PacRepoMirror.__setup_filesystem__()
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

if __name__ == '__main__':
  PacRepoMirror()
