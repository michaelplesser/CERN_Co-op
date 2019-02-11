#!/usr/bin/python

## By Michael Plesser
## Sloppy script, under development but pushed so others can see while I'm on holiday
## Don't judge meeeee

import ROOT
from numpy import roots, isreal

def find_target_center(files, trees):

    ri.axis
    centers = []
    print "Finding target centers..."

    for file, t_tree in zip(files, trees):

        filei   = file[0]
        xtal    = file[1]

        ## Hodoscope center, not beam center, but useful for reference
        # Finds the first and last bins above some threshold and takes the mid-bin between them.
        # This prevents uneven distributions from skewing the result if you just used GetMean()
        hodox = ROOT.TH1F("hodox", "", 100, -20, 20)
        hodoy = ROOT.TH1F("hodoy", "", 100, -20, 20)
        t_tree.Draw("fitResult[0].x()>>hodox")
        t_tree.Draw("fitResult[0].y()>>hodoy")
        threshold = hodox.GetMaximum()/3.
        threshold = hodoy.GetMaximum()/3.
        hodo_x_center  = hodox.GetBinCenter( (hodox.FindFirstBinAbove(threshold) + hodox.FindLastBinAbove(threshold)) / 2 )
        hodo_y_center  = hodoy.GetBinCenter( (hodoy.FindFirstBinAbove(threshold) + hodoy.FindLastBinAbove(threshold)) / 2 )

        x_center = hodo_x_center
        y_center = hodo_y_center
        print "{0:^9s}:".format(xtal[2]), "X center: {0:.2f}\t".format(x_center), "Y center: {0:.2f}".format(y_center)
        centers.append([x_center, y_center])

        hodox.Delete()
        hodoy.Delete()

    return centers

def find_C3_center(files, centers):

    ri      = runinfo(files[1][1])
    sign    = ri.axis_sign
    C3_centers  = []
    for filei, centers in zip(files, centers):
        
        xtal = filei[1]
        if   'x' in ri.axis:
            center = centers[0]     # x_center
        elif 'y' in ri.axis:
            center = centers[1]     # y_center

        position = xtal[2]
        if   position == 'C3':
            C3_centers.append(center)
        elif len(position) > 2:         # IE C3left, C3right, etc
            C3_centers.append(center + sign*11)
        elif len(position) == 2:        # IE C4, B3, D3, etc
            C3_centers.append(center + sign*22)
    return C3_centers

class runinfo:
    def __init__(self, xtal):
        if   xtal[2] == 'C3down':
            self.axis        = 'fitResult[0].y()'
            self.ampbias     = 0.866
            self.axis_sign   = 1    # This is a confusing var. From somewhere between the xtals (C3 and C2) do you + or - from the y-coord to get back to C3? Add, so sign=+1 in this case
        elif xtal[2] == 'C3up':
            self.axis        = 'fitResult[0].y()'
            self.ampbias     = 0.945
            self.axis_sign   = -1
        elif xtal[2] == 'C3left':
            self.axis        = 'fitResult[0].x()'
            self.ampbias     = 0.905
            self.axis_sign   = 1
        elif xtal[2] == 'C3right':
            self.axis        = 'fitResult[0].x()'
            self.ampbias     = 0.905
            self.axis_sign   = -1
        else:
            print xtal[2], 'not found'
            self.axis   = 'N/A'
            self.ampbias= 1

def stitch_and_plot(files):

    ri      = runinfo(files[1][1])
    axis    = ri.axis

    f0 = files[0]
    f1 = files[1]
    f2 = files[2]

    f0_tfile        = ROOT.TFile(f0[0])
    f1_tfile        = ROOT.TFile(f1[0])
    f2_tfile        = ROOT.TFile(f2[0])
    
    f0_h4           = f0_tfile.Get("h4")
    f1_h4           = f1_tfile.Get("h4")
    f2_h4           = f2_tfile.Get("h4")
    h4_trees        = [f0_h4, f1_h4, f2_h4]

    target_centers  = find_target_center(files, h4_trees)
    C3_centers      = find_C3_center(files, target_centers)

    bins  = 70,-35,35,1000,-7,7
    phase_corr = "int((fit_time[C3] - fit_time[MCP1] + fit_time[VFE_CLK])/{0})*{0}".format(6.238)
    dt     = "fit_time[C3] - fit_time[MCP1] + fit_time[VFE_CLK] - %s" % phase_corr
    ##dt    = "fit_time[C3]  - fit_time[{0}]".format(f1[1][1])
    ##cut   = "n_tracks==1 && fit_time[C3]>0 && fit_time[{0}]>0 && fit_time[{1}]>0 && ".format(f1[1][0], f1[1][1])
    cut   = "n_tracks==1 && fit_time[C3]>0 && fit_ampl[MCP1]>50 && fit_chi2[C3]<100 && "

    f_cut  = "fabs(fitResult[0].x() - {0})<5 && fabs(fitResult[0].y() - {1})<5 && "

    print "File 1: ", f0[0]
    f0_tfile.cd()
    dr              = "{0} - {1}".format(C3_centers[0], axis)
    f0_cut          = cut
    f0_cut         += f_cut.format(target_centers[0][0], target_centers[0][1])
    f0_cut         += "fit_chi2[{0}]>0 && fit_chi2[{0}]<100".format(f0[1][0]) 
    f0_lincorr      = ROOT.TH2F("f0_lincorr","",bins[0], bins[1], bins[2], bins[3], bins[4], bins[5])
    f0_h4.Draw(dt+":"+dr+">>f0_lincorr", ROOT.TCut(f0_cut))
    f0_lincorr.FitSlicesY()
    f0_lincorr_1    = f0_tfile.Get("f0_lincorr_1")

    print "File 2: ", f1[0]
    f1_tfile.cd()
    dr              = "{0} - {1}".format(C3_centers[1], axis)
    f1_cut          = cut
    f1_cut         += f_cut.format(target_centers[1][0], target_centers[1][1])
    f1_cut         += "fit_chi2[{0}]>0 && fit_chi2[{0}]<100 && fit_chi2[{1}]>0 && fit_chi2[{1}]<100".format(f1[1][0], f1[1][1]) 
    f1_lincorr      = ROOT.TH2F("f1_lincorr","",bins[0], bins[1], bins[2], bins[3], bins[4], bins[5])
    f1_h4.Draw(dt+":"+dr+">>f1_lincorr", ROOT.TCut(f1_cut))
    f1_lincorr.FitSlicesY()
    f1_lincorr_1    = f1_tfile.Get("f1_lincorr_1")

    print "File 3: ", f2[0]
    f2_tfile.cd()
    dr              = "{0} - {1}".format(C3_centers[2], axis)
    f2_cut          = cut
    f2_cut         += f_cut.format(target_centers[2][0], target_centers[2][1])
    f2_cut         += "fit_chi2[{0}]>0 && fit_chi2[{0}]<100".format(f2[1][0]) 
    f2_lincorr      = ROOT.TH2F("f2_lincorr","",bins[0], bins[1], bins[2], bins[3], bins[4], bins[5])
    f2_h4.Draw(dt+":"+dr+">>f2_lincorr", ROOT.TCut(f2_cut))
    f2_lincorr.FitSlicesY()
    f2_lincorr_1    = f2_tfile.Get("f2_lincorr_1")

    h = ROOT.TH1D("h","",bins[0], bins[1], bins[2])
    h.Add(f0_lincorr_1)
    h.Add(f1_lincorr_1)
    h.Add(f2_lincorr_1)
    
    root_savefile = ROOT.TFile("/afs/cern.ch/user/m/mplesser/tmp/plots/{0}_extended_lin_corr.root".format(files[1][1][2]), "recreate")
    root_savefile.cd()              
    h.Write()

def main():

    ROOT.gROOT.ProcessLine("gErrorIgnoreLevel = kError;")
    #ROOT.gROOT.SetBatch(ROOT.kTRUE)
    ROOT.gStyle.SetOptStat(0)

    ## allows you you to use fitResult.x() and y()
    ROOT.gSystem.Load("/afs/cern.ch/user/m/mplesser/H4Analysis/CfgManager/lib/libCFGMan.so")
    ROOT.gSystem.Load("/afs/cern.ch/user/m/mplesser/H4Analysis/lib/libH4Analysis.so")
    ROOT.gSystem.Load("/afs/cern.ch/user/m/mplesser/H4Analysis/DynamicTTree/lib/libDTT.so")

    ### Files ###
    C3file      = '/eos/user/m/mplesser/matrix_time_analysis_recos/ntuples_C3_160_18/compiled_roots/ECAL_H4_Oct2018_160MHz_18deg_onefileperenergy_C3.root'       , ['C3','','C3']

    #C3down
    C3downfile  = '/eos/user/m/mplesser/matrix_time_analysis_recos/ntuples_C3ud_160_18/compiled_roots/ECAL_H4_Oct2018_160MHz_18deg_onefileperenergy_C3down.root' , ['C3','C2','C3down']
    C2file      = '/eos/user/m/mplesser/matrix_time_analysis_recos/ntuples_C2_160_18/compiled_roots/ECAL_H4_Oct2018_160MHz_18deg_onefileperenergy_C2.root'       , ['C2','','C2']

    #C3up
    C3upfile    = '/eos/user/m/mplesser/matrix_time_analysis_recos/ntuples_C3ud_160_18/compiled_roots/ECAL_H4_Oct2018_160MHz_18deg_onefileperenergy_C3up.root'   , ['C3','C4','C3up']
    C4file      = '/eos/user/m/mplesser/matrix_time_analysis_recos/ntuples_C4_160_18/compiled_roots/ECAL_H4_Oct2018_160MHz_18deg_onefileperenergy_C4.root'       , ['C4','','C4']

    #C3left
    C3leftfile  = '/eos/user/m/mplesser/matrix_time_analysis_recos/ntuples_C3lr_160_18/compiled_roots/ECAL_H4_Oct2018_160MHz_18deg_compiled_C3left.root' , ['C3','B3','C3left']
    B3file      = '/eos/user/m/mplesser/matrix_time_analysis_recos/ntuples_B3_160_18/ECAL_H4_October2018_13403.root'                                     , ['B3','','B3']
    
    #C3right
    C3rightfile = '/eos/user/m/mplesser/matrix_time_analysis_recos/ntuples_C3lr_160_18/compiled_roots/ECAL_H4_Oct2018_160MHz_18deg_compiled_C3right.root', ['C3','D3','C3right']
    D3file      = '/eos/user/m/mplesser/matrix_time_analysis_recos/ntuples_D3_160_18/ECAL_H4_October2018_13410.root'                                     , ['D3','','D3']
    
    C3down_files  = [C3file, C3downfile , C2file]
    C3up_files    = [C3file, C3upfile   , C4file]
    C3left_files  = [C3file, C3leftfile , B3file]
    C3right_files = [C3file, C3rightfile, D3file]

    print
    stitch_and_plot(C3down_files)
    print
    stitch_and_plot(C3up_files)
    print
    #stitch_and_plot(C3left_files)
    print
    #stitch_and_plot(C3right_files)

if __name__=="__main__":
    main()
