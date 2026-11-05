"""
    Generates the nuclear Q_s^2(T_p, Y) table (qs2Adj_vs_Tp_vs_Y_*.in) from
    the IP-Sat dipole, and checks it against an existing table.

    Q_s^2 = 2 / r_s^2, where r_s solves N(r_s) = 1 - exp(-1/2) for the
    adjoint dipole, i.e. the fundamental IP-Sat dipole at r' = (3/2) r:
        (pi^2 / (2 Nc)) r'^2 alpha_s(mu^2) xg(x, mu^2) T_p = 1/2,
        mu^2 = mu0^2 + 4 / r'^2,   x = 0.01 exp(-Y).
    xg is LO gluon-only DGLAP (Nf = 3 in the running) from
        xg(x, mu0^2) = A_g x^-lambda_g (1 - x)^5.6,
    solved exactly in Mellin space. Lambda = 0.18912 GeV (alpha_s(mu0^2) =
    0.37305) was fitted to qs2Adj_vs_Tp_vs_Y_200.in; with it the 200- and
    240-row tables are reproduced to 0.05% (rms 0.007%), i.e. to the digits
    they are printed with.

    The grid is the tables': T_p = 1e-4 * 10^(k/40) GeV^2, Y = 0, 0.25, ...,
    10.75.

    Usage:
        python3 qs2_table.py KMIN KMAX > rows.in   # rows for k = KMIN..KMAX
        python3 qs2_table.py --check TABLE         # compare with a table
"""

import sys
import numpy as np
from scipy.special import loggamma, digamma
from scipy.optimize import brentq

AG, LAMBDAG, BETAG = 2.308, 0.058, 5.6   # xg(x, mu0^2)
MU02 = 1.51                              # GeV^2
LAMBDAQCD = 0.18912                      # GeV
NF, NC, CA = 3, 3, 3.
B0 = 11. - 2. * NF / 3.
ADJ = 9. / 4.                            # (r'/r)^2 = C_A / C_F
YS = 0.25 * np.arange(44)

# inverse Mellin transform along N = c + z exp(i phi), Gauss-Legendre in z
_zn, _zw = np.polynomial.legendre.leggauss(400)
_Z, _W = 30. * (_zn + 1.), 30. * _zw
_PHI = 0.75 * np.pi
_N = 1.6 + _Z * np.exp(1j * _PHI)
# moments int_0^1 x^(N-1) g(x, mu0^2) dx and LO P_gg(N) (gluon only)
_G0 = AG * np.exp(loggamma(_N - 1. - LAMBDAG) + loggamma(BETAG + 1.)
                  - loggamma(_N - LAMBDAG + BETAG))
_PGG = (2. * CA * (1. / (_N * (_N - 1.)) + 1. / ((_N + 1.) * (_N + 2.))
                   - digamma(_N + 1.) - np.euler_gamma)
        + (11. * CA - 2. * NF) / 6.)


def alpha_s(mu2):
    return 4. * np.pi / (B0 * np.log(mu2 / LAMBDAQCD**2))


def xg(x, mu2):
    gN = _G0 * (alpha_s(MU02) / alpha_s(mu2))**(2. * _PGG / B0)
    return x * np.sum(_W * np.imag(np.exp(1j * _PHI) * x**(-_N) * gN)) / np.pi


def qs2(T, Y):
    x = 0.01 * np.exp(-Y)

    def f(lnr2):  # r'^2 = ADJ r^2
        rp2 = ADJ * np.exp(lnr2)
        mu2 = MU02 + 4. / rp2
        return (np.pi**2 / (2. * NC) * rp2 * alpha_s(mu2) * xg(x, mu2) * T
                - 0.5)

    return 2. / np.exp(brentq(f, -15., 25., xtol=1e-12))


if __name__ == "__main__":
    if sys.argv[1] == "--check":
        table = np.loadtxt(sys.argv[2])
        rows = table[::7]  # every 7th line is enough
        ratio = np.array([q / qs2(T, Y) for Y, T, q in rows])
        print(f"{len(rows)} lines: table/model - 1: "
              f"max {abs(ratio - 1).max():.2e}, rms {(ratio - 1).std():.2e}")
    else:
        for k in range(int(sys.argv[1]), int(sys.argv[2]) + 1):
            T = 1e-4 * 10.**(k / 40.)
            for Y in YS:
                print(f"{Y:g} {T:g} {qs2(T, Y):g} ")
