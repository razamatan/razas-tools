#!/usr/bin/env python -t
''' backu.py or backupy

local back ups, with configuration sprinkled via backupy dotfiles on the
filesystem.

the main idea is to leverage tar as much as possible by utilizing the nearest
context to decide what to do.  mainly, this is achieved via the use of
.__backupy_[content]__ files that you sprinke around.

the only thing you really need to get started is a .__backupy_root__ (json
format) file with any config overrides.  then, just point this script at that
directory and have at it!

i use gnu versions of the various commands where appropriate.

requirements:
   python (2.6 tested)
   argparse

cvs isn't supported b/c i'm too lazy and you shouldn't use cvs anymore.
'''

import os, sys, json, re
import logging as log
from argparse import ArgumentParser
from glob import glob, iglob
from pprint import pformat

from future_builtins import map

bpy_filename = '.__backupy_%s__'
bpy_re = re.compile(r'.__backupy_(?P<content>[^_]+)__')
vcs_content = 'bzr git hg svn'.split()
valid_content = 'root exclude src svnrepo flat auto'.split() + vcs_content

compressed_ftypes = '7z 7zip rar tbz tbz2 tbzip2 tar.bz tar.bz2 tar.bzip2 tgz tar.gz txz tar.xz tz zip z'.split()

def bpy(path='', content=''):
   ''' helper to get backupy filenames '''
   if content:
      bpy = bpy_filename % content
      return os.path.join(path, bpy) if path else bpy
   elif path:
      # there can be only one
      found = glob(os.path.join(path, bpy_filename % '*'))
      assert len(found) < 2, 'mutliple backupy files found:\n\t%s' % found
      if found: return found[0]
   else:
      raise SyntaxError('bpy called without a path or content')

default_cfg = {
      # excludes are relative to the stack
      'exclude': '*.a *.o *.lo *.py[co] *.class *.sw[nop] *~ .#* [#]*#'.split(),
      # number of backups to keep around
      'numbak': 4,
      # file format of the backup
      'ftype': 'tgz',
      # name of backup files
      'bakname': '%(path)s-%(timestamp)s.%(ftype)',
      # default tar args
      'tarargs': '--preserve --same-owner --auto-compress --exclude-tag=%s' % bpy(content='exclude')
}

def load_bpy(path, cfgs):
   ''' loads the backupy configuration '''
   b = bpy(path)
   if not b: return

   content = bpy_re.search(b).group('content')
   if content not in valid_content:
      log.warn('skipping unrecognized bpy:\n\t%s' % b)
      return

   cfg = {} if cfgs else default_cfg
   try:
      if os.path.getsize(b):
         with file(b) as f:
            cfg.update(json.load(f))
   except:
      log.fatal('unable to successfully read:\n\t%s', b)
      raise
   cfg['__path__'] = path
   cfg['__content__'] = content
   cfgs.append(cfg)
   log.debug('processed bpy:\n\t%s' % b)
   return (content, cfg)


# repositories inside other repositories, but nesting in general

def backup_bzr(path, dirs, files):
   # only if it's a lightweight checkout, statused, unknown and ignored files
   # look at bzrignore files to backup
   # honor excludes

   # no working tree: bare repository
   # test for being a shared repository
   # it's not a "repo" if bzr info indicates it has checkout or pull/pushes
   print 'bzr', path
   dirs[:] = []

def backup_git(path, dirs, files):
   # git remote
   # git branch
   # git config -l
   # statused and unknown files, honor excludes

   # no working tree: bare repository
   print 'git', path
   dirs[:] = []

def backup_hg(path, dirs, files):
   # statused and unknown files, honor excludes
   print 'hg', path
   dirs[:] = []

def backup_svn(path, dirs, files):
   # statused, ignored and unknown files, honor excludes
   print 'svn', path
   dirs[:] = []

def backup_svnrepo(path, dirs, files):
   # svnadmin dump to a dumpfile
   # exclude everything but that dumpfile
   # delete dumpfile
   print 'svnrepo', path
   dirs[:] = []

def backup_src(path, dirs, files):
   # don't archive the tarballs of the same prefix!, honor excludes
   print 'src', path

def backup_flat(path, dirs, files):
   # everything but excludes
   pass
   print 'flat', path

def find_svnrepo(path, dirs, files):
   # find a db directory and a readme.txt saying that it is so
   lfiles = set(map(str.lower, files))
   if 'readme.txt' not in lfiles or 'db' not in set(map(str.lower, dirs)):
      return

   with open(os.path.join(path, 'readme.txt')) as readme:
      read = readme.read().lower()
      if 'is a subversion repository' in read: return 'svnrepo'

def find_vcs(path, dirs, files):
   # find vcs subdirectories
   vcs = set('.%s' % x for x in vcs_content) & set(map(str.lower, dirs))
   if len(vcs) == 1:
      return vcs.pop().lstrip('.')
   elif len(vcs) > 1:
      log.error('confusing to have many vcs in the same directory, please use an explicit backpuy dotfile to indicate the one to utilize for backup.  treating this directory as "flat" (archiving all files): %s' % path)


ap = ArgumentParser()
ap.add_argument('root', help='directory to backup')
ap.add_argument('backpath', help='backup directory')
ap.add_argument('-l', '--loglevel', help='logging output log level', choices='error warning info debug'.split(), default='info')
ap.add_argument('-f', '--forceroot', help='not implemented', action='store_true')
args = ap.parse_args()

# verify that the root is a backupy root
rootpath = os.path.realpath(args.root)
if not (os.path.isdir(rootpath) and os.path.exists(bpy(rootpath, 'root'))):
   ap.error('%s is not backupy enabled (%s is missing)' % (rootpath, bpy(rootpath, 'root')))

log.basicConfig(level=getattr(log, args.loglevel.upper()),
                format='%(asctime)s %(levelname)-8s %(message)s',)

# state
cfgs = list()     # .__backupy__ files
excludes = list() # tar exclude list

# walk!
for path, dirs, files in os.walk(rootpath):
   content, cfg = load_bpy(path, cfgs) or ('auto', None)

   if content == 'exclude':
      dirs[:] = []
      continue

   if content == 'auto' or content == 'root':
      # try to be automagic, chained to reflect priority
      content = find_vcs(path, dirs, files) or \
                find_svnrepo(path, dirs, files) or \
                'flat'

   fname = 'backup_%s' % content
   if fname in globals():
      globals()[fname](path, dirs, files)
   else:
      log.error('content "%s" is not implemented yet, sorry' % content)


log.debug('ran using the following bpys:\n%s' % pformat(cfgs))

# verify that the backpath is not part of the path (can be excluded)
backpath = os.path.realpath(args.backpath)
