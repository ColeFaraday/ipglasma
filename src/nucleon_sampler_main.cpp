#include <cstdlib>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <string>
#include <vector>

#include "Glauber.h"
#include "Init.h"
#include "Parameters.h"
#include "Random.h"
#include "Setup.h"

using namespace std;

namespace {

void printUsage(const char *exe) {
  cerr << "Usage: " << exe
       << " <input_file> <num_samples> [output_file] [projectile|target|both]"
       << endl;
}

int parsePositiveInt(const char *arg, const char *name) {
  char *end = nullptr;
  long value = std::strtol(arg, &end, 10);
  if (end == arg || *end != '\0' || value <= 0) {
    cerr << "Invalid " << name << ": " << arg << endl;
    exit(1);
  }
  return static_cast<int>(value);
}

void initSamplerParameters(Setup &setup, Parameters &param,
                           const string &inputFile) {
  param.setNucleonPositionsFromFile(
      setup.IFind(inputFile, "nucleonPositionsFromFile"));
  param.setTarget(setup.StringFind(inputFile, "Target"));
  param.setProjectile(setup.StringFind(inputFile, "Projectile"));
  param.setSigmaNN(setup.DFind(inputFile, "SigmaNN"));
  param.setAverageOverNuclei(setup.IFind(inputFile, "averageOverThisManyNuclei"));
  param.setlightNucleusOption(setup.IFind(inputFile, "lightNucleusOption"));

  param.setSetWSDeformParams(setup.IFind(inputFile, "setWSDeformParams"));
  if (param.getSetWSDeformParams()) {
    param.setR_WS(setup.DFind(inputFile, "R_WS"));
    param.setA_WS(setup.DFind(inputFile, "a_WS"));
    param.setBeta2(setup.DFind(inputFile, "beta2"));
    param.setBeta3(setup.DFind(inputFile, "beta3"));
    param.setBeta4(setup.DFind(inputFile, "beta4"));
    param.setGamma(setup.DFind(inputFile, "gamma"));
    param.setForceDmin(setup.DFind(inputFile, "force_dmin_flag"));
    param.setDmin(setup.DFind(inputFile, "d_min"));
  }

  param.setSeed(setup.ULLIFind(inputFile, "seed"));
  param.setUseSeedList(setup.IFind(inputFile, "useSeedList"));
  param.setUseTimeForSeed(setup.IFind(inputFile, "useTimeForSeed"));
}

void initializeRandom(Random &random, Parameters &param) {
  unsigned long long seed = 0;
  if (param.getUseSeedList() == 0) {
    if (param.getUseTimeForSeed() == 1) {
      seed = static_cast<unsigned long long>(time(0));
    } else {
      seed = param.getSeed();
    }
  } else {
    ifstream fin("seedList");
    if (!fin) {
      cerr << "Random seed file 'seedList' not found. Exiting." << endl;
      exit(1);
    }
    if (!(fin >> seed)) {
      cerr << "Could not read first seed from seedList. Exiting." << endl;
      exit(1);
    }
  }
  random.init_genrand64(seed);
  random.gslRandomInit(seed);
}

void sampleSingleNucleus(Init &init, Random &random, Glauber &glauber, int A,
                         int Z, int projectileOrTarget, double a_WS,
                         double R_WS, double beta2, double beta3,
                         double beta4, double gamma, bool forceDmin,
                         double dMin, vector<ReturnValue> &nucleus) {
  ReturnValue rv;
  if (A == 1) {
    rv.x = 0.0;
    rv.y = 0.0;
    rv.z = 0.0;
    rv.collided = 0;
    rv.proton = 1;
    nucleus.push_back(rv);
    return;
  }

  if (A == 2) {
    rv = glauber.SampleTARejection(&random, projectileOrTarget);
    rv.x /= 2.0;
    rv.y /= 2.0;
    rv.z = 0.0;
    rv.proton = 1;
    rv.collided = 0;
    nucleus.push_back(rv);

    rv.x = -rv.x;
    rv.y = -rv.y;
    rv.z = -rv.z;
    rv.proton = (projectileOrTarget == 1) ? 0 : 0;
    rv.collided = 0;
    nucleus.push_back(rv);
    return;
  }

  init.generate_nucleus_configuration(
      &random, A, Z, a_WS, R_WS, beta2, beta3, beta4, gamma, forceDmin, dMin,
      nucleus);
}

void sampleFromNucleusConfigurationFile(Init &init, Random &random, int A,
                                        int Z,
                                        const vector<vector<float> > &nucleonPosArr,
                                        vector<ReturnValue> &nucleus) {
  if (!nucleonPosArr.empty()) {
    const int nucleusNumber =
        static_cast<int>(random.genrand64_real3() * nucleonPosArr.size());
    for (int i = 0; i < A; i++) {
      ReturnValue rv;
      rv.x = nucleonPosArr[nucleusNumber][3 * i];
      rv.y = nucleonPosArr[nucleusNumber][3 * i + 1];
      rv.z = nucleonPosArr[nucleusNumber][3 * i + 2];
      rv.collided = 0;
      rv.proton = ((i % 2) == 0) ? 0 : 1;
      nucleus.push_back(rv);
    }
    init.assignProtons(nucleus, Z);
    init.recenter_nucleus(nucleus);
  }
}

void sampleNuclei(Init &init, Parameters &param, Random &random, Glauber &glauber,
                  vector<vector<float> > &nucleonPosArrA,
                  vector<vector<float> > &nucleonPosArrB,
                  vector<ReturnValue> &nucleusA,
                  vector<ReturnValue> &nucleusB) {
  const int mode = param.getNucleonPositionsFromFile();
  const int avg = param.getAverageOverNuclei();

  const int A1 = static_cast<int>(glauber.nucleusA1()) * avg;
  const int A2 = static_cast<int>(glauber.nucleusA2()) * avg;
  const int Z1 = static_cast<int>(glauber.nucleusZ1()) * avg;
  const int Z2 = static_cast<int>(glauber.nucleusZ2()) * avg;

  if (avg > 1 && (glauber.nucleusA1() == 1 || glauber.nucleusA2() == 1)) {
    cerr << "Averaging not supported for collisions involving protons. Exiting."
         << endl;
    exit(1);
  }

  if (mode == 0) {
    sampleSingleNucleus(init, random, glauber, A1, Z1, 1,
                        glauber.GlauberData.Projectile.a_WS,
                        glauber.GlauberData.Projectile.R_WS,
                        glauber.GlauberData.Projectile.beta2,
                        glauber.GlauberData.Projectile.beta3,
                        glauber.GlauberData.Projectile.beta4,
                        glauber.GlauberData.Projectile.gamma,
                        glauber.GlauberData.Projectile.forceDminFlag,
                        glauber.GlauberData.Projectile.d_min, nucleusA);
    sampleSingleNucleus(init, random, glauber, A2, Z2, 2,
                        glauber.GlauberData.Target.a_WS,
                        glauber.GlauberData.Target.R_WS,
                        glauber.GlauberData.Target.beta2,
                        glauber.GlauberData.Target.beta3,
                        glauber.GlauberData.Target.beta4,
                        glauber.GlauberData.Target.gamma,
                        glauber.GlauberData.Target.forceDminFlag,
                        glauber.GlauberData.Target.d_min, nucleusB);
  } else if (mode == 1) {
    sampleFromNucleusConfigurationFile(init, random,
                                       static_cast<int>(glauber.nucleusA1()),
                                       static_cast<int>(glauber.nucleusZ1()),
                                       nucleonPosArrA, nucleusA);
    if (nucleusA.empty()) {
      sampleSingleNucleus(init, random, glauber, static_cast<int>(glauber.nucleusA1()),
                          static_cast<int>(glauber.nucleusZ1()), 1,
                          glauber.GlauberData.Projectile.a_WS,
                          glauber.GlauberData.Projectile.R_WS,
                          glauber.GlauberData.Projectile.beta2,
                          glauber.GlauberData.Projectile.beta3,
                          glauber.GlauberData.Projectile.beta4,
                          glauber.GlauberData.Projectile.gamma,
                          glauber.GlauberData.Projectile.forceDminFlag,
                          glauber.GlauberData.Projectile.d_min, nucleusA);
    }

    sampleFromNucleusConfigurationFile(init, random,
                                       static_cast<int>(glauber.nucleusA2()),
                                       static_cast<int>(glauber.nucleusZ2()),
                                       nucleonPosArrB, nucleusB);
    if (nucleusB.empty()) {
      sampleSingleNucleus(init, random, glauber, static_cast<int>(glauber.nucleusA2()),
                          static_cast<int>(glauber.nucleusZ2()), 2,
                          glauber.GlauberData.Target.a_WS,
                          glauber.GlauberData.Target.R_WS,
                          glauber.GlauberData.Target.beta2,
                          glauber.GlauberData.Target.beta3,
                          glauber.GlauberData.Target.beta4,
                          glauber.GlauberData.Target.gamma,
                          glauber.GlauberData.Target.forceDminFlag,
                          glauber.GlauberData.Target.d_min, nucleusB);
    }
  } else {
    cerr << "nucleonPositionsFromFile can only be 0 or 1 in this sampler."
         << endl;
    exit(1);
  }

  init.rotate_nucleus_3D(&random, nucleusA);
  init.rotate_nucleus_3D(&random, nucleusB);
}

void writeConfigurationLine(ofstream &out, const vector<ReturnValue> &nucleus,
                            bool includeTrailingComma) {
  for (size_t i = 0; i < nucleus.size(); ++i) {
    out << nucleus[i].x << ',' << nucleus[i].y << ',' << nucleus[i].z;
    if (i + 1 < nucleus.size() || includeTrailingComma) {
      out << ',';
    }
  }
}

} // namespace

int main(int argc, char *argv[]) {
  if (argc < 3 || argc > 5) {
    printUsage(argv[0]);
    return 1;
  }

  const string inputFile = argv[1];
  const int numSamples = parsePositiveInt(argv[2], "num_samples");
  const string outputFile = (argc >= 4) ? argv[3] : "nucleon_samples.csv";
  const string which = (argc == 5) ? argv[4] : "projectile";

  if (which != "projectile" && which != "target" && which != "both") {
    cerr << "Last argument must be one of: projectile, target, both" << endl;
    return 1;
  }

  Setup setup;
  Parameters param;
  initSamplerParameters(setup, param, inputFile);

  Random random;
  initializeRandom(random, param);

  Glauber glauber;
  glauber.initGlauber(param.getSigmaNN(), param.getTarget(),
                      param.getProjectile(), 0.0,
                      param.getSetWSDeformParams(),
                      param.getR_WS(), param.getA_WS(),
                      param.getBeta2(), param.getBeta3(),
                      param.getBeta4(), param.getGamma(),
                      param.getForceDmin(), param.getDmin(), 100);

  int nn[2] = {1, 1};
  Init init(nn);

  vector<vector<float> > nucleonPosArrA;
  vector<vector<float> > nucleonPosArrB;
  init.readInNucleusConfigs(static_cast<int>(glauber.nucleusA1()),
                            param.getlightNucleusOption(),
                            nucleonPosArrA);
  init.readInNucleusConfigs(static_cast<int>(glauber.nucleusA2()),
                            param.getlightNucleusOption(),
                            nucleonPosArrB);

  ofstream out(outputFile.c_str(), ios::out);
  if (!out) {
    cerr << "Could not open output file: " << outputFile << endl;
    return 1;
  }
  out << std::setprecision(10);

  for (int i = 0; i < numSamples; ++i) {
    vector<ReturnValue> nucleusA;
    vector<ReturnValue> nucleusB;
    sampleNuclei(init, param, random, glauber,
                 nucleonPosArrA, nucleonPosArrB, nucleusA, nucleusB);

    if (which == "projectile") {
      writeConfigurationLine(out, nucleusA, false);
    } else if (which == "target") {
      writeConfigurationLine(out, nucleusB, false);
    } else {
      writeConfigurationLine(out, nucleusA, !nucleusB.empty());
      writeConfigurationLine(out, nucleusB, false);
    }
    out << '\n';
  }

  out.close();
  cout << "Wrote " << numSamples << " sampled configurations to "
       << outputFile << endl;
  return 0;
}


