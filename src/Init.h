// Init.h is part of the IP-Glasma solver.
// Copyright (C) 2012 Bjoern Schenke.

#ifndef Init_H
#define Init_H

#include <functional>
#include <string>
#include <cstdint>

#include "FFT.h"
#include "Glauber.h"
#include "Group.h"
#include "Lattice.h"
#include "Matrix.h"
#include "Parameters.h"
#include "Random.h"
#include "pretty_ostream.h"

class Init {
  private:
    int const static iymaxNuc = 44;  // for the Tp-y table

    // room for the T_p rows of the Q_s table; the number used, nTp_, is read
    // from the file (200 in qs2Adj_vs_Tp_vs_Y_200.in)
    int const static iTpmax = 400;
    int nTp_ = 0;

    double const deltaYNuc = 0.25;  // for the new table

    FFT fft;
    //  Matrix** A;
    //  Glauber *glauber;
    double Qs2Nuclear[iTpmax][iymaxNuc];
    double Tlist[iTpmax];
    bool QsTableLoaded_ = false;  // the Q_s table is a fixed file: read once
    // below the table, Q_s^2 proportional to T_p instead of 0 (criterion 4)
    bool QsBelowTable_ = false;

    double As[1];

    std::vector<vector<float> > nucleonPosArrA_;
    std::vector<vector<float> > nucleonPosArrB_;

    // list of x and y coordinates of nucleons in nucleus A
    std::vector<ReturnValue> nucleusA_;
    // list of x and y coordinates of nucleons in nucleus B
    std::vector<ReturnValue> nucleusB_;

    pretty_ostream messager;

    int Nc_, Nc2m1_;
    Group *group_ptr_;
    Random *random_ptr_;

    Matrix one_;

    // hard-soft estimate (hardSoftEstimator) in its k_T bins [1/GeV^2], used
    // by glasmaFreeSpectrum above the lattice momenta
    std::vector<double> hardSoftTail_;

    // ---- refined sub-box (subBoxPass) ----
    // random state at the start of the last setV: its colour charges can be
    // drawn again
    Random::MTState setVStartState_;
    bool haveSetVState_ = false;
    // constituent positions, widths and Q_s normalizations of the last
    // setColorChargeDensity, to evaluate T_p on another lattice
    std::vector<std::vector<double> > xq1_, yq1_, BGq1_, gauss1_;
    std::vector<std::vector<double> > xq2_, yq2_, BGq2_, gauss2_;
    double nucleiInAverage_ = 1.;
    // centroid [fm] of the last hard-soft map (sMap)
    double hsCentroidX_ = 0., hsCentroidY_ = 0.;
    // position [fm] of site (0, 0) if it is not (-L/2, -L/2)
    bool customOrigin_ = false;
    double originX_ = 0., originY_ = 0.;
    // prefix of glasmaFree and hardSoftMap file names
    std::string outputPrefix_;
    // if set, setV takes the unit Gaussians of each sheet from here
    std::function<void(std::vector<double> &)> chargeOverride_;
    // capture mode: setV only draws the unit Gaussians of its sheets and
    // hands each to chargeCapture_ (sheet index, Gaussians), builds nothing
    bool captureOnly_ = false;
    std::function<void(const std::vector<double> &, int)> chargeCapture_;

  public:
    // Constructor.
    Init(const int nn[]) : fft(nn) {};

    ~Init() {};

    void init(
        Lattice *lat, Group *group, Parameters *param, Random *random,
        Glauber *glauber, int READFROMFILE);
    void sampleTA(Parameters *param, Random *random, Glauber *glauber);
    void readNuclearQs(Parameters *param);
    void solveAxbComplex(double *Jab, double *Fa, std::vector<double> &xvec);
    void solveAxb(double *Jab, double *Fa, std::vector<double> &xvec);

    double getNuclearQs2(double Qs2atZeroY, double y);
    bool passesInelasticCriterion(Parameters *param, Random *random);
    bool passesFieldOverlapCriterion(
        Lattice *lat, Parameters *param, Random *random);
    void setG2mu2(Lattice *lat, Parameters *param, bool ownCharges);
    void setColorChargeDensity(
        Lattice *lat, Parameters *param, Random *random, Glauber *glauber);
    void setV(Lattice *lat, Parameters *param, Random *random);
    // advances the random stream exactly as setV does, without building V
    void skipColorCharges(Parameters *param, Random *random);
    void hardSoftEstimator(Lattice *lat, Parameters *param);
    // tau = 0+ fields from the Wilson lines (the second half of init)
    void forwardLightcone(Lattice *lat, Parameters *param);
    // T_p of both nuclei on a lattice from the stored geometry of the event
    void setThicknessFromStoredGeometry(Lattice *lat, Parameters *param);
    // the accepted event on a finer lattice in a periodic box around it
    void subBoxPass(Lattice *lat, Group *group, Parameters *param);
    void glasmaFreeSpectrum(Lattice *lat, Group *group, Parameters *param);
    void readV(Lattice *lat, Parameters *param, int format);
    // void eccentricity(Lattice *lat, Group *group, Parameters *param, Random
    // *random, Glauber *glauber);
    void multiplicity(Lattice *lat, Parameters *param);

    Matrix getUfromExponent(std::vector<double> &in);
    bool findUInForwardLightconeBjoern(Matrix &U1, Matrix &U2, Matrix &Usol);
    bool findUInForwardLightconeChun(
        Matrix &U1, Matrix &U2, Matrix &Usol, std::uint64_t retrySeed);

    void readInNucleusConfigs(
        const int nucleusA, const int lightNucleusOption,
        const int polarizationFlag, const double polJz,
        vector<vector<float> > &nucleonPosArr);
    void generate_nucleus_configuration(
        Random *random, int A, int Z, double a_WS, double R_WS, double beta2,
        double beta3, double beta4, double gamma, bool force_dmin_flag,
        double d_min, double dR_np, double da_np,
        std::vector<ReturnValue> &nucleus);
    void generate_nucleus_configuration_with_woods_saxon(
        Random *random, int A, int Z, double a_WS, double R_WS, double d_min,
        double dR_np, double da_np, std::vector<ReturnValue> &nucleus);
    void generate_nucleus_configuration_with_deformed_woods_saxon(
        Random *random, int A, int Z, double a_WS, double R_WS, double beta2,
        double beta3, double beta4, double d_min, double dR_np, double da_np,
        std::vector<ReturnValue> &nucleus);
    void generate_nucleus_configuration_with_deformed_woods_saxon2(
        Random *random, int A, int Z, double a_WS, double R_WS, double beta2,
        double beta3, double beta4, double gamma, double dR_np, double da_np,
        std::vector<ReturnValue> &nucleus);
    void generate_nucleus_configuration_with_deformed_woods_saxon_force_dmin(
        Random *random, int A, int Z, double a_WS, double R_WS, double beta2,
        double beta3, double beta4, double gamma, double d_min, double dR_np,
        double da_np, std::vector<ReturnValue> &nucleus);
    double sample_r_from_woods_saxon(
        Random *random, double a_WS, double R_WS) const;
    void sample_r_and_costheta_from_deformed_woods_saxon(
        Random *random, double a_WS, double R_WS, double beta2, double beta3,
        double beta4, double &r, double &costheta) const;
    double fermi_distribution(double r, double R_WS, double a_WS) const;
    double spherical_harmonics(int l, double ct) const;
    double spherical_harmonics_Y22(double ct, double phi) const;
    void recenter_nucleus(
        std::vector<double> &x, std::vector<double> &y, std::vector<double> &z);
    void recenter_nucleus(std::vector<ReturnValue> &nucleus);
    void assignProtons(
        Random *random, std::vector<ReturnValue> &nucleus, const int Z);
    void rotate_nucleus(Random *random, std::vector<ReturnValue> &nucleus);
    void rotate_nucleus(
        double phi_global, double theta_global,
        std::vector<ReturnValue> &nucleus);
    void rotate_nucleus_3D(Random *random, std::vector<ReturnValue> &nucleus);

    void samplePartonPositions(
        Parameters *param, Random *random, std::vector<double> &x_array,
        std::vector<double> &y_array, std::vector<double> &z_array,
        std::vector<double> &BGq_array);

    double sampleLogNormalDistribution(
        Random *random, const double mean, const double variance);

    void sampleQsNormalization(
        Random *random, Parameters *param, const int Nq,
        std::vector<double> &gauss_array);
    int sampleNumberOfPartons(Random *random, Parameters *param);
};

#endif  // Init_H
