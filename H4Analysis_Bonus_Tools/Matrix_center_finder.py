#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess

import ROOT

def input_arguments():

    parser = argparse.ArgumentParser (description = 'Submit multiple templateMaker.py batches at once')
    default_H4_path = '/afs/cern.ch/work/m/mplesser/private/my_git/CERN_Co-op/H4Analysis_Fork/H4Analysis/'
    parser.add_argument('freq',  action='store',                                        help='Sampling frequency of the data run (160 or 120 MHz)')
    parser.add_argument('temp',  action='store',                                        help='Temperature of the data run (18 or 9 deg C)')
    parser.add_argument('f'   ,  action='store',                                        help='Input file containing run #s and positions')
    parser.add_argument('-d'  ,  action='store', default=',',                           help='Text delimiter in the input file, "," or "\ t"')
    parser.add_argument('-t'  ,  action='store', default='ECAL_H4_Oct2018',             help='Name tag for files, IE ECAL_H4_June2018_')
    parser.add_argument('-p'  ,  action='store', default=default_H4_path,               help='Path to H4Analysis')
    parser.add_argument('-n'  ,  action='store', default=default_H4_path+'ntuples/',    help='Path to ntuples if available')
    parser.add_argument('-c'  ,  action='store',                                        help='Which channels to find centers for')
    args = parser.parse_args ()

    if   (args.freq == '160') or (args.freq == '160MHz'): args.freq = '160MHz'                      # Ensures consistent formatting
    elif (args.freq == '120') or (args.freq == '120MHz'): args.freq = '120MHz'                      # IE does the user enter '120', or '120MHz'?
    if   (args.temp == '18' ) or (args.temp == '18deg' ): args.temp = '18deg'                       # Resolve it either way
    elif (args.temp == '9'  ) or (args.temp == '9deg'  ): args.temp = '9deg'                        # blahblah licht mehr licht
    
    return args

## Read the list of runs and positions and compile them into a dictionary indexed by xtal name, with a list of runs at that position    
def get_runs_and_channels(f, r_a_cs):
    if not os.path.exists(f): sys.exit("Error!!! Input file not found!")
    with open(f, 'r') as fi:
        for line in fi: 
            if line == '\n': continue                                                               # If the line is just '\n', skip it. "last line bug"
            position  = str(line.split(',')[1].split('\n')[0])                                      # line = '<pos>,<run#>\n'
            runnumber = str(line.split(',')[0])                                                     # line = '<pos>,<run#>\n'
            r_a_cs[position].extend([runnumber])                                                    # Add each run number under the right dictionary index  
    return r_a_cs

## Checks H4Analysis/ntuples/ to see if the reconstruction has been done already
def check_for_ntuple(args, runs):
    
    name    = args.t
    H4path  = args.p
    ntuplepath = args.n
    ntuples = ['-f', '']
    for runnumber in runs:
        ntuple_fname = args.n+name+'_'+runnumber+'.root'
        if os.path.exists(ntuple_fname):                                                            # If the ntuple already exists
            ntuples[1] += ntuple_fname + ','                                                        # Add ntuple to list
            print '\n{0} found!'.format(ntuple_fname)
    ntuples[-1] = ntuples[-1][:-1]                                                                  # Remove trailing comma
    if ntuples[-1] == '': ntuples = []                                                              # If ntuples don't already exist, return empty list

    return ntuples  

def main():
    args    = input_arguments()

    freq    = args.freq
    temp    = args.temp
    H4path  = args.p

    ROOT.gROOT.ProcessLine("gErrorIgnoreLevel = kError;")                                                # Surpress info messages below Error or Fatal levels (IE info or warning)
    ROOT.gROOT.SetBatch(ROOT.kTRUE)                                                                           # Don't show graphics 

    ## Crystal center positions in hodoscope coordinates
    xtal_positions = {  'A1': [], 'A2': [], 'A3': [], \
                        'B1': [], 'B2': [], 'B3': [], 'B4': [], 'B5': [], \
                        'C1': [], 'C2': [], 'C3': [], 'C4': [], 'C5': [], \
                        'D1': [], 'D2': [], 'D3': [], 'D4': [], 'D5': [], \
                        'E1': [], 'E2': [], 'E3': []    }
    
    runs_and_channels = {ch:[] for ch in xtal_positions}                                            # Initialize an empty dictionary with channel names as indices
    runs_and_channels = get_runs_and_channels(args.f, runs_and_channels)

    if args.c is not None:  args.c = args.c.split(',')                                              # Use provided channels if provided
    else:                   args.c = [ch for ch in xtal_positions]                                  # Otherwise use all channels, taken from the positions dict.

    for ch in args.c:

        if len(runs_and_channels[ch]) == 0: continue                                                # If there are no runs, skip that crystal
        
        ntuples = check_for_ntuple(args, runs_and_channels[ch])

        tfile   = ROOT.TFile(ntuples[1])
        h       = tfile.Get("h4")
        hx      = ROOT.TH1F("hx","",100,-20,20)
        hy      = ROOT.TH1F("hy","",100,-20,20)
        ROOT.gSystem.Load("./CfgManager/lib/libCFGMan.so")
        ROOT.gSystem.Load("./lib/libH4Analysis.so")
        h.Draw("fitResult[0].x()>>hx", "n_tracks==1")
        h.Draw("fitResult[0].y()>>hy", "n_tracks==1")
        xtal_positions[ch].append(int(100.*hx.GetMean())/100.)
        xtal_positions[ch].append(int(100.*hy.GetMean())/100.)

        tfile.Close()

    print xtal_positions

if __name__=="__main__":
    main()
