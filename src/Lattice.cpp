#include "Lattice.h"

#include <algorithm>
#include <cstdlib>
#include <iostream>

#include "Instrumentation.h"

namespace {

inline void requireSU3Lattice(int Nc) {
    if (Nc != 3) {
        std::cerr << "Error: lattice matrix storage is SU(3)-only; received Nc="
                  << Nc << ". Exiting." << std::endl;
        std::exit(1);
    }
}

}  // namespace

Lattice::Lattice(Parameters *param, int N, int length) {
    IPG_PROFILE_SCOPE("lattice.allocate");
    Nc = N;
    requireSU3Lattice(Nc);
    size = length * length;
    const double a = param->getL() / static_cast<double>(length);

    std::cout << "Allocating square lattice of size " << length << "x" << length
              << " with a=" << a << " fm ...";

    // Each vector is one contiguous field of fixed 3x3 matrices.  Preserve the
    // original Cell constructor semantics: all eight matrices start as I_3.
    const Matrix identity(3, 1.0);
    U.assign(size, identity);
    U2.assign(size, identity);
    Ux.assign(size, identity);
    Uy.assign(size, identity);
    Ux1.assign(size, identity);
    Uy1.assign(size, identity);
    Ux2.assign(size, identity);
    Uy2.assign(size, identity);

    cellStorage.reserve(size);
    cells.reserve(size);
    for (int i = 0; i < size; ++i) cellStorage.emplace_back(Nc);
    for (int i = 0; i < size; ++i) cells.push_back(&cellStorage[i]);

    posmX.reserve(size);
    pospX.reserve(size);
    posmY.reserve(size);
    pospY.reserve(size);
    posmXpY.reserve(size);
    pospXmY.reserve(size);

    for (int i = 0; i < length; ++i) {
        const int im = std::max(0, i - 1);
        const int ip = std::min(length - 1, i + 1);
        for (int j = 0; j < length; ++j) {
            const int jm = std::max(0, j - 1);
            const int jp = std::min(length - 1, j + 1);

            pospX.push_back(ip * length + j);
            pospY.push_back(i * length + jp);
            posmX.push_back(im * length + j);
            posmY.push_back(i * length + jm);
            posmXpY.push_back(im * length + jp);
            pospXmY.push_back(ip * length + jm);
        }
    }

    std::cout << " done on rank " << param->getMPIRank() << "." << std::endl;
}

BufferLattice::BufferLattice(int N, int length) {
    Nc = N;
    requireSU3Lattice(Nc);
    size = length * length;

    const Matrix identity(3, 1.0);
    buffer1.assign(size, identity);
    buffer2.assign(size, identity);

}
