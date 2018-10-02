#!/usr/bin/python

## By Michael Plesser

import os   
import sys
import signal
import numpy as np
from ROOT import *
from array import array
from math   import floor, ceil

## Makes for clean exits out of while loops
def signal_handler(signal, frame):
    print("\nprogram exiting gracefully")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

class PlotterTools:

    def __init__(self, args, savepath, filei):

        ## savepath (only used for logfiles)
        self.savepath   = savepath
        
        ## Analysis file
        self.file       = filei[0]                      # Full file with path
        self.file_title = filei[1]                      # '<energy>_<position>', IE '25GeV_C3up'

        ## Giving args shorter/more informative names
        self.args = args

        self.dir     = self.args.d
        self.energy  = self.args.e

        self.chi2    = self.args.x
        self.a       = self.args.a
        self.res     = self.args.r

        self.quant   = self.args.q
        self.fit     = self.args.fit

        self.xbins   = self.args.xb
        self.rbins   = self.args.rb
        self.abins   = self.args.ab

        self.ampmax  = self.args.am
        self.dampcut = self.args.da
        self.y_pos_cut  = self.args.pc
        
        self.freq    = self.args.freq
        self.temp    = self.args.temp

        ## Some internal commonly used function calls
        self.xtal    = self.get_xtals()                 # From self.file's 'info' TTree, get which crystals to use
        self.ampbias = self.amp_coeff()                 # From self.xtal and self.freq, get calibration coeff.s.

        ## Start a log file
        with open(self.savepath+self.xtal[2]+'_log.txt','w') as f:
            f.write(self.xtal[2]+" "+self.energy+" energy log file\n\n")

        self.x_center, self.y_center = self.find_center()   # Get the target center (more tricky than you think, check fn comments...)

        ## Define Aeff since it is used in many places
        self.Aeff    = "pow( 2 / ( (1/pow(fit_ampl[{}]/b_rms[{}], 2)) + (1/pow({}*fit_ampl[{}]/b_rms[{}],2)) ) , 0.5)".format(self.xtal[0],self.xtal[0],self.ampbias,self.xtal[1],self.xtal[1])     


    ## Get crystal pair from Position (C3_down = ['C3', 'C2'], C3_up = ['C3', 'C4'])
    def get_xtals(self):
        tfile    = TFile(self.file)
        infotree = tfile.Get("info")
        infotree.GetEntry(0)
        position = infotree.Positions
        if   position == 2.5:   return ['C3', 'C2', 'C3down'        ]
        elif position == 3.5:   return ['C3', 'C4', 'C3up'          ]
        else:   sys.exit("\nUnrecognized crystal position, aborting...")

    ## Get the amplitude calibration coefficient
    def amp_coeff(self):
        if self.temp == '18deg':
            if   self.xtal[1] == 'C4':  amp_calibration = 0.944866 
            elif self.xtal[1] == 'C2':  amp_calibration = 0.866062 
        elif self.temp == '9deg':
            if   self.xtal[1] == 'C4':  amp_calibration = 0.926351
            elif self.xtal[1] == 'C2':  amp_calibration = 0.849426

        return str(amp_calibration)
    
    ## Find the center of the target
    def find_center(self):  

        t_file  = TFile(self.file)
        t_tree  = t_file.Get("h4")
        fit_range = 2,7
        hx = TH1F("hx", "", 100, -20, 20)
        hy = TH2F("hy", "", 100, fit_range[0], fit_range[1], 100,0,10)      # Some what manually tuned... If it fails:
                                                                            # Check "dampl:Y[0]", and make sure that y=1 in fit_range
        # x mean found by averaging the Hodo.X[0] plot. Valid since amplitudes are basically independent of X
        t_tree.Draw("X[0]>>hx")
        threshold = hx.GetMaximum()/10
        lower_bin = hx.FindFirstBinAbove(threshold)
        upper_bin = hx.FindLastBinAbove(threshold)
        x_mean = hx.GetBinCenter((upper_bin+lower_bin)/2)

        # For y mean, the crystal edge is found by locating where the fit_ampl's of the two xtals are equal (ratio==1)
        y_var = "fit_ampl[{}]/({}*fit_ampl[{}]):Y[0]>>hy".format(self.xtal[0], self.ampbias, self.xtal[1])
        y_cut = "{}*fit_ampl[{}]>1000".format(self.ampbias, self.xtal[1])
        t_tree.Draw(y_var, y_cut)                                           # Draw the ratio of the two xtal's amplitudes against Y[0] into 'hy'
        poly2 = TF1("poly2", "pol2", 3, 6)                                  # Fit the plot, pol2 works well, but is not physically justified
        poly2.SetParameter(0,5)                                             # Get the parameters in the right ballpark to start
        poly2.SetParameter(1,-1)
        poly2.SetParameter(2,0.1)
        hy.Fit("poly2", "QR")
        p0   = float(poly2.GetParameter(0))-1.                              # Subtract one because we want to solve p2*x^2 + p1*x + p0 = 1
        p1   = float(poly2.GetParameter(1))
        p2   = float(poly2.GetParameter(2))
        
        ## Quadratic formula gives two solutions
        yplus  = (-p1+pow(p1*p1-4*p0*p2, 0.5))/(2*p2)
        yminus = (-p1-pow(p1*p1-4*p0*p2, 0.5))/(2*p2)

        ypluslogic  = yplus  > fit_range[0] and yplus  < fit_range[1]       # Checks if yplus  is in the expected range
        yminuslogic = yminus > fit_range[0] and yminus < fit_range[1]       # Checks if yminus is in the expected range
        
        ## Check for which quadratic solution is the right one (in fit_range). There should ideally be exactly 1!!!
        if   ypluslogic and yminuslogic : sys.exit("Error!!! Y_center fitting gave two solutions in the range! Aborting... \n")
        elif ypluslogic                 : y_mean = yplus                            # yplus  is in the range and yminus isn't
        elif yminuslogic                : y_mean = yminus                           # yminus is in the range and yplus  isn't
        else                            : sys.exit("Error!!! Y_center fitting gave no  solutions in the range! Aborting... \n") 

        # Some info for the log file
        with open(self.savepath+self.xtal[2]+'_log.txt', 'a') as f:
            f.write("Target center position:\n")
            f.write("\tX_center:\n\t\t {} \n".format(x_mean))
            f.write("\tY_center:\n\t\t {} \n\n".format(y_mean))
        
        return str(x_mean), str(y_mean)

    ## When we assign a y-vale (resolution) to a bin, by default it is assigned to the mid-point as an x-value (Aeff).
    ## Really we should assign it to be the mean of the Aeff distribution in that bin. This fn makes that adjustmenti.
    def adjust_bin_centers(self, h):

        t_file  = TFile(self.file)
        t_tree  = t_file.Get("h4")

        n_bins = h.GetN()
        xs = []
        ys = h.GetY()
        xerr_low  = []
        xerr_high = []
        yerr = []
        for i in range(n_bins):
            lbound = h.GetX()[i] - h.GetEXlow()[i]                                                              # Lower bin edge of bini
            ubound = h.GetX()[i] + h.GetEXhigh()[i]                                                             # Upper bin edge of bini
            h_aeff  = TH1F("h_aeff", "", 100, 0, 2000)
            t_tree.Draw(self.Aeff+">>h_aeff", TCut("{0}>={1} && {0}<={2}".format(self.Aeff, lbound, ubound)) )  # Plot Aeff for just bini
            xs.append(h_aeff.GetMean())
            xerr_low.append(xs[-1]-lbound)                                                                      # Xerr reflects the binwidth with the center shifted
            xerr_high.append(ubound-xs[-1])                                                                     # Xerr_low + xerr_high = original binwidth
            yerr.append(h.GetErrorY(i))
        xs = array('d', xs)
        xerr_low  = array('d', xerr_low)
        xerr_high = array('d', xerr_high)
        yerr = array('d', yerr)
        return TGraphAsymmErrors(len(xs), xs, ys, xerr_low, xerr_high, yerr, yerr)

    ## Aligns the two X and Y hodoscope planes, such that X[0] = X[1]-dx_hodo_align
    def hodoscope_alignment(self):

        tfile  = TFile(self.file)
        tree   = tfile.Get("h4")

        hox   = TH1F("hox", '', 100,-20,20)      
        hoy   = TH1F("hoy", '', 100,-20,20)
        cutx = "nFibresOnX[0]==2 && nFibresOnX[1]==2"
        cuty = "nFibresOnY[0]==2 && nFibresOnY[1]==2"

        tree.Draw("X[0]-X[1]>>hox", TCut(cutx))
        dx_hodo_align = hox.GetMean()

        tree.Draw("Y[0]-Y[1]>>hoy", TCut(cuty))
        dy_hodo_align = hoy.GetMean()
        
        if (dx_hodo_align==0.0) or (dy_hodo_align==0.0): sys.exit("Error! Hodoscope alignment failed!")
        return dx_hodo_align, dy_hodo_align

    ## Sweep to find the chi2 range [1/val,val] that gives 95% acceptance when used as a cut
    def chi2_range_sweep(self):

        ## Checks if the chi2 sweep is complete, or if it needs to change directions because it overshot
        def check_range(window, percentage):
            if (percentage <= 0.95+window) and (percentage >= 0.95-window):
                direction = 0                                                               # Sweep is complete
            elif percentage>0.95+window:
                direction = -1
            elif percentage<0.95+window:
                direction = 1
            return direction 

        print
        tfile  = TFile(self.file)
        tree = tfile.Get("h4")
        h_chi = TH2F("h_chi","",100,-20,20,100,-20,20)
        tree.Draw("Y[0]:X[0]>>h_chi")
        tot_events = h_chi.GetEntries()
        chi_vals = [0,0]    # One for xtal[0], one for xtal[1]
        for i in range(len(chi_vals)):
            print "Beginning chi2 sweep for {}".format(self.xtal[i])

            chi_val = 25                                                                    # A guess to start
            percent_plus_minus = 0.005                                                      # What is the acceptable range of percent's around 0.95, IE 0.01->0.94-0.96
            chi_cut = "fit_chi2[{0}]>1./{1} && fit_chi2[{0}]<{1}".format(self.xtal[i],chi_val)
            tree.Draw("Y[0]:X[0]>>h_chi", TCut(chi_cut))
            percent_accept     = 1.*h_chi.GetEntries()/tot_events
            direction          = check_range(percent_plus_minus, percent_accept)            # +1 or -1, does the chi_val get increased or decreased?
            lastdirection      = direction                                                  # Memory for checking if the direction changed
            stepsize           = 8                                                          # By how much chi_val is changed each time

            while check_range(percent_plus_minus, percent_accept) != 0:                     # Keep searching until 'direction'==0

                direction     = check_range(percent_plus_minus, percent_accept)             # +1 or -1, does the chi_val get increased or decreased?
                if direction != lastdirection:  stepsize /= 2.                              # Reduce step size if we overshoot it and changed direction

                chi_val = chi_val + (direction * stepsize)                                  # Adjust the chi_val in the right direction, by the current stepsize
                chi_cut = "fit_chi2[{0}]>1./{1} && fit_chi2[{0}]<{1}".format(self.xtal[i],chi_val)
                tree.Draw("Y[0]:X[0]>>h_chi", TCut(chi_cut))
                percent_accept  = 1.*h_chi.GetEntries()/tot_events
                lastdirection   = direction

            chi_vals[i] = chi_val
            print "Range found for {}:\n\t{:.4f} - {} with {:.2f}% acceptance".format(self.xtal[i], 1./chi_val, chi_val, percent_accept*100.)

        return [ [1./chi_vals[0], chi_vals[0]], [1./chi_vals[1], chi_vals[1]] ]


    ## Cuts to selection
    def define_cuts(self):

        ## Misc cuts that may be applied

        # We have 2 hodo planes we can use for X and Y. This cut picks the best one for position and nFibresOn
        x_pos_cut = 4                                                                           # 1/2 the x-sidelength of the position cut (in mm)
        x_align, y_align = self.hodoscope_alignment()
        fiber_cut    = "fabs(nFibresOnX[{0}]-2)<={1} && fabs(nFibresOnY[{0}]-2)<={1}"           # {0} is which of the 2 hodoscope planes we use
                                                                                                # {1} is dfibers, see comment below
        position_cut = "(fabs( (X[{0}]-{1}) - {2})<{3}) && (fabs( (Y[{0}]-{4}) -{5})<{6})"      # {0}=which plane
                                                                                                # {1}=x_hodo_alignment
                                                                                                # {2}=x_center
                                                                                                # {3}=x_pos_cut (1/2 the x-sidelength)
                                                                                                # {4}=y_hodo_alignment
                                                                                                # {5}=y_center
                                                                                                # {6}=poscut
        dfibers = 1                                                                             # nfibers +- from 2 to accept. IE df = 1 -> 1-3 fibersOn 
        fiber_and_position  = '( ('+fiber_cut.format(0,dfibers)+" && "+position_cut.format(0,0      ,self.x_center,x_pos_cut,0      ,self.y_center,self.y_pos_cut)+') || '
        fiber_and_position += '  ('+fiber_cut.format(1,dfibers)+" && "+position_cut.format(1,x_align,self.x_center,x_pos_cut,y_align,self.y_center,self.y_pos_cut)+') )'

        clock_cut    = "1==1"#"time_maximum[{}]==time_maximum[{}]".format(self.xtal[0],self.xtal[1])
        amp_cut      = "amp_max[{}]>{} && {}*amp_max[{}]>{}".format(self.xtal[0],str(self.ampmax),self.ampbias,self.xtal[1],str(self.ampmax))
        dampl_cut    = "fabs(fit_ampl[{}]-{}*fit_ampl[{}] )<{}".format(self.xtal[0], self.ampbias, self.xtal[1], self.dampcut)

        chi2_bounds  = self.chi2_range_sweep()
        chi2_cut     = "fit_chi2[{}]<{} && fit_chi2[{}]>{} && ".format(self.xtal[0],chi2_bounds[0][1],self.xtal[0],chi2_bounds[0][0])
        chi2_cut    += "fit_chi2[{}]<{} && fit_chi2[{}]>{}    ".format(self.xtal[1],chi2_bounds[1][1],self.xtal[1],chi2_bounds[1][0])

        Cts = []

        ## Chi2 cuts
        if self.chi2 is not False:              
            Cts.append( fiber_and_position + " && " + clock_cut ) 
            Cts.append( fiber_and_position + " && " + clock_cut )
        ## Aeff cuts
        if self.a is not False: 
            Cts.append( fiber_and_position + " && " + clock_cut + " && " + amp_cut + " && " + dampl_cut )    
        ## Res. cuts
        if self.res is not False:
            Cts.append( fiber_and_position + " && " + clock_cut + " && " + amp_cut + " && " + dampl_cut + " && " + chi2_cut )

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
    
        Plts    = []
        
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
            sigbounds = self.rbins.split(',')
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
        if self.quant == True:      ## Use quantiles

            ## Hybrid quantile method. Uses fixed width bins up to aeff_min_quant, then quantiles above that
            aeff_min_quant = 600                                                                        # The Aeff value above which quantiles are used
            aeff_tmp       = TH1F('aeff',"", 100, aeff_min_quant, p[4])                                 # Creates a temporary histogram to find the quantiles
            tree.Draw(self.Aeff+'>>aeff', TCut(cut))
            nquants   = int(ceil(p[2]/2.)+1)                                                            # n_quantiles = nbins / 2 + 1 (round up if odd)
            probs     = array('d', [x/(nquants-1.) for x in range(0, nquants)])                         # Quantile proportions array
            quantiles = array('d', [0 for x in range(0, nquants)])                                      # Bin edges, initialized as all 0's
            aeff_tmp.GetQuantiles(nquants, quantiles, probs)                                            # Overwrites 'quantiles' with bin edges positions
            nfixed_bins    = int(floor(p[2]/2.))                                                        # n_fixed_bins = nbins/2 + 1 (round down if odd)
            fixed_bin_size = (aeff_min_quant-p[3])/nfixed_bins              
            bins = array('d', [fixed_bin_size*n for n in range(nfixed_bins)]) + quantiles               # Fixed width bins up to aeff_min_quant, then uses quantiles
            hh   = TH2F('hh', self.file_title+'_dt_vs_aeff_heatmap', p[2], bins, p[5], p[6], p[7])      # Return a TH2F with quantile binning

        else:                       ## Use fixed width bins
            hh = TH2F('hh', self.file_title+'_dt_vs_aeff_heatmap', p[2], p[3], p[4], p[5], p[6], p[7])  # Return a TH2F with fixed-width binning    

        return hh

    ## Adjust dT using a linear fit, to correct "mean walking" location effects in the deposition
    def dt_adjustment(self, tree, cut):

        ## Checks to see if any points shouldn't be trusted based on a large residual, and returns TGraph without those points
        ## Helps the linear correction remain accurate when one or more fits from fit_y_slices fails
        def remove_outliers(gr):                                                    # gr input is a TGraphAsymmErrors TObject
            x         = array('d', [])                                              # Initialize the arrays to create the filteres TGraph output
            y         = array('d', [])
            xerr_low  = array('d', [])
            xerr_high = array('d', [])
            yerr      = array('d', [])
            median    = np.median(list(filter(lambda x: abs(x)>1e-1 and abs(x)<2, [gr.GetY()[i] for i in range(nbins)])))
            n_points  = gr.GetN()
            for i in range(n_points):
                if abs(gr.GetY()[i] - median) < 0.15:                               # Only accept points who have a residual between resolution fit means and the median <200ps
                    x.append(gr.GetX()[i])                                          # Add all the usual points needed for a TGraphAsymmError constructor, etcetc
                    y.append(gr.GetY()[i])
                    xerr_low.append(gr.GetEXlow()[i])
                    xerr_high.append(gr.GetEXhigh()[i])
                    yerr.append(gr.GetEYhigh()[i])
                else:
                    print "Outlier found at point {0}: fit_mean = {1:4.3f} \t median fit_mean = {2:4.3f} \t residual = {3:4.3f}".format(i, gr.GetY()[i], median, abs(gr.GetY()[i] - median))
            return TGraphAsymmErrors(len(x), x, y, xerr_low, xerr_high, yerr, yerr) # Return a TGraph with any outliers removed
        
        ## Draw the plot and fit y slices to fit linearly
        nbins = 30
        fit_lbound = float(self.y_center) - 4.0
        fit_ubound = float(self.y_center) + 4.0
        hadjust    = TH2F('hadjust', '', nbins, fit_lbound, fit_ubound, 100, -2, 2)
        dt         = "fit_time[{}]-fit_time[{}]".format(self.xtal[0],self.xtal[1])
        tree.Draw(dt+":Y[0]>>hadjust", TCut(cut), "COLZ")
        hadjust_1  = self.fit_y_slices(hadjust)[0]                                  # Mean of the dt distribution plotted against Y[0]
        hadjust_1  = remove_outliers(hadjust_1)
        self.save_files(hadjust_1, self.savepath,"{}_{}_".format(self.energy,self.xtal[2]),"dt_adjustment") # Saving post-fit causes a seg fault in terminal mode ROOT

        slope = 1                                                                   # Enter the coming while loop directly instead of fitting once, getting the slope, and then entering
        if hadjust_1.GetN() < 4:                                                    # If outlier removal leaves < 4 points, that's not enough for a trustworthy fit
            print "Not enough points remaining for accurate linear fit. Dt vs Dampl slope set to 0"
            slope = 0

        print
        refit_counter = 1
        max_n_refits  = 10
        poly1 = TF1("poly1", "pol1", fit_lbound, fit_ubound)                      
        while (abs(slope) > 0.1):                                                   # Helps tell if the fit failed
            print "Attempting Dt linear fit {}/{}".format(refit_counter, max_n_refits)
            ## Reset parameters randomly (within ranges) and attempt a fit
            tr = TRandom()
            tr.SetSeed(0)
            poly1.SetParameter(0, tr.Uniform(-2,2)      )   
            poly1.SetParameter(1, tr.Uniform(-0.1, 0.1) )
            poly1.SetParLimits(0, -2  , 2)
            poly1.SetParLimits(1, -0.5, 0.5)
            hadjust_1.Fit("poly1", "QFWBR")
 
            ## Get the fit parameters
            dt0   = poly1.GetParameter(0)                             
            slope = poly1.GetParameter(1)
            if poly1.GetNDF() != 0:
                red_chi2  = hadjust_1.Chisquare(poly1)/poly1.GetNDF()
            else: 
                red_chi2 = 'N/A'
             
            if (refit_counter == max_n_refits) and (abs(slope) > 0.1):
                print "Dt adjustment linear fit failed. Dt vs Y[0] slope set to 0"
                slope = 0
            refit_counter += 1

        self.save_files(hadjust_1, self.savepath,"{}_{}_".format(self.energy,self.xtal[2]),"dt_adjustment_fitted") # Post-fit plots DO show correctly on EOS-webpage, so save pre- and post-fit 
        print 'Dt adjustment parameters: slope = {:.7f}, y-intercept = {:.3f}, reduced chi2: {}'.format(slope, dt0, red_chi2)
        
        ## Some info for the log file       
        with open(self.savepath+self.xtal[2]+'_log.txt', 'a') as f:
            f.write("\nDt adjustment parameters:\n")
            f.write("\tSlope:       \t\t {}\n".format(slope))
            f.write("\tY-intercept: \t\t {}\n".format(dt0))
            f.write("\tReduced chi2:\t\t {}\n".format(red_chi2))

        ## Add a linear correction to dt: dt --> dt-(dampl*slope)
        adjusted_plot = "( ({0}) - ( {1} * (Y[0]-{2}) ) ):{3}".format(dt,slope,self.y_center,self.Aeff)
        return adjusted_plot


    ## Fit the resolution vs Aeff using a user-defined function
    def fit_resolution(self, gr):
    
        ## The function used to fit our distribution. N/Aeff (+) sqrt(2)*c, (+) -> sum in quadrature
        def userfit(x,par):
            if x[0]>0:
                fit = pow(pow(par[0]/(x[0]),2) + 2*pow(par[1],2), 0.5)                                
                return fit
        userfit = TF1('userfit', userfit, 1, 2000, 2)  
        userfit.SetParameters(1, 0.05)                     # Set a guess for the parameters (N, c)
    
        print
        fit_status = ''
        refit_counter = 0
        max_n_refits  = 25
        while (not 'OK' in fit_status) and (not 'CONVERGED' in fit_status):                         # As long as the fit status is not a good one, keep trying
            print 'Attempting resolution fit {}/{}'.format(refit_counter+1, max_n_refits)
            tr = TRandom()
            tr.SetSeed(0)
            userfit.SetParameter(0, tr.Uniform(-1, 1   ))  # Re-guess the parameters
            userfit.SetParameter(1, tr.Uniform( 0, 0.05))  # Re-guess the parameters 
            fit = gr.Fit("userfit", "QRM")                 # Try the fit again
            fit_status = gMinuit.fCstatu                   # Get the fit status
            refit_counter += 1

            if ('OK' in fit_status) or ('CONVERGED' in fit_status):
                if (abs(userfit.GetParameter(1)) < 0.001) or (abs(userfit.GetParameter(1)) > 0.2):  # We know the resolution shouldn't be outside 1-200 ps
                    fit_status = ''                                                                 # Don't believe status='OK' if we know the value is bad
                    print 'Bad constant term value, fit discarded'
                else:                                                                               # If the cterm seems reasonable, accept the fit
                    print 'Fit successful!'

            if refit_counter == max_n_refits:
                print 'Refit limit reached, resolution fit failed.'
                fit_status = 'OKNOTOK'                                                              # Exit the while loop, but know it failed. (Radiohead? Anyone?)

        if refit_counter < max_n_refits:                            # If the fit succeeded before the refit cap was reached...
            cterm     = 1000*abs(userfit.GetParameter(1))           # Get the constant term's fit value (IN PICOSECONDS) (abs b/c of sum in quad.)
            Nterm     = 1000*abs(userfit.GetParameter(0))           # Get the noise    term's fit value (IN PICOSECONDS) (abs b/c of sum in quad.)
            cterm_err = 1000*userfit.GetParError(1)        
            Nterm_err = 1000*userfit.GetParError(0)        
            if userfit.GetNDF() != 0:
                red_chi2  = gr.Chisquare(userfit)/userfit.GetNDF()   # Get the reduced chi2 of the fit
            else:
                red_chi2  = 'N/A'
    
            print '\tResolution fit status:                     {}'.format(fit_status)
            print '\tReduced fit chi2:                          {}'.format(red_chi2)
            print '\tConstant term from the resolution fitting: {:.2f} +- {:.2f} ps'.format(cterm, cterm_err)

        else:                                               # If we hit the refit limit, don't believe the fit values
            cterm     = 0
            Nterm     = 0
            cterm_err = 0
            Nterm_err = 0
            red_chi2  = 'N/A'

        gStyle.SetOptFit(1)                                 # Include fit parameters in the stats box
        gPad.Modified()
        gPad.Update()

        # Some info for the log file
        with open(self.savepath+self.xtal[2]+'_log.txt', 'a') as f:
            f.write("\nResolution fitting parameters:  \n")
            f.write("\tConstant term:       \t{:.2f} ps\n".format(cterm)    )
            f.write("\tConstant term error: \t{:.2f} ps\n".format(cterm_err))
            f.write("\tNoise    term:       \t{:.2f} ps\n".format(Nterm)    )
            f.write("\tNoise    term error: \t{:.2f} ps\n".format(Nterm_err))
            f.write("\tReduced  fit chi2:   \t{}       \n".format(red_chi2))

    ## Advanced version of FitSlicesY(). Uses a double sided crystal ball fit, and in bins with low statistics
    ## switches back to gaussian for performance reasons
    def fit_y_slices(self, h):

        ## Double sided crystal ball function
        def double_xtal_ball(x,par):
            f1 = TF1('f1','crystalball')
            f2 = TF1('f2','crystalball')
            f1.SetParameters(par[0], par[1], par[2], par[3], par[5])            # The trick is to share all variables except 
            f2.SetParameters(par[0], par[1], par[2], par[4], par[5])            # 'A', which determines the side of the tail
            return f1(x) + f2(x)

        double_xtal_ball = TF1("double_xtal_ball", double_xtal_ball, -2, 2, 6)  # -2 to 2 is my fit range
        double_xtal_ball.SetParNames("c","mu","sig","A1","A2","n")              
        
        ## Set par. limits to help the minimizer converge
        ## Perhaps overkill, but at least set A1 and A2 to have different signs, one for each tail!!!
        ## Example values, tune based on your specific usage case. Not all limits may be necessary for you
        double_xtal_ball.SetParLimits(0 , 0 ,999)                               # c >= 0
        double_xtal_ball.SetParLimits(1 ,-2 ,2  )                               # mu between -2 and 2
        double_xtal_ball.SetParLimits(2 , 0 ,0.2)                               # sigma between 0 and 200ps
        double_xtal_ball.SetParLimits(3 , 0 ,99 )                               # A1 >= 0
        double_xtal_ball.SetParLimits(4 ,-99,0  )                               # A2 <= 0
        double_xtal_ball.SetParLimits(5 , 0 ,99 )                               # n  >= 0
        double_xtal_ball.SetParameters(1, 0.5, 0.05, 1, -1, 1)                  # Some guesses to help things along 

        print
        bins     = []
        hh_1_tmp = []
        hh_2_tmp = []
        n_bins   = h.GetXaxis().GetNbins()
        for bini in range(1, n_bins):

            h_p = h.ProjectionY('h_p',bini,bini) # Get the distribution in y as  TH1 for bin# 'bini'
             
            refit_counter = 0
            max_n_refits  = 25
            min_n_events  = 50
            n_entries = int(h_p.GetEntries())

            if (n_entries > min_n_events): 

                fit = h_p.Fit("double_xtal_ball", "RQM")
                status = gMinuit.fCstatu    # Get the fit status, IE 'OK', 'CONVERGED', 'FAILED'
                while (not 'OK' in status) and (not 'CONVERGED' in status): # These are the good ones :(

                    print 'Fit failed for slice number {} with {} entries. Attempting refit {}/{}'.format(bini, n_entries, refit_counter+1, max_n_refits)
                    tr = TRandom()
                    tr.SetSeed(0)
                    double_xtal_ball.SetParameter(0, tr.Uniform(  0, 10 ))  # Reset the parameters (add a small delta??)
                    double_xtal_ball.SetParameter(1, tr.Uniform( -2, 2  ))  # Reset the parameters (add a small delta??)
                    double_xtal_ball.SetParameter(2, tr.Uniform(  0, 0.2))  # Reset the parameters (add a small delta??)
                    double_xtal_ball.SetParameter(3, tr.Uniform(  0, 99 ))  # Reset the parameters (add a small delta??)
                    double_xtal_ball.SetParameter(4, tr.Uniform(-99, 0  ))  # Reset the parameters (add a small delta??)
                    fit = h_p.Fit("double_xtal_ball", "RBQ")                # Try the fit again
                    status = gMinuit.fCstatu                                # Get the fit status
                    refit_counter += 1

                    if ('OK' in status) or ('CONVERGED' in status):
                        print 'Refit successful!'
                    if refit_counter == max_n_refits:
                        print 'Refit limit reached, ommiting slice {}'.format(bini)
                        status = 'OKNOTOK'

                if refit_counter != max_n_refits:
                 
                    mean = double_xtal_ball.GetParameter(1)
                    res  = double_xtal_ball.GetParameter(2)
                    mean_err = double_xtal_ball.GetParError(1)
                    res_err  = double_xtal_ball.GetParError(2)

                    lowedge  = h.GetXaxis().GetBinLowEdge(bini)
                    highedge = h.GetXaxis().GetBinLowEdge(bini+1)
                    center   = (lowedge + highedge) / 2.

                    bins.append( [lowedge, highedge, center] )
                    hh_1_tmp.append([mean, mean_err])
                    hh_2_tmp.append([res, res_err])

        print
        xs              = array('d', [ x[2] for x in bins])
        xerr            = array('d', [(x[1]-x[0])/2. for x in bins])
        means           = array('d', [ x[0] for x in hh_1_tmp])
        means_err       = array('d', [ x[1] for x in hh_1_tmp])
        resolutions     = array('d', [ x[0] for x in hh_2_tmp])
        resolutions_err = array('d', [ x[1] for x in hh_2_tmp])
        hh_1 = TGraphAsymmErrors(len(bins), xs, means       , xerr, xerr, means_err      , means_err      ) 
        hh_2 = TGraphAsymmErrors(len(bins), xs, resolutions , xerr, xerr, resolutions_err, resolutions_err) 

        return hh_1, hh_2

