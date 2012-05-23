# -*- encoding: utf-8 -*-
import argparse
import os
import shutil

import tempfile
import unittest


SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
TEST_DIRECTORY = os.path.join(SCRIPT_DIRECTORY, 'test')
EXISTING_FILE = os.path.join(TEST_DIRECTORY, 'existing_file')
NON_EXISTING_FILE = os.path.join(TEST_DIRECTORY, 'non_existing_file')

READ_BUFFER_SIZE = 100 * 1024 ** 2


class NotDuplicate(Exception):

    def __init__(self, orig, duplicate, reason):
        self.orig = orig
        self.duplicate = duplicate
        self.reason = reason

    def __str__(self):
        return '"{self.orig}" and "{self.duplicate}" are not duplicates: {self.reason}'.format(self=self)


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
                self.assertEqual(content, f.read())

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
                self.assertEqual(content, f.read())


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


# FIXME: test?
def same_size(fname1, fname2):
    try:
        if os.path.getsize(fname1) != os.path.getsize(fname2):
            return False
    except OSError:
        return False

    return True


def same_content(fname1, fname2, read_block=_read_block):
    # sizes must match
    if not same_size(fname1, fname2):
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
            self.assertEqual(['1', '1', '2', '3'], reads)

    def test_missing_files_are_not_same(self):
        self.assertFalse(same_content(    EXISTING_FILE, NON_EXISTING_FILE))
        self.assertFalse(same_content(NON_EXISTING_FILE,     EXISTING_FILE))
        self.assertFalse(same_content(NON_EXISTING_FILE, NON_EXISTING_FILE))


def not_duplicate_file_reason(fname1, fname2):
    if same_file_or_dir(fname1, fname2):
        return '"{0}" and "{1}" are referencing the same file'.format(fname1, fname2)

    if not same_content(fname1, fname2):
        return 'files "{0}" and "{1}" differ'.format(fname1, fname2)


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

    for skip_path in path_list:
        tree = skip_path_tree
        for path in skip_path.split(os.path.sep):
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
    for path in files_and_dirs:
        if path in skip_path_tree and 0 == len(skip_path_tree[path]):
            # leaf in skip path tree
            continue

        full_path = os.path.join(directory, path)
        if os.path.isdir(full_path):
            for f in _files_in(full_path, skip_path_tree.get(path, {})):
                yield f
        else:
            yield full_path


def files_in(directory, skip_paths=None):
    return (os.path.relpath(f, directory) for f in _files_in(directory, _make_skip_path_tree(skip_paths)))


class Test_files_in(unittest.TestCase):

    def test_subdirectories_traversed_all_files_returned(self):
        with TempDir() as d:
            files = set(['a', 'b/c', 'b/d/e', 'f/g'])
            for f in files:
                d.make_file(f, '')

            self.assertEqual(files, set(files_in(d.path)))

    def test_file_in_skip_path_not_in_result(self):
        with TempDir() as d:
            d.make_file('f', '')
            d.make_file('f_skipped', '')

            self.assertEqual(set(['f']), set(files_in(d.path, skip_paths=['f_skipped'])))

    def test_file_in_directory_on_skip_path_not_in_result(self):
        with TempDir() as d:
            d.make_file('f', '')
            d.make_file('skipped/dir/g', '')

            self.assertEqual(set(['f']), set(files_in(d.path, skip_paths=['skipped/dir'])))


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
        return 'duplicate candidate contains extra non-duplicate file[s]: {0}'.format(sorted(extra_files))

    # FIXME: DRY & test
    for f in possible_duplicate_files:
        fname = os.path.join(directory, f)
        candidate_fname = os.path.join(duplicate_candidate, f)
        if not same_size(fname, candidate_fname):
            return 'sizes of files "{0}" and "{1}" differ'.format(fname, candidate_fname)

    print 'sizes match, comparing content'

    for f in possible_duplicate_files:
        fname = os.path.join(directory, f)
        candidate_fname = os.path.join(duplicate_candidate, f)
        if not same_content(fname, candidate_fname):
            return 'files "{0}" and "{1}" differ'.format(fname, candidate_fname)

    # they are acceptable duplicates
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
            self.assertIn('duplicate candidate contains extra non-duplicate file[s]:', reason)

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


def remove_file_or_dir(path):
    isdir = os.path.isdir(path)

    print 'removing {0}'.format(path)
    if isdir:
        shutil.rmtree(path)
    else:
        os.remove(path)


def process_duplicate(orig, duplicate, ignored_differences=None, process=remove_file_or_dir):
    if not os.path.exists(duplicate):
        raise NotDuplicate(orig, duplicate, '"{0}" does not exist'.format(duplicate))

    isdir = os.path.isdir(duplicate)

    if isdir:
        reason_not_duplicate = not_duplicate_dir_reason(orig, duplicate, ignored_differences)
    else:
        reason_not_duplicate = not_duplicate_file_reason(orig, duplicate)

    if reason_not_duplicate is None:
        process(duplicate)
    else:
        raise NotDuplicate(orig, duplicate, reason_not_duplicate)


class Test_process_duplicate(unittest.TestCase):

    def test_duplicate_file_is_removed(self):
        with TempDir() as d:
            d.make_file('1', 'asd')
            d.make_file('2', 'asd')

            orig = d.subpath('1')
            duplicate = d.subpath('2')
            process_duplicate(orig, duplicate)

            self.assertTrue(file_exists(orig))
            self.assertFalse(file_exists(duplicate))

    def test_non_duplicate_file_is_not_removed(self):
        with TempDir() as d:
            d.make_file('1', 'asd')
            d.make_file('2', 'asdf')

            orig = d.subpath('1')
            duplicate = d.subpath('2')
            try:
                process_duplicate(orig, duplicate)
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
            process_duplicate(orig, duplicate, ['extra'])

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
                process_duplicate(orig, duplicate)
                self.fail('NotDuplicate not raised')
            except NotDuplicate:
                pass

            self.assertTrue(file_exists(orig))
            self.assertTrue(file_exists(duplicate))

    def test_duplicate_does_not_exist_raises_error(self):
        with TempDir() as d:
            d.make_file('1/f', 'asd')

            orig = d.subpath('1')
            duplicate = d.subpath('2')
            self.assertRaises(NotDuplicate,
                lambda: process_duplicate(orig, duplicate))

            self.assertTrue(file_exists(orig))
            self.assertFalse(file_exists(duplicate))

    def test_removal_is_done_with_the_process_parameter(self):
        with TempDir() as d:
            d.make_file('1', 'asd')
            d.make_file('2', 'asd')

            orig = d.subpath('1')
            duplicate = d.subpath('2')
            process_called = set()
            def check_process_called(arg):
                process_called.add(arg)

            process_duplicate(orig, duplicate, process=check_process_called)

            self.assertEqual(process_called, set([duplicate]))
            self.assertTrue(file_exists(orig))
            # it was not removed in our version of process!
            self.assertTrue(file_exists(duplicate))


def print_duplicate(path):
    print 'in non dry-run mode, "{0}" would be removed'.format(path)


def mkparser():
    parser = argparse.ArgumentParser(
        description='Determine if a file/directory is duplicate of another (with some relax) and optionally remove the duplicate')
    parser.add_argument('main', help='primary location - will be kept')
    parser.add_argument('duplicate', help='location of duplicate - may be removed if contains no unknown change')
    parser.add_argument('ignored_differences', nargs='*', help='extra or changed files in duplicate, that are known and can be removed')
    parser.add_argument('-n', '--dry-run', dest='duplicate_processor', default=remove_file_or_dir, const=print_duplicate, action='store_const',
        help='just say if something would be removed instead of actually removing it')
    return parser


if __name__ == '__main__':
    args = mkparser().parse_args()
    try:
        process_duplicate(args.main, args.duplicate, args.ignored_differences, args.duplicate_processor)
    except NotDuplicate as e:
        print e

# /opt/sfk dup -file .mov