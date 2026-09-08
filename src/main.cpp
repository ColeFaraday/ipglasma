#include <cmath>
#include <complex>
#include <cstdlib>
#include <ctime>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdio.h>
#include <string>
#include <vector>
#include <random>

#ifndef DISABLEMPI
#include "mpi.h"
#endif

#include "Evolution.h"
#include "FFT.h"
#include "Init.h"
#include "Lattice.h"
#include "Matrix.h"
#include "Parameters.h"
#include "Random.h"
#include "Setup.h"
#include "Spinor.h"
#include "pretty_ostream.h"

#define _SECURE_SCL 0
#define _HAS_ITERATOR_DEBUGGING 0
using namespace std;

int readInput(Setup *setup, Parameters *param, int argc, char *argv[],
              int rank);
void display_logo();
void writeparams(Parameters *param);
void runCrossSectionMode(Parameters *param, Random *random, int rank);

// main program 1
int main(int argc, char *argv[]) {
  int rank;
  int size;

  int nev = 1;
  if (argc == 3) {
    nev = atoi(argv[2]);
  }

#ifndef DISABLEMPI
  // initialize MPI
  MPI_Init(&argc, &argv);
  MPI_Comm_rank(MPI_COMM_WORLD, &rank); // get current process id
  MPI_Comm_size(MPI_COMM_WORLD, &size); // get number of processes
#else
  rank = 0;
  size = 1;
#endif

  int h5Flag = 0;
  pretty_ostream messager;

  Parameters *param = new Parameters();
  param->setMPIRank(rank);
  param->setMPISize(size);
  Setup setup;

  // read parameters from file
  readInput(&setup, param, argc, argv, rank);

  // initialize random generator using time and seed from input file
  Random *random = new Random();
  unsigned long long int rnum;
  if (param->getUseSeedList() == 0) {
    if (param->getUseTimeForSeed() == 1) {
      std::random_device ran_dev;
      rnum = ran_dev();
      //rnum = time(0) + param->getSeed() * 10000;
    } else {
      rnum = param->getSeed();
      messager << "Random seed = " << rnum + (rank * 1000)
               << " - entered directly +rank*1000.";
      messager.flush("info");
    }
    param->setRandomSeed(rnum + rank * 1000);
    if (param->getUseTimeForSeed() == 1) {
      messager << "Random seed = " << param->getRandomSeed();
               //<< " made from time " << rnum - param->getSeed() - (rank * 1000)
               //<< " and argument (+1000*rank) "
               //<< param->getSeed() + (rank * 1000);
      messager.flush("info");
    }
    random->init_genrand64(rnum + rank * 1000);
    random->gslRandomInit(rnum + rank * 1000);
  } else {
    ifstream fin;
    fin.open("seedList");
    std::vector<unsigned long long int> seedList(size, 0);
    if (fin) {
      for (int i = 0; i < size; i++) {
        if (!fin.eof()) {
          fin >> seedList[i];
        } else {
          cerr << "Error: Not enough random seeds for the number of "
               << "processors selected. Exiting." << endl;
          exit(1);
        }
      }
    } else {
      cerr << "Random seed file 'seedList' not found. Exiting." << endl;
      exit(1);
    }
    fin.close();
    param->setRandomSeed(seedList[rank]);
    random->init_genrand64(seedList[rank]);
    random->gslRandomInit(seedList[rank]);
    messager << "Random seed on rank " << rank << " = " << seedList[rank]
             << " read from list.";
    messager.flush("info");
  }

  // Cross section mode: no events are generated, so bypass the event loop.
  if (param->getCrossSectionOnly() == 1) {
    if (rank == 0)
      display_logo();
    runCrossSectionMode(param, random, rank);
    delete random;
    delete param;
#ifndef DISABLEMPI
    MPI_Barrier(MPI_COMM_WORLD);
    MPI_Finalize();
#endif
    return 0;
  }

  // event loop starts ...
  for (int iev = 0; iev < nev; iev++) {
    messager << "Generating event " << iev + 1 << " out of " << nev << " ...";
    messager.flush("info");
    // welcome
    if (rank == 0)
      display_logo();

    if (param->getSubNucleonParamType() > 0) {
        // sample the sub-nucleon parameters from the posterior distribution
        int iSubNucleonParamSet = param->getSubNucleonParamSet();
        if (iSubNucleonParamSet == -1) {
            iSubNucleonParamSet = random->genrand64_int63();
        }
        param->setParamsWithPosteriorParameterSet(
                param->getSubNucleonParamType(), iSubNucleonParamSet);
    }

    // initialize helper class objects

    param->setEventId(rank + iev * size);
    param->setSuccess(0);

    writeparams(param);

    int nn[2];
    nn[0] = param->getSize();
    nn[1] = param->getSize();

    stringstream strup_name;
    strup_name << "usedParameters" << param->getEventId() << ".dat";
    string up_name;
    up_name = strup_name.str();
    ofstream fout1(up_name.c_str(), ios::app);
    fout1 << "Random seed used on rank " << rank << ": "
          << param->getRandomSeed() << endl;
    fout1.close();

    // initialize init object
    Init init(nn);

    // initialize group
    Group group(param->getNc());

    // initialize Glauber class
    messager << "Init Glauber on rank " << param->getMPIRank() << " ... ";
    messager.flush("info");
    Glauber glauber;
    glauber.initGlauber(param->getSigmaNN(), param->getTarget(),
                        param->getProjectile(), param->getb(),
                        param->getSetWSDeformParams(),
                        param->getR_WS(), param->getA_WS(),
                        param->getBeta2(), param->getBeta3(),
                        param->getBeta4(), param->getGamma(),
                        param->getForceDmin(), param->getDmin(), 100);

    // measure and output eccentricity, triangularity
    // init.eccentricity(lat, &group, param, random, glauber);

    // initialize evolution object
    Evolution evolution(nn);

    // either read k_T spectrum from file or do a fresh start
    if (param->getReadMultFromFile() == 1) {
      evolution.readNkt(param);
    } else {
      // clean files
      // stringstream strNpartdNdy_name;
      // strNpartdNdy_name << "NpartdNdy" << rank << ".dat";
      // string NpartdNdy_name;
      // NpartdNdy_name = strNpartdNdy_name.str();

      // ofstream foutNN(NpartdNdy_name.c_str(),ios::out);
      // foutNN.close();

      // stringstream strNpartdNdyH_name;
      // strNpartdNdyH_name << "NpartdNdyHadrons" << rank << ".dat";
      // string NpartdNdyH_name;
      // NpartdNdyH_name = strNpartdNdyH_name.str();

      // ofstream foutNNH(NpartdNdyH_name.c_str(),ios::out);
      // foutNNH.close();

      // stringstream strNpartdEdy_name;
      // strNpartdEdy_name << "NpartdEdy" << param->getEventId() << ".dat";
      // string NpartdEdy_name;
      // NpartdEdy_name = strNpartdEdy_name.str();

      // ofstream foutE(NpartdEdy_name.c_str(),ios::out);
      // foutE.close();

      // stringstream strdNdy_name;
      // strdNdy_name << "dNdy" << param->getEventId() << ".dat";
      // string dNdy_name;
      // dNdy_name = strdNdy_name.str();

      // ofstream foutN(dNdy_name.c_str(),ios::out);
      // foutN.close();

      // stringstream strCorr_name;
      // strCorr_name << "Corr" << param->getEventId() << ".dat";
      // string Corr_name;
      // Corr_name = strCorr_name.str();

      // ofstream foutCorr(Corr_name.c_str(),ios::out);
      // foutCorr.close();

      // stringstream strPhiMult_name;
      // strPhiMult_name << "MultPhi" << param->getEventId() << ".dat";
      // string PhiMult_name;
      // PhiMult_name = strPhiMult_name.str();

      // ofstream foutPhiMult(PhiMult_name.c_str(),ios::out);
      // foutPhiMult.close();

      // stringstream strPhi2ParticleMult_name;
      // strPhi2ParticleMult_name << "MultPhi2Particle" << param->getEventId()
      // << ".dat"; string Phi2ParticleMult_name; Phi2ParticleMult_name =
      // strPhi2ParticleMult_name.str();

      // ofstream foutPhi2ParticleMult(Phi2ParticleMult_name.c_str(),ios::out);
      // foutPhi2ParticleMult.close();

      // stringstream strPhiMultHad_name;
      // strPhiMultHad_name << "MultPhiHadrons" << param->getEventId() <<
      // ".dat"; string PhiMultHad_name; PhiMultHad_name =
      // strPhiMultHad_name.str();

      // ofstream foutPhiMultHad(PhiMultHad_name.c_str(),ios::out);
      // foutPhiMultHad.close();

      // stringstream strPhi2ParticleMultHad_name;
      // strPhi2ParticleMultHad_name << "MultPhiHadrons2Particle" <<
      // param->getEventId() << ".dat"; string Phi2ParticleMultHad_name;
      // Phi2ParticleMultHad_name = strPhi2ParticleMultHad_name.str();

      // ofstream
      // foutPhi2ParticleMultHad(Phi2ParticleMultHad_name.c_str(),ios::out);
      // foutPhi2ParticleMultHad.close();

      // stringstream strame_name;
      // strame_name << "AverageMaximalEpsilon" << param->getEventId() <<
      // ".dat"; string ame_name; ame_name = strame_name.str();

      // ofstream foutEpsA(ame_name.c_str(),ios::out);
      // foutEpsA.close();

      // stringstream strepsx_name;
      // strepsx_name << "eps-x" << param->getEventId() << ".dat";
      // string epsx_name;
      // epsx_name = strepsx_name.str();

      // ofstream foutEpsX(epsx_name.c_str(),ios::out);
      // foutEpsX.close();

      // stringstream strdEdy_name;
      // strdEdy_name << "dEdy" << param->getEventId() << ".dat";
      // string dEdy_name;
      // dEdy_name = strdEdy_name.str();

      // ofstream foutdE(dEdy_name.c_str(),ios::out);
      // foutdE.close();

      // stringstream straniso_name;
      // straniso_name << "anisotropy" << param->getEventId() << ".dat";
      // string aniso_name;
      // aniso_name = straniso_name.str();

      // ofstream foutAni(aniso_name.c_str(),ios::out);
      // foutAni.close();

      // stringstream strecc_name;
      // strecc_name << "eccentricities" << param->getEventId() << ".dat";
      // string ecc_name;
      // ecc_name = strecc_name.str();

      // ofstream foutEcc(ecc_name.c_str(),ios::out);
      // foutEcc.close();

      // stringstream strmult_name;
      // strmult_name << "multiplicity" << param->getEventId() << ".dat";
      // string mult_name;
      // mult_name = strmult_name.str();
      // ofstream foutmult(mult_name.c_str(),ios::out);
      // foutmult.close();

      // stringstream strmult2_name;
      // strmult2_name << "multiplicityCorr" << param->getEventId() << ".dat";
      // string mult2_name;
      // mult2_name = strmult2_name.str();
      // ofstream foutmult2(mult2_name.c_str(),ios::out);
      // foutmult2.close();

      // stringstream strmult3_name;
      // strmult3_name << "multiplicityCorrFromPhi" << param->getEventId() <<
      // ".dat"; string mult3_name; mult3_name = strmult3_name.str(); ofstream
      // foutmult3(mult3_name.c_str(),ios::out); foutmult3.close();

      // stringstream strmult4_name;
      // strmult4_name << "multiplicityCorrFromPhiHadrons" <<
      // param->getEventId() << ".dat"; string mult4_name; mult4_name =
      // strmult4_name.str(); ofstream foutmult4(mult4_name.c_str(),ios::out);
      // foutmult4.close();
    }

      // allocate lattice
      Lattice lat(param, param->getNc(), param->getSize());
      BufferLattice bufferlat(param->getNc(), param->getSize());
      messager.info("Lattice generated.");

    // count how many impact parameters had to be sampled before one was
    // accepted (the accepted one is included in the count). Needed to turn
    // per-event yields into cross sections:
    //   sigma_acc = pi*(bmax^2-bmin^2) * N_events / sum_events(nAttempts)
    // NOTE: this only counts b values drawn by init.init(). If useFixedNpart
    // is switched on, Init::init resamples b internally and those draws are
    // NOT counted here, which invalidates the formula above.
    int nAttempts = 0;

    while (param->getSuccess() == 0) {
      param->setSuccess(0);
      nAttempts++;

      // initialize gsl random number generator (used for non-Gaussian
      // distributions)
      // random->gslRandomInit(rnum);

      // initialize U-fields on the lattice
      init.init(&lat, &group, param, random, &glauber,
                param->getReadInitialWilsonLines());
      messager.info("initialization done.");


      if (param->getSuccess() == 0)
        {
          continue;
        }

      messager.info("Start evolution");
      // do the CYM evolution of the initialized fields using parmeters in param
      evolution.run(&lat, &bufferlat, &group, param);

    }

    {
      stringstream strattempts_name;
      strattempts_name << "attempts" << param->getEventId() << ".dat";
      ofstream foutAttempts(strattempts_name.str().c_str(), ios::out);
      foutAttempts << "# eventId nAttempts b bmin bmax samplebFromLinear "
                   << "SigmaNN L size Projectile Target" << endl;
      foutAttempts << param->getEventId() << " " << nAttempts << " "
                   << param->getb() << " " << param->getbmin() << " "
                   << param->getbmax() << " " << param->getLinearb() << " "
                   << param->getSigmaNN() << " " << param->getL() << " "
                   << param->getSize() << " " << param->getProjectile() << " "
                   << param->getTarget() << endl;
      foutAttempts.close();
    }

#ifndef DISABLEMPI
    MPI_Barrier(MPI_COMM_WORLD);
#endif

    messager.info("One event finished");
    if (param->getWriteOutputsToHDF5() == 1) {
      int status = 0;
      stringstream h5output_filename;
      h5output_filename << "RESULTS_rank" << rank;
      stringstream collect_command;
      collect_command << "python3 utilities/combine_events_into_hdf5.py ."
                      << " --output_filename " << h5output_filename.str()
                      << " --event_id " << param->getEventId();
      status = system(collect_command.str().c_str());
      messager << "finished system call to python script with status: "
               << status;
      messager.flush("info");
      h5Flag = 1;
    }
  }

  delete random;
  delete param;

  if (h5Flag == 1 && rank == 0) {
    int status = 0;
    stringstream collect_command;
    collect_command << "python3 utilities/combine_events_into_hdf5.py ."
                    << " --output_filename RESULTS"
                    << " --combine_hdf5_files_only";
    status = system(collect_command.str().c_str());
    messager << "finished system call to python script with status: " << status;
    messager.flush("info");
  }

#ifndef DISABLEMPI
  MPI_Finalize();
#endif

  return 1;
}


// ---------------------------------------------------------------------------
// Cross section mode.
//
// Measures only the inelastic nucleon-nucleon cross section. The
// elastic/inelastic decision is made entirely inside
// Init::setColorChargeDensity; the Wilson lines, the forward lightcone solve
// and the CYM evolution that normally follow have no influence on it, so this
// path skips all of them (see the early return in Init::init) and simply
// repeats the sampling.
//
// Estimator. With b drawn from the linear distribution
// (samplebFromLinearDistribution 1, pdf = 2b/(bmax^2-bmin^2)),
//
//     sigma_inel = pi (bmax^2 - bmin^2) * S / M,
//
// and with b drawn uniformly (pdf = 1/(bmax-bmin)),
//
//     sigma_inel = 2 pi (bmax - bmin) * <b*I>,
//
// where S is the number of accepted trials out of M and I is the indicator of
// acceptance. Both are unbiased with a simple error bar. This is preferable to
// the N_events / sum(nAttempts) form produced by the normal event loop, which
// is a ratio of random variables and is biased at O(1/N).
//
// Also writes P_inel(b) binned in b, which is what N_coll actually needs and
// what allows the b-dependence to be reweighted in post-processing.
// ---------------------------------------------------------------------------
void runCrossSectionMode(Parameters *param, Random *random, int rank) {
  pretty_ostream messager;

  const int N = param->getSize();
  int nn[2] = {N, N};
  const int M = param->getCrossSectionTrials();
  const double bmin = param->getbmin();
  const double bmax = param->getbmax();
  const bool linearb = (param->getLinearb() == 1);

  if (bmax <= bmin) {
    cerr << "[crossSectionOnly] bmax must exceed bmin. Exiting." << endl;
    exit(1);
  }

  // One parameter set for the whole run, chosen once rather than per event.
  if (param->getSubNucleonParamType() > 0) {
    int iSet = param->getSubNucleonParamSet();
    if (iSet == -1)
      iSet = random->genrand64_int63();
    param->setParamsWithPosteriorParameterSet(param->getSubNucleonParamType(),
                                              iSet);
  }
  param->setEventId(rank);
  writeparams(param);

  Init init(nn);
  Group group(param->getNc());
  Glauber glauber;
  glauber.initGlauber(param->getSigmaNN(), param->getTarget(),
                      param->getProjectile(), param->getb(),
                      param->getSetWSDeformParams(), param->getR_WS(),
                      param->getA_WS(), param->getBeta2(), param->getBeta3(),
                      param->getBeta4(), param->getGamma(),
                      param->getForceDmin(), param->getDmin(), 100);
  // Allocated once for the whole run, not per trial.
  Lattice lat(param, param->getNc(), N);

  // Load the Q_s table up front so that the threshold it establishes is
  // reported before per-trial output is silenced below.
  if (param->getUseNucleus() == 1)
    init.readNuclearQs(param);

  const int nbins = 100;
  std::vector<long> nTrialBin(nbins, 0), nInelBin(nbins, 0);
  long nInel = 0;
  double sumbI = 0., sumb2I = 0.;
  // Q_s,min^2 S_T controls dN/dy at leading order, so accumulating it over
  // the accepted trials gives d(sigma)/dy up to an overall constant that
  // cancels in any ratio of cross sections (R_AB^sigma and its double
  // ratio). Unlike sigma_inel it is an integral over the bulk of the
  // density rather than a level set in its tail, so it responds very
  // differently to the threshold.
  double sumQ = 0., sumQ2 = 0., sumTpp = 0.;

  ofstream foutTrials;
  if (param->getCrossSectionDumpTrials() == 1) {
    stringstream tname;
    tname << "trials" << rank << ".dat";
    foutTrials.open(tname.str().c_str(), ios::out);
    foutTrials << "# itrial b inelastic Qs2minST Tpp" << endl;
  }

  messager << "Measuring sigma_inel with " << M << " trials on rank " << rank
           << ", b in [" << bmin << ", " << bmax << "] fm, "
           << (linearb ? "linear" : "uniform") << " b sampling.";
  messager.flush("info");

  // Init prints per-trial diagnostics that would dominate both the runtime and
  // the log at 10^4 trials, so silence stdout for the loop unless asked not to.
  std::ofstream devnull("/dev/null");
  std::streambuf *coutbuf = std::cout.rdbuf();
  const bool quiet = (param->getCrossSectionVerbose() == 0);
  if (quiet)
    std::cout.rdbuf(devnull.rdbuf());

  for (int i = 0; i < M; i++) {
    param->setSuccess(0);
    init.init(&lat, &group, param, random, &glauber, 0);

    const double b = param->getb();
    int ib = static_cast<int>((b - bmin) / (bmax - bmin) * nbins);
    if (ib < 0)
      ib = 0;
    if (ib >= nbins)
      ib = nbins - 1;
    nTrialBin[ib]++;

    if (param->getCrossSectionDumpTrials() == 1)
      foutTrials << i << " " << b << " " << param->getSuccess() << " "
                 << (param->getSuccess() == 1 ? param->getQs2minST() : 0.)
                 << " " << param->getTpp() << endl;

    if (param->getSuccess() == 1) {
      nInel++;
      nInelBin[ib]++;
      sumbI += b;
      sumb2I += b * b;
      const double q = param->getQs2minST();
      sumQ += q;
      sumQ2 += q * q;
      sumTpp += param->getTpp();
    }

    if (quiet && (i + 1) % 500 == 0)
      cerr << "[Info] rank " << rank << ": " << (i + 1) << "/" << M
           << " trials, " << nInel << " inelastic" << endl;
  }

  if (quiet)
    std::cout.rdbuf(coutbuf);
  if (foutTrials.is_open())
    foutTrials.close();

  // sigma_inel and its statistical error, in fm^2 then converted to mb.
  const double Md = static_cast<double>(M);
  double sigma_fm2 = 0., err_fm2 = 0.;
  if (linearb) {
    const double area = M_PI * (bmax * bmax - bmin * bmin);
    const double p = nInel / Md;
    sigma_fm2 = area * p;
    err_fm2 = area * sqrt(p * (1. - p) / Md);
  } else {
    const double pref = 2. * M_PI * (bmax - bmin);
    const double mean = sumbI / Md;
    // sample variance of the per-trial estimator b*I
    double var = (sumb2I - Md * mean * mean) / (Md - 1.);
    if (var < 0.)
      var = 0.;
    sigma_fm2 = pref * mean;
    err_fm2 = pref * sqrt(var / Md);
  }
  const double sigma_mb = 10. * sigma_fm2;
  const double err_mb = 10. * err_fm2;

  stringstream fname;
  fname << "crossSection" << rank << ".dat";
  ofstream fout(fname.str().c_str(), ios::out);
  fout << "# IP-Glasma inelastic cross section (crossSectionOnly mode)" << endl;
  fout << "# sigma_inel = "
       << (linearb ? "pi(bmax^2-bmin^2) * nInelastic/nTrials"
                   : "2pi(bmax-bmin) * <b*I>")
       << ", error is statistical only" << endl;
  // d(sigma)/dy up to a constant: same b-measure as sigma_inel, weighted by
  // the density instead of by acceptance alone.
  const double norm = linearb ? M_PI * (bmax * bmax - bmin * bmin)
                              : 2. * M_PI * (bmax - bmin);
  const double dsigdy = 10. * norm * sumQ / Md;
  // Standard error of the per-trial estimator q*I (q for accepted trials,
  // zero for rejected ones), over all M trials -- not sqrt(sum q^2).
  const double meanAll = sumQ / Md;
  double varAll = (sumQ2 - Md * meanAll * meanAll) / (Md - 1.);
  if (varAll < 0.)
    varAll = 0.;
  const double dsigdy_err = 10. * norm * sqrt(varAll / Md);
  const double meanQ = (nInel > 0) ? sumQ / nInel : 0.;
  const double meanTpp = (nInel > 0) ? sumTpp / nInel : 0.;
  double varQ = (nInel > 1) ? (sumQ2 - nInel * meanQ * meanQ) / (nInel - 1.) : 0.;
  if (varQ < 0.)
    varQ = 0.;

  fout << "# rank nTrials nInelastic sigma_inel_mb stat_err_mb bmin bmax "
       << "samplebFromLinear QsTableTmin_GeV2 BG BGq dqMin smearingWidth "
       << "QsmuRatio m NqBase SigmaNN roots Projectile Target size L "
       << "meanQs2minST rmsQs2minST meanTpp dsigmady_arb dsigmady_err" << endl;
  fout << rank << " " << M << " " << nInel << " " << sigma_mb << " " << err_mb
       << " " << bmin << " " << bmax << " " << param->getLinearb() << " "
       << param->getQsTableTmin() << " " << param->getBG() << " "
       << param->getBGq() << " " << param->getDqmin() << " "
       << param->getSmearingWidth() << " " << param->getQsmuRatio() << " "
       << param->getm() << " " << param->getNqBase() << " "
       << param->getSigmaNN() << " " << param->getRoots() << " "
       << param->getProjectile() << " " << param->getTarget() << " "
       << param->getSize() << " " << param->getL() << " "
       << meanQ << " " << sqrt(varQ) << " " << meanTpp << " "
       << dsigdy << " " << dsigdy_err << endl;
  fout.close();

  stringstream pname;
  pname << "PinelOfB" << rank << ".dat";
  ofstream foutP(pname.str().c_str(), ios::out);
  foutP << "# P_inel(b) from " << M << " trials on rank " << rank << endl;
  foutP << "# b_lo b_hi b_mid nTrials nInelastic P_inel P_inel_err" << endl;
  const double db = (bmax - bmin) / nbins;
  for (int i = 0; i < nbins; i++) {
    const double blo = bmin + i * db;
    const long nt = nTrialBin[i], ni = nInelBin[i];
    double p = 0., ep = 0.;
    if (nt > 0) {
      p = static_cast<double>(ni) / static_cast<double>(nt);
      ep = sqrt(p * (1. - p) / static_cast<double>(nt));
    }
    foutP << blo << " " << blo + db << " " << blo + 0.5 * db << " " << nt << " "
          << ni << " " << p << " " << ep << endl;
  }
  foutP.close();

  messager << "sigma_inel = " << sigma_mb << " +/- " << err_mb << " mb  ("
           << nInel << "/" << M << " inelastic), <Qs2minST> = " << meanQ
           << ", dsigma/dy [arb] = " << dsigdy << ". Written to "
           << fname.str() << " and " << pname.str() << ".";
  messager.flush("info");
}

void display_logo() {
  cout << endl;
  cout << "--------------------------------------------------------------------"
          "---------"
       << endl;
  cout << "| Classical Yang-Mills evolution with IP-Glasma initial "
          "configurations v1.4 |"
       << endl;
  cout << "--------------------------------------------------------------------"
          "---------"
       << endl;
  cout << "| References:                                                       "
          "        |"
       << endl;
  cout << "| B. Schenke, P. Tribedy, R. Venugopalan                            "
          "        |"
       << endl;
  cout << "| Phys. Rev. Lett. 108, 252301 (2012) and Phys. Rev. C86, 034908 "
          "(2012)     |"
       << endl;
  cout << "--------------------------------------------------------------------"
          "---------"
       << endl;

  cout << "This version uses Qs as obtained from IP-Sat using the sum over "
          "proton T_p(b)"
       << endl;
  cout << "This is a simple MPI version that runs many events in one job. No "
          "communication."
       << endl;

  cout << "Run using large lattices to improve convergence of the root finder "
          "in initial condition. "
       << "Recommended: 600x600 using L=30fm" << endl;
  cout << endl;
}

int readInput(Setup *setup, Parameters *param, int argc, char *argv[],
              int rank) {
  // the first given argument is taken to be the input file name
  // if none is given, that file name is "input"
  // cout << "Opening input file ... " << endl;
  string file_name;
  if (argc > 1) {
    file_name = argv[1];
    if (rank == 0)
      cout << "Using file name \"" << file_name << "\"." << endl;
  } else {
    file_name = "input";
    if (rank == 0)
      cout << "No input file name given. Using default \"" << file_name << "\"."
           << endl;
  }

  // read and set all the parameters in the "param" object of class "Parameters"
  if (rank == 0)
    cout << "Reading parameters from file ... ";
  param->setNucleusQsTableFileName(
      setup->StringFind(file_name, "NucleusQsTableFileName"));
  param->setNucleonPositionsFromFile(
      setup->IFind(file_name, "nucleonPositionsFromFile"));
  param->setTarget(setup->StringFind(file_name, "Target"));
  param->setProjectile(setup->StringFind(file_name, "Projectile"));
  param->setMode(setup->IFind(file_name, "mode"));
  param->setRunningCoupling(setup->IFind(file_name, "runningCoupling"));
  param->setL(setup->DFind(file_name, "L"));
  param->setLOutput(setup->DFind(file_name, "LOutput"));
  param->setBG(setup->DFind(file_name, "BG"));
  param->setBGq(setup->DFind(file_name, "BGq"));
  param->setBGqVar(setup->DFind(file_name, "BGqVar"));
  param->setDqmin(setup->DFind(file_name, "dqMin"));
  param->setMuZero(setup->DFind(file_name, "muZero"));
  param->setc(setup->DFind(file_name, "c"));
  param->setSize(setup->IFind(file_name, "size"));
  param->setSizeOutput(setup->IFind(file_name, "sizeOutput"));
  param->setEtaSizeOutput(setup->IFind(file_name, "etaSizeOutput"));
  param->setDetaOutput(setup->DFind(file_name, "detaOutput"));
  param->setUseFluctuatingx(setup->IFind(file_name, "useFluctuatingx"));
  param->setNc(setup->IFind(file_name, "Nc"));
  param->setInverseQsForMaxTime(setup->IFind(file_name, "inverseQsForMaxTime"));
  param->setSeed(setup->ULLIFind(file_name, "seed"));
  param->setUseSeedList(setup->IFind(file_name, "useSeedList"));
  param->setNy(setup->IFind(file_name, "Ny"));
  param->setRoots(setup->DFind(file_name, "roots"));
  param->setNu(setup->DFind(file_name, "tDistNu"));
  param->setUseFatTails(setup->IFind(file_name, "useFatTails"));
  param->setg(setup->DFind(file_name, "g"));
  param->setm(setup->DFind(file_name, "m"));
  param->setJacobianm(setup->DFind(file_name, "Jacobianm"));
  param->setSigmaNN(setup->DFind(file_name, "SigmaNN"));
  param->setRmax(setup->DFind(file_name, "rmax"));
  param->setUVdamp(setup->DFind(file_name, "UVdamp"));
  param->setSetWSDeformParams(setup->IFind(file_name, "setWSDeformParams"));
  if (param->getSetWSDeformParams()) {
    param->setR_WS(setup->DFind(file_name, "R_WS"));
    param->setA_WS(setup->DFind(file_name, "a_WS"));
    param->setBeta2(setup->DFind(file_name, "beta2"));
    param->setBeta3(setup->DFind(file_name, "beta3"));
    param->setBeta4(setup->DFind(file_name, "beta4"));
    param->setGamma(setup->DFind(file_name, "gamma"));
    param->setForceDmin(setup->DFind(file_name, "force_dmin_flag"));
    param->setDmin(setup->DFind(file_name, "d_min"));
  }
  param->setbmin(setup->DFind(file_name, "bmin"));
  param->setbmax(setup->DFind(file_name, "bmax"));
  param->setQsmuRatio(setup->DFind(file_name, "QsmuRatio"));
  param->setUsePseudoRapidity(setup->DFind(file_name, "usePseudoRapidity"));
  param->setRapidity(setup->DFind(file_name, "Rapidity"));
  param->setUseNucleus(setup->IFind(file_name, "useNucleus"));
  param->setUseGaussian(setup->IFind(file_name, "useGaussian"));
  param->setlightNucleusOption(setup->IFind(file_name, "lightNucleusOption"));
  param->setg2mu(setup->DFind(file_name, "g2mu"));
  param->setMaxtime(setup->DFind(file_name, "maxtime"));
  double lattice_a = param->getL()/static_cast<double>(param->getSize());
  //param->setdtau(setup->DFind(file_name, "dtau"));
  double dtau = param->getMaxtime()/100./lattice_a;
  param->setdtau(dtau);
  // param->setxExponent(setup->DFind(file_name,"xExponent")); //  is now
  // obsolete
  param->setRunWithQs(setup->IFind(file_name, "runWith0Min1Avg2MaxQs"));
  param->setRunWithkt(setup->IFind(file_name, "runWithkt"));
  param->setRunWithLocalQs(setup->IFind(file_name, "runWithLocalQs"));
  param->setRunWithThisFactorTimesQs(
      setup->DFind(file_name, "runWithThisFactorTimesQs"));
  param->setxFromThisFactorTimesQs(
      setup->DFind(file_name, "xFromThisFactorTimesQs"));
  param->setLinearb(setup->IFind(file_name, "samplebFromLinearDistribution"));
  param->setWriteOutputs(setup->IFind(file_name, "writeOutputs"));
  param->setWriteOutputsToHDF5(setup->IFind(file_name, "writeOutputsToHDF5"));
  param->setWriteEvolution(setup->IFind(file_name, "writeEvolution"));
  param->setWriteInitialWilsonLines(
      setup->IFind(file_name, "writeInitialWilsonLines"));
  param->setReadInitialWilsonLines(
        setup->IFind(file_name, "readInitialWilsonLines"));
  param->setAverageOverNuclei(
      setup->IFind(file_name, "averageOverThisManyNuclei"));
  param->setUseTimeForSeed(setup->IFind(file_name, "useTimeForSeed"));
  param->setUseFixedNpart(setup->IFind(file_name, "useFixedNpart"));
  param->setSmearQs(setup->IFind(file_name, "smearQs"));
  param->setSmearingWidth(setup->DFind(file_name, "smearingWidth"));
  param->setGaussianWounding(setup->IFind(file_name, "gaussianWounding"));
  param->setReadMultFromFile(setup->IFind(file_name, "readMultFromFile"));
  param->setProtonAnisotropy(setup->DFind(file_name, "protonAnisotropy"));
  param->setUseConstituentQuarkProton(
      setup->DFind(file_name, "useConstituentQuarkProton"));
  param->setNqBase(setup->DFind(file_name, "useConstituentQuarkProton"));
  param->setNqFluc(setup->DFind(file_name, "NqFluc"));
  param->setUseSmoothNucleus(setup->IFind(file_name, "useSmoothNucleus"));
  param->setShiftConstituentQuarkProtonOrigin(
      setup->DFind(file_name, "shiftConstituentQuarkProtonOrigin"));
  param->setMinimumQs2ST(setup->IFind(file_name, "minimumQs2ST"));
  param->setSubNucleonParamType(setup->IFind(file_name, "SubNucleonParamType"));
  param->setSubNucleonParamSet(setup->IFind(file_name, "SubNucleonParamSet"));
  if (param->getSubNucleonParamType() > 0) {
      param->loadPosteriorParameterSets(param->getSubNucleonParamType());
  }
  // Optional keys: absent from input files written before they existed, so
  // read them with defaults rather than exiting.
  // tau, the threshold on T_p [GeV^2] that decides elastic vs inelastic.
  // <= 0 keeps the historical behaviour (the lower edge of the Q_s table).
  param->setQsTableTmin(setup->DFindOpt(file_name, "QsTableTmin", -1.));
  param->setCrossSectionOnly(setup->IFindOpt(file_name, "crossSectionOnly", 0));
  param->setCrossSectionTrials(
      setup->IFindOpt(file_name, "crossSectionTrials", 10000));
  param->setCrossSectionVerbose(
      setup->IFindOpt(file_name, "crossSectionVerbose", 0));
  param->setCrossSectionDumpTrials(
      setup->IFindOpt(file_name, "crossSectionDumpTrials", 0));
  param->setOutputCondensedGrid(setup->IFind(file_name, "outputCondensedGrid"));
  param->setSmallestEnergyGeV(setup->DFind(file_name, "smallestEnergyGeV"));
  if (rank == 0)
    cout << "done." << endl;

  return 0;
}

void writeparams(Parameters *param)
{
  // write the used parameters into file "usedParameters.dat" as a double check
  // for later
  time_t rawtime = time(0);
  stringstream strup_name;
  strup_name << "usedParameters" << param->getEventId() << ".dat";
  string up_name;
  up_name = strup_name.str();

  fstream fout1(up_name.c_str(), ios::out);
  char *timestring = ctime(&rawtime);
  fout1 << "File created on " << timestring << endl;
  fout1 << "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ " << endl;
  fout1 << "Used parameters by IP-Glasma v1.3" << endl;
  fout1 << "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ " << endl;
  fout1 << " " << endl;
  fout1 << " Output by readInput in main.cpp: " << endl;
  fout1 << " " << endl;
  fout1 << "Program run in mode " << param->getMode() << endl;
  fout1 << "Nc " << param->getNc() << endl;
  fout1 << "size " << param->getSize() << endl;
  fout1 << "lattice spacing a "
        << param->getL() / static_cast<double>(param->getSize()) << " fm "
        << endl;
  fout1 << "Ny " << param->getNy() << endl;
  fout1 << "Projectile " << param->getProjectile() << endl;
  fout1 << "Target " << param->getTarget() << endl;
  if (param->getUseConstituentQuarkProton() > 0) {
    fout1 << "Nucleons consists of " << param->getUseConstituentQuarkProton()
          << " constituent quarks" << endl;
    if (param->getShiftConstituentQuarkProtonOrigin())
      fout1 << "... constituent quark center of mass moved to origin" << endl;
  }
  fout1 << "Smooth nucleus " << param->getUseSmoothNucleus() << endl;
  fout1 << "Gaussian wounding " << param->getGaussianWounding() << endl;
  fout1 << "Using fluctuating x=Qs/root(s) " << param->getUseFluctuatingx()
        << endl;
  if (param->getRunWithkt() == 0)
    fout1 << "Using local Qs to run " << param->getRunWithLocalQs() << endl;
  else
    fout1 << "running alpha_s with k_T" << endl;
  fout1 << "QsmuRatio " << param->getQsmuRatio() << endl;
  fout1 << "smeared mu " << param->getSmearQs() << endl;
  fout1 << "m " << param->getm() << endl;
  fout1 << "rmax " << param->getRmax() << endl;
  fout1 << "UVdamp " << param->getUVdamp() << endl;
  if (param->getSetWSDeformParams()) {
    fout1 << "setWSDeformParams " << param->getSetWSDeformParams() << endl;
    fout1 << "R_WS " << param->getR_WS() << endl;
    fout1 << "a_WS " << param->getA_WS() << endl;
    fout1 << "beta2 " << param->getBeta2() << endl;
    fout1 << "beta3 " << param->getBeta3() << endl;
    fout1 << "beta4 " << param->getBeta4() << endl;
    fout1 << "gamma " << param->getGamma() << endl;
  }
  if (param->getSmearQs() == 1) {
    fout1 << "smearing width " << param->getSmearingWidth() << endl;
  }
  fout1 << "Using fat tailed distribution " << param->getUseFatTails() << endl;
  if (param->getQsTableTmin() > 0.)
    fout1 << "QsTableTmin (tau) " << param->getQsTableTmin() << " GeV^2" << endl;
  else
    fout1 << "QsTableTmin (tau) from the Q_s table's lower edge" << endl;
  if (param->getCrossSectionOnly() == 1)
    fout1 << "crossSectionOnly 1, trials " << param->getCrossSectionTrials()
          << endl;
  fout1.close();
}
