#!/usr/bin/env python3

import sys
import logging
import os
import json
from filecmp import dircmp
import shutil
import argparse
from abc import ABCMeta, abstractmethod

class AssetComparer(metaclass=ABCMeta):
    def __init__(self, preview):
        self.preview = preview

    @abstractmethod
    def validate(self, origin, local):
        pass

    @abstractmethod
    def left_only(self, dcmp, asset):
        pass

    @abstractmethod
    def right_only(self, dcmp, asset):
        pass

    @abstractmethod
    def diff(self, dcmp, asset):
        pass

    def copy_asset(self, src, dest):
        print('Copying asset:\n  From: {0}\n  To: {1}'.format(src, dest))

        if self.preview:
            return

        if os.path.isdir(src):
            shutil.copytree(src, dest)
        else:
            shutil.copy2(src, dest)

        src_metafile = src = '.meta'
        if os.path.isfile(src_metafile):
            shutil.copy2(src_metafile, dest + '.meta')

    def remove_asset(self, path):
        print('Removing asset:\n  {0}'.format(path))

        if self.preview:
            return

        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

class DiffComparer(AssetComparer):
    def __init__(self):
        super().__init__(False)

    def validate(self, origin, local):
        if not os.path.isdir(local):
            print('L: {0}'.format(origin))
            return False

        if not os.path.isdir(origin):
            print('R: {0}'.format(local))
            return False

        return True

    def left_only(self, dcmp, asset):
        print('L: {0}'.format(os.path.join(dcmp.left, asset)))

    def right_only(self, dcmp, asset):
        print('R: {0}'.format(os.path.join(dcmp.right, asset)))

    def diff(self, dcmp, asset):
        print('D: {0}'.format(os.path.join(dcmp.right, asset)))

class PullComparer(AssetComparer):
    def __init__(self, clean, preview):
        super().__init__(preview)
        self.clean = clean

    def validate(self, origin, local):
        if not os.path.isdir(local):
            self.copy_asset(origin, local)
            return False

        if not os.path.isdir(origin):
            return False

        return True

    def left_only(self, dcmp, asset):
        self.copy_asset(os.path.join(dcmp.left, asset), os.path.join(dcmp.right, asset))

    def right_only(self, dcmp, asset):
        if self.clean:
            self.remove_asset(os.path.join(dcmp.right, asset))

    def diff(self, dcmp, asset):
        self.copy_asset(os.path.join(dcmp.left, asset), os.path.join(dcmp.right, asset))

class PushComparer(AssetComparer):
    def __init__(self, clean, preview):
        super().__init__(preview)
        self.clean = clean

    def validate(self, origin, local):
        if not os.path.isdir(local):
            return False

        if not os.path.isdir(origin):
            self.copy_asset(local, origin)
            return False

        return True

    def left_only(self, dcmp, asset):
        if self.clean:
            self.remove_asset(os.path.join(dcmp.left, asset))

    def right_only(self, dcmp, asset):
        self.copy_asset(os.path.join(dcmp.right, asset), os.path.join(dcmp.left, asset))

    def diff(self, dcmp, asset):
        self.copy_asset(os.path.join(dcmp.right, asset), os.path.join(dcmp.left, asset))

def visit_dcmp(dcmp, comparer):
    logging.debug('visiting comparison of {0} and {1}'.format(dcmp.left, dcmp.right))
    
    for name in dcmp.left_only:
        comparer.left_only(dcmp, name)

    for name in dcmp.right_only:
        comparer.right_only(dcmp, name)

    for name in dcmp.diff_files:
        comparer.diff(dcmp, name)

    for name, subdcmp in dcmp.subdirs.items():
        visit_dcmp(subdcmp, comparer)

def local_root(dependfile):
    curdir = os.path.abspath(os.curdir)
    rootdir = os.path.abspath(os.sep)

    while True:
        if os.path.isfile(os.path.join(curdir, dependfile)):
            break 

        if curdir == rootdir:
            return None

        curdir = os.path.abspath(os.path.join(curdir, os.pardir))

    return curdir

def load_conf(dependfile):
    root = local_root(dependfile) 

    if not root:
        return None

    with open(os.path.join(root, dependfile)) as json_data:
        conf = json.load(json_data)
        return conf

def compare_projects(args, comparer):
    conf = load_conf(args.dependfile)
    if not conf:
        print('No depend file named "{0}" found in current or parent folders.'.format(dependfile))
        return 1

    local_assets = os.path.join(local_root(args.dependfile), 'Assets')

    for proj in conf['projects']:
        print('  With project {0}:'.format(proj['path']))
        origin_assets = os.path.join(proj['path'], 'Assets')
        
        for asset in proj['assets']:
            origin_path = os.path.join(origin_assets, asset)
            local_path = os.path.join(local_assets, asset)

            if not comparer.validate(origin_path, local_path):
                continue

            dcmp = dircmp(origin_path, local_path)
            visit_dcmp(dcmp, comparer)

def diff_cmd(args):
    print('Comparing changes')
    comparer = DiffComparer()
    compare_projects(args, comparer)

def pull_cmd(args):
    print('Pulling changes')
    comparer = PullComparer(args.clean, args.preview)
    compare_projects(args, comparer)

def push_cmd(args):
    logging.debug('executing "push" command')
    print('Pushing changes')
    comparer = PushComparer(args.clean, args.preview)
    compare_projects(args, comparer)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='unitysync')
    parser.add_argument('--dependfile', default='depend.json', help='The name of the json dependencies file to use in the current directory.')
    parser.add_argument('--log', default='ERROR')
    subparsers = parser.add_subparsers(dest='subparser_name')

    diff_parser = subparsers.add_parser('diff', help='Compares the origin projects with the local projects.')
    diff_parser.set_defaults(func=diff_cmd)

    pull_parser = subparsers.add_parser('pull', help='Copies changes in the the origin project folders to their local folders.')
    pull_parser.add_argument('--clean', action='store_true', help='Removes project files from the local folder that don\'t exist in the origin folder.')
    pull_parser.add_argument('--preview', action='store_true', help='Prints the actions that will be performed, but does not perform them.')
    pull_parser.set_defaults(func=pull_cmd)

    push_parser = subparsers.add_parser('push', help='Copies changes in the local project folders to their origin folders.')
    push_parser.add_argument('--clean', action='store_true', help='Removes project files from the origin folder that don\'t exist in the local folder.')
    push_parser.add_argument('--preview', action='store_true', help='Prints the actions that will be performed, but does not perform them.')
    push_parser.set_defaults(func=push_cmd)

    args = parser.parse_args()

    loglevel = getattr(logging, args.log.upper())
    logging.basicConfig(level=loglevel)

    if args.subparser_name == None:
        parser.print_help()
    else:
        sys.exit(args.func(args))

