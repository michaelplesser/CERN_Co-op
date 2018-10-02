#!/usr/bin/python

## By Michael Plesser

import sys
from ROOT import TFile, TH1F, TH2F, TF1

class RunInfoTools:

    def __init__(self, args, savepath, filei):
        self.args = args
        
        self.file     = filei[0]
        self.savepath = savepath

        self.xtal                    = self.get_xtals()
        self.ampbias                 = self.amp_calibration_coeff()
        self.x_center, self.y_center = self.find_target_center()

        ## Define Aeff since it is used in many places
        self.Aeff    = "pow( 2 / ( (1/pow(fit_ampl[{0}]/b_rms[{0}], 2)) + (1/pow({1}*fit_ampl[{2}]/b_rms[{2}],2)) ) , 0.5)".format(self.xtal[0],self.ampbias,self.xtal[1])     


    ## Get crystal pair from Position (C3_down = ['C3', 'C2'], C3_up = ['C3', 'C4'])
    def get_xtals(self):
        tfile    = TFile(self.file)
        infotree = tfile.Get("info")
        infotree.GetEntry(0)
        position = infotree.Positions
        if   position == 2.5:   return ['C3', 'C2', 'C3down']
        elif position == 3.5:   return ['C3', 'C4', 'C3up'  ]
        else:   sys.exit("\nUnrecognized crystal position, aborting...")

    ## Get the amplitude calibration coefficient
    def amp_calibration_coeff(self):
        if self.args.temp   == '18deg':
            if   self.xtal[1]  == 'C4':  amp_calibration = 0.944866 
            elif self.xtal[1]  == 'C2':  amp_calibration = 0.866062 
        elif self.args.temp ==  '9deg':
            if   self.xtal[1]  == 'C4':  amp_calibration = 0.926351
            elif self.xtal[1]  == 'C2':  amp_calibration = 0.849426
        return str(amp_calibration)
    
    ## Find the center of the target
    ## X_center is found by taking the mid-point bin between the first and last bins that have bincontent above a set threshold
    ## Y_center is trickier. The amplitude response ratio of the two crystals is plotted against Y[0]. It's then fitted with a 
    ##  pol2, and solved for where the ratio == 1. An electron incident on the edge should respond the same in both crystals.
    def find_target_center(self):  

        t_file  = TFile(self.file)
        t_tree  = t_file.Get("h4")
        fit_range = 2,7                                                     # pol2 is a good fit, but gives 2 solutions. If in the future 
                                                                            # we have y-centers that vary more widely then using pol2 may cause
                                                                            # problems. fit_range auto-setting is TBD and could resolve this potential issue.
        hx = TH1F("hx", "", 100, -20, 20)
        hy = TH2F("hy", "", 100, fit_range[0], fit_range[1], 100,0,10)      # Some what manually tuned... Auto-tuning TBD. If it fails:
                                                                            # Check "dampl:Y[0]", and make sure that y=1 in fit_range
        # x_center found by taking the mid-bin between the first and last bins that are above a threshold value
        t_tree.Draw("X[0]>>hx")
        threshold = hx.GetMaximum()/10
        lower_bin = hx.FindFirstBinAbove(threshold)
        upper_bin = hx.FindLastBinAbove(threshold)
        x_center  = hx.GetBinCenter((upper_bin+lower_bin)/2)

        # For y_center, the crystal edge is found by locating where the fit_ampl's of the two xtals are equal (ratio==1)
        y_var = "fit_ampl[{}]/({}*fit_ampl[{}]):Y[0]>>hy".format(self.xtal[0], self.ampbias, self.xtal[1])
        y_cut = "{}*fit_ampl[{}]>500".format(self.ampbias, self.xtal[1])
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
        elif ypluslogic                 : y_center = yplus                            # yplus  is in the range and yminus isn't
        elif yminuslogic                : y_center = yminus                           # yminus is in the range and yplus  isn't
        else                            : sys.exit("Error!!! Y_center fitting gave no  solutions in the range! Aborting... \n") 

        # Some info for the log file
        with open(self.savepath+self.xtal[2]+'_log.txt', 'a') as f:
            f.write("Target center position:\n")
            f.write("\tX_center:\n\t\t {} \n".format(x_center))
            f.write("\tY_center:\n\t\t {} \n\n".format(y_center))
        
        return str(x_center), str(y_center)

