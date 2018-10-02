#!/usr/bin/python

## By Michael Plesser

import os
import sys
import argparse
from ROOT import *

from utilities import FileTools
from utilities import PlotterTools
from utilities import AnalysisTools

def input_arguments():
    parser = argparse.ArgumentParser(description='Control plotting and cuts for inter-crystal time resolution studies')
    
    parser.add_argument('-d'  ,    type=str,                                                     help='Use all the files in the given directory for analysis ')
    parser.add_argument('-f'  ,    type=str,                                                     help='Use the given file for analysis(use the absolute path)')
    parser.add_argument('-e'  ,    type=str,                                                     help='Energy to use for analysis (IE "250GeV" or "compiled")')
    parser.add_argument('--freq',  type=str,                        default='160MHz',            help='Sampling frequency,   IE "160MHz" or "120 MHz"')
    parser.add_argument('--temp',  type=str,                        default='18deg' ,            help='Sampling temperature, IE "18deg"  or "9deg"')

    parser.add_argument('-x'  ,             action='store_true',                                 help='Create plots for fit_chi2[C3] and fit_chi2[<2nd xtal>]')
    parser.add_argument('-a'  ,             action='store_true',                                 help='Create effective voltage (Aeff) plot')
    parser.add_argument('-r'  ,             action='store_true',                                 help='Create resolution versus  Aeff  plot')
    
    parser.add_argument('-q'   ,            action='store_true',                                 help='Use a quantile method for the resolution versus Aeff plot')
    parser.add_argument('--fit',            action='store_true',                                 help='Fit using a user function the resolution versus Aeff plot')

    parser.add_argument('--xb',             action='store',         default='100,-5,1000',       help='Chi2  plot bounds, "nbins,chi2min,chi2max"')
    parser.add_argument('--rb',             action='store',         default='20,0,2000,100,-2,2',help='Res.  plot bounds, "nbins1,Aeffmin,Aeffmax,nbins2,dtmin,dtmax"')
    parser.add_argument('--ab',             action='store',         default='100,0,2000',        help='Aeff  plot bounds, "nbins,Aeffmin,Aeffmax"')

    parser.add_argument('--am', '--ampmax' ,action='store',         default='0',                 help='Amp_max lower bound, used for cuts ')
    parser.add_argument('--da', '--dampl'  ,action='store',         default='5000',              help='dampl cut, max allowed difference in fit_ampl between xtals')
    parser.add_argument('--pc', '--poscut' ,action='store',         default='3',                 help='Position cut, side-length of a square around target center to accept')
    parser.add_argument('--lc', '--lincorr',action='store_true',    default=False,               help='Use a linear correction to counter the "walking mean" effect')

    args = parser.parse_args()

    if   (args.freq == '160') or (args.freq == '160MHz'): args.freq = '160MHz'      # Ensures consistent formatting 
    elif (args.freq == '120') or (args.freq == '120MHz'): args.freq = '120MHz'      # IE does the user enter '120', or '120MHz'?
    if   (args.temp == '18' ) or (args.temp == '18deg' ): args.temp = '18deg'       # Resolve it either way 
    elif (args.temp == '9'  ) or (args.temp == '9deg'  ): args.temp = '9deg'        # blahblah licht mehr licht

    if len(sys.argv[1:])==0:                                                        # Print help if no options given    
        parser.print_help()
        sys.exit("\n")

    return args

def main():
    ## Stats box parameters
    #gStyle.SetOptStat(0)                               # No stat box 
    gStyle.SetStatY(0.9)                                # Y-position (fraction of pad size)                
    gStyle.SetStatX(0.9)                                # X-position         
    gStyle.SetStatW(0.2)                                # Width           
    gStyle.SetStatH(0.1)                                # Height
    gROOT.SetBatch(kTRUE)                               # Don't show graphics 
    gROOT.ProcessLine("gErrorIgnoreLevel = kError;")    # Surpress info messages below Error or Fatal levels (IE info or warning)

    args = input_arguments()

    ## Class for defining save path and finding analysis files. Also has "save_files" fn   
    ft        = FileTools.FileTools(args)                        
    savepath  = ft.output_location()
    Files     = ft.analysis_path()
    for f in Files:
        print "\n","#"*int(os.popen('stty size', 'r').read().split()[1]) # print a line of ###'s, aesethetic
        print "File:", f[0]
        
        at    = AnalysisTools(args, savepath, f)        # Class with tools for analysis. Mainly adjustments
        pt    = PlotterTools(args, savepath, f)         # Class with tools for plotting
        Cuts  = pt.define_cuts()                        # Get the cuts for the relevant plots, flagged in args
        Plots = pt.define_plots()                       # Get what plots are desired, flagged in args
    
        for i in xrange(len(Plots)):                    # For each plot of interest
                
                print "\n","#"*int(os.popen('stty size', 'r').read().split()[1]) # print a line of ###'s, aesethetic

                cut = Cuts[i]                           # Cuts for the current plot of interest
                p   = Plots[i]                          # Plotting info, what to plot, what bounds, etcetc

                tfile = TFile(f[0])
                tree  = tfile.Get("h4")
                c0    = TCanvas('c0', 'c0', 900, 600)

                if len(p)==5:   # -x and -a options are for TH1F, and require 5 params 

                    # Create the desired plot
                    h = TH1F('h', f[1]+'_'+p[1], p[2], p[3], p[4])  
                    tree.Draw(p[0]+'>>h')
                    nentries_precut  = int(h.GetEntries()) 
                    tree.Draw(p[0]+'>>h', TCut(cut))
                    nentries_postcut = int(h.GetEntries()) 
                    
                    h.GetXaxis().SetTitle(p[1])
                    print
                    print "Number of entries pre-cuts: ", nentries_precut
                    print "Number of entries post-cuts:", nentries_postcut
                    print

                    # Save plots
                    ft.save_files(h, savepath, f[1], '_'+p[1])

                if len(p)==8:   # -s is for a TH2F and requires 8 params
                    
                    # Use a linear adjustment to account for the "walking-mean" effect resulting from largely uneven Aeff's
                    if args.lc == True: p[0] = at.dt_linear_correction(tree,cut)

                    # Create the color map
                    hh = pt.make_color_map(p,'',tree)
                    tree.Draw(p[0]+">>hh", "", "COLZ")
                    nentries_precut   = int(hh.GetEntries())
                    hh = pt.make_color_map(p, cut, tree)
                    tree.Draw(p[0]+">>hh", TCut(cut), "COLZ")
                    nentries_postcut  = int(hh.GetEntries())    

                    print
                    print "Number of entries pre-cuts:", nentries_precut
                    print "Number of entries post-cuts: {} \t {:5.2f}% efficiency ".format(nentries_postcut, 100.*nentries_postcut/nentries_precut)
                    with open(savepath+f[1].split('_')[-1]+'_log.txt', 'a') as logfile:
                        logfile.write("\nNumber of entries ( hh.GetEntries() ):\n\tpre-cuts:\n")
                        logfile.write("\t\t" + str(nentries_precut)  + '\n')    
                        logfile.write("\t\t" + str(nentries_postcut) + '\n')

                    # Create the resolution versus Aeff plot
                    hh_2 = at.fit_y_slices(hh)[1]
                    hh_2.SetTitle(f[1]+'_dt_resolution_vs_aeff')                    
                    hh_2.Draw()
                    
                    hh_2 = at.adjust_bin_centers(hh_2)

                    # Fit the plot using a user defined function
                    if args.fit == True: at.fit_resolution(hh_2)

                    # Save plots
                    print
                    ft.save_files(hh,   savepath, f[1], '_dt_vs_aeff_heatmap')
                    ft.save_files(hh_2, savepath, f[1], '_resolution_vs_aeff')
        

if __name__ == "__main__":
    main()
