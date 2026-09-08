// Setup.h is part of the IP-Glasma solver.
// Copyright (C) 2012 Bjoern Schenke.

#ifndef Setup_H
#define Setup_H

#include <fstream>
#include <iostream>
#include <sstream>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

using namespace std;

class Setup {

public:
  // Constructor.
  Setup() {}

  string StringFind(string file_name, string st);
  int IFind(string file_name, string st);
  // Variants that return a default instead of exiting when the key is absent,
  // so that input files written before a key existed keep working.
  bool HasKey(string file_name, string st);
  double DFindOpt(string file_name, string st, double def);
  int IFindOpt(string file_name, string st, int def);
  unsigned long long int ULLIFind(string file_name, string st);
  double DFind(string file_name, string st);
  int IsFile(string file_name);
};

#endif // Setup_H
