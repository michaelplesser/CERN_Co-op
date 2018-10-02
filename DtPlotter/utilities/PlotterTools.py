#!/usr/bin/python

## By Michael Plesser

import sys
import signal
import RunInfoTools
from ROOT import TFile, TH1F, TH2F, TF1, TCut
from array import array
from math   import floor, ceil

## Makes for clean exits out of while loops
def signal_handler(signal, frame):
    print("\program exiting gracefully")
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
        self.args    = args

        self.ampmax     = self.args.am
        self.dampcut    = self.args.da
        self.y_pos_cut  = self.args.pc

        rit = RunInfoTools.RunInfoTools(args, savepath, filei)
        self.ampbias                 = rit.ampbias
        self.xtal                    = rit.xtal
        self.x_center, self.y_center = rit.x_center, rit.y_center
        self.Aeff                    = rit.Aeff

        ## Start a log file
        with open(self.savepath+self.xtal[2]+'_log.txt','w') as f:
            f.write(self.xtal[2]+" "+self.args.e+" energy log file\n\n")


    ## Cuts to selection
    def define_cuts(self):

        ## Sweep to find the chi2 range [1/val,val] that gives 95% acceptance when used as a cut
        def chi2_range_sweep():
            ## Checks if the chi2 sweep is complete, or if it needs to change directions because it overshot
            def check_range(window, percentage):
                if (percentage <= 0.95+window) and (percentage >= 0.95-window): direction =  0  # Sweep completed
                elif percentage>0.95+window:                                    direction = -1  # Decrease chi_val
                elif percentage<0.95+window:                                    direction =  1  # Increase chi_val
                return direction 

            print
            tfile  = TFile(self.file)
            tree   = tfile.Get("h4")
            h_chi  = TH2F("h_chi","",100,-20,20,100,-20,20) # We'll draw the hodoscope position as some arbitrary TH2F to use.
            tree.Draw("Y[0]:X[0]>>h_chi")                   # It doesn't matter what TH2F we draw, we only care about the cut efficiency
            tot_events = h_chi.GetEntries()
            chi_vals   = [0,0]                              # One range for xtal[0], and one for xtal[1]
            for i in range(len(chi_vals)):
                print "Beginning chi2 sweep for {}".format(self.xtal[i])
                stepsize           = 8                                                          # By how much chi_val is changed each time
                chi_val            = 20                                                         # A guess to start
                percent_plus_minus = 0.005                                                      # What is the acceptable range of percent's around 0.95, IE 0.01->0.94-0.96
                direction          = 1                                                          # Start by increasing chi_val
                lastdirection      = direction                                                  # Memory for checking if the direction has changed
                while direction != 0:                                                           # Keep searching until 'direction'==0
                    chi_val += (direction * stepsize)                                           # Adjust the chi_val in the right direction, by the current stepsize
                    chi_cut  = "fit_chi2[{0}]>1./{1} && fit_chi2[{0}]<{1}".format(self.xtal[i],chi_val)
                    tree.Draw("Y[0]:X[0]>>h_chi", TCut(chi_cut))
                    percent_accept  = 1.*h_chi.GetEntries()/tot_events
                    lastdirection   = direction

                    direction       = check_range(percent_plus_minus, percent_accept)           # Update direction. +1, -1, or 0 if complete
                    if direction   != lastdirection:  stepsize /= 2.                            # Reduce step size if we overshoot it and changed direction
                chi_vals[i] = chi_val
                print "Range found for {}:\n\t{:.4f} - {} with {:.2f}% acceptance".format(self.xtal[i], 1./chi_val, chi_val, percent_accept*100.)
            return [ [1./chi_vals[0], chi_vals[0]], [1./chi_vals[1], chi_vals[1]] ]

        ## Aligns the two X and Y hodoscope planes, such that X[0] = X[1]-dx_hodo_align
        ## Allows us to choose the best hodoscope plane for fiber and position cuts
        def hodoscope_alignment():
            tfile  = TFile(self.file)
            tree   = tfile.Get("h4")
            hox   = TH1F("hox", '', 100,-20,20)             # Initialize some basic TH1s 
            hoy   = TH1F("hoy", '', 100,-20,20)
            cutx = "nFibresOnX[0]==2 && nFibresOnX[1]==2"   # For alignment require strictly 2 fibers in X and Y on each plane
            cuty = "nFibresOnY[0]==2 && nFibresOnY[1]==2"
            tree.Draw("X[0]-X[1]>>hox", TCut(cutx))         # Plot the difference distribution between the two X hodoscope values
            tree.Draw("Y[0]-Y[1]>>hoy", TCut(cuty))         # Repeat the same protocol for y...
            dx_hodo_align = hox.GetMean()                   # Assuming mostly straight paths, the mean value is the alignment shift
            dy_hodo_align = hoy.GetMean()                   # Same same
            if (dx_hodo_align==0.0) or (dy_hodo_align==0.0): sys.exit("Error! Hodoscope alignment failed!") # May be no longer needed. Used in debugging
            return dx_hodo_align, dy_hodo_align

        ## Misc cuts that may be applied
        # We have 2 hodo planes we can use for X and Y. This cut picks the best one for position and nFibresOn
        x_pos_cut = 4                                                                           # 1/2 the x-sidelength of the position cut (in mm)
        x_align, y_align = hodoscope_alignment()
        fiber_cut    = "fabs(nFibresOnX[{0}]-2)<={1} && fabs(nFibresOnY[{0}]-2)<={1}"           # {0} is which of the 2 hodoscope planes we use
                                                                                                # {1} is dfibers, see comment below
        position_cut = "(fabs( (X[{0}]-{1}) - {2})<{3}) && (fabs( (Y[{0}]-{4}) -{5})<{6})"      # {0}=which plane
                                                                                                # {1}=x_hodo_alignment
                                                                                                # {2}=x_center
                                                                                                # {3}=x_pos_cut (1/2 the x-sidelength)
                                                                                                # {4}=y_hodo_alignment
                                                                                                # {5}=y_center
                                                                                                # {6}=y_pos_cut (1/2 the y-sidelength)
        dfibers = 1                                                                             # nfibers +- from 2 to accept. IE df = 1 -> 1-3 fibersOn 
        fiber_and_position  = '( ('+fiber_cut.format(0,dfibers)+" && "+position_cut.format(0,0      ,self.x_center,x_pos_cut,0      ,self.y_center,self.y_pos_cut)+') || '
        fiber_and_position += '  ('+fiber_cut.format(1,dfibers)+" && "+position_cut.format(1,x_align,self.x_center,x_pos_cut,y_align,self.y_center,self.y_pos_cut)+') )'

        clock_cut    = "time_maximum[{}]==time_maximum[{}]".format(self.xtal[0],self.xtal[1])
        amp_cut      = "amp_max[{}]>{} && {}*amp_max[{}]>{}".format(self.xtal[0],str(self.ampmax),self.ampbias,self.xtal[1],str(self.ampmax))
        dampl_cut    = "fabs(fit_ampl[{}]-{}*fit_ampl[{}] )<{}".format(self.xtal[0], self.ampbias, self.xtal[1], self.dampcut)

        chi2_bounds  = chi2_range_sweep()
        chi2_cut     = "fit_chi2[{}]<{} && fit_chi2[{}]>{} && ".format(self.xtal[0],chi2_bounds[0][1],self.xtal[0],chi2_bounds[0][0])
        chi2_cut    += "fit_chi2[{}]<{} && fit_chi2[{}]>{}    ".format(self.xtal[1],chi2_bounds[1][1],self.xtal[1],chi2_bounds[1][0])

        Cts = []
        ## Chi2 cuts
        if self.args.x is not False:              
            Cts.append( fiber_and_position + " && " + clock_cut ) 
            Cts.append( fiber_and_position + " && " + clock_cut )
        ## Aeff cuts
        if self.args.a is not False: 
            Cts.append( fiber_and_position + " && " + clock_cut + " && " + amp_cut + " && " + dampl_cut )    
        ## Res. cuts
        if self.args.r is not False:
            Cts.append( fiber_and_position + " && " + clock_cut + " && " + amp_cut + " && " + dampl_cut + " && " + chi2_cut )

        # Write some info to the logfile
        with open(self.savepath+self.xtal[2]+'_log.txt', 'a') as f:
            f.write("Args: \n\t"+str(self.args)+'\n\n')
            f.write("Plots specified (in order): \n")
            if self.args.x is not False: f.write("\tChi2 for {}\n\tChi2 for {}\n".format(self.xtal[0], self.xtal[1]))
            if self.args.a is not False: f.write("\tAeff\n")
            if self.args.r is not False: f.write("\tTime resolution vs Aeff/b_rms\n")
            f.write("\nCuts applied: \n")
            for i in range(len(Cts)): f.write('\t'+Cts[i]+'\n')

        return Cts

    ## Plots to be created, similar structure to define_cuts
    def define_plots(self):
    
        Plts    = []
        if self.args.x is not False:
            chi2bins   = self.args.xb.split(',')
            bins       = [ int(chi2bins[0]), int(chi2bins[1]), int(chi2bins[2]) ]
            Plts.append(["fit_chi2["+self.xtal[0]+"]", "Fit_Chi2_"+self.xtal[0], bins[0], bins[1], bins[2]])
            Plts.append(["fit_chi2["+self.xtal[1]+"]", "Fit_Chi2_"+self.xtal[1], bins[0], bins[1], bins[2]])

        if self.args.a is not False: 
            abins   = self.args.ab.split(',')
            bins    = [ int(abins[0]), int(abins[1]), int(abins[2]) ]
            Plts.append([self.Aeff, "aeff_response", bins[0], bins[1], bins[2]])

        if self.args.r is not False:
            resbins   = self.args.rb.split(',')
            bins      = [ int(resbins[0]), int(resbins[1]), int(resbins[2]), int(resbins[3]), int(resbins[4]), int(resbins[5]) ]
            Plts.append(["fit_time[{}]-fit_time[{}]:{}".format(self.xtal[0],self.xtal[1],self.Aeff), "resolution_vs_aeff", bins[0], bins[1], bins[2], bins[3], bins[4], bins[5]])

        return Plts


    ## Make the dt vs aeff color map, and use quantiles if so directed
    def make_color_map(self, p, cut, tree):

        if self.args.q == True:                                                                                      # Use quantile binning
            ## Hybrid quantile method. Uses fixed width bins up to aeff_min_quant, then quantiles above that
            aeff_min_quant = 600                                                                                # The Aeff value above which quantiles are used
            aeff_tmp       = TH1F('aeff',"", 100, aeff_min_quant, p[4])                                         # Creates a temporary histogram to find the quantiles
            tree.Draw(self.Aeff+'>>aeff', TCut(cut))
            nquants   = int(ceil(p[2]/2.)+1)                                                                    # n_quantiles = nbins / 2 + 1 (round up if odd)
            probs     = array('d', [x/(nquants-1.) for x in range(0, nquants)])                                 # Quantile proportions array
            quantiles = array('d', [0 for x in range(0, nquants)])                                              # Bin edges, initialized as all 0's
            aeff_tmp.GetQuantiles(nquants, quantiles, probs)                                                    # Overwrites 'quantiles' with bin edges positions
            nfixed_bins    = int(floor(p[2]/2.))                                                                # n_fixed_bins = nbins/2 + 1 (round down if odd)
            fixed_bin_size = (aeff_min_quant-p[3])/nfixed_bins              
            bins = array('d', [fixed_bin_size*n for n in range(nfixed_bins)]) + quantiles                       # Fixed width bins up to aeff_min_quant, then uses quantiles
            hh   = TH2F('hh', self.file_title+'_dt_vs_aeff_heatmap', p[2], bins, p[5], p[6], p[7])              # Return a TH2F with quantile binning
        else:                                                                                                   # Use fixed width bins
            hh   = TH2F('hh', self.file_title+'_dt_vs_aeff_heatmap', p[2], p[3], p[4], p[5], p[6], p[7])          # Return a TH2F with fixed-width binning    

        return hh
