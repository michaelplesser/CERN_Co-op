#!/usr/local/bin/python

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
    C3upenergies    = { '25GeV' : [], '50GeV' : [], '100GeV' : [], '150GeV' : [], '200GeV' : [], '250GeV' : [] }
    C3downenergies  = { '25GeV' : [], '50GeV' : [], '100GeV' : [], '150GeV' : [], '200GeV' : [], '250GeV' : [] }
    C3leftenergies  = { '25GeV' : [], '50GeV' : [], '100GeV' : [], '150GeV' : [], '200GeV' : [], '250GeV' : [] }
    C3rightenergies = { '25GeV' : [], '50GeV' : [], '100GeV' : [], '150GeV' : [], '200GeV' : [], '250GeV' : [] }
    C3energies      = { '25GeV' : [], '50GeV' : [], '100GeV' : [], '150GeV' : [], '200GeV' : [], '250GeV' : [] }

    mastertable    = { 'C3up'  : C3upenergies, 'C3down' : C3downenergies, 'C3left' : C3leftenergies, 'C3right' : C3rightenergies, 'C3' : C3energies}
    
    # Create output directories if none exist
    if os.path.exists(args.directory+"reco_roots") == False:
        os.mkdir(args.directory+"/reco_roots")
    if os.path.exists(args.directory+"compiled_roots") == False:
        os.mkdir(args.directory+"/compiled_roots")

    print
    # Get position and energy info on all files in the directory, and sort them into the mastertable (dict)
    for filei in os.listdir(args.directory):        # Iterate over all files in the given directory
        if filei.endswith(".root"):                 # Only includes .root files
            print "Found file:", filei,"\t\t", 
            tfile = TFile(args.directory+filei)
            infotree  = tfile.Get("info")
            infotree.GetEntry(1)
            Energy    = int(infotree.Energy)
            Position  = str(infotree.Positions)
            
            ## In case the energies were put in ~exactly~ (IE 49.99 instead of 50), find the closest value from the 'int_e_list' of expected integer energies
            int_e_list = [25, 50, 100, 150, 200, 250]                                               # List of expected integer energies
            int_float_e_diff = [abs( e-int(Energy) ) for e in int_e_list]                           # List of expected energies - found energies (abs_val)
            Energy  = str( int_e_list[ int_float_e_diff.index( min(int_float_e_diff) ) ] )+"GeV"    # Take the expected energy which is closest to the found energy
            
            print "Position: {0:9} \t Energy: {1}".format(Position, Energy)
            mastertable[Position][Energy].append(filei)                                             # Add each file under the proper energy and position indices
    print
    

    # Build the 'hadd' command and run
    for p in mastertable:                                                                                   # Iterate over positions: p=dict_key (position)
        compiledoutfile = args.directory + "compiled_roots/" + name_base + "compiled_" + p + ".root"        # Name of the compiled hadd output file
        compiledcommand = ["hadd",'-f', compiledoutfile]                                                    # -f flag forces save file overwrite if necessary   
        for e in mastertable[p]:                                                                            # Iterate over energies : e=dict_key (energy)
            if len(mastertable[p][e]) != 0:                                                                 # Only create an hadd instance if there are actually files to hadd
                outfile = args.directory + "compiled_roots/" + name_base + e + "_" + p + ".root"            # Name of the individual (energy) hadd output files
                command = ["hadd",'-f', outfile]                                                            # -f flag forces save file overwrite if necessary               
                for filei in mastertable[p][e]:
                    command.append(args.directory+filei)                                                    # Append the name of each file to be hadd-ed for each energy
                    compiledcommand.append(args.directory+filei)                                            # Append the name of each file to be hadd-ed all compiled
                p1 = subprocess.Popen(command)                                                              # Run the individual (energy) hadd command
                p1.wait()                                                                                   # Wait for it to finish before moving on
                print
        if len(compiledcommand) != 3:                                                                       # Don't run if no files were found
            pcompiled = subprocess.Popen(compiledcommand)                                                   # Run the compiled hadd command
            pcompiled.wait()                                                                                # Wait for it to finish before moving on
        print

    # Move the reco files to the /reco_roots directory  
    for filei in os.listdir(args.directory):    
        if filei.endswith(".root"):
            os.rename(args.directory+filei, args.directory+"reco_roots/"+filei) 
            
if __name__=="__main__":
    main()
