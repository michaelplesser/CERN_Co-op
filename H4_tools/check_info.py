#!/usr/local/bin/python

import os
import argparse
from ROOT import TFile, gROOT

def input_arguments():
    parser = argparse.ArgumentParser(description='Easilly run hadd on root files by skimming their positions and energies from the info tree')
    
    parser.add_argument('files',   type=str, help='Check energy and position info for given file/directory')

    return parser.parse_args()

def main():

    gROOT.ProcessLine("gErrorIgnoreLevel = kFatal;")    # Surpress info messages below Error or Fatal levels (IE info or warning)

    args = input_arguments()
    if      os.path.isfile(args.files):  files = [args.files]
    elif    os.path.isdir(args.files) :  files = os.listdir(args.files)

    ## Get position and energy info on all files in the directory, and sort them into the mastertable (dict)
    for filei in files:                             # Iterate over all files in the given directory(or just the given file)
        if filei.endswith(".root"):                 # Only includes .root files
            print "Found file:", filei,"\t\t", 
            tfile = TFile(filei)
            infotree  = tfile.Get("info")
            try:
                infotree.GetEntry(1)
            except AttributeError:
                print "\nfile "+filei+" is messed up"
            Energy    = int(infotree.Energy)
            Position  = str(infotree.Positions)
            
            print "Position: {0:9} \t Energy: {1}".format(Position, Energy)
    print
            
if __name__=="__main__":
    main()
