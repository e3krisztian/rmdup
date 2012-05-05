# -*- encoding: utf-8 -*-
import argparse
import os
import shutil
import sys

import tempfile
import unittest


SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
TEST_DIRECTORY = os.path.join(SCRIPT_DIRECTORY, 'test')
EXISTING_FILE = os.path.join(TEST_DIRECTORY, 'existing_file')
NON_EXISTING_FILE = os.path.join(TEST_DIRECTORY, 'non_existing_file')

READ_BUFFER_SIZE = 1024 ** 2


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
        self.path = None

    def __enter__(self):
        self.path = tempfile.mkdtemp()
        return self

    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.path, ignore_errors=True)
        self.path = None

    def subpath(self, relative_path):
        return os.path.join(self.path, relative_path)

    def make_file(self, fname, content):
        filename = self.subpath(fname)
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(filename, 'wb') as f:
            f.write(content)


class Test_TempDir(unittest.TestCase):

    def test_new_directory_created_and_removed(self):
        tempdir = None
        with TempDir() as d:
            tempdir = d.path

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

    def test_make_file_creates_a_file_in_binary_mode(self):
        relpath = 'file'
        with TempDir() as d:
            fname = d.subpath(relpath)
            self.assertFalse(file_exists(fname))
            content = 'some\ntext\rcontent\r\n'

            d.make_file(relpath, content)

            self.assertTrue(file_exists(fname))
            with open(fname, 'rb') as f:
                self.assertEquals(content, f.read())


def same_file_or_dir(path1, path2):
    try:
        return os.stat(path1) == os.stat(path2)
    except OSError:
        return False


class Test_same_file_or_dir(unittest.TestCase):

    def test_same_file_or_dir(self):
        fname = EXISTING_FILE
        self.assertTrue(same_file_or_dir(fname, fname))

    def test_different_files_same_content_is_not_same(self):
        with TempDir() as d:
            content = 'some text'
            d.make_file('f1', content)
            d.make_file('f2', content)
            f1 = d.subpath('f1')
            f2 = d.subpath('f2')

            self.assertTrue(file_exists(f1))
            self.assertTrue(file_exists(f2))

            self.assertFalse(same_file_or_dir(f1, f2))

    def  test_non_existing_files_are_not_same(self):
        # that is - no exceptions are raised!
        with TempDir() as d:
            f = d.subpath('non_existing_file')
            self.assertFalse(same_file_or_dir(f, f))


def _read_block(file):
    return file.read(READ_BUFFER_SIZE)

def same_content(fname1, fname2, read_block=_read_block):
    # sizes must match
    try:
        if os.path.getsize(fname1) != os.path.getsize(fname2):
            return False
    except OSError:
        return False

    # compare contents
    with open(fname1, 'rb') as f1:
        with open(fname2, 'rb') as f2:
            buff1 = True # just started
            while buff1:
                buff1 = read_block(f1)
                buff2 = read_block(f2)
                if buff1 != buff2:
                    return False

    return True


class Test_same_content(unittest.TestCase):

    def test_same_content(self):
        with TempDir() as d:
            content = 'same'
            d.make_file('f1', content)
            d.make_file('f2', content)

            self.assertTrue(same_content(d.subpath('f1'), d.subpath('f2')))

    def test_different_content(self):
        with TempDir() as d:
            d.make_file('f1', 'content\n')
            d.make_file('f2', 'content\r\n')

            self.assertFalse(same_content(d.subpath('f1'), d.subpath('f2')))

    def test_same_file_multiple_reads(self):
        with TempDir() as d:
            d.make_file('f1', '12')
            d.make_file('f2', '13')

            reads = []

            def counting_read_block(f):
                buff = f.read(1)
                reads.append(buff)
                return buff

            self.assertFalse(same_content(d.subpath('f1'), d.subpath('f2'), read_block=counting_read_block))
            self.assertEquals(['1', '1', '2', '3'], reads)

    def test_missing_files_are_not_same(self):
        self.assertFalse(same_content(    EXISTING_FILE, NON_EXISTING_FILE))
        self.assertFalse(same_content(NON_EXISTING_FILE,     EXISTING_FILE))
        self.assertFalse(same_content(NON_EXISTING_FILE, NON_EXISTING_FILE))


def not_duplicate_file_reason(fname1, fname2):
    if same_file_or_dir(fname1, fname2):
        return '"{0}" and "{1}" are referencing the same file'.format(fname1, fname2)

    if not same_content(fname1, fname2):
        return 'Files "{0}" and "{1}" differ'.format(fname1, fname2)


    return None


class Test_not_duplicate_file_reason(unittest.TestCase):

    def test_two_files_same_content_is_duplicate(self):
        with TempDir() as d:
            d.make_file('1', '')
            d.make_file('2', '')
            reason = not_duplicate_file_reason(d.subpath('1'), d.subpath('2'))
            self.assertIsNone(reason)

    def test_different_content_not_duplicate(self):
        with TempDir() as d:
            d.make_file('1', '')
            d.make_file('2', '2')
            reason = not_duplicate_file_reason(d.subpath('1'), d.subpath('2'))
            self.assertIn('differ', reason)

    def test_same_file_is_not_duplicate(self):
        reason = not_duplicate_file_reason(EXISTING_FILE, EXISTING_FILE)
        self.assertIn('referencing the same file', reason)


def _make_skip_path_tree(path_list):
    path_list = path_list or []
    skip_path_tree = {}

    for path in path_list:
        tree = skip_path_tree
        for directory in path.split(os.path.sep):
            tree[path] = tree.get(path, {})
            tree = tree[path]
        tree.clear()

    return skip_path_tree


def _files_in(directory, skip_path_tree):
    '''directory -> [fname]

    Subdirectories are traversed.
    Files in skip_paths are not listed,
    directories in skip_paths are not traversed.
    '''

    files_and_dirs = os.listdir(directory)
    for fd in files_and_dirs:
        if fd in skip_path_tree and 0 == len(skip_path_tree[fd]):
            # leaf in skip path tree
            continue

        path = os.path.join(directory, fd)
        if os.path.isdir(path):
            for f in _files_in(path, skip_path_tree.get(directory, {})):
                yield f
        else:
            yield path


def files_in(directory, skip_paths=None):
    return (os.path.relpath(f, directory) for f in _files_in(directory, _make_skip_path_tree(skip_paths)))


class Test_files_in(unittest.TestCase):

    def test_subdirectories_traversed_all_files_returned(self):
        with TempDir() as d:
            files = set(['a', 'b/c', 'b/d/e', 'f/g'])
            for f in files:
                d.make_file(f, '')

            self.assertEquals(files, set(files_in(d.path)))

    def test_file_in_skip_path_not_in_result(self):
        with TempDir() as d:
            d.make_file('f', '')
            d.make_file('f_skipped', '')

            self.assertEquals(set(['f']), set(files_in(d.path, skip_paths=['f_skipped'])))

    def test_file_in_directory_on_skip_path_not_in_result(self):
        with TempDir() as d:
            d.make_file('f', '')
            d.make_file('skipped/dir/g', '')

            self.assertEquals(set(['f']), set(files_in(d.path, skip_paths=['skipped'])))


def not_duplicate_dir_reason(directory, duplicate_candidate, ignored_differences):
    '''
    Check if the duplicate candidate can be safely removed (all files exist elsewhere or we explicitly ignore the different files).

    Returns
      None if the candidate can be safely removed
      or a string explanation about the data loss if the candidate is removed.
    '''

    if same_file_or_dir(directory, duplicate_candidate):
        return '"{0}" and "{1}" are referencing the same directory'.format(directory, duplicate_candidate)

    possible_duplicate_files = set(files_in(duplicate_candidate, ignored_differences))

    extra_files = possible_duplicate_files - set(files_in(directory))
    if extra_files:
        return 'Duplicate candidate contains extra non-duplicate file[s]: {0}'.format(sorted(extra_files))

    for f in possible_duplicate_files:
        fname = os.path.join(directory, f)
        candidate_fname = os.path.join(duplicate_candidate, f)
        if not same_content(fname, candidate_fname):
            return 'Files "{0}" and "{1}" differ'.format(fname, candidate_fname)

    return None


class Test_not_duplicate_dir_reason(unittest.TestCase):

    def test_two_empty_dirs_are_duplicates(self):
        with TempDir() as d:
            directory = d.subpath('directory')
            os.mkdir(directory)

            candidate_dir = d.subpath('candidate_dir')
            os.mkdir(candidate_dir)

            reason = not_duplicate_dir_reason(directory, candidate_dir, [])
            self.assertIsNone(reason)

    def test_same_directory_is_not_duplicate(self):
        d = os.getcwd()
        reason = not_duplicate_dir_reason(d, d, [])
        self.assertIn('referencing the same directory', reason)

    def test_candidate_has_extra_file_not_duplicate(self):
        with TempDir() as d:
            directory = d.subpath('directory')
            os.mkdir(directory)

            candidate_dir = d.subpath('candidate_dir')
            os.mkdir(candidate_dir)
            d.make_file('candidate_dir/extra_file', '')

            reason = not_duplicate_dir_reason(directory, candidate_dir, [])
            self.assertIn('Duplicate candidate contains extra non-duplicate file[s]:', reason)

    def test_candidate_has_a_file_with_different_content_not_duplicate(self):
        with TempDir() as d:
            directory = d.subpath('directory')
            d.make_file('directory/d/file', '')

            candidate_dir = d.subpath('candidate_dir')
            d.make_file('candidate_dir/d/file', 'x')

            reason = not_duplicate_dir_reason(directory, candidate_dir, [])
            self.assertIn('differ', reason)

    def test_change_in_ignored_file_duplicate(self):
        with TempDir() as d:
            directory = d.subpath('directory')
            d.make_file('directory/d/file', '')

            candidate_dir = d.subpath('candidate_dir')
            d.make_file('candidate_dir/d/file', 'x')

            reason = not_duplicate_dir_reason(directory, candidate_dir, ['d'])
            self.assertIsNone(reason)

    def test_extra_files_under_ignored_directory_duplicate(self):
        with TempDir() as d:
            directory = d.subpath('directory')
            d.make_file('directory/file', '')

            candidate_dir = d.subpath('candidate_dir')
            d.make_file('candidate_dir/file', '')
            d.make_file('candidate_dir/d/extra_file', '')
            d.make_file('candidate_dir/d/extra_file2', '')

            reason = not_duplicate_dir_reason(directory, candidate_dir, ['d'])
            self.assertIsNone(reason)


def remove_duplicate(orig, duplicate, ignored_differences=None):
    if not os.path.exists(duplicate):
        return

    isdir = os.path.isdir(orig)

    if isdir:
        reason_not_duplicate = not_duplicate_dir_reason(orig, duplicate, ignored_differences)
    else:
        reason_not_duplicate = not_duplicate_file_reason(orig, duplicate)

    if reason_not_duplicate is None:
        print 'remove duplicate {0}'.format(duplicate)
        if isdir:
            shutil.rmtree(duplicate)
        else:
            os.remove(duplicate)
    else:
        print reason_not_duplicate
        raise NotDuplicate(orig, duplicate)


class Test_remove_duplicate(unittest.TestCase):

    def test_duplicate_file_is_removed(self):
        with TempDir() as d:
            d.make_file('1', 'asd')
            d.make_file('2', 'asd')

            orig = d.subpath('1')
            duplicate = d.subpath('2')
            remove_duplicate(orig, duplicate)

            self.assertTrue(file_exists(orig))
            self.assertFalse(file_exists(duplicate))

    def test_non_duplicate_file_is_not_removed(self):
        with TempDir() as d:
            d.make_file('1', 'asd')
            d.make_file('2', 'asdf')

            orig = d.subpath('1')
            duplicate = d.subpath('2')
            try:
                remove_duplicate(orig, duplicate)
                self.fail('NotDuplicate not raised')
            except NotDuplicate:
                pass

            self.assertTrue(file_exists(orig))
            self.assertTrue(file_exists(duplicate))

    def test_duplicate_dir_is_removed(self):
        with TempDir() as d:
            d.make_file('1/f', 'asd')
            d.make_file('2/f', 'asd')
            d.make_file('2/extra', 'whatever')

            orig = d.subpath('1')
            duplicate = d.subpath('2')
            remove_duplicate(orig, duplicate, ['extra'])

            self.assertTrue(file_exists(orig))
            self.assertFalse(file_exists(duplicate))

    def test_non_duplicate_dir_is_not_removed(self):
        with TempDir() as d:
            d.make_file('1/f', 'asd')
            d.make_file('2/f', 'asd')
            d.make_file('2/extra', 'whatever')

            orig = d.subpath('1')
            duplicate = d.subpath('2')
            try:
                remove_duplicate(orig, duplicate)
                self.fail('NotDuplicate not raised')
            except NotDuplicate:
                pass

            self.assertTrue(file_exists(orig))
            self.assertTrue(file_exists(duplicate))

    def test_duplicate_does_not_exist_raises_no_error(self):
        with TempDir() as d:
            d.make_file('1/f', 'asd')

            orig = d.subpath('1')
            duplicate = d.subpath('2')
            remove_duplicate(orig, duplicate)

            self.assertTrue(file_exists(orig))
            self.assertFalse(file_exists(duplicate))


orig_duplicate = [
("Konyv/collections/1770 db e-konyv", "disks/Csalad/Books/1770 db e-konyv"),
("Konyv/collections/Könyv/_Scifi", "disks/Csalad/Books/Könyv/_Scifi"),
# ("Mentesek/2006/xr", "disks/Archive1/regi-linux/xr"),
("Mentesek/2006/xr", "disks/Csalad/Backups/2006/xr"),

]

def main():
    for orig, dup in orig_duplicate:
        try:
            remove_duplicate(orig, dup)
        except NotDuplicate:
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