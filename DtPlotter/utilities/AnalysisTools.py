#!/usr/bin/python

## By Michael Plesser

import sys
import numpy as np
import FileTools
import RunInfoTools
from array import array as carray
from ROOT import * 

class AnalysisTools:

    def __init__(self, args, savepath, filei):
        self.args   = args
        self.energy = self.args.e
        
        self.file     = filei[0]
        self.savepath = savepath

        self.ft  = FileTools.FileTools(args)

        rit = RunInfoTools.RunInfoTools(args, savepath, filei)
        self.ampbias                 = rit.ampbias
        self.xtal                    = rit.xtal
        self.x_center, self.y_center = rit.x_center, rit.y_center
        self.Aeff                    = rit.Aeff

    ## When we assign a y-value (resolution) to a bin, by default it is assigned to the mid-point as an x-value (Aeff).
    ## Really we should assign it to be the mean of the Aeff distribution in that bin. This fn makes that adjustmenti.
    def adjust_bin_centers(self, h):

        t_file    = TFile(self.file)
        t_tree    = t_file.Get("h4")

        n_bins    = h.GetN()
        xs        = []
        ys        = h.GetY()
        xerr_low  = []
        xerr_high = []
        yerr      = []
        for i in range(n_bins):
            lbound = h.GetX()[i] - h.GetEXlow()[i]                                                              # Lower bin edge of bini
            ubound = h.GetX()[i] + h.GetEXhigh()[i]                                                             # Upper bin edge of bini
            h_aeff = TH1F("h_aeff", "", 100, 0, 2000)
            t_tree.Draw(self.Aeff+">>h_aeff", TCut("{0}>={1} && {0}<={2}".format(self.Aeff, lbound, ubound)) )  # Plot Aeff for just bini
            xs.append(h_aeff.GetMean())
            xerr_low.append(xs[-1]-lbound)                                                                      # Xerr reflects the binwidth with the center shifted
            xerr_high.append(ubound-xs[-1])                                                                     # Xerr_low + xerr_high = original binwidth
            yerr.append(h.GetErrorY(i))
        xs        = carray('d', xs       )
        xerr_low  = carray('d', xerr_low )
        xerr_high = carray('d', xerr_high)
        yerr      = carray('d', yerr     )
        return TGraphAsymmErrors(len(xs), xs, ys, xerr_low, xerr_high, yerr, yerr)

    ## Adjust dT using a linear fit, to correct "mean walking" location effects in the deposition
    def dt_linear_correction(self, tree, cut):

        ## Checks to see if any points shouldn't be trusted based on a large residual, and returns TGraph without those points
        ## Helps the linear correction remain accurate when one or more fits from fit_y_slices fails
        def remove_outliers(gr):                                                    # gr input is a TGraphAsymmErrors TObject
            x         = carray('d', [])                                             # Initialize the arrays to create the filteres TGraph output
            y         = carray('d', [])
            xerr_low  = carray('d', [])
            xerr_high = carray('d', [])
            yerr      = carray('d', [])
            median    = np.median(list(filter(lambda x: abs(x)>1e-1 and abs(x)<2, [gr.GetY()[i] for i in range(nbins)])))
            n_points  = gr.GetN()
            for i in range(n_points):
                if abs(gr.GetY()[i] - median) < 0.15:                               # Only accept points who have a residual between resolution fit means and the median <150ps
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
        self.ft.save_files(hadjust_1, self.savepath,"{}_{}_".format(self.energy,self.xtal[2]),"dt_adjustment") # Saving post-fit causes a seg fault in terminal mode ROOT

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

        self.ft.save_files(hadjust_1, self.savepath,"{}_{}_".format(self.energy,self.xtal[2]),"dt_adjustment_fitted") # Post-fit plots DO show correctly on EOS-webpage, so save pre- and post-fit 
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
        max_n_refits  = 50
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

        xs              = carray('d', [ x[2] for x in bins])
        xerr            = carray('d', [(x[1]-x[0])/2. for x in bins])
        means           = carray('d', [ x[0] for x in hh_1_tmp])
        means_err       = carray('d', [ x[1] for x in hh_1_tmp])
        resolutions     = carray('d', [ x[0] for x in hh_2_tmp])
        resolutions_err = carray('d', [ x[1] for x in hh_2_tmp])
        hh_1 = TGraphAsymmErrors(len(bins), xs, means       , xerr, xerr, means_err      , means_err      ) 
        hh_2 = TGraphAsymmErrors(len(bins), xs, resolutions , xerr, xerr, resolutions_err, resolutions_err) 

        return hh_1, hh_2

