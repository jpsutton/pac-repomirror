#!/usr/bin/env python

import os
import sys
import shutil
import pyalpm
from pprint import pprint
from pycman_config import PacmanConfig


class PacOptions:
  root = "./alpmroot"
  dbpath = "./alpmdb"
  cachedir = "./alpmcache"
  logfile = "./alpmroot/pac-repomirror.log"

PACMAN_CONF = os.path.join(PacOptions.root, "etc/pacman.conf")

for dir in (PacOptions.root, PacOptions.dbpath, PacOptions.cachedir):
  os.makedirs(dir, exist_ok=True)

if not os.path.exists(PACMAN_CONF):
  os.makedirs(os.path.dirname(PACMAN_CONF))
  shutil.copytree("root.sample/etc", f"{PacOptions.root}/etc", dirs_exist_ok=True)


alpmcfg = PacmanConfig(conf=PACMAN_CONF)
handle = alpmcfg.initialize_alpm()
pprint(handle.get_syncdbs())
extra = handle.get_syncdbs()[0]
extra.update(True)
t = handle.init_transaction(downloadonly=True, nodeps=True)
t.add_pkg(extra.get_pkg("linux-zen"))
t.prepare()
t.commit()
#pprint(extra.search("linux-zen"))
