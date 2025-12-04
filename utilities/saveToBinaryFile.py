#!/usr/bin/env python3
"""
    Save a python data array to a binary file that a C++ program can read.
    The data is saved with single float precision (float32).
"""

import argparse
import array
import numpy as np


def main():
    parser = argparse.ArgumentParser(
        description="Convert a text data file to binary format (float32)."
    )
    parser.add_argument("input", help="Input text file to read")
    parser.add_argument("output", help="Output binary file to write")
    args = parser.parse_args()

    data = np.loadtxt(args.input)

    with open(args.output, "wb") as outputFile:
        for config_i in data:
            float_array = array.array('f', config_i)
            float_array.tofile(outputFile)


if __name__ == "__main__":
    main()
