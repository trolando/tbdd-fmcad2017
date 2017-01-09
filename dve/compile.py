#!/usr/bin/env python
import os
import random
import sh
import sys


def strip_ext(files, ext):
    return [f[:-len(ext)] for f in filter(lambda f: f.endswith(ext), files)]


def generate_all(files=None):
    if files is None:
        files = list(filter(os.path.isfile, os.listdir(os.curdir)))

    files = strip_ext(list(set(files)), ".dve")
    random.shuffle(files)

    divine = sh.Command("divine")

    for m in files:

        dve_file = m+".dve"
        dve2C_file = m+".dve2C"

        # if the DVE2C file does not exist, generate it

        if not os.path.isfile(dve2C_file):
            print("Generating {}...".format(dve2C_file))
            try:
                divine("compile", "-l", dve_file, _err=sys.stdout, _out=sys.stdout, _out_bufsize=1)
            except sh.ErrorReturnCode:
                print("Error")
        if not os.path.isfile(dve2C_file):
            print("File {} could not be generated!".format(dve2C_file))
            continue


if __name__ == "__main__":
    if len(sys.argv) > 1:
        generate_all(sys.argv[1:])
    else:
        generate_all()
