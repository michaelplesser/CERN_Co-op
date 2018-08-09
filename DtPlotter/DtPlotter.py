## Michael Plesser
## Last revised: July 30 2018

from PlotterTools import *
from array import array
from ROOT import *
import argparse


def input_arguments():
	parser = argparse.ArgumentParser(description='Control plotting and cuts for inter-crystal time resolution studies')
	
	parser.add_argument('-d'  , 	 type=str,            help='Use all the files in the given directory for analysis ')
	parser.add_argument('-f'  , 	 type=str,            help='Use the given file for analysis(use the absolute path)')
	parser.add_argument('-e'  , 	 type=str,            help='Energy of files to use for analysis (IE "250GeV")')
	
	parser.add_argument('-x'  , 	 action='store_true', help='Create plots for fit_chi2[C3] and fit_chi2[<other xtal>]')
	parser.add_argument('-a'  , 	 action='store_true', help='Create effective voltage (Aeff) plot')
	parser.add_argument('-s'  , 	 action='store_true', help='Create resolution versus  Aeff  plot')

	parser.add_argument('-q'   ,     action='store_true', help='Use a quantile method for the resolution versus Aeff plot')
	parser.add_argument('--fit', 	 action='store_true', help='Fit using a user function the resolution versus Aeff plot')

	parser.add_argument('--sb',  	 action='store',      help='Sigma plot bounds, "nbins1,Aeffmin,Aeffmax,nbins2,dtmin,dtmax"')
	parser.add_argument('--ab',  	 action='store',      help='Aeff plot bounds,  "nbins,Aeffmin,Aeffmax"')

	parser.add_argument('--chicuts', action='store',      help='Chi squared cuts, "lb1,ub1,lb2,ub2"')
	parser.add_argument('--ampmax' , action='store',      help='Amp_max lower bound, used for cuts')

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

	savepath  = output_location()
	Files     = analysis_path(args)
	for fi,f in enumerate(Files):	# For each file (fi is a file number)
		Cuts  = define_cuts( f[0], args)  # Get the cuts for the relevant plots, flagged in args
		Plots = define_plots(f[0], args)  # Get what plots are desired, flagged in args
		for i in xrange(len(Plots)):	  # For each plot of interest, set in PlotterTools.py			
				cut = Cuts[i]	  # Cuts for the current plot of interest
				p   = Plots[i]	  # For all things to plot. Each element in Plots has <=5 elements

				plot_title =  f[1] + '_' + p[1]
				file_title =  f[1] + '_' + p[1]
				tfile = TFile(f[0])
				tree  = tfile.Get("h4")
				c0 = TCanvas('c0', 'c0', 900, 600)

				terminalwidth = int(os.popen('stty size', 'r').read().split()[1])

				print "\n","#"*terminalwidth
				print "File:", f[0],"\n"
				if len(p)==5:	# -x and -a options are for TH1F, and require 5 params 

					# Create the desired plot
					hname = f[1] +'_'+str(fi) 
					h = TH1F(hname, plot_title, p[2], p[3], p[4])
												
					tree.Draw(p[0]+'>>'+hname, TCut(cut))

					print "Number of events post-cuts:", int(h.GetEntries())

					h.GetXaxis().SetTitle(p[1])
					c0.SaveAs(savepath + "images/" + file_title + '.png', "update")				# Save a .png of the canvas

					histosavefile = TFile(savepath + "root_files/" + file_title + ".root", "update")
					histosavefile.cd()				
					c0.Write()										# Save the canvas as a .root file

				if len(p)==8:	# -s is for a TH2F and requires 8 params
					
					# Use a linear adjustment to account for the "walking-mean" effect resulting from largely uneven Aeff's
					p[0] = dt_adjustment(f[0],tree,cut)
					
					# Create the heat map
					if args.q == True:	 # Use quantiles
						quantiles = find_quantiles(p,cut,tree)
						hh = TH2F('hh', f[1]+'_dt_vs_aeff_heatmap', p[2], quantiles , p[5], p[6], p[7])
					else:			# Use fixed width bins
						hh = TH2F('hh', f[1]+'_dt_vs_aeff_heatmap', p[2], p[3], p[4], p[5], p[6], p[7])		
					tree.Draw(p[0]+">>hh", TCut(cut), "COLZ")

					print "Number of events post-cuts:", int(hh.GetEntries())

					c0.SaveAs(savepath + "images/" + f[1] + '_dt_vs_aeff_heatmap.png', "update")			# Save a .png of the canvas
					histosavefile = TFile(savepath + "root_files/" + f[1] + '_dt_vs_aeff_heatmap.root', "update")
					histosavefile.cd()				
					c0.Write()											# Save the canvas as a .root file

					# Create the resolution versus Aeff plot
					hh.FitSlicesY()
					hh_2 = gDirectory.Get("hh_2")
					hh_2.SetTitle(f[1]+'_dt_resolution_vs_aeff')					
					hh_2.Draw()

					# Fit the plot using a user defined function
					if args.fit == True:
						def userfit(x,par):
							if x[0]>0:
								fit = pow(pow(par[0]/(x[0]),2)+2*pow(par[1],2), 0.5)								
								return fit
						userfit = TF1('userfit', userfit, 50, 2300, 2)	
						userfit.SetParameters(10, 0.1)			# Set a guess for the parameters
						userfit.SetParNames("N", "c")			# Name the parameters
						hh_2.Fit("userfit", 'qR')			# Fit the data
						cterm = userfit.GetParameter("c")
						print "\nConstant term from the resolution fitting: ", 1000*cterm, "ps\n"
			
					c0.SaveAs(savepath + "images/" + file_title + '.png', "update")					# Save a .png of the canvas
					resosavefile = TFile(savepath + "root_files/" + file_title + ".root", "update")
					resosavefile.cd()				
					c0.Write()											# Save the canvas as a .root file

					hh.Delete()
					del c0

if __name__ == "__main__":
	main()
