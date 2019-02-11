#!/usr/bin/env python

import os
import sys
import ROOT
import argparse
import subprocess

'''
    A basic script for creating templates using Simone's templateMaker.py
    Place this file in H4Analysis/scripts and run from the H4Analysis folder
    (There's been some strange bug in the fitResult class that requires you run from thw H4Analysis folder for it to work properly...)
    A few important formatting notes:
        cfg:    Your cfg file must be in the format 'cfg/<args.t>_templates_<frequency>.cfg'
            IE: 11307,C3
                11308,C4
                etc...
    Run as, for example: 'python scripts/templateSubmitter.py 160 18 /path/to/file_of_160MHz_18deg.list -n /path/to/ntuples/ -c <channels>'
    Contact Michael Plesser for more info (michael.plesser@cern.ch)
'''

def input_arguments():

    parser = argparse.ArgumentParser (description = 'Submit multiple templateMaker.py batches at once')
    default_H4_path     = os.getcwd() + '/'
    parser.add_argument('freq',  action='store',                                        help='Sampling frequency of the data run (160 or 120 MHz)')
    parser.add_argument('temp',  action='store',                                        help='Temperature of the data run (18 or 9 deg C)')
    parser.add_argument('f'   ,  action='store',                                        help='Input file containing run #s and positions')
    parser.add_argument('-d'  ,  action='store', default=','                        ,   help='Text delimiter in the input file, likely comma or tab')
    parser.add_argument('-t'  ,  action='store', default='ECAL_H4_Oct2018'          ,   help='Name tag for files, IE ECAL_H4_June2018_')
    parser.add_argument('-p'  ,  action='store', default=default_H4_path            ,   help='Path to H4Analysis')
    parser.add_argument('-n'  ,  action='store', default=default_H4_path+'ntuples/' ,   help='Path to ntuples, if available')
    parser.add_argument('-c'  ,  action='store',                                        help='Which channels to create templates for')
    args = parser.parse_args ()

    if   (args.freq == '160') or (args.freq == '160MHz'): args.freq = '160MHz'                      # Ensures consistent formatting
    elif (args.freq == '120') or (args.freq == '120MHz'): args.freq = '120MHz'                      # IE does the user enter '120', or '120MHz'?
    if   (args.temp == '18' ) or (args.temp == '18deg' ): args.temp = '18deg'                       # Resolve it either way
    elif (args.temp == '9'  ) or (args.temp == '9deg'  ): args.temp = '9deg'                        # blahblah licht mehr licht
    
    return args

## Read the list of runs and positions and compile them into a dictionary indexed by xtal name, with a list of runs at that position    
def get_runs_and_channels(txt_delimit, f, r_a_cs):
    if not os.path.exists(f): sys.exit("Error!!! Input file not found!")
    with open(f, 'r') as fi:
        for line in fi: 
            if line == '\n': continue                                                               # If the line is just '\n', skip it. "last line bug"
            position  = str(line.split(txt_delimit)[1].split('\n')[0])                              # line = '<pos>,<run#>\n'
            runnumber = str(line.split(txt_delimit)[0])                                             # line = '<pos>,<run#>\n'
            r_a_cs[position].extend([runnumber])                                                    # Add each run number under the right dictionary index  
    return r_a_cs

## Checks to see if the reconstruction has been done already
def check_for_ntuple(args, runs, outdir):
    name         = args.t
    ntuplepath   = args.n
    ntuples_file = outdir+'hadded_ntuples.root'
    if os.path.exists(ntuples_file): os.remove(ntuples_file)
    ntuples = [ ['-f', ntuples_file ], [] ]
    for runnumber in runs:
        ntuple_fname = ntuplepath + name + '_' + runnumber + '.root'
        if os.path.exists(ntuple_fname):                                                            # If the ntuple already exists
            ntuples[1].append(ntuple_fname)
            print '\n{0} found! Skipping reconstruction'.format(ntuple_fname)
    if   len(ntuples[1]) == 0: ntuples = []                                                         # If ntuples don't already exist, return empty list
    elif len(ntuples[1]) == 1: 
        ntuples[0] = ['-f', ntuples[1][0]]
    elif len(ntuples[1]) >  1:
        print 
        print "Hadd-ing ntuples..."
        hadd_cmd = ['hadd',ntuples_file] + [filei for filei in ntuples[1]]
        print ' '.join(hadd_cmd)
        p = subprocess.Popen(hadd_cmd)
        p.communicate()              
        print
        
    return ntuples  

def main():

    args    = input_arguments()
    freq    = args.freq
    temp    = args.temp
    H4path  = args.p

    ROOT.gSystem.Load(H4path + "CfgManager/lib/libCFGMan.so")
    ROOT.gSystem.Load(H4path + "lib/libH4Analysis.so")
    ROOT.gROOT.ProcessLine("gErrorIgnoreLevel = kError;")                                           # Surpress info messages below Error or Fatal levels (IE info or warning)
    ROOT.gROOT.SetBatch(ROOT.kTRUE)                                                                 # Don't show graphics 

    ## Crystal center positions in hodoscope coordinates. Can be fairly approximate for our purposes...
    xtal_positions = {  'A1': [-3.7,2.5], 'A2': [-3.7,2.5], 'A3': [-3.7,2.5], \
                        'B1': [-3.7,2.5], 'B2': [-3.7,2.5], 'B3': [-3.7,2.5], 'B4': [-3.7,2.5], 'B5': [-3.7,2.5], \
                        'C1': [-3.7,2.5], 'C2': [-3.7,2.5], 'C3': [-3.7,2.5], 'C4': [-4.1,4.0], 'C5': [-3.7,2.5], \
                        'D1': [-3.7,2.5], 'D2': [-3.7,2.5], 'D3': [-3.7,2.5], 'D4': [-3.7,2.5], 'D5': [-3.7,2.5], \
                        'E1': [-3.7,2.5], 'E2': [-3.7,2.5], 'E3': [-3.7,2.5]    }
    
    runs_and_channels = {ch:[] for ch in xtal_positions}                                            # Initialize an empty dictionary with channel names as indices
    runs_and_channels = get_runs_and_channels(args.d, args.f, runs_and_channels)                    # Fill run numbers under the appropriate channel index
    
    if not os.path.exists(H4path + 'tmp/'):
        os.mkdir(H4path + 'tmp/')                                                                   # Make a tmp/ directory to hold the templates if none exists
    if not os.path.exists('{}tmp/{}_{}_templates/'.format(H4path, freq, temp)):
        os.mkdir('{}tmp/{}_{}_templates/'.format(H4path, freq, temp))

    outdir = '{}tmp/{}_{}_templates/'.format(H4path, freq, temp)
    cfg_path = '/afs/cern.ch/work/m/mplesser/public/ECAL_TB_analysis/templates/ECAL_H4_Oct2018/scripts/cfg/'
    cmd     = ['python',    H4path + 'scripts/templateMaker.py'                    ]                # Start with the "base" cmd
    bins    = ['--bins',    '1000,-25,125'                                         ]                # Make sure the upper bound captures the peak pre-timeshift
    cfg     = ['-t'    ,    cfg_path + '{0}_templates_{1}.cfg'.format(args.t,freq) ]                # Path to .cfg file for templates. Included in my public folder
    if not os.path.exists(cfg[1]): sys.exit("Error!!! Cfg {} file not found!".format(cfg[1]))
    cmd.extend(cfg)                                                                                 # Add the options to the base cmd
    cmd.extend(bins)

    if args.c is not None:  args.c = args.c.split(',')                                              # Use provided channels if provided
    else:                   args.c = [ch for ch in xtal_positions]                                  # Otherwise use all channels, taken from the positions dict.
    
    f = open('{}log_{}_{}_templateSubmitter.txt'.format(outdir,freq,temp), 'w')                     # Keep a log file in case any template creations fail
    f.write("{} {} template log: \n\n".format(freq,temp))
    for ch in args.c:

        if len(runs_and_channels[ch]) == 0: continue                                                # If there are no runs, skip that crystal
        
        ntuples = check_for_ntuple(args, runs_and_channels[ch], outdir)

        ## Misc cuts, can be played with a bit

        ## Get the amp_max peak so you can place a cut around it
        cutstring = 'amp_max[{}]>1000'.format(ch)                                                   # A basic amplitude cut
        if len(ntuples[1]) != 0:
            tfile   = ROOT.TFile(ntuples[1][0])
            h       = tfile.Get("h4")
            hh      = ROOT.TH1F("hh","",1000,0,10000)
            h.Draw("amp_max[{}]>>hh".format(ch), "n_tracks==1")
            am_peak = hh.GetBinCenter(hh.GetMaximumBin())                                           # Use the amp_max peak to tune cuts
            am_peak_cut = 0.05*am_peak                                                              # 5% window. You can play with this a bit
            cutstring  = 'amp_max[{0}]>{1}-{2} && amp_max[{0}] < {1}+{2} && '.format(ch, am_peak, am_peak_cut)  # If you have the ntuple, use a fancier amp cut
        cutstring += 'n_tracks==1 && '
#        cutstring += 'fabs(fitResult[0].x()-{})<5 && fabs(fitResult[0].y()-{})<5 && '.format(str(xtal_positions[ch][0]), str(xtal_positions[ch][1]))
        cutstring += '1'

        cut        = ['--cut'   , cutstring                                                      ]
        channels   = ['-c'      , ch                                                             ]
        runs       = ['-r'      , runs_and_channels[ch][0]                                       ]
        output     = ['-o'      , '{0}{1}_template_file_{2}_{3}.root'.format(outdir,ch,freq,temp)]
        maxevents  = ['-m'      , '-1'                                                           ]
#        batchmode  = ['--batch']
    
        runcmd  = cmd[:]                                                                            # runcmd is the cmd command with channel-specific flags added
        runcmd += output
        runcmd += channels
        runcmd += runs
        runcmd += cut   
        runcmd += maxevents
        runcmd += ntuples[0]   
#        runcmd += batchmode

        print('\nRunning: '+' '.join(runcmd)+'\n')
        p = subprocess.Popen(runcmd)                                                                # Actually run the command
        p.communicate()                                                                             # Wait for the command to finish before moving on
    
        os.remove(outdir+'hadded_ntuples.root')

        if os.path.exists(output[1]): f.write("File {} creation successful!\n".format(output[1]))
        else: f.write("File {} creation FAILED!\n".format(output[1]))
    f.close()

    ## Compile each individual template into one master .root file
    ## Maybe comment out if you're just re-doing certain channels
    print
    compilecmd = ['hadd', outdir+args.t+'_template_file_'+freq+'_'+temp+'.root']
    for file in os.listdir(outdir):
        if file.endswith('.root'):
            compilecmd.append(outdir+file)
    p = subprocess.Popen(compilecmd)
    p.communicate()

if __name__=="__main__":
    main()
