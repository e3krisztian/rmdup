# -*- encoding: utf-8 -*-
import os
import shutil
from pprint import pprint

import tempfile
import unittest

import sys
import argparse


SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
TEST_DIRECTORY = os.path.join(SCRIPT_DIRECTORY, 'test')
EXISTING_FILE = os.path.join(TEST_DIRECTORY, 'existing_file')
NON_EXISTING_FILE = os.path.join(TEST_DIRECTORY, 'non_existing_file')


class NotDuplicate(Exception):

    def __init__(self, orig, duplicate):
        self.orig = orig
        self.duplicate = duplicate

    def __str__(self):
        return 'NotDuplicate({self.orig}, {self.duplicate})'.format(self=self)


def file_exists(fname):
    return os.path.exists(fname)


class Test_file_exists(unittest.TestCase):

    def test_existing_file(self):
        self.assertTrue(file_exists(EXISTING_FILE))

    def test_non_existing_file(self):
        self.assertFalse(file_exists(NON_EXISTING_FILE))


class TempDir:
    '''Temporary directory usable only by the current user.

    Removed with its content after exiting.'''

    def __init__(self):
        self.tempdir = None

    def __enter__(self):
        self.tempdir = tempfile.mkdtemp()
        return self

    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.tempdir, ignore_errors=True)
        self.tempdir = None

    def subpath(self, relative_path):
        return os.path.join(self.tempdir, relative_path)

    def make_file(self, fname, content):
        filename = self.subpath(fname)
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(filename, 'w') as f:
            f.write(content)


class Test_TempDir(unittest.TestCase):

    def test_new_directory_created_and_removed(self):
        tempdir = None
        with TempDir() as d:
            tempdir = d.tempdir

            self.assertTrue(file_exists(tempdir))

        self.assertFalse(file_exists(tempdir))

    def test_temp_file_created_and_removed(self):
        tempfile = None
        with TempDir() as d:
            tempfile = d.subpath('tempfile')
            with open(tempfile, 'w'):
                pass

            self.assertTrue(file_exists(tempfile))

        self.assertFalse(file_exists(tempfile))

    def check_make_file(self, relpath):
        with TempDir() as d:
            fname = d.subpath(relpath)
            self.assertFalse(file_exists(fname))
            content = 'some text content'

            d.make_file(relpath, content)

            self.assertTrue(file_exists(fname))
            with open(fname) as f:
                self.assertEquals(content, f.read())

    def test_make_file_creates_a_file(self):
        self.check_make_file('test_file')

    def test_make_file_creates_a_file_in_a_non_existent_subdir(self):
        self.check_make_file('x/test_file')

    def test_make_file_creates_a_file_with_two_subdirs(self):
        self.check_make_file('x/y/test_file')


def same_files(fname1, fname2):
    try:
        return os.stat(fname1) == os.stat(fname2)
    except OSError:
        return False


class Test_same_files(unittest.TestCase):

    def test_same_file(self):
        fname = EXISTING_FILE
        self.assertTrue(same_files(fname, fname))

    def test_different_files_same_content_is_not_same(self):
        with TempDir() as d:
            content = 'some text'
            d.make_file('f1', content)
            d.make_file('f2', content)
            f1 = d.subpath('f1')
            f2 = d.subpath('f2')

            self.assertTrue(file_exists(f1))
            self.assertTrue(file_exists(f2))

            self.assertFalse(same_files(f1, f2))

    def  test_non_existing_files_are_not_same(self):
        # that is - no exceptions are raised!
        with TempDir() as d:
            f = d.subpath('non_existing_file')
            self.assertFalse(same_files(f, f))



# class Test_same_content(unittest.TestCase):

#     def test_
# same_content(f1, f2)
# is_duplicate(f1, f2)
#     (not same_files) and same_content
# treat_as_duplicate(orig_dir, duplicate_candidate, ignored_differences)
#     files(duplicate_candidate) - files(orig_dir) - ignored_differences = set()
#     (file2 in ignored_differences) or is_duplicate(file1, file2) for all common files in orig_dir, duplicate_candidate
#     duplicate_candidate has no subdirs
# remove_file(f)
# remove_empty_subdirs(path)


def filesize(fname):
    if os.path.islink(fname):
        return None
    return os.path.getsize(fname)


def files_in(directory):
    '''directory -> [(fname, size)]

    Where files are relative to directory
    '''
    result = []
    for d, subdirs, files in os.walk(directory):
        reld = os.path.relpath(d, directory)
        for f in files:
            fname = os.path.join(reld, f)
            fsize = filesize(os.path.join(directory, fname))
            result.append((fname, fsize))
    return sorted(result)


def is_duplicate(dir1, dir2):
    files1 = files_in(dir1)
    files2 = files_in(dir2)
    if files1 == files2:
        return True

    # give a difference:
    f1 = set(files1)
    f2 = set(files2)

    only_f1 = f1 - f2
    if only_f1:
        print 'only in original ({0})'.format(orig)
        pprint(sorted(only_f1))

    only_f2 = f2 - f1
    if only_f2:
        print 'only in duplicate ({0})'.format(dup)
        pprint(sorted(only_f2))

    return False


def remove_dup(orig, duplicate):
    if not os.path.exists(duplicate):
        return
    if os.path.abspath(orig) == os.path.abspath(duplicate):
        raise NotDuplicate(orig, duplicate)
    if not is_duplicate(orig, duplicate):
        raise NotDuplicate(orig, duplicate)

    print 'remove duplicate {0}'.format(duplicate)
    shutil.rmtree(duplicate)
    print 'done'


orig_duplicate = [
("Konyv/collections/1770 db e-konyv", "disks/Csalad/Books/1770 db e-konyv"),
("Konyv/collections/Könyv/_Scifi", "disks/Csalad/Books/Könyv/_Scifi"),
# ("Mentesek/2006/xr", "disks/Archive1/regi-linux/xr"),
("Mentesek/2006/xr", "disks/Csalad/Backups/2006/xr"),

]

def main():
    for orig, dup in orig_duplicate:
        try:
            remove_dup(orig, dup)
        except NotDuplicate as e:
            print 'Skipped {0}'.format((orig, dup))


def mkparser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--test', action='store_const', const=unittest.main, dest='func', default=main)
    return parser


if __name__ == '__main__':
    args = mkparser().parse_args()
    sys.argv = sys.argv[:1] # + ['-v']
    args.func()
# /opt/sfk dup -file .mov