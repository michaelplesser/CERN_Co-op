#!/usr/bin/python

## By Michael Plesser

import os	
import sys
import numpy as np
from ROOT import *
from array import array
from math   import floor, ceil

class PlotterTools:

	def __init__(self, args, savepath, filei):

		## savepath (only used for logfiles)
		self.savepath 	= savepath
		
		## Analysis file
		self.file    	= filei[0]	# Full file with path
		self.file_title = filei[1]	# '<energy>_<position>', IE '25GeV_C3up'

		## Giving args shorter/more informative names
		self.args = args

		self.dir     = self.args.d
		self.energy  = self.args.e

		self.chi2    = self.args.x
		self.a       = self.args.a
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

		## Some internal commonly used function calls
		self.xtal    = self.get_xtals()				# From self.file's 'info' TTree, get which crystals to use
		self.ampbias = self.amp_coeff()				# From self.xtal and self.freq, get calibration coeff.s.
		self.x_center, self.y_center = self.find_center()	# Get the target center (more tricky than you think, check fn comments...)

		## Define Aeff since it is used in many places
		self.Aeff    = "pow( 2 / ( (1/pow(fit_ampl[{}]/b_rms[{}], 2)) + (1/pow({}*fit_ampl[{}]/b_rms[{}],2)) ) , 0.5)".format(self.xtal[0],self.xtal[0],self.ampbias,self.xtal[1],self.xtal[1])		
		## Start a log file
		with open(self.savepath+self.xtal[2]+'_log.txt','w') as f:
			f.write(self.xtal[2]+" "+self.energy+" energy log file\n\n")

	## Get crystal pair from Position (C3_down = ['C3', 'C2'], C3_up = ['C3', 'C4'])
	def get_xtals(self):
		tfile    = TFile(self.file)
		infotree = tfile.Get("info")
		infotree.GetEntry(0)
		position = infotree.Positions
		if   position == 2.5:	return ['C3', 'C2', 'C3down'		]
		elif position == 3.5:	return ['C3', 'C4', 'C3up'  		]
		else:	sys.exit("\nUnrecognized crystal position, aborting...")

	## Get the amplitude calibration coefficient
	def amp_coeff(self):
		if   self.freq == '160MHz':
			if   self.xtal[1] == 'C4':	amp_calibration = 0.944866 
			elif self.xtal[1] == 'C2':	amp_calibration = 0.866062 
		elif self.freq == '120MHz':
			if   self.xtal[1] == 'C4':	amp_calibration = 0.948113 
			elif self.xtal[1] == 'C2':	amp_calibration = 0.869192 

		return str(amp_calibration)
	
	## Find the center of the target
	def find_center(self):	
		
		t_file  = TFile(self.file)
		t_tree  = t_file.Get("h4")
		fit_range = 2,7
		hx = TH1F("hx", "", 50, -20, 20)
		hy = TH2F("hy", "", 100, fit_range[0], fit_range[1], 100,0,10)	# Some what manually tuned... If it fails:
										# Check "dampl:Y[0]", and make sure that y=1 in fit_range
		# x mean found by averaging the Hodo.X[0] plot. Valid since amplitudes are basically independent of X
		t_tree.Draw("X[0]>>hx")
		x_mean = hx.GetMean()

		# For y mean, the crystal edge is found by locating where the fit_ampl's of the two xtals are equal (ratio==1)
		y_var = "fit_ampl[{}]/({}*fit_ampl[{}]):Y[0]>>hy".format(self.xtal[0], self.ampbias, self.xtal[1])
		y_cut = "{}*fit_ampl[{}]>1000".format(self.ampbias, self.xtal[1])
		t_tree.Draw(y_var, y_cut)			# Draw the ratio of the two xtal's amplitudes against Y[0] into 'hy'
		poly2 = TF1("poly2", "pol2", 3, 6) 		# Fit the plot, pol2 works well, but is not physically justified
		poly2.SetParameter(0,5)				# Get the parameters in the right ballpark to start
		poly2.SetParameter(1,-1)
		poly2.SetParameter(2,0.1)
		hy.Fit("poly2", "qR")
		p0   = float(poly2.GetParameter(0))-1.		# Subtract one because we want to solve p2*x^2 + p1*x + p0 = 1
		p1   = float(poly2.GetParameter(1))
		p2   = float(poly2.GetParameter(2))
		
		## Quadratic formula gives two solutions
		yplus  = (-p1+pow(p1*p1-4*p0*p2, 0.5))/(2*p2)
		yminus = (-p1-pow(p1*p1-4*p0*p2, 0.5))/(2*p2)

		ypluslogic  = yplus  > fit_range[0] and yplus  < fit_range[1]		# Checks if yplus  is in the expected range
		yminuslogic = yminus > fit_range[0] and yminus < fit_range[1]		# Checks if yminus is in the expected range
		
		## Check for which quadratic solution is the right one (in fit_range). There should ideally be exactly 1!!!
		if   ypluslogic and yminuslogic	: sys.exit("Error!!! Y_center fitting gave two solutions in the range! Aborting... \n")
		elif ypluslogic			: y_mean = yplus			# yplus  is in the range and yminus isn't
		elif yminuslogic		: y_mean = yminus			# yminus is in the range and yplus  isn't
		else				: sys.exit("Error!!! Y_center fitting gave no  solutions in the range! Aborting... \n")	

		# Some info for the log file
		with open(self.savepath+self.xtal[2]+'_log.txt', 'a') as f:
			f.write("Target center position:\n")
			f.write("\tX_center:\n\t\t" + str(x_mean) + ' \n')
			f.write("\tY_center:\n\t\t" + str(y_mean) + ' \n\n')
		
		return str(x_mean), str(y_mean)

	## Cuts to selection
	def define_cuts(self):

		## Misc cuts that may be applied
		fiber_cut    = "fabs(nFibresOnX[0]-2)<1 && fabs(nFibresOnY[0]-2)<1"
		clock_cut    = "time_maximum[{}]==time_maximum[{}]".format(self.xtal[0],self.xtal[1])
		position_cut = "(fabs(X[0]-{})<4) && (fabs(Y[0]-{})<{})".format(self.x_center, self.y_center, self.poscut)
		amp_cut      = "amp_max[{}]>{} && {}*amp_max[{}]>{}".format(self.xtal[0],str(self.ampmax),self.ampbias,self.xtal[1],str(self.ampmax))
		dampl_cut    = "fabs(fit_ampl[{}]-{}*fit_ampl[{}] )<{}".format(self.xtal[0], self.ampbias, self.xtal[1], self.dampcut)

		chicuts      = self.chicuts.split(',')
		chi2_bounds  = [ [int(chicuts[0]), int(chicuts[1])], [int(chicuts[2]), int(chicuts[3])] ]
		chi2_cut     = "fit_chi2[{}]<{} && fit_chi2[{}]>{} && ".format(self.xtal[0],chi2_bounds[0][1],self.xtal[0],chi2_bounds[0][0])
		chi2_cut    += "fit_chi2[{}]<{} && fit_chi2[{}]>{}    ".format(self.xtal[1],chi2_bounds[1][1],self.xtal[1],chi2_bounds[1][0])

		Cts = []

		## Chi2 cuts
		if self.chi2 is not False:				
			Cts.append( fiber_cut + " && " + clock_cut + " && " + position_cut )
			Cts.append( fiber_cut + " && " + clock_cut + " && " + position_cut )
		## Aeff cuts
		if self.a is not False:	
			Cts.append( fiber_cut + " && " + clock_cut + " && " + position_cut + " && " + amp_cut + " && " + dampl_cut )	
		## Res. cuts
		if self.res is not False:
			Cts.append( fiber_cut + " && " + clock_cut + " && " + position_cut + " && " + amp_cut + " && " + dampl_cut + " && " + chi2_cut )

		# Write some info to the logfile
		with open(self.savepath+self.xtal[2]+'_log.txt', 'a') as f:
			f.write("Args: \n\t"+str(self.args)+'\n\n')
			f.write("Plots specified (in order): \n")
			if self.chi2 is not False: f.write("\tChi2 for {}\n\tChi2 for {}\n".format(self.xtal[0], self.xtal[1]))
			if self.a    is not False: f.write("\tAeff\n")
			if self.res  is not False: f.write("\tTime resolution vs Aeff/b_rms\n")
			f.write("\nCuts applied: \n")
			for i in range(len(Cts)): f.write('\t'+Cts[i]+'\n')

		return Cts

	## Plots to be created, similar structure to define_cuts
	def define_plots(self):
	
		Plts 	= []
		
		if self.chi2 is not False:
			chi2bounds = self.xbins.split(',')
			bins       = [ int(chi2bounds[0]), int(chi2bounds[1]), int(chi2bounds[2]) ]
			Plts.append(["fit_chi2["+self.xtal[0]+"]", "Fit_Chi2_"+self.xtal[0], bins[0], bins[1], bins[2]])
			Plts.append(["fit_chi2["+self.xtal[1]+"]", "Fit_Chi2_"+self.xtal[1], bins[0], bins[1], bins[2]])

		if self.a is not False:	
			abounds = self.abins.split(',')
			bins    = [ int(abounds[0]), int(abounds[1]), int(abounds[2]) ]
			Plts.append([self.Aeff, "aeff_response", bins[0], bins[1], bins[2]])

		if self.res is not False:
			sigbounds = self.sbins.split(',')
			bins      = [ int(sigbounds[0]), int(sigbounds[1]), int(sigbounds[2]), int(sigbounds[3]), int(sigbounds[4]), int(sigbounds[5]) ]
			Plts.append(["fit_time[{}]-fit_time[{}]:{}".format(self.xtal[0],self.xtal[1],self.Aeff), "resolution_vs_aeff", bins[0], bins[1], bins[2], bins[3], bins[4], bins[5]])

		return Plts

	## Save a .root of the given TObject
	def save_files(self, h, path, file_title, name_tag):
		root_savefile = TFile(path + file_title + name_tag + ".root", "recreate")
		root_savefile.cd()				
		h.Write()
		print  "Saved file:", path + file_title + name_tag + '.root'

	## Make the dt vs aeff color map, and use quantiles if so directed
	def make_color_map(self, p, cut, tree):
		if self.quant == True:	## Use quantiles

			## Hybrid quantile method. Uses fixed width bins up to aeff_min_quant, then quantiles above that
			aeff_min_quant = 400									# The Aeff value above which quantiles are used
			aeff_tmp       = TH1F('aeff',"", 100, aeff_min_quant, p[4])				# Creates a temporary histogram to find the quantiles
			tree.Draw(self.Aeff+'>>aeff', TCut(cut))
			nquants   = int(ceil(p[2]/2.)+1)							# n_quantiles = nbins / 2 + 1 (round up if odd)
			probs     = array('d', [x/(nquants-1.) for x in range(0, nquants)])			# Quantile proportions array
			quantiles = array('d', [0 for x in range(0, nquants)])					# Bin edges, initialized as all 0's
			aeff_tmp.GetQuantiles(nquants, quantiles, probs)					# Overwrites 'quantiles' with bin edges positions
			nfixed_bins    = int(floor(p[2]/2.))							# n_fixed_bins = nbins/2 + 1 (round down if odd)
			fixed_bin_size = (aeff_min_quant-p[3])/nfixed_bins				
			bins = array('d', [fixed_bin_size*n for n in range(nfixed_bins)]) + quantiles		# Fixed width bins up to aeff_min_quant, then uses quantiles
			hh   = TH2F('hh', self.file_title+'_dt_vs_aeff_heatmap', p[2], bins, p[5], p[6], p[7])	# Return a TH2F with quantile binning

		else:			## Use fixed width bins
			hh = TH2F('hh', self.file_title+'_dt_vs_aeff_heatmap', p[2], p[3], p[4], p[5], p[6], p[7])	# Return a TH2F with fixed-width binning	

		return hh

	## Adjust dT using a linear fit, to correct "mean walking" location effects in the deposition
	def dt_adjustment(self, tree, cut):
		
		dt    = "fit_time[{}]-fit_time[{}]".format(self.xtal[0],self.xtal[1])
		dampl = "fit_ampl[{}]-{}*fit_ampl[{}]".format(self.xtal[0],self.ampbias,self.xtal[1])

		hadjust = TH2F('hadjust', '', 15, -1500, 1500, 100, -2, 2)
		tree.Draw(dt+":"+dampl+">>hadjust", TCut(cut), "COLZ")
		hadjust.FitSlicesY()
		hadjust_1 = gDirectory.Get("hadjust_1")		# Get the means from FitSlicesY()
		hadjust_1.Draw()				# Plot dt distribution means versus difference in crystal amplitudes


		poly1 = TF1("poly1", "pol1", -1500, 1500)	# Fit the means linearly against dampl
		poly1.SetParameter(0,0.5)	
		poly1.SetParameter(1,0.00001)
		hadjust_1.Fit("poly1", "qR")

		dt0   = str(poly1.GetParameter(0))		# Get the fit parameters
		slope = str(poly1.GetParameter(1))
		chi2  = str(hadjust_1.Chisquare(poly1))
		
		## Some info for the log file		
		with open(self.savepath+self.xtal[2]+'_log.txt', 'a') as f:
			f.write("\nDt adjustment parameters:\n")
			f.write("\tSlope: 	\t\t" + slope + "\n")
			f.write("\tY-intercept: \t\t" + dt0   + "\n")
			f.write("\tchi2: 	\t\t" + chi2  + "\n")

		print 'Dt adjustment parameters: slope = {}, y-intercept = {}, chi2: {}'.format(slope, dt0, chi2)

		## Add a linear correction to dt: dt --> dt-(dampl*slope)
		adjusted_plot = "(fit_time[{}]-fit_time[{}])-({}*({})):{}".format(self.xtal[0],self.xtal[1],slope,dampl,self.Aeff)
		return adjusted_plot



	## Fit the resolution vs Aeff using a user-defined function
	def fit_resolution(self, histo):
	
		def userfit(x,par):
			if x[0]>0:
				fit = pow(pow(par[0]/(x[0]),2)+2*pow(par[1],2), 0.5)								
				return fit
		userfit = TF1('userfit', userfit, 50, 2000, 2)	
		userfit.SetParameters(10, 0.1)			# Set a guess for the parameters
		userfit.SetParNames("N", "c")			# Name the parameters
		histo.Fit("userfit", 'qR')			# Fit the data
		cterm	  = 1000*userfit.GetParameter("c")	# Get the constant term's fit value (IN PICOSECONDS)
		Nterm	  = 1000*userfit.GetParameter("N")	# Get the noise    term's fit value (IN PICOSECONDS)
		cterm_err = 1000*userfit.GetParError(1)		# Very stupidly, GetParError requires a number index, 1="c"
		Nterm_err = 1000*userfit.GetParError(0)		# Very stupidly, GetParError requires a number index, 0="N"
		print 'Constant term from the resolution fitting: {:.2f} +- {:.2f} ps'.format(cterm, cterm_err)

		gStyle.SetOptFit(1)				# Include fit parameters in the stats box
		gPad.Modified()
		gPad.Update()

		# Some info for the log file
		with open(self.savepath+self.xtal[2]+'_log.txt', 'a') as f:
			f.write("\nResolution fitting parameters:  \n")
			f.write("\tConstant term:       \t{:.2f} ps\n".format(cterm)    )
			f.write("\tConstant term error: \t{:.2f} ps\n".format(cterm_err))
			f.write("\tNoise    term:       \t{:.2f} ps\n".format(Nterm)    )
			f.write("\tNoise    term error: \t{:.2f} ps\n".format(Nterm_err))



