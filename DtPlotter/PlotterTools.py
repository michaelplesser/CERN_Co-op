## Michael Plesser
## Last revised: July 12 2018

from ROOT import *
import numpy as np
import sys
import os

## Output location for plots
def output_location():
	if os.getcwd().split('/')[-1] != "DtPlotter":
		sys.exit("Error: Please run from within DtPlotter directory!")
	savepath = os.getcwd() + "/plots/"
	if os.path.exists(savepath) == False:	# Creates an output directory if none exists
		os.mkdir(savepath)
	return savepath

## Define location of files to be analyzed
def analysis_path(args):
	Files = []			# Filled with format [ ["name", "<energy> <position>"], ...], and assumes the filename is of form <blablabla>_energy_position.root

	if args.f is not None:			# File specified
		file = args.f
		Files.append( [file, file.split('_')[-2]+'_'+file.split('_')[-1].split('.')[0]] )			
		print "Found file: ", file
	else:
		if args.d is not None:		# Directory specified
			analysispath = args.d
		else:				# Nothing specified. Use default analysis path
			analysispath = "/eos/user/m/mplesser/timing_resolution/batch_ntuples/ECAL_H4_June2018_160MHz_18deg_EScan_edges/compiled_roots/"

		for file in os.listdir(analysispath):
			if file.endswith('.root'):
				Files.append( [analysispath + file, file.split('_')[-2]+'_'+file.split('_')[-1].split('.')[0]] )
				print "Found file: ", analysispath + file

	return Files

## Get crystal pair from position (c3_down = ['C3', 'C2'], C3_up = ['C3', 'C4'])
def get_xtals(filei):
	tfile = TFile(filei)
	infotree = tfile.Get("info")
	infotree.GetEntry(0)
	position = infotree.Positions
	if position == 2.5:
		return ['C3', 'C2']
	elif position == 3.5:
		return ['C3', 'C4']
	else:
		sys.exit("\nUnrecognized crystal position, aborting...")

## Cuts to selection
def define_cuts(filei, args):
	Cts = []
	
	if args.x is not False:
		# Chi2 cuts
		Cts.append('')
		Cts.append('')

	if args.dt is not False:	
		# Dt cuts
		xtal 	  = get_xtals(filei)
		chi2_lb   = 1	# chi2 lower bound
		chi2_ub   = 200	# chi2 upper bound
		chi2_cut  = "fit_chi2["+xtal[0]+"]<"+str(chi2_ub)+" && fit_chi2["+xtal[0]+"]>"+str(chi2_lb)+" &&"
		chi2_cut += "fit_chi2["+xtal[1]+"]<"+str(chi2_ub)+" && fit_chi2["+xtal[1]+"]>"+str(chi2_lb)
		fiber_cut = "nFibresOnX[0]==2 && nFibresOnY[0]==2"
		clock_cut = "time_maximum["+xtal[0]+"]-time_maximum["+xtal[1]+"]==0"
		#amp_cut   = ""

		Cts.append(clock_cut + " && " + chi2_cut + " && " + fiber_cut)
	return Cts

## Plots to be created (append used for future uses, creating multiple plots)
## [ values to be plotted, plot name, xbins, xmin, xmax]
def define_plots(filei, args):
	Plts = []
	xtal = get_xtals(filei)
	
	if args.x is not False:
		# Chi2 bounds
		xbins  = 100
		xmin   = -5
		xmax   = 1000	
		Plts.append(["fit_chi2["+xtal[0]+"]", "Fit_Chi2_"+xtal[0], xbins, xmin, xmax])
		Plts.append(["fit_chi2["+xtal[1]+"]", "Fit_Chi2_"+xtal[1], xbins, xmin, xmax])

	if args.dt is not False:
		# Dt bounds
		xbins = 100
		xmin  = -5
		xmax  = 5
		Plts.append(["fit_time["+xtal[0]+"]-fit_time["+xtal[1]+"]", "Intercrystal_time_difference", xbins, xmin, xmax])
	return Plts		
