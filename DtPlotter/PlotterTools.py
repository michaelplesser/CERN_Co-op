## Michael Plesser
## Last revised: July 17 2018

from ROOT import *
from array import array
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
		os.mkdir(savepath + "images/")
		os.mkdir(savepath + "root_files/")
	return savepath



## Define location of files to be analyzed
def analysis_path(args):
	Files = []		# Filled with format [ ["name", "<energy> <position>"], ...], and assumes the filename is of form <blablabla>_energy_position.root
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
				if args.e is not None:	# Energy is specified, only adds files with that energy
					if file.split('_')[-2]==args.e:
						Files.append( [analysispath + file, file.split('_')[-2]+'_'+file.split('_')[-1].split('.')[0]] )
						print "Found file: ", analysispath + file
				else:			# Add all files in analysispath
					Files.append( [analysispath + file, file.split('_')[-2]+'_'+file.split('_')[-1].split('.')[0]] )
					print "Found file: ", analysispath + file

	return Files



## Get crystal pair from Position (c3_down = ['C3', 'C2'], C3_up = ['C3', 'C4'])
def get_xtals(filei):
	tfile = TFile(filei)
	infotree = tfile.Get("info")
	infotree.GetEntry(0)
	position = infotree.Positions
	if   position == 2.5:
		return ['C3', 'C2']
	elif position == 3.5:
		return ['C3', 'C4']
	else:
		sys.exit("\nUnrecognized crystal position, aborting...")



## Get the amplitude calibration coefficient
def amp_coeff(xtal):
	if   xtal[1] == 'C4':   amp_calibration = 0.944866
	elif xtal[1] == 'C2':	amp_calibration = 0.866062
	return str(amp_calibration)



## Find the center of the target
def find_center(filei):
	t_file  = TFile(filei)
	t_tree  = t_file.Get("h4")
	hx = TH1F("hx", "", 50, -20, 20)
	hy = TH1F("hy", "", 50, -20, 20)
	t_tree.Draw("X[0]>>hx")
	t_tree.Draw("Y[0]>>hy")
	x_mean = hx.GetMean()
	y_mean = hy.GetMean()
	return str(x_mean), str(y_mean)



## Calculate uneven bin widths to get the same number of events in each, "quantiles"
def find_quantiles(p,cut,tree):
	Aeff 	 = p[0].split(':')[-1]
	aeff_tmp = TH1F('aeff',"", 100, p[3], p[4])	# Creates a temporary histogram to find the quantiles
	tree.Draw(Aeff+'>>aeff', TCut(cut))
	nquants = p[2]+1							# n_quantiles = nbins + 1
	probs = array('d', [x/(nquants-1.) for x in range(0, nquants)])		# Quantile proportions array
	quantiles = array('d', [0 for x in range(0, nquants)])			# Bin edges, initialized as all 0's
	aeff_tmp.GetQuantiles(nquants, quantiles, probs)			# Overwrites quantiles with bin edges positions
	
	return quantiles



## Cuts to selection
def define_cuts(filei, args):
	Cts          = []
	xtal 	     = get_xtals(filei)
	ampbias      = amp_coeff(xtal)

	x_center, y_center = find_center(filei)

	pos_val      = "5"
	dampl_val    = "100"

	fiber_cut    = "fabs(nFibresOnX[0]-2)<2 && fabs(nFibresOnY[0]-2)<2"
	clock_cut    = "time_maximum[" +xtal[0]+"]==time_maximum["+xtal[1]+"]"
	position_cut = "(fabs(X[0]-"+x_center+")<"+pos_val+") && (fabs(Y[0]-"+y_center+")<"+pos_val+")"
	dampl_cut    = "fabs(fit_ampl["+xtal[0]+"]-"+ampbias+"*fit_ampl["+xtal[1]+"] )<"+dampl_val

	chi2_bounds  = [[1, 100],[1,100]]	# chi2 bounds for [[C3],[C2/4]]
	if args.chicuts is not None:
		chicuts = args.chicuts.split(',')
		chi2_bounds = [ [int(chicuts[0]), int(chicuts[1])], [int(chicuts[2]), int(chicuts[3])] ]
	chi2_cut  = "fit_chi2["+xtal[0]+"]<"+str(chi2_bounds[0][1])+" && fit_chi2["+xtal[0]+"]>"+str(chi2_bounds[0][0])+" && "
	chi2_cut += "fit_chi2["+xtal[1]+"]<"+str(chi2_bounds[1][1])+" && fit_chi2["+xtal[1]+"]>"+str(chi2_bounds[1][0])
	
	amp_max = "0"
	if args.ampmax is not None:
		amp_max = str(args.ampmax) 
	amp_cut = "amp_max[" + xtal[0] + "]>" + amp_max + " && " + ampbias + "*amp_max[" + xtal[1] + "]>" + amp_max 

	Aeff = "fit_ampl["+xtal[0]+"]*" + ampbias + "*fit_ampl["+xtal[1]+"] /  pow( pow(fit_ampl["+xtal[0]+"],2)+pow(" + ampbias + "*fit_ampl["+xtal[1]+"],2) , 0.5)"

	if args.x is not False:
		# Chi2 cuts
		Cts.append( fiber_cut + " && " + clock_cut + " && " + position_cut )
		Cts.append( fiber_cut + " && " + clock_cut + " && " + position_cut )

	if args.dt is not False:	
		# Dt cuts
		Cts.append( fiber_cut + " && " + clock_cut + " && " + position_cut + " && " + chi2_cut + " && " + amp_cut )

	if args.a is not False:	
		# Aeff cuts
		Cts.append( fiber_cut + " && " + clock_cut + " && " + position_cut )	

	if args.s is not False:	
		# sigma cuts
		Cts.append( fiber_cut + " && " + clock_cut + " && " + position_cut + " && " + chi2_cut + " && " + amp_cut + " && " + dampl_cut )

	return Cts



## Plots to be created
def define_plots(filei, args):
	Plts 	= []
	xtal	= get_xtals(filei)
	ampbias = amp_coeff(xtal)
	Aeff 	= "fit_ampl["+xtal[0]+"]*" + ampbias + "*fit_ampl["+xtal[1]+"] /  pow( pow(fit_ampl["+xtal[0]+"],2)+pow(" + ampbias + "*fit_ampl["+xtal[1]+"],2) , 0.5)"
	
	if args.x is not False:
		# Chi2 bounds
		bins  = [100, -5, 800]	
		Plts.append(["fit_chi2["+xtal[0]+"]", "Fit_Chi2_"+xtal[0], bins[0], bins[1], bins[2]])
		Plts.append(["fit_chi2["+xtal[1]+"]", "Fit_Chi2_"+xtal[1], bins[0], bins[1], bins[2]])

	if args.dt is not False:
		# Dt bounds
		bins  = [40, -1, 0]
		Plts.append(["fit_time["+xtal[0]+"]-fit_time["+xtal[1]+"]", "intercrystal_time_difference", bins[0], bins[1], bins[2]])

	if args.a is not False:	
		# Aeff bounds
		bins  = [100, 0, 3500]		
		if args.ab is not None:
			abounds = args.ab.split(',')
			bins    = [ int(abounds[0]), int(abounds[1]), int(abounds[2]) ]

		Plts.append([Aeff, "aeff_response", bins[0], bins[1], bins[2]])

	if args.s is not False:
		# Sigma vs Aeff bounds
		bins  = [7, 100, 3500, 300, -2, 2]
		if args.sb is not None:
			sigbounds = args.sb.split(',')
			bins    = [ int(sigbounds[0]), int(sigbounds[1]), int(sigbounds[2]), int(sigbounds[3]), int(sigbounds[4]), int(sigbounds[5]) ]

		Plts.append(["fit_time["+xtal[0]+"]-fit_time["+xtal[1]+"]:" + Aeff+"/b_rms", "resolution_vs_aeff", bins[0], bins[1], bins[2], bins[3], bins[4], bins[5]])

	return Plts
