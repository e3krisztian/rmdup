# -*- encoding: utf-8 -*-
import os
import shutil
from pprint import pprint

import unittest

import sys
import argparse


SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
TEST_DIRECTORY = os.path.join(SCRIPT_DIRECTORY, 'test')


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
		existing_file = os.path.join(TEST_DIRECTORY, 'existing_file')
		self.assertTrue(file_exists(existing_file))

	def test_non_existing_file(self):
		non_existing_file = os.path.join(TEST_DIRECTORY, 'non_existing_file')
		self.assertFalse(file_exists(non_existing_file))


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