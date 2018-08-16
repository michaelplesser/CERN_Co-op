#!/usr/bin/python

## By Michael Plesser

import os
import sys
import argparse
from ROOT import *
from array import array
from utilities import PlotterTools

def input_arguments():
	parser = argparse.ArgumentParser(description='Control plotting and cuts for inter-crystal time resolution studies')
	
	parser.add_argument('-d'  ,    type=str,            						help='Use all the files in the given directory for analysis ')
	parser.add_argument('-f'  ,    type=str,            						help='Use the given file for analysis(use the absolute path)')
	parser.add_argument('-e'  ,    type=str,            						help='Energy to use for analysis (IE "250GeV" or "compiled")')
	parser.add_argument('--freq',  type=str, 		 	default='160MHz',		help='Sampling frequency,   IE "160MHz" or "120 MHz"')
	parser.add_argument('--temp',  type=str, 		 	default='18deg' ,		help='Sampling temperature, IE "18deg"  or "9deg"')
	
	parser.add_argument('-x'  , 	 	 action='store_true', 					help='Create plots for fit_chi2[C3] and fit_chi2[<2nd xtal>]')
	parser.add_argument('-a'  , 	 	 action='store_true', 					help='Create effective voltage (Aeff) plot')
	parser.add_argument('-s'  , 	 	 action='store_true', 					help='Create resolution versus  Aeff  plot')
	
	parser.add_argument('-q'   ,     	 action='store_true', 					help='Use a quantile method for the resolution versus Aeff plot')
	parser.add_argument('--fit', 	 	 action='store_true', 					help='Fit using a user function the resolution versus Aeff plot')

	parser.add_argument('--xb',  	 	 action='store', 	default='100,-5,1000',		help='Chi2 plot bounds,  "nbins,chi2min,chi2max"')
	parser.add_argument('--sb', 	 	 action='store',	default='100,0,2300,100,-2,2',	help='Sigma plot bounds, "nbins1,Aeffmin,Aeffmax,nbins2,dtmin,dtmax"')
	parser.add_argument('--ab',  	 	 action='store', 	default='100,0,2300',		help='Aeff plot bounds,  "nbins,Aeffmin,Aeffmax"')

	parser.add_argument('--xc', '--chicuts', action='store',	default='1,100,1,100',		help='Chi squared cuts, "lb1,ub1,lb2,ub2"')
	parser.add_argument('--am', '--ampmax' , action='store',	default=1,			help='Amp_max lower bound, used for cuts ')
	parser.add_argument('--da', 		 action='store',	default=5000, 			help='dampl cut, max allowed difference in fit_ampl between xtals')
	parser.add_argument('--pc', '--poscut' , action='store',	default=3, 			help='Position cut, how large an area around target center to accept')
	parser.add_argument('--lc',  		 action='store_true', 	default=False,			help='Use a linear correction to counter the "walking mean" effect')

	if len(sys.argv[1:])==0: 	# Print help if no options given	
		parser.print_help()
		sys.exit("\n")

	return parser.parse_args()

def main():
	## Stats box parameters
	#gStyle.SetOptStat(0)	# No stat box 
	gStyle.SetStatY(0.9)	# Y-position (fraction of pad size)                
	gStyle.SetStatX(0.9)	# X-position         
	gStyle.SetStatW(0.2)	# Width           
	gStyle.SetStatH(0.1)	# Height
	gROOT.SetBatch(kTRUE)	# Don't show graphics 

	gROOT.ProcessLine("gErrorIgnoreLevel = kError;") # Surpress info messages below Error or Fatal levels (IE info or warning)

	args = input_arguments()
	pt = PlotterTools(args)
	
	print
	savepath  = pt.output_location()
	Files     = pt.analysis_path()
	for fi,f in enumerate(Files):	# For each file (fi is a file number)

		Cuts  = pt.define_cuts( f[0]) 	 # Get the cuts for the relevant plots, flagged in args
		Plots = pt.define_plots(f[0]) 	 # Get what plots are desired, flagged in args
		for i in xrange(len(Plots)):	 # For each plot of interest, set in PlotterTools.py			
				
				print "\n","#"*int(os.popen('stty size', 'r').read().split()[1]) # print a line of ###'s, aesethetic
				print "File:", f[0],"\n"

				cut = Cuts[i]	 	# Cuts for the current plot of interest
				p   = Plots[i]	 	# Plotting info, what to plot, what bounds, etcetc

				tfile = TFile(f[0])
				tree  = tfile.Get("h4")
				c0 = TCanvas('c0', 'c0', 900, 600)

				if len(p)==5:	# -x and -a options are for TH1F, and require 5 params 

					# Create the desired plot
					hname = f[1] +'_'+str(fi) 
					h     = TH1F(hname, f[1]+'_'+p[1], p[2], p[3], p[4])	
					tree.Draw(p[0]+'>>'+hname, TCut(cut))
					h.GetXaxis().SetTitle(p[1])
					print "\nNumber of entries post-cuts:", int(h.GetEntries())

					# Save plots
					pt.save_files(h, savepath, f[1], '_'+p[1])


				if len(p)==8:	# -s is for a TH2F and requires 8 params
					
					# Use a linear adjustment to account for the "walking-mean" effect resulting from largely uneven Aeff's
					if args.lc == True: p[0] = pt.dt_adjustment(f[0],tree,cut)

					# Create the color map
					hh = pt.make_color_map(f, p, cut, tree)	
					tree.Draw(p[0]+">>hh", TCut(cut), "COLZ")

					print "\nNumber of entries post-cuts:", int(hh.GetEntries())
					
					# Create the resolution versus Aeff plot
					hh.FitSlicesY()
					hh_2 = gDirectory.Get("hh_2")
					hh_2.SetTitle(f[1]+'_dt_resolution_vs_aeff')					
					hh_2.Draw()

					# Fit the plot using a user defined function
					if args.fit == True: 
						pt.fit_resolution(hh_2, f[0])
						gStyle.SetOptFit(1)		# Include fit parameters in the stats box
						gPad.Update()

					# Save plots
					print
					pt.save_files(hh,   savepath, f[1], '_dt_vs_aeff_heatmap')
					pt.save_files(hh_2, savepath, f[1], '_resolution_vs_aeff')
		


if __name__ == "__main__":
	main()
