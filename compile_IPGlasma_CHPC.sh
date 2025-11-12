#!/usr/bin/env bash

# Usage: ./compile_IPGlasma.sh [KNL|noMPI|default]
module purge
module load gcc/6.1.0
module load chpc/cmake/3.20.0/gcc-6.1.0
module load chpc/fftw/3.3.6-pl1/gcc-6.1.0

Flag=$1

# FFTW paths
FFTW_INC=/apps/libs/fftw/3.3.6-pl1/gcc-6.1.0/include
FFTW_LIB=/apps/libs/fftw/3.3.6-pl1/gcc-6.1.0/lib/libfftw3.so

# GSL paths
GSL_INC=/home/apps/chpc/earth/GSL-2.7-gcc/include
GSL_LIB=/home/apps/chpc/earth/GSL-2.7-gcc/lib/libgsl.so
GSL_CBLAS=/home/apps/chpc/earth/GSL-2.7-gcc/lib/libgslcblas.so

# Clean previous build
mkdir -p build
cd build
rm -fr *

# Configure CMake
if [ "$Flag" == "KNL" ]; then
    CXX=g++ CC=gcc cmake .. -DKNL=ON \
        -DFFTW_INCLUDE_DIRS=$FFTW_INC \
        -DFFTW_LIBRARIES=$FFTW_LIB \
        -DGSL_INCLUDE_DIR=$GSL_INC \
        -DGSL_LIBRARY=$GSL_LIB \
        -DGSL_CBLAS_LIBRARY=$GSL_CBLAS
elif [ "$Flag" == "noMPI" ]; then
    CXX=g++ CC=gcc cmake .. -DdisableMPI=ON \
        -DFFTW_INCLUDE_DIRS=$FFTW_INC \
        -DFFTW_LIBRARIES=$FFTW_LIB \
        -DGSL_INCLUDE_DIR=$GSL_INC \
        -DGSL_LIBRARY=$GSL_LIB \
        -DGSL_CBLAS_LIBRARY=$GSL_CBLAS
else
    CXX=g++ CC=gcc cmake .. \
        -DFFTW_INCLUDE_DIRS=$FFTW_INC \
        -DFFTW_LIBRARIES=$FFTW_LIB \
        -DGSL_INCLUDE_DIR=$GSL_INC \
        -DGSL_LIBRARY=$GSL_LIB \
        -DGSL_CBLAS_LIBRARY=$GSL_CBLAS
fi

# Build and install
make -j4
make install

# Clean up
cd ..
rm -fr build