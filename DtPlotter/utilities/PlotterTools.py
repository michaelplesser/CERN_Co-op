#!/usr/bin/python

## By Michael Plesser

import sys
import signal
import RunInfoTools
from ROOT import TFile, TH1F, TH2F, TF1, TCut, gSystem
from array import array

## Makes for clean exits out of while loops
def signal_handler(signal, frame):
    print("\program exiting gracefully")
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

class PlotterTools:

    def __init__(self, args, savepath, filei, centers):

        ## savepath (only used for logfiles)
        self.savepath    = savepath
        
        ## Analysis file
        self.file        = filei[0]                      # Full file with path
        self.file_title  = filei[1]                      # '<energy>_<position>', IE '25GeV_C3up'

        self.args        = args

        self.min_amp_max = self.args.am
        self.dampcut     = self.args.da
        self.x_pos_cut   = float(self.args.pc.split(',')[0])
        self.y_pos_cut   = float(self.args.pc.split(',')[1])

        rit = RunInfoTools.RunInfoTools(args, savepath, filei)
        self.ampbias                 = rit.ampbias
        self.xtal                    = rit.xtal
        self.x_center, self.y_center = centers[0], centers[1] 
        self.Aeff                    = rit.Aeff

        # These lines annoyingly needed to make fitResult work :(
        gSystem.Load("/afs/cern.ch/user/m/mplesser/H4Analysis/CfgManager/lib/libCFGMan.so")
        gSystem.Load("/afs/cern.ch/user/m/mplesser/H4Analysis/lib/libH4Analysis.so")
        gSystem.Load("/afs/cern.ch/user/m/mplesser/H4Analysis/DynamicTTree/lib/libDTT.so")

    ## Cuts to selection
    def define_cuts(self):

        tfile  = TFile(self.file)
        tree   = tfile.Get("h4")

        ## Sweep to find the chi2 range [1/val,val] that gives 95% acceptance when used as a cut
        def chi2_range_sweep():

            ## Checks if the chi2 sweep is complete, or if it needs to change directions because it overshot
            def check_range(window, percentage):
                if (percentage <= 0.95+window) and (percentage >= 0.95-window): direction =  0  # Sweep completed
                elif percentage>0.95+window:                                    direction = -1  # Decrease chi_val
                elif percentage<0.95+window:                                    direction =  1  # Increase chi_val
                return direction 

            chi_vals   = [0,0]                              # One range for xtal[0], and one for xtal[1]
            print "Beginning chi2 sweep..."
            for i in range(len(chi_vals)):
                h_chi  = TH1F("h_chi","",1000,0,1000)                                           
                basic_cut  = "n_tracks==1 && "
                basic_cut += "fabs(fitResult[0].y())<10 && fabs(fitResult[0].x())<10 && ".format(self.xtal[i])
                basic_cut += "fit_time[{0}]>0 && fit_time[{1}]>0".format(self.xtal[0], self.xtal[1])
                tree.Draw("fit_chi2[{}]>>h_chi".format(self.xtal[i]), TCut(basic_cut))         
                tot_events = h_chi.GetEntries()
                stepsize           = 64                                                         # By how much chi_val is changed each time
                chi_val            = 0                                                          # A guess to start
                percent_plus_minus = 0.005                                                      # What is the acceptable range of percent's around 0.95, IE 0.01->0.94-0.96
                direction          = 1                                                          # Start by increasing chi_val
                lastdirection      = direction                                                  # Memory for checking if the direction has changed
                while direction != 0:                                                           # Keep searching until 'direction'==0
                    chi_val += (direction * stepsize)                                           # Adjust the chi_val in the right direction, by the current stepsize
                    chi_cut  = "fit_chi2[{0}]>1./{1} && fit_chi2[{0}]<{1} && {2}".format(self.xtal[i],chi_val, basic_cut)
                    tree.Draw("fit_chi2[{}]>>h_chi".format(self.xtal[i]), TCut(chi_cut))
                    percent_accept  = 1.*h_chi.GetEntries()/tot_events
                    lastdirection   = direction
                    direction       = check_range(percent_plus_minus, percent_accept)           # Update direction. +1, -1, or 0 if complete
                    if direction   != lastdirection:  stepsize /= 2.                            # Reduce step size if we overshoot it and changed direction

                chi_vals[i] = chi_val
                print "Range found for {}:\n\t{:.4f} - {} with {:.2f}% acceptance".format(self.xtal[i], 1./chi_val, chi_val, percent_accept*100.)
            return [ [1./chi_vals[0], chi_vals[0]], [1./chi_vals[1], chi_vals[1]] ]

        ## Misc cuts that may be applied
        
        tracks_cut = "n_tracks == 1"

        ## Loose cut, fabs(X) and fabs(Y)<20, but also cut out 1mm around the center in the interesting direction
        ## Not ideal, but eliminates the knee in the res. plot from gap electrons
        if (self.xtal[2] == 'C3down') or (self.xtal[2] == 'C3up'):
            position_cut  = "(fabs( fitResult[0].x() - {0} ) < {1})".format(self.x_center, self.x_pos_cut)
            position_cut += " && (fitResult[0].y() > ({0}+1) || fitResult[0].y() < ({0}-1))".format(self.y_center)
            position_cut += " && fabs( fitResult[0].y() ) < 15"
        elif (self.xtal[2] == 'C3left') or (self.xtal[2] == 'C3right'):
            position_cut  = "(fabs( fitResult[0].y()  ) < {1})".format(self.y_center, self.y_pos_cut)
            position_cut += " && (fitResult[0].x() > ({0}+1) || fitResult[0].x() < ({0}-1))".format(self.x_center)
            position_cut += " && fabs( fitResult[0].x() ) < 15"

        ## Back-pocket position cut, maybe to be used later. More basic, just cuts around the center
        #position_cut = "(fabs( fitResult[0].x()-{0} )<{1}) && (fabs( fitResult[0].y()-{2} )<{3})".format(self.x_center, self.x_pos_cut, self.y_center, self.y_pos_cut)
        #position_cut = "fabs( fitResult[0].x())<10 && fabs(fitResult[0].y())<10"

        clock_cut    = "time_maximum[{}]==time_maximum[{}]".format(self.xtal[0],self.xtal[1])
        ## amp_cut is due for improvement! TBD
        amp_cut      = "fit_ampl[{}]>{} && {}*fit_ampl[{}]>{}".format(self.xtal[0],self.min_amp_max,self.ampbias,self.xtal[1],self.min_amp_max)
        dampl_cut    = "fabs(fit_ampl[{}]-{}*fit_ampl[{}] )<{}".format(self.xtal[0], self.ampbias, self.xtal[1], self.dampcut)

        chi2_bounds  = chi2_range_sweep()
        chi2_cut     = "fit_chi2[{}]<{} && fit_chi2[{}]>{} && ".format(self.xtal[0],chi2_bounds[0][1],self.xtal[0],chi2_bounds[0][0])
        chi2_cut    += "fit_chi2[{}]<{} && fit_chi2[{}]>{}    ".format(self.xtal[1],chi2_bounds[1][1],self.xtal[1],chi2_bounds[1][0])

        Cts = []
        ## Chi2 cuts
        if self.args.x is not False:              
            Cts.append( tracks_cut + " && " + position_cut + " && " + clock_cut + " && " + amp_cut + " && " + dampl_cut )
            Cts.append( tracks_cut + " && " + position_cut + " && " + clock_cut + " && " + amp_cut + " && " + dampl_cut )

        ## Aeff cuts
        if self.args.a is not False: 
            Cts.append( tracks_cut + " && " + position_cut + " && " + clock_cut + " && " + amp_cut + " && " + dampl_cut + " && " + chi2_cut )

        ## Res. cuts
        if self.args.r is not False:
            Cts.append( tracks_cut + " && " + position_cut + " && " + clock_cut + " && " + amp_cut + " && " + dampl_cut + " && " + chi2_cut )

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
            Plts.append(["fit_chi2[{}]".format(self.xtal[0]), "Fit_Chi2_"+self.xtal[0], bins[0], bins[1], bins[2]])
            Plts.append(["fit_chi2[{}]".format(self.xtal[1]), "Fit_Chi2_"+self.xtal[1], bins[0], bins[1], bins[2]])

        if self.args.a is not False: 
            abins   = self.args.ab.split(',')
            bins    = [ int(abins[0]), int(abins[1]), int(abins[2]) ]
            Plts.append([self.Aeff, "aeff_response", bins[0], bins[1], bins[2]])

        if self.args.r is not False:
            resbins   = self.args.rb.split(',')
            bins      = [ int(resbins[0]), int(resbins[1]), int(resbins[2]), int(resbins[3]), int(resbins[4]), int(resbins[5]) ]
            var       = "fit_time[{}]-fit_time[{}]:{}".format(self.xtal[0],self.xtal[1],self.Aeff)
            Plts.append([var, "resolution_vs_aeff", bins[0], bins[1], bins[2], bins[3], bins[4], bins[5]])

        return Plts


    ## Make the dt vs aeff color map, and use quantiles if so directed
    def make_color_map(self, p, cut, tree):

        def quants_in_range(nbins_quant, lb, ub):
            aeff_tmp       = TH1F('aeff',"", 100, lb, ub)                                                       # Creates a temporary histogram to find the quantiles
            tree.Draw(self.Aeff+'>>aeff', TCut(cut))
            probs     = array('d', [x/(nbins_quant-1.) for x in range(0, nbins_quant)])                         # Quantile proportions array
            quantiles = array('d', [0 for x in range(0, nbins_quant)])                                          # Bin edges, initialized as all 0's
            aeff_tmp.GetQuantiles(nbins_quant, quantiles, probs)                                                # Overwrites 'quantiles' with bin edges positions
            return quantiles

        def fixed_bins_in_range(nbins, lb, ub):
            fixed_bin_size  = (ub - lb)/(nbins+1)              
            return array('d', [lb+fixed_bin_size*n for n in range(1, nbins+1)])

        if self.args.q == True:                                                                                 # Use quantile binning
            ## Hybrid quantile method. Uses quantiles in low and high Aeff regions, and fixed bins between.
            n_lower_quants  = int(p[2]/2)+1                                                                     # Number of quantiles in low Aeff region
            lower_quants_ub = 400                                                                               # Upper bound of lower quantile region (lb taken from p[3])
            lower_quants    = quants_in_range(n_lower_quants,p[3],lower_quants_ub )
            nfixed_bins     = p[2] - n_lower_quants + 1                                                         # n_fixed_bins = whatever is left (done this way to avoid rounding issues)
            fixed_bins      = fixed_bins_in_range(nfixed_bins, lower_quants_ub, p[4])              
            bins = lower_quants + fixed_bins                                                                    # Mix of quantiles and fixed width bins.
            hh   = TH2F('hh', self.file_title+'_dt_vs_aeff_heatmap', p[2], bins, p[5], p[6], p[7])              # Return a TH2F with mixed quantile/fixed binning
        else:                                                                                                   # Use fixed width bins
            hh   = TH2F('hh', self.file_title+'_dt_vs_aeff_heatmap', p[2], p[3], p[4], p[5], p[6], p[7])        # Return a TH2F with fixed-width binning    

        return hh
