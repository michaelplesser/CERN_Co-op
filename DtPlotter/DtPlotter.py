## Michael Plesser
## Last revised: July 12 2018

from PlotterTools import * # Almost all user-level parameters not set by args are set from PlotterTools.py, go there first
from ROOT import *
import argparse

def input_arguments():
	parser = argparse.ArgumentParser(description='Control plotting and cuts for inter-crystal time resolution studies')
	parser.add_argument('-x'  , action='store_true', help='Create plots for fit_chi2[C3]')
	parser.add_argument('--dt', action='store_true', help='Create plots for fit_time[C3] - fit_time[<other xtal>]')
	parser.add_argument('-d'  , type=str,            help='Use all files in this directory for analysis')
	parser.add_argument('-f'  , type=str,            help='Use this file for analysis(use full path!)')
	args = parser.parse_args()
	return parser.parse_args()

def main():
	## Stats box parameters
	#gStyle.SetOptStat(0)	# No stats box 
	gStyle.SetStatY(0.9)	# Y-position (fraction of pad size)                
	gStyle.SetStatX(0.9)	# X-position         
	gStyle.SetStatW(0.2)	# Width           
	gStyle.SetStatH(0.1)	# Height
	gROOT.SetBatch(kTRUE)	# Don't show graphics 
	
	args = input_arguments()

	savepath  = output_location()
	Files     = analysis_path(args)
	for fi,f in enumerate(Files):	# For each file (fi is a file number)
		Cuts  = define_cuts( f[0], args)
		Plots = define_plots(f[0], args)  # Get what plots are desired, set in PlotterTools.py
		for i in xrange(len(Plots)):	# For each plot of interest, set in PlotterTools.py			
				cut = Cuts[i]	# Cuts for the current plot of interest
				p   = Plots[i]	# For all things to plot. Each element in Plots has <=5 elements

				c0 = TCanvas('c0', 'c0', 800, 600)
				plot_title =  f[1] + '_' + p[1]
				file_title =  f[1] + '_' + p[1]

				tfile = TFile(f[0])
				tree  = tfile.Get("h4")
				hname = f[1] +'_'+str(fi)		# Statsbox title 
				h = TH1F(hname, plot_title, p[2], p[3], p[4])
				tree.Draw(p[0]+'>>'+hname, TCut(cut))
				h.GetXaxis().SetTitle(p[1])
		
				c0.SaveAs(savepath + file_title + '.png')

if __name__ == "__main__":
	main()
