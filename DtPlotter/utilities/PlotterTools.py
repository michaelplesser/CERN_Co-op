#!/usr/bin/python

## By Michael Plesser

import os	
import sys
import numpy as np
from ROOT import *
from array import array

class PlotterTools:

	def __init__(self, args):
		self.args = args

		self.file    = self.args.f
		self.dir     = self.args.d
		self.energy  = self.args.e

		self.chi2    = self.args.x
		self.aeff    = self.args.a
		self.res     = self.args.s

		self.quant   = self.args.q
		self.fit     = self.args.fit

		self.xbins   = self.args.xb
		self.sbins   = self.args.sb
		self.abins   = self.args.ab

		self.chicuts = self.args.xc
		self.ampmax  = self.args.am
		self.dampcut = self.args.da
		self.poscut  = self.args.pc
		
		self.freq    = self.args.freq
		self.temp    = self.args.temp

		self.defaultanalysispath = "/eos/user/m/mplesser/timing_resolution/batch_ntuples/ECAL_H4_June2018_"+self.freq+"_"+self.temp+"_EScan_edges/compiled_roots/"

	## Output location for plots
	def output_location(self):
		savepath = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','plots'))+'/' 	# In the same directory as DtPlotter.py, save to a /plots/ subdir
		#savepath = '/eos/user/m/mplesser/www/php-plots/tmp/'					# Save to my web eos folder
		if os.path.exists(savepath) == False:							# Creates an output directory if none exists
			os.mkdir(savepath)
		if os.path.exists(savepath+ "/root_files/") == False:					# Creates an output directory if none exists
			os.mkdir(savepath + "/root_files/")
		return savepath



	## Define location of files to be analyzed
	def analysis_path(self):
		Files = []									# Format: [ ["name", "<energy>_<position>"], ...]
		energy_position = file.split('_')[-2]+'_'+file.split('_')[-1].split('.')[0]	# Assumes the filename of form <blablabla>_energy_position.root

		if self.file is not None:							# File specified
			file = self.file
			Files.append( [ file, energy_position ] )			
			print "Found file: ", file
			return Files

		if self.dir is not None: analysispath = self.dir				# Directory specified
		else:			 analysispath = self.defaultanalysispath		# Use default directory

		for file in os.listdir(analysispath):
			if file.endswith('.root'):
				if self.energy is not None:					# Energy specified, only adds files with that energy
					if file.split('_')[-2]==self.energy:
						Files.append( [ analysispath + file, energy_position ] )
						print "Found file: ", analysispath + file
				else:								# Add all root files in analysispath
					Files.append( [ analysispath + file, energy_position ] )
					print "Found file: ", analysispath + file

		return Files



	## Save a .root of the given TObject
	def save_files(self, h, path, file_title, name_tag):
		root_savefile = TFile(path + "root_files/" + file_title + name_tag + ".root", "recreate")
		root_savefile.cd()				
		h.Write()
		print  "Saved file:", path + "root_files/" + file_title + name_tag + '.root'



	## Get crystal pair from Position (c3_down = ['C3', 'C2'], C3_up = ['C3', 'C4'])
	def get_xtals(self, filei):
		tfile = TFile(filei)
		infotree = tfile.Get("info")
		infotree.GetEntry(0)
		position = infotree.Positions
		if   position == 2.5:	return ['C3', 'C2', 'C3down']
		elif position == 3.5:	return ['C3', 'C4', 'C3up'  ]
		else:	sys.exit("\nUnrecognized crystal position, aborting...")



	## Get the amplitude calibration coefficient
	def amp_coeff(self, xtal):
		if   self.freq == '160MHz':
			if   xtal[1] == 'C4':   amp_calibration = 0.944866 
			elif xtal[1] == 'C2':	amp_calibration = 0.866062 
		elif self.freq == '120MHz':
			if   xtal[1] == 'C4':   amp_calibration = 0.948113 
			elif xtal[1] == 'C2':	amp_calibration = 0.869192 

		return str(amp_calibration)



	## Find the center of the target
	def find_center(self, filei):	
		xtal 	     = self.get_xtals(filei)
		ampbias      = self.amp_coeff(xtal)
		
		t_file  = TFile(filei)
		t_tree  = t_file.Get("h4")
		hx = TH1F("hx", "", 50, -20, 20)
		hy = TH2F("hy", "", 100, 2, 7, 100,0,10)	
		
		# x mean found by averaging the Hodo.X[0] plot. Valid since amplitudes are basically independent of X
		t_tree.Draw("X[0]>>hx")
		x_mean = hx.GetMean()

		# For y mean, the crystal edge is found by locating where the fit_ampl's of the two xtals are equal (ratio==1)
		t_tree.Draw("fit_ampl[{}]/({}*fit_ampl[{}]):Y[0]>>hy".format(xtal[0], ampbias, xtal[1]), "{}*fit_ampl[{}]>100".format(ampbias, xtal[1]))
		poly2 = TF1("poly2", "pol2", 2, 7) # Fit the plot, pol2 works well enough in general, but is not physically justified
		poly2.SetParameter(0,5)	
		poly2.SetParameter(1,-1)
		poly2.SetParameter(2,0.1)
		hy.Fit("poly2", "qR")
		p0   = float(poly2.GetParameter(0))-1.		# Subtract one because we want to solve p2*x^2 + p1*x + p0 = 1
		p1   = float(poly2.GetParameter(1))
		p2   = float(poly2.GetParameter(2))
		yplus  = (-p1+pow(p1*p1-4*p0*p2, 0.5))/(2*p2)	# Quadratic formula gives two solutions
		yminus = (-p1-pow(p1*p1-4*p0*p2, 0.5))/(2*p2) 	# Quadratic formula gives two solutions
		ypluslogic  = yplus  > 2 and yplus  < 7		# Checks if yplus  is in the expected range
		yminuslogic = yminus > 2 and yminus < 7		# Checks if yminus is in the expected range

		if   ypluslogic and yminuslogic: sys.exit("Error!!! Y_center fitting gave two solutions in the range! Aborting... \n")
		elif ypluslogic:  y_mean = yplus	
		elif yminuslogic: y_mean = yminus	
		else: sys.exit("Error!!! Y_center fitting gave no solutions in the range! Aborting... \n")	
	
		return str(x_mean), str(y_mean)



	## Make the dt vs aeff color map, and use quantiles if so directed
	def make_color_map(self, f, p, cut, tree):
		if self.quant == True:	 								# Use quantiles
			Aeff 	 = p[0].split(':')[-1]
			aeff_tmp = TH1F('aeff',"", 100, p[3], p[4])					# Creates a temporary histogram to find the quantiles
			tree.Draw(Aeff+'>>aeff', TCut(cut))
			nquants = p[2]+1								# n_quantiles = nbins + 1
			probs = array('d', [x/(nquants-1.) for x in range(0, nquants)])			# Quantile proportions array
			quantiles = array('d', [0 for x in range(0, nquants)])				# Bin edges, initialized as all 0's
			aeff_tmp.GetQuantiles(nquants, quantiles, probs)				# Overwrites 'quantiles' with bin edges positions
			hh = TH2F('hh', f[1]+'_dt_vs_aeff_heatmap', p[2], quantiles , p[5], p[6], p[7])	# Return a TH2F with quantile binning
		else:											# Use fixed width bins
			hh = TH2F('hh', f[1]+'_dt_vs_aeff_heatmap', p[2], p[3], p[4], p[5], p[6], p[7])	# Return a TH2F with fixed-width binning	

		return hh



	## Adjust dT using a linear fit, to correct "mean walking" location effects in the deposition
	def dt_adjustment(self, filei, tree, cut):
		xtal 	     = self.get_xtals(filei)
		ampbias      = self.amp_coeff(xtal)

		Aeff  = "fit_ampl[{}]*{}*fit_ampl[{}] /  pow( pow(fit_ampl[{}],2)+pow({}*fit_ampl[{}],2) , 0.5)/b_rms".format(xtal[0],ampbias,xtal[1],xtal[0],ampbias,xtal[1])
		dt    = "fit_time[{}]-fit_time[{}]".format(xtal[0],xtal[1])
		dampl = "fit_ampl[{}]-{}*fit_ampl[{}]".format(xtal[0],ampbias,xtal[1])

		hadjust = TH2F('hadjust', '', 15, -1500, 1500, 100, -2, 2)
		tree.Draw(dt+":"+dampl+">>hadjust", TCut(cut), "COLZ")
		hadjust.FitSlicesY()
		hadjust_1 = gDirectory.Get("hadjust_1")		# Plot dt distribution means versus difference vs crystal amplitudes
		hadjust_1.Draw()

		poly1 = TF1("poly1", "pol1", -1500, 1500)	# Fit linearly
		poly1.SetParameter(0,0.5)	
		poly1.SetParameter(1,0.00001)
		hadjust_1.Fit("poly1", "qR")
		dt0   = str(poly1.GetParameter(0))	
		slope = str(poly1.GetParameter(1))
		chi2  = str(hadjust_1.Chisquare(poly1))
		
		# Some info for the log file		
		with open(self.output_location()+xtal[2]+'_log.txt', 'a') as f:
			f.write("\nDt adjustment parameters:\n")
			f.write("\tslope: \t\t"+slope+"\n\ty-intercept: \t"+dt0+'\n\tchi2: \t\t'+chi2+'\n')
		print "Dt adjustment parameters: slope =", slope, ", y-intercept =", dt0, ", chi2:", chi2

		adjusted_plot = "(fit_time[{}]-fit_time[{}])-({}*({})):{}".format(xtal[0],xtal[1],slope,dampl,Aeff)
		return adjusted_plot



	## Fit the resolution vs Aeff using a user-defined function
	def fit_resolution(self, histo, filei):
		xtal = self.get_xtals(filei)		
		def userfit(x,par):
			if x[0]>0:
				fit = pow(pow(par[0]/(x[0]),2)+2*pow(par[1],2), 0.5)								
				return fit
		userfit = TF1('userfit', userfit, 100, 2000, 2)	
		userfit.SetParameters(10, 0.1)			# Set a guess for the parameters
		userfit.SetParNames("N", "c")			# Name the parameters
		histo.Fit("userfit", 'qR')			# Fit the data
		cterm = userfit.GetParameter("c")
		print "Constant term from the resolution fitting: ", 1000*cterm, "ps"

		# Some info for the log file
		with open(self.output_location()+xtal[2]+'_log.txt', 'a') as f:
			f.write("\nResolution fitting parameters:\n")
			f.write("\tConstant term: \t"+str(cterm)+" ns\n\tN term: \t"+str(userfit.GetParameter("N"))+'\n\n')



	## Cuts to selection
	def define_cuts(self, filei):
		Cts          = []
		xtal 	     = self.get_xtals(filei)
		ampbias      = self.amp_coeff(xtal)

		x_center, y_center = self.find_center(filei)

		fiber_cut    = "fabs(nFibresOnX[0]-2)<1 && fabs(nFibresOnY[0]-2)<1"
		clock_cut    = "time_maximum[{}]==time_maximum[{}]".format(xtal[0],xtal[1])
		position_cut = "(fabs(X[0]-{})<{}) && (fabs(Y[0]-{})<{})".format(x_center, self.poscut, y_center, self.poscut)
		amp_cut      = "amp_max[{}]>{} && {}*amp_max[{}]>{}".format(xtal[0],str(self.ampmax),ampbias,xtal[1],str(self.ampmax))
		dampl_cut    = "fabs(fit_ampl[{}]-{}*fit_ampl[{}] )<{}".format(xtal[0], ampbias, xtal[1], self.dampcut)

		chicuts     = self.chicuts.split(',')
		chi2_bounds = [ [int(chicuts[0]), int(chicuts[1])], [int(chicuts[2]), int(chicuts[3])] ]
		chi2_cut  = "fit_chi2[{}]<{} && fit_chi2[{}]>{} && ".format(xtal[0],chi2_bounds[0][1],xtal[0],chi2_bounds[0][0])
		chi2_cut += "fit_chi2[{}]<{} && fit_chi2[{}]>{}    ".format(xtal[1],chi2_bounds[1][1],xtal[1],chi2_bounds[1][0])

		if self.chi2 is not False:	# Chi2 cuts				
			Cts.append( fiber_cut + " && " + clock_cut + " && " + position_cut )
			Cts.append( fiber_cut + " && " + clock_cut + " && " + position_cut )

		if self.aeff is not False:	# Aeff cuts
			Cts.append( fiber_cut + " && " + clock_cut + " && " + position_cut + " && " + amp_cut + " && " + dampl_cut )	

		if self.res is not False:	# Resolution cuts
			Cts.append( fiber_cut + " && " + clock_cut + " && " + position_cut + " && " + amp_cut + " && " + dampl_cut + " && " + chi2_cut )


		# Write some info to a logfile
		with open(self.output_location()+xtal[2]+'_log.txt', 'w') as f:
			f.write("Args: \n\t"+str(self.args)+'\n\n')
			f.write("Plots specified (in order): \n")
			if self.chi2 is not False: f.write("\tChi2 for {}\n\tChi2 for {}\n".format(xtal[0], xtal[1]))
			if self.aeff is not False: f.write("\tAeff\n")
			if self.res  is not False: f.write("\tTime resolution vs Aeff/b_rms\n")
			f.write("\nCuts applied: \n")
			for i in range(len(Cts)): f.write('\t'+Cts[i]+'\n')

		return Cts



	## Plots to be created
	def define_plots(self, filei):
		Plts 	= []
		xtal	= self.get_xtals(filei)
		ampbias = self.amp_coeff(xtal)
		Aeff    = "fit_ampl[{}]*{}*fit_ampl[{}] /  pow( pow(fit_ampl[{}],2)+pow({}*fit_ampl[{}],2) , 0.5)/b_rms".format(xtal[0],ampbias,xtal[1],xtal[0],ampbias,xtal[1])
	
		if self.chi2 is not False:
			# Chi2 bounds
			chi2bounds = self.xbins.split(',')
			bins       = [ int(chi2bounds[0]), int(chi2bounds[1]), int(chi2bounds[2]) ]
			Plts.append(["fit_chi2["+xtal[0]+"]", "Fit_Chi2_"+xtal[0], bins[0], bins[1], bins[2]])
			Plts.append(["fit_chi2["+xtal[1]+"]", "Fit_Chi2_"+xtal[1], bins[0], bins[1], bins[2]])

		if self.aeff is not False:	
			# Aeff bounds
			abounds = self.abins.split(',')
			bins    = [ int(abounds[0]), int(abounds[1]), int(abounds[2]) ]
			Plts.append([Aeff, "aeff_response", bins[0], bins[1], bins[2]])

		if self.res is not False:
			# Sigma vs Aeff bounds
			sigbounds = self.sbins.split(',')
			bins      = [ int(sigbounds[0]), int(sigbounds[1]), int(sigbounds[2]), int(sigbounds[3]), int(sigbounds[4]), int(sigbounds[5]) ]
			Plts.append(["fit_time[{}]-fit_time[{}]:{}".format(xtal[0],xtal[1],Aeff), "resolution_vs_aeff", bins[0], bins[1], bins[2], bins[3], bins[4], bins[5]])

		return Plts
