#!/usr/bin/python

## By Michael Plesser

import sys
from array import array
from numpy import roots, isreal
from ROOT import TFile, TH1F, TH2F, TF1, TGraph, TGraphErrors, TLine

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

    def start_log_file(self):
        ## Start a log file
        with open(self.savepath+self.xtal[2]+'_log.txt','w') as f:
            f.write(self.xtal[2]+" "+self.args.e+" energy log file\n\n")

    ## Get crystal pair from Position (C3_down = ['C3', 'C2'], C3_up = ['C3', 'C4'])
    def get_xtals(self):
        tfile    = TFile(self.file)
        infotree = tfile.Get("info")
        infotree.GetEntry(0)
        position = infotree.Positions
        if   (position == 2.5) or (position == 'C3down') :   return ['C3', 'C2', 'C3down' ]
        elif (position == 3.5) or (position == 'C3up'  ) :   return ['C3', 'C4', 'C3up'   ]
        elif                      (position == 'C3left' ):   return ['C3', 'B3', 'C3left' ]
        elif                      (position == 'C3right'):   return ['C3', 'D3', 'C3right']
        else:   sys.exit("\nUnrecognized crystal position, aborting...")

    ## Get the amplitude calibration coefficient
    def amp_calibration_coeff(self):
        if self.args.temp   == '18deg':
            if   self.xtal[2]  == 'C3up'   :  amp_calibration = 0.944866 
            elif self.xtal[2]  == 'C3down' :  amp_calibration = 0.866062 
            elif self.xtal[2]  == 'C3left' :  amp_calibration = 0.905111 
            elif self.xtal[2]  == 'C3right':  amp_calibration = 0.995219 
        elif self.args.temp ==  '9deg':
            if   self.xtal[2]  == 'C3up'  :  amp_calibration = 0.926351
            elif self.xtal[2]  == 'C3down':  amp_calibration = 0.849426
            elif self.xtal[2]  == 'C3left' :  amp_calibration = 0.905111 
            elif self.xtal[2]  == 'C3right':  amp_calibration = 0.995219 
        return str(amp_calibration)
    
    ## Find the center of the target
    ## In general one dimension's center will have symmetry so we can just use the hodoscope mean (IE for C3up/down X is mostly constant, for C3left/right Y is then constant)
    def find_target_center(self):  

        t_file  = TFile(self.file)
        t_tree  = t_file.Get("h4")
        
        ## Hodoscope center, not beam center, but useful for reference
        hodox = TH1F("hodox", "", 100, -20, 20)
        hodoy = TH1F("hodoy", "", 100, -20, 20)
        t_tree.Draw("X>>hodox")
        threshold = hodox.GetMaximum()/10.
        hodo_x_center  = hodox.GetBinCenter( (hodox.FindFirstBinAbove(threshold) + hodox.FindLastBinAbove(threshold)) / 2 )
        t_tree.Draw("Y>>hodoy")
        threshold = hodoy.GetMaximum()/10.
        hodo_y_center  = hodoy.GetBinCenter( (hodoy.FindFirstBinAbove(threshold) + hodoy.FindLastBinAbove(threshold)) / 2 )

        ## Think which axis has a shower-sharing dt dependance. That's the one we use special tricks for, and for the other we just use the hodoscope center
        if   (self.xtal[2] == 'C3down') or (self.xtal[2] == 'C3up'   ): 
            hodo_center = hodo_y_center
            axis        = 'Y'
        elif (self.xtal[2] == 'C3left') or (self.xtal[2] == 'C3right'): 
            hodo_center = hodo_x_center
            axis        = 'X'
       
        ## In the dt vs (X or Y) plot there was a dip feature determined to be electrons entering the gap between crystals
        ## This fn takes advantage of this to find center as the max residual bin off of the linear fitting.
        def dip_residual_method():
            
            hh  = TH2F("hh","",30, hodo_center - 4.0, hodo_center + 4.0, 100,-2,2)
            t_tree.Draw("(fit_time[{0}]-fit_time[{1}]):{2}>>hh".format(self.xtal[0], self.xtal[1], axis),"","COLZ")     # Plot dt vs (X or Y)
            hh.FitSlicesY()                                                                                             # Fit slices with gaussians
            gr  = TGraphErrors(t_file.Get("hh_1"))                                                                      # hh_1 is the histo of means from FitSlicesY

            ## Sorry for the confusing names. We plot dt vs (X or Y), so dt is our y_var, and dx is our x_var, the distance term (ie X OR Y)
            points = range(gr.GetN())
            dx     = array('d', gr.GetX())                                                                    
            dt     = array('d', gr.GetY())
            p1     = TF1("p1","pol1")
            TGraph(gr.GetN(), dx, dt).Fit("p1","WQ")                                                       # Fit dt_mean vs Y linearly

            ## Sum each 3 consecutive residuals, take the max from this value's abs(), and the middle index is where the "dip" is farthest from the fit, the "center"
            res         = [dt[i] - p1.Eval(dx[i]) for i in points     ]                                    # The residual between the fit and data
            sum_res     = [abs(sum(res[i:i+3]))   for i in points[:-2]]                                    # Sum 3 residuals ([:-2] to avoid index out of range)
            axis_center = dx[sum_res.index(max(sum_res))+1]                                                # +1 b/c we index the 1st out of 3 residuals, but we want the middle one
            gr.Draw()
            
            return axis_center

        ## Simpler but less accurate. This method takes the ratio of the two amplitudes vs Y, fits it, and defines center as where the ratio is 1
        def ratio_method():

            ## Sorry for confusing names. consider "x" as in dx, simply denoting some length. It might be X or Y, depending on which position you're at. See above
            fit_range = [hodo_center - 2.0, hodo_center + 2.0]
            hx    = TH2F("hx", "", 100, fit_range[0], fit_range[1], 100, 0, 10)               
            x_var = "fit_ampl[{0}]/({1}*fit_ampl[{2}]):{3}>>hy".format(self.xtal[0], self.ampbias, self.xtal[1], axis)  # amp1/(calibrate*amp2) vs (X or Y)
            x_cut = "{0}*fit_ampl[{1}]>100".format(self.ampbias, self.xtal[1])                                          # Avoid /0 errors
            t_tree.Draw(x_var, x_cut)                                                                                   # Draw the ratio of the two xtal's amplitudes against (X or Y) into 'hx'
            poly2 = TF1("poly2", "pol2", 3, 6)                                                                          # Fit the plot, pol2 works well, but is not physically justified
            poly2.SetParameters(5, -1, 0.1)                                                                             # Get the parameters in the right ballpark to start
            hx.Fit("poly2", "QR")
            p         = poly2.GetParameters()                                                                           # Get the parameters from the fit
            solutions = [sol for sol in roots([p[2],p[1],p[0]-1]) if isreal(sol)]                                       # Find roots of the quadratic, and make sure they're real
                                                                                                                        # (p[0]-1 b/c we want to solve for where the pol2 == 1)

            sol_in_range = [s for s in solutions if (s>fit_range[0]) and (s<fit_range[1])]                              # Only take solutions in the defined fit_range

            ## There should only be 1 solution in the fit range. If there are 0 or >1, abort!
            if   len(sol_in_range) == 2: sys.exit("Error!!! {}_center fitting gave two solutions in the range! Aborting... \n".format(axis))
            elif len(sol_in_range) == 0: sys.exit("Error!!! {}_center fitting gave no  solutions in the range! Aborting... \n".format(axis))
            else                       : axis_center = sol_in_range[0]

            return axis_center
       
        ## Find the center using the dip_residual_method, and if that answer is too far off, try the ratio_method, and if THAT doesn't work, abort.
        def find_and_check_center():
            center = dip_residual_method()
            if abs(center - hodo_center) > 3.:
                ratio_center = ratio_method()
                if abs(ratio_center - hodo_center) > 3.: 
                    sys.exit("Neither center-finding algortihm succeeded. Aborting... \n")
                else: 
                    center = ratio_center
            return center

        ## Take the right x_center and y_center based on the run position
        if   axis == 'X':
            x_center = find_and_check_center()
            y_center = hodo_y_center
        elif axis == 'Y':
            x_center = hodo_x_center
            y_center = find_and_check_center()

        ## Some info for the log file
        with open(self.savepath+self.xtal[2]+'_log.txt', 'a') as f:
            f.write("Target center position:\n")
            f.write("\tX_center:\n\t\t {} \n  ".format(x_center))
            f.write("\tY_center:\n\t\t {} \n\n".format(y_center))
        
        return str(x_center), str(y_center)

