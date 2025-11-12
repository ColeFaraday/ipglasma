#!/usr/bin/env bash

# Usage: ./compile_IPGlasma.sh [KNL|noMPI|default]
# First run:
# module purge
# module load gcc/6.1.0
# module load chpc/cmake/3.20.0/gcc-6.1.0
# module load chpc/fftw/3.3.6-pl1/gcc-6.1.0

Flag=$1

# FFTW paths from the loaded module
FFTW_INC=/apps/libs/fftw/3.3.6-pl1/gcc-6.1.0/include
FFTW_LIB=/apps/libs/fftw/3.3.6-pl1/gcc-6.1.0/lib/libfftw3.so

# Clean previous build
mkdir -p build
cd build
rm -fr *

# Configure CMake based on flag
if [ "$Flag" == "KNL" ]; then
    CXX=g++ CC=gcc cmake .. -DKNL=ON \
        -DFFTW_INCLUDE_DIRS=$FFTW_INC \
        -DFFTW_LIBRARIES=$FFTW_LIB
elif [ "$Flag" == "noMPI" ]; then
    CXX=g++ CC=gcc cmake .. -DdisableMPI=ON \
        -DFFTW_INCLUDE_DIRS=$FFTW_INC \
        -DFFTW_LIBRARIES=$FFTW_LIB
else
    CXX=g++ CC=gcc cmake .. \
        -DFFTW_INCLUDE_DIRS=$FFTW_INC \
        -DFFTW_LIBRARIES=$FFTW_LIB
fi

# Build and install
make -j4
make install

# Clean up
cd ..
rm -fr build