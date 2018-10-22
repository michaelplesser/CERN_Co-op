#!/usr/bin/python

#By Michael Plesser

import os
import sys
import signal
import shutil
import argparse
import subprocess
from ROOT import *
from utilities import FileTools
from utilities import RunInfoTools

'''
        Code to check the efficiencies of cuts
'''
 
## Makes for clean exits out of while loops
def signal_handler(signal, frame):
    print("\program exiting gracefully")
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

def input_arguments(): 
        
    parser = argparse.ArgumentParser (descrirition = 'Submit multiple templateMaker.py batches at once') 
    parser.add_argument('freq',             action='store',                     help='Sampling frequency of the data run (160 or 120 MHz)'          ) 
    parser.add_argument('temp',             action='store',                     help='Temperature of the data run (18 or 9 deg C)'                  ) 
    parser.add_argument('pos',              action='store',                     help='Position, probably C3up or C3down'                            ) 
    parser.add_argument('-e',               action='store', default='compiled', help='Energy of the data, probably you want "compiled"'             ) 

    print sys.argv

    if len(sys.argv[1:])==0:                                                        # use 160/18/C3up as a default
        sys.argv[1:] = ['160', '18', 'C3up']

    args = parser.parse_args()

    if   (args.freq == '160') or (args.freq == '160MHz'): args.freq = '160MHz'  # Ensures consistent formatting 
    elif (args.freq == '120') or (args.freq == '120MHz'): args.freq = '120MHz'  # IE does the user enter '120', or '120MHz'? 
    if   (args.temp == '18' ) or (args.temp == '18deg' ): args.temp = '18deg'   # Resolve it either way 
    elif (args.temp == '9'  ) or (args.temp == '9deg'  ): args.temp = '9deg'    # blahblah licht mehr licht
        
    return args 

def get_events(testfile, cut):

    tfile  = TFile(testfile[0])
    tree = tfile.Get("h4")
    p   = ["Y[0]:X[0]", '', 100,-100,100,100,-100,100]      # Plot something 2d, doesn't matter what. We just need the # of events
    hh = TH2F('hh', '', p[2], p[3], p[4], p[5], p[6], p[7]) 
    tree.Draw(p[0]+">>hh", TCut(cut))
    nentries  = int(hh.GetEntries())    
    return nentries

## Functions that just return cuts

def fiber_and_position(testfile, df, y_pos_cut, rit):
    dfibers = 1                                                                             # nfibers +- from 2 to accept. IE df = 1 -> 1-3 fibersOn 
    fiber_cut_tmp = "fabs(nFibresOnX[{0}]-2)<={1} && fabs(nFibresOnY[{0}]-2)<={1}"
    fiber_cut = "("+fiber_cut_tmp.format(0,dfibers)+' || '+fiber_cut_tmp.format(1,dfibers)+")"
    x_pos_cut = 4                                                                           # 1/2 the x-sidelength of the position cut (in mm)
    x_center, y_center = rit.find_target_center()
    position_cut = "(fabs( X-{0} )<{1}) && (fabs( Y-{2} )<{3})".format(x_center, x_pos_cut, y_center, y_pos_cut)
    return fiber_and_position
def fiber(df):  # df is how many fibers it can differ from 2. 
    return " fabs(nFibresOnX[0]-2)<={0} && fabs(nFibresOnY[0]-2)<={0} ".format(df)
def clock(rit):
    xtal = rit.get_xtals()
    return " time_maximum[{}]==time_maximum[{}] ".format(xtal[0],xtal[1])
def position(poscut, rit):
    x_center, y_center = rit.find_target_center()
    return " (fabs(X[0]-{:.4f})<4) && (fabs(Y[0]-{:.4f})<{}) ".format(float(x_center), float(y_center), poscut)
def amp(ampmax, rit):
    xtal = rit.get_xtals()
    ampbias = rit.amp_calibration_coeff()
    return " amp_max[{}]>{} && {:.4f}*amp_max[{}]>{} ".format(xtal[0],ampmax,float(ampbias),xtal[1],ampmax)
def dampl(dampcut, rit):
    xtal = rit.get_xtals()
    ampbias = rit.amp_calibration_coeff()
    return " fabs(fit_ampl[{}]-{:.4f}*fit_ampl[{}] )<{} ".format(xtal[0], float(ampbias), xtal[1], dampcut)

def main():

    print 'IM ALIVE'
    gROOT.ProcessLine("gErrorIgnoreLevel = kError;")    # Surpress info messages below Error or Fatal levels (IE info or warning)
    gROOT.SetBatch(kTRUE)                               # Don't actually display the canvases from .Draw(...)

    args = input_arguments()

    ft       = FileTools.FileTools(args)
    savepath = ft.output_location()
    path     = '/eos/user/m/mplesser/timing_resolution/batch_ntuples/ECAL_H4_June2018_'+args.freq+'_'+args.temp+'_EScan_edges/compiled_roots/'
    testfile = [path+'ECAL_H4_June2018_'+args.freq+'_'+args.temp+'_'+args.e+'_'+args.pos+'.root', args.e+'_'+args.pos]
    rit      = RunInfoTools.RunInfoTools(args, savepath, testfile)
    
    # Custom cuts used in CutBatchAnalysis.py
    # Note: no linear correction because that isn't actually a cut!
    aand = " && "
    baseline = fiber(1)+aand+clock(rit)+aand+position(3,rit)+aand+amp(100,rit)+aand+dampl(5000,rit)
    BaseAdv  = fiber_and_position(testfile,1,3,rit)+aand+clock(rit)+aand+amp(100,rit)+aand+dampl(5000,rit)
    da       = fiber(1)+aand+clock(rit)+aand+position(3,rit)+aand+amp(100,rit)+aand+dampl(1000,rit)
    pc       = fiber(1)+aand+clock(rit)+aand+position(1,rit)+aand+amp(100,rit)+aand+dampl(5000,rit)
    da_pc    = fiber(1)+aand+clock(rit)+aand+position(1,rit)+aand+amp(100,rit)+aand+dampl(1000,rit)
    da_pc_Adv= fiber_and_position(testfile,1,1,rit)+aand+clock(rit)+aand+amp(100,rit)+aand+dampl(1000,rit)

    # Cuts to check, no cut (1==1), individual cuts at differing severity levels, and finally the custom cuts
    cuts = ["1==1",\
            fiber(0),\
            fiber(1),\
            clock(rit),\
            position(3,rit),\
            position(1,rit),\
            fiber(1)+aand+position(3,rit),\
            fiber_and_position(testfile,1,3,rit),\
            amp(100,rit),\
            dampl(5000,rit),\
            dampl(1000,rit),\
            baseline,\
            BaseAdv,\
            da,\
            pc,\
            da_pc,\
            da_pc_Adv]

    cutnames = ['no cuts',\
                '2 fibers for X and Y',\
                '1-3 fibers for X and Y',\
                'time_maximum must match' ,\
                '8x6mm position \t\t *(baseline setting)',\
                '8x2mm position',\
                'naive fiber and position cuts',\
                'advanced fiber and position cuts',\
                'amp_max>100 \t\t\t *(baseline setting)',\
                'damplitude<5000 \t\t *(baseline setting)',\
                'damplitude<1000',\
                'baseline(naive fiber and pos cuts)',\
                'new baseline(advanced fiber and pos cuts)',\
                'baseline plus dampl<1000',\
                'baseline plus 8x2mm pos',\
                'baseline plus dampl<1000 plus 8x2mm pos',\
                'new baseline plus dampl<1000 plus 8x2mm pos']
   
    nevents_by_cut = [0]*len(cuts)
    for i in range(len(cuts)):
        nevents_by_cut[i] = get_events(testfile,cuts[i])

    print
    print "Cut efficiency summary for "+args.freq+'/'+args.temp+' '+args.e+' at '+args.pos
    for i in range(len(cuts)):
        print '{:>6.2f}%'.format(100.*nevents_by_cut[i]/nevents_by_cut[0]), '{:8d}'.format(nevents_by_cut[i]), cutnames[i]

    print    

if __name__=="__main__":
    main()
