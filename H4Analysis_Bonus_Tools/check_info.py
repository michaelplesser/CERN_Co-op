#!/usr/local/bin/python

## Can be run on batch ntuples to check if the info tree was filled correctly or not

import os
import sys
import argparse
import subprocess
from ROOT import TFile, gROOT

def input_arguments():
    parser = argparse.ArgumentParser(description='Easilly run hadd on root files by skimming their positions and energies from the info tree')
    
    parser.add_argument('directory', type=str, help='hadd files within the given directory by energy and position ')
    parser.add_argument('freq',      type=str, help='Sampling frequency of files, IE 120 or 160')
    parser.add_argument('temp',      type=str, help='Sampling temperature, IE 9 or 18')

    return parser.parse_args()

def main():

    gROOT.ProcessLine("gErrorIgnoreLevel = kError;")    # Surpress info messages below Error or Fatal levels (IE info or warning)

    args = input_arguments()
    if   (args.freq == '160') or (args.freq == '160MHz'): freq = '160MHz'           # Ensures consistent formatting
    elif (args.freq == '120') or (args.freq == '120MHz'): freq = '120MHz'           # IE does the user enter '120', or '120MHz'?
    if   (args.temp == '18' ) or (args.temp == '18deg' ): temp = '18deg'            # Resolve it either way
    elif (args.temp == '9'  ) or (args.temp == '9deg'  ): temp = '9deg'             # blahblah licht mehr licht
    
    if not args.directory.endswith('/'): args.directory+='/' # For consistency, makes sure '/directory/path/ends/with/' <-- a '/'

    name_base       = "ECAL_H4_Oct2018_" + freq + "_" + temp + "_"
    # Get position and energy info on all files in the directory, and sort them into the mastertable (dict)
    for filei in os.listdir(args.directory):        # Iterate over all files in the given directory
        if filei.endswith(".root"):                 # Only includes .root files
            print "Found file:", filei,"\t\t", 
            tfile = TFile(args.directory+filei)
            infotree  = tfile.Get("info")
            try:
                infotree.GetEntry(1)
            except AtributeError:
                print "file "+filei+"is missing info!"
            Energy    = int(infotree.Energy)
            Position  = str(infotree.Positions)
            
            print "Position: {0:9} \t Energy: {1}".format(Position, Energy)
    print
            
if __name__=="__main__":
    main()
