#!/usr/bin/env python3

#By Michael Plesser

import os
import sys
import shutil
import argparse
import subprocess
from ROOT import *
from utilities import FilesTools
from utilities import PlotterTools

'''
        Code to check the efficiencies of cuts
'''
 
def input_arguments(): 
        
    parser = argparse.ArgumentParser (description = 'Submit multiple templateMaker.py batches at once') 
    parser.add_argument('freq',             action='store',                     help='Sampling frequency of the data run (160 or 120 MHz)'          ) 
    parser.add_argument('temp',             action='store',                     help='Temperature of the data run (18 or 9 deg C)'                  ) 
    parser.add_argument('pos',              action='store',                     help='Position, probably C3up or C3down'                            ) 
    parser.add_argument('-e',               action='store', default='compiled', help='Energy of the data, probably you want "compiled"'             ) 

    # Very poor form, my apologies...
    # These arguments below are needed, but only for PlotterTools, and I don't want them cluttering up my code or confusing people.
    # Do not touch these, do not use them, do not look for them in --help. Their existence even is hidden by argparse.SUPPRESS
    # Forgive my shoddy worksmanship
    parser.add_argument('-d'  ,    type=str,                                                     help=argparse.SUPPRESS)
    parser.add_argument('-f'  ,    type=str,                                                     help=argparse.SUPPRESS)

    parser.add_argument('-x'  ,             action='store_true',                                 help=argparse.SUPPRESS)
    parser.add_argument('-a'  ,             action='store_true',                                 help=argparse.SUPPRESS)
    parser.add_argument('-r'  ,             action='store_true',                                 help=argparse.SUPPRESS)
    
    parser.add_argument('-q'   ,            action='store_true',                                 help=argparse.SUPPRESS)
    parser.add_argument('--fit',            action='store_true',                                 help=argparse.SUPPRESS)

    parser.add_argument('--xb',             action='store',         default='100,-5,1000',       help=argparse.SUPPRESS)
    parser.add_argument('--sb',             action='store',         default='20,0,1500,100,-2,2',help=argparse.SUPPRESS)
    parser.add_argument('--ab',             action='store',         default='100,0,1500',        help=argparse.SUPPRESS)

    parser.add_argument('--xc', '--chicuts',action='store',         default='1,10,1,10',         help=argparse.SUPPRESS)
    parser.add_argument('--am', '--ampmax' ,action='store',         default='100',               help=argparse.SUPPRESS)
    parser.add_argument('--da', '--dampl'  ,action='store',         default='5000',              help=argparse.SUPPRESS)
    parser.add_argument('--pc', '--poscut' ,action='store',         default='3',                 help=argparse.SUPPRESS)
    parser.add_argument('--lc', '--lincorr',action='store_true',    default=False,               help=argparse.SUPPRESS)

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

## Aligns the two X and Y hodoscope planes, such that X[0] = X[1]-dx_hodo_align
def fiber_and_position(testfile, df, poscut, pt):

    tfile  = TFile(testfile[0])
    tree   = tfile.Get("h4")

    hox   = TH1F("hox", '', 100,-20,20)      
    hoy   = TH1F("hoy", '', 100,-20,20)
    cutx = "nFibresOnX[0]==2 && nFibresOnX[1]==2"
    cuty = "nFibresOnY[0]==2 && nFibresOnY[1]==2"

    tree.Draw("X[0]-X[1]>>hox", TCut(cutx))
    x_align = hox.GetMean()

    tree.Draw("Y[0]-Y[1]>>hoy", TCut(cuty))
    y_align = hoy.GetMean()
    
    if (x_align==0.0) or (y_align==0.0): sys.exit("Error! Hodoscope alignment failed!")

    # We have 2 hodo planes we can use for X and Y. This cut picks the best one for position and nFibresOn
    fiber_cut    = "fabs(nFibresOnX[{0}]-2)<={1} && fabs(nFibresOnY[{0}]-2)<={1}"                 # 2 hodoscope planes we can use, [0]. [1]
    position_cut = "(fabs( (X[{0}]-{1}) - {2})<4) && (fabs( (Y[{0}]-{3}) -{4})<{5})"        # {0}=which plane
                                                                                            # {1}=x_hodo_alignment
                                                                                            # {2}=x_center
                                                                                            # {3}=y_hodo_alignment
                                                                                            # {4}=y_center
                                                                                            # {5}=poscut
    x_center, y_center = pt.find_center()
    fiber_and_position  = '('+fiber_cut.format(0,df)+" && "+position_cut.format(0,0,x_center,0,y_center,poscut)+') || '
    fiber_and_position += '('+fiber_cut.format(1,df)+" && "+position_cut.format(1,x_align,x_center,y_align,y_center,poscut)+')'
    return fiber_and_position
def fiber(df):  # df is how many fibers it can differ from 2. IE fiiber(0)
    return " fabs(nFibresOnX[0]-2)<={0} && fabs(nFibresOnY[0]-2)<={0} ".format(df)
def clock(pt):
    xtal = pt.get_xtals()
    return " time_maximum[{}]==time_maximum[{}] ".format(xtal[0],xtal[1])
def position(poscut, pt):
    x_center, y_center = pt.find_center()
    return " (fabs(X[0]-{:.4f})<4) && (fabs(Y[0]-{:.4f})<{}) ".format(float(x_center), float(y_center), poscut)
def amp(ampmax, pt):
    xtal = pt.get_xtals()
    ampbias = pt.amp_coeff()
    return " amp_max[{}]>{} && {:.4f}*amp_max[{}]>{} ".format(xtal[0],ampmax,float(ampbias),xtal[1],ampmax)
def dampl(dampcut, pt):
    xtal = pt.get_xtals()
    ampbias = pt.amp_coeff()
    return " fabs(fit_ampl[{}]-{:.4f}*fit_ampl[{}] )<{} ".format(xtal[0], float(ampbias), xtal[1], dampcut)
def chi2(lb, ub, pt):
    xtal = pt.get_xtals()
    chi2_cut     = " fit_chi2[{}]>{} && fit_chi2[{}]<{} &&".format(xtal[0],lb,xtal[0],ub)
    chi2_cut    += " fit_chi2[{}]>{} && fit_chi2[{}]<{} ".format(xtal[1],lb,xtal[1],ub)
    return chi2_cut

def main():

    gROOT.ProcessLine("gErrorIgnoreLevel = kError;")    # Surpress info messages below Error or Fatal levels (IE info or warning)
    gROOT.SetBatch(kTRUE)                               # Don't actually display the canvases from .Draw(...)

    args = input_arguments()
    


    ft       = FilesTools(args)
    savepath = ft.output_location()
    path     = '/eos/user/m/mplesser/timing_resolution/batch_ntuples/ECAL_H4_June2018_'+args.freq+'_'+args.temp+'_EScan_edges/compiled_roots/'
    testfile = [path+'ECAL_H4_June2018_'+args.freq+'_'+args.temp+'_'+args.e+'_'+args.pos+'.root', args.e+'_'+args.pos]
    pt       = PlotterTools(args, savepath, testfile)
    
    # Custom cuts used in CutBatchAnalysis.py
    # Note: no linear correction because that isn't actually a cut!
    aand = " && "
    baseline = fiber(1)+aand+clock(pt)+aand+position(3,pt)+aand+amp(100,pt)+aand+dampl(5000,pt)
    BaseAdv  = fiber_and_position(testfile,1,3,pt)+aand+clock(pt)+aand+amp(100,pt)+aand+dampl(5000,pt)
    da       = fiber(1)+aand+clock(pt)+aand+position(3,pt)+aand+amp(100,pt)+aand+dampl(1000,pt)
    pc       = fiber(1)+aand+clock(pt)+aand+position(1,pt)+aand+amp(100,pt)+aand+dampl(5000,pt)
    da_pc    = fiber(1)+aand+clock(pt)+aand+position(1,pt)+aand+amp(100,pt)+aand+dampl(1000,pt)
    da_pc_Adv= fiber_and_position(testfile,1,1,pt)+aand+clock(pt)+aand+amp(100,pt)+aand+dampl(1000,pt)

    # Cuts to check, no cut (1==1), individual cuts at differing severity levels, and finally the custom cuts
    cuts = ["1==1",\
            fiber(0),\
            fiber(1),\
            clock(pt),\
            position(3,pt),\
            position(1,pt),\
            fiber(1)+aand+position(3,pt),\
            fiber_and_position(testfile,1,3,pt),\
            amp(100,pt),\
            dampl(5000,pt),\
            dampl(1000,pt),\
            chi2(0.1,10,pt),\
            baseline,\
            BaseAdv,\
            da,\
            pc,\
            da_pc,\
            da_pc_Adv]

    cutnames = ['no cuts',\
                '2 fibers for X and Y \t\t *(baseline setting)',\
                '1-3 fibers for X and Y',\
                'time_maximum must match \t *(baseline setting)',\
                '8x6mm position \t\t *(baseline setting)',\
                '8x2mm position',\
                'naive fiber and position',\
                'advanced fiber and position',\
                'amp_max>100 \t\t\t *(baseline setting)',\
                'damplitude<5000 \t\t *(baseline setting)',\
                'damplitude<1000',\
                'chi2 between 0.1,10 \t\t *(baseline setting)',\
                'baseline',\
                'new baseline(8B+)',\
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
