#!/usr/bin/python

## By Michael Plesser
## Sloppy script, under development but pushed so others can see while I'm on holiday
## Don't judge meeeee

import ROOT
from numpy import roots, isreal

def find_target_center(t_tree, xtal):  

    print "Finding target center..."

    ## Hodoscope center, not beam center, but useful for reference
    # Finds the first and last bins above some threshold and takes the mid-bin between them.
    # This prevents uneven distributions from skewing the result if you just used GetMean()
    hodox = TH1F("hodox", "", 100, -20, 20)
    hodoy = TH1F("hodoy", "", 100, -20, 20)
    t_tree.Draw("fitResult[0].x()>>hodox")
    t_tree.Draw("fitResult[0].y()>>hodoy")
    threshold = hodox.GetMaximum()/3.
    threshold = hodoy.GetMaximum()/3.
    hodo_x_center  = hodox.GetBinCenter( (hodox.FindFirstBinAbove(threshold) + hodox.FindLastBinAbove(threshold)) / 2 )
    hodo_y_center  = hodoy.GetBinCenter( (hodoy.FindFirstBinAbove(threshold) + hodoy.FindLastBinAbove(threshold)) / 2 )

    ## Simpler but less accurate. This method takes the ratio of the two amplitudes vs Y, fits it, and defines center as where the ratio is 1
    def ratio_method(hodo_center):

        ## Sorry for confusing names. consider "x" as in dx, simply denoting some length. It might be X or Y, depending on which position you're at. See above
        ampbias = 0.866
        axis = "fitResult[0].y()"
        fit_range = [hodo_center - 2.0, hodo_center + 2.0]
        hx    = ROOT.TH2F("hx", "", 100, fit_range[0], fit_range[1], 100, 0, 10)               
        x_var = "fit_ampl[{0}]/({1}*fit_ampl[{2}]):{3}>>hx".format(xtal[0], ampbias, xtal[1], axis)   # Amp ratio: amp1/(calibrate*amp2) vs (X or Y)
        basic_cut = "fit_chi2[{0}]>0 && fit_chi2[{1}]>0 && fabs(fitResult[0].y())<20 && fabs(fitResult[0].x())<20".format(xtal[0], xtal[1])
        x_cut = "{0}*fit_ampl[{1}]>0".format(ampbias, xtal[1]) + " && " + basic_cut                                     # Avoid /0 errors
        t_tree.Draw(x_var, ROOT.TCut(x_cut), "COLZ")                                                                    # Draw the ratio of the two xtal's amplitudes against (X or Y) into 'hx'
        poly2 = ROOT.TF1("poly2", "pol2", fit_range[0], fit_range[1])                                                   # Fit the plot, pol2 works well, but is not physically justified
        poly2.SetParameters(5, -1, 0.1)                                                                                 # Get the parameters in the right ballpark to start
        hx.Fit("poly2", "QR")
        p         = poly2.GetParameters()                                                                               # Get the parameters from the fit
        solutions = [s for s in roots([p[2],p[1],p[0]-1]) if isreal(s) and (s>fit_range[0]) and (s<fit_range[1])]       # (p[0]-1 b/c we want to solve for where the pol2 == 1)

        ## There should only be 1 solution in the fit range. If there are 0 or >1, abort!
        if len(solutions) != 1: 
            return hodo_center
        else: 
            return solutions[0]

    x_center = hodo_x_center

    if xtal[2] == 'C3down':
        y_center = ratio_method(hodo_y_center)
    else:
        y_center = hodo_y_center
    
    #print "Dip_residual center: {0:.2f} Ratio center: {1:.2f}".format(found_centers[0], found_centers[1])
    print "Hodoscope centers: {0:.2f}, {1:.2f}".format(hodo_x_center, hodo_y_center)
    print "X center: {0:.2f}".format(x_center)
    print "Y center: {0:.2f}".format(y_center)

    return x_center, y_center

def find_C3_center(xtal, target_center):
    position = xtal[2]
    if position == 'C3':
        return target_center
    elif position == 'C3down':
        return target_center + 11
    elif position == 'C2':
        return target_center + 22

def main():

    ROOT.gSystem.Load("/afs/cern.ch/user/m/mplesser/H4Analysis/CfgManager/lib/libCFGMan.so")
    ROOT.gSystem.Load("/afs/cern.ch/user/m/mplesser/H4Analysis/lib/libH4Analysis.so")
    ROOT.gSystem.Load("/afs/cern.ch/user/m/mplesser/H4Analysis/DynamicTTree/lib/libDTT.so")

    C3file      = '/eos/user/m/mplesser/matrix_time_analysis_recos/ntuples_C3_160_18/compiled_roots/ECAL_H4_Oct2018_160MHz_18deg_compiled_C3.root'      , ['C3','','C3']
    C3downfile  = '/eos/user/m/mplesser/matrix_time_analysis_recos/ntuples_C3ud_160_18/compiled_roots/ECAL_H4_Oct2018_160MHz_18deg_compiled_C3down.root', ['C3','C2','C3down']
    C2file      = '/eos/user/m/mplesser/matrix_time_analysis_recos/ntuples_C2_160_18/compiled_roots/ECAL_H4_Oct2018_160MHz_18deg_compiled_C2.root'      , ['C2','','C2']

    bins = 90,-5,25,1000,-5,5

    # This is a horrible, ugly, lazy way to do this.
    # Sorry, it WILL be fixed after the holidays...

    C3_tfile      = ROOT.TFile(C3file[0])
    C3_h4         = C3_tfile.Get("h4")
    target_center = find_target_center(C3_h4, C3file[1])
    C3_center     = find_C3_center(C3file[1], target_center[1])
    dt   = "fit_time[C3]  - fit_time[C2]"
    dr   = "{0} - fitResult[0].y()".format(C3_center)
    cut  = "n_tracks==1 && "
    cut += "fit_time[C3]>0 && fit_time[C2]>0 && "
    cut += "fabs(fitResult[0].x() - {0})<3 && ".format(target_center[0])
    cut += "fabs(fitResult[0].y() - {0})<5 && ".format(target_center[1])
    cut += "1"
    C3_lincorr    = ROOT.TH2F("C3_lincorr","",bins[0], bins[1], bins[2], bins[3], bins[4], bins[5])
    C3_h4.Draw(dt+":"+dr+">>C3_lincorr", ROOT.TCut(cut))
    C3_lincorr.FitSlicesY()
    C3_lincorr_1  = C3_tfile.Get("C3_lincorr_1")


    C3down_tfile     = ROOT.TFile(C3downfile[0])
    C3down_h4        = C3down_tfile.Get("h4")
    target_center    = find_target_center(C3down_h4, C3downfile[1])
    C3_center        = find_C3_center(C3downfile[1], target_center[1])
    dt   = "fit_time[C3]  - fit_time[C2]"
    dr   = "{0} - fitResult[0].y()".format(C3_center)
    cut  = "n_tracks==1 && "
    cut += "fit_time[C3]>0 && fit_time[C2]>0 && "
    cut += "fabs(fitResult[0].x() - {0})<3 && ".format(target_center[0])
    cut += "fabs(fitResult[0].y() - {0})<5 && ".format(target_center[1])
    cut += "1"
    C3down_lincorr   = ROOT.TH2F("C3down_lincorr","",bins[0], bins[1], bins[2], bins[3], bins[4], bins[5])
    C3down_h4.Draw(dt+":"+dr+">>C3down_lincorr", ROOT.TCut(cut))
    C3down_lincorr.FitSlicesY()
    C3down_lincorr_1 = C3down_tfile.Get("C3down_lincorr_1")


    C2_tfile      = ROOT.TFile(C2file[0])
    C2_h4         = C2_tfile.Get("h4")
    target_center = find_target_center(C2_h4, C2file[1])
    C3_center     = find_C3_center(C2file[1], target_center[1])
    dt   = "fit_time[C3]  - fit_time[C2]"
    dr   = "{0} - fitResult[0].y()".format(C3_center)
    cut  = "n_tracks==1 && "
    cut += "fit_time[C3]>0 && fit_time[C2]>0 && "
    cut += "fabs(fitResult[0].x() - {0})<3 && ".format(target_center[0])
    cut += "fabs(fitResult[0].y() - {0})<5 && ".format(target_center[1])
    cut += "1"
    C2_lincorr    = ROOT.TH2F("C2_lincorr","",bins[0], bins[1], bins[2], bins[3], bins[4], bins[5])
    C2_h4.Draw(dt+":"+dr+">>C2_lincorr", ROOT.TCut(cut))
    C2_lincorr.FitSlicesY()
    C2_lincorr_1  = C2_tfile.Get("C2_lincorr_1")

    
    h = ROOT.TH1D("h","",bins[0], bins[1], bins[2])
    h.Add(C3_lincorr_1)
    h.Add(C2_lincorr_1)
    h.Add(C3down_lincorr_1)
    
    root_savefile = ROOT.TFile("/afs/cern.ch/user/m/mplesser/extended_lin_corr.root", "recreate")
    root_savefile.cd()              
    h.Write()


if __name__=="__main__":
    main()
