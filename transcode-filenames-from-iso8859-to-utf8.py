'''
Rename files and directories below the current directory whose names are not utf-8 to utf-8.
'''
import os
import sys
import subprocess


def print_mv(src, dest):
    f = sys.stdout
    f.write('mv ')
    f.write(src)
    f.write(' ')
    f.write(dest)
    f.write('\n')
    f.flush()


def mv(src, dest):
    subprocess.call(['mv', src, dest])


def transcode(process):
    for root, dirs, files in os.walk('.', topdown=False):
        for line in dirs + files:
            try:
                line.decode('utf-8')
            except UnicodeDecodeError:
                line = line.rstrip()
                src = line
                dest = line.decode('iso8859-2').encode('utf8')
                src = os.path.join(root, src)
                dest = os.path.join(root, dest)
                process(src, dest)


def main():
    rename_command = sys.argv[1]

    commands = {
        'mv': mv,
        'move': mv,
        'print': print_mv,
        'print_mv': print_mv}

    if rename_command not in commands:
        print 'Unknown command "{0}", give one of {1}'.format(rename_command, sorted(commands.keys()))
        sys.exit(1)

    transcode(commands[rename_command])


if __name__ == '__main__':
    main()
