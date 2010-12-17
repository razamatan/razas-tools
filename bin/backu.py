#!/usr/bin/env python -t
''' backu.py or backupy

local back ups, with configuration sprinkled via .__backupy__ files on the
filesystem.

the main idea is to utilize the nearest context to decide what to do.  you can
always be explicit with what to do by creating a .__backupy__ configuration
file (json format) at the direction you want to control.

i use gnu versions of the various commands where appropriate.

requirements:
   python (2.6 tested)
   argparse

cvs isn't supported b/c i'm too lazy and don't use cvs anymore
'''

import argparse
import os, sys, json
from copy import deepcopy

import logging as log
from pprint import pprint


valid_content = set('backupy exclude src hg git bzr svn svn/repo'.split())

default_cfg = {
      # specify the type of content found in this directory
      'content': None,
      # excludes are relative to the stack and may include wildcards
      'exclude': '*.a *.o *.py[co] *.sw[nop] *~ .#* [#]*#'.split(),
      # number of backups to keep around
      'numbak': 4,
      # file format of the backup
      'ftype': 'tgz',
      # name of backup files
      'bakname': '%(path)s-%(timestamp)s.%(ftype)',
      # followlinks during walk?
      'followlinks': False,
}

def bpy(path): return '%s/.__backupy__' % path

def load_bpy(state, path):
   if not os.path.exists(bpy(path)): return
   log.debug('found bpy: %s' % bpy(path))
   cfg = {} if state else default_cfg
   try:
      with file(bpy(path)) as f:
         cfg.update(json.load(f))
   except:
      log.fatal('unable to successfully read in %s', bpy(path))
      raise
   cfg['__path__'] = path
   state.append(cfg)

ap = argparse.ArgumentParser()
ap.add_argument('path', help='directory path to backup')
ap.add_argument('backpath', help='backup directory')
ap.add_argument('-l', '--loglevel', help='logging output log level', choices='error warning info debug'.split(), default='warn')
args = ap.parse_args()

# verify that the path is backupy configured
path = os.path.realpath(args.path)
if not (os.path.isdir(path) and os.path.exists(bpy(path))):
   ap.error('%s is not backupy enabled (%s is missing)' % (path, bpy(path)))

log.basicConfig(level=getattr(log, args.loglevel.upper()), format='%(asctime)s %(levelname)-8s %(message)s')

# store our config in a state stack
state = list()

# survey configuration
for root, dirs, files in os.walk(path, onerror=''):
   load_bpy(state, root)

pprint( state )

# verify that the backpath is not part of the path (can be excluded)
backpath = os.path.realpath(args.backpath)
