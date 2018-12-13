#!/usr/bin/python

## By Michael Plesser
## Sloppy script, under development but pushed so others can see while I'm on holiday
## Don't judge meee

from ROOT import *
from array import array

def find_fit_range(h):
    ## The double crystal ball converges faster with a selected fit range for the mean
    ## This function uses a gaussian to find it
    bini = 1
    h_p   = h.ProjectionY("h_p", bini, bini)
    min_n_events = 1000
    while h_p.GetEntries()<min_n_events:
        bini += 1
        h_p   = h.ProjectionY("h_p", bini, bini)
    h_p.Fit("gaus","QRM","",0,8.317)
    gaus.SetParameters(100, h_p.GetBinCenter(h_p.GetMaximumBin()), 0.05)
    gaus.SetParLimits(2,0.01,0.2)
    h_p.Fit("gaus","QRBM","",0,8.317)
    mean, sigma = gaus.GetParameter(1), gaus.GetParameter(2)
    return [mean - 10*sigma, mean + 10*sigma] 

def find_mcp_resolution(h):
    ## The MCP resolution vs A/n curve
    def mcp_res_fit(x,par):
        if x[0]>0:
            fit = pow(pow(par[0]/(x[0]),2) + pow( par[1]/pow(x[0],0.5), 2) + pow(par[2],2), 0.5)                                
            return fit
    mcp_res_fit = TF1('mcp_res_fit', mcp_res_fit, 50, 400, 3) 
    mcp_res_fit.SetParameters(1.139e-4, 0.1189, 4.458e-3)                           
    mcp_res_fit.Draw()
    mcp_savefile = TFile("/afs/cern.ch/user/m/mplesser/tmp/mcp_res.root", "recreate")
    mcp_savefile.cd()              
    mcp_res_fit.Write()
    raw_input("hodl")

    ## Find the mcp resolution contribution in each bin on the TH2F
    bin_edges = [] 
    bin_mcp_res = []
    for bin in range(1, h.GetNbinsX()+2):   bin_edges.append(h.GetXaxis().GetBinLowEdge(bin))   # Get bin edges
    for bin in range(h.GetNbinsX()):
        var     = 'fit_ampl[MCP1]/b_rms[MCP1]'
        cuts    = "fit_ampl[MCP1]>200 && "
        cuts   += "fit_chi2[MCP1]<10 && fit_chi2[MCP1]>0.1 && "
        cuts   += "n_tracks==1 && "
        cuts   += "fit_ampl[C3]/b_rms[C3]>={0} && ".format(bin_edges[bin])
        cuts   += "fit_ampl[C3]/b_rms[C3]< {0} && ".format(bin_edges[bin+1])
        cuts   += "1"

        bins = 100,50,400
        hmcp = TH1F("hmcp","", bins[0], bins[1], bins[2])
        h4.Draw(var+">>hmcp",TCut(cuts))
        mean_mcp_aeff = hmcp.GetMean()                                                          # Get mean MCP aeff in each bin
        bin_mcp_res.append(mcp_res_fit.Eval(mean_mcp_aeff))                                     # Use the fit function to get the avg mcp resolution
        hmcp.Delete()

    return bin_mcp_res

def fit_y_slices(h4, h):
    
    def subtract_mcp_res(mcp_res, r, bin):
        return pow( r*r - mcp_res[bin-1]*mcp_res[bin-1], 0.5)
    mcp_res_by_bin = find_mcp_resolution(h)
    
    fit_range = find_fit_range(h)

    ## Use a c version of the double crystal ball function. Faster...
    gROOT.ProcessLine(".x /afs/cern.ch/user/m/mplesser/my_git/CERN_Co-op/DtPlotter/utilities/Double_Crystal_Ball_Fit.C")
    dcb =  TF1("dcb",  double_xtal_ball, fit_range[0], fit_range[1], 5)                 # 0 to 7 is my fit range
    dcb.SetParNames("c","mu","sig","A","n")              
    
    ## Set par. limits to help the minimizer converge
    dcb.SetParLimits(0 , 0              ,99999          )                               # c >= 0
    dcb.SetParLimits(1 , fit_range[0]   ,fit_range[1]   )                               # mu between -1 and 1
    dcb.SetParLimits(2 , 0.01           ,0.2            )                               # sigma between 10 and 200ps
    dcb.SetParLimits(3 , 0              ,9              )                               # A1 >= 0
    dcb.SetParLimits(4 , 0              ,9              )                               # n  >= 0
    dcb.SetParameters(100, sum(fit_range)/2., 0.05, 1, 1)                               # Some guesses to help things along

    bins     = []
    hh_1_tmp = []
    hh_2_tmp = []
    n_bins   = h.GetXaxis().GetNbins()
    for bini in range(1, n_bins+1):

        h_p = h.ProjectionY('h_p',bini,bini)                            # Get the distribution in y as  TH1 for bin# 'bini'
        refit_counter  = 0
        max_n_refits   = 1
        min_n_events   = 200
        if (int(h_p.GetEntries()) >= min_n_events): 
            h_p.Fit("gaus","QRM","",fit_range[0],fit_range[1])          # Use a gaussian to quickly get a good init value for peak, mean, and sigma
            p_gaus =  gaus.GetParameters()
            dcb.SetParameters(p_gaus[0], p_gaus[1], p_gaus[2], 1, 1)    # Use the gaussian parameters to help the dcb
            fit    = h_p.Fit("dcb", "QBRM")                             # Try the fit again
            status =  gMinuit.fCstatu                                   # Get the fit status, IE 'OK', 'CONVERGED', 'FAILED'
            h_p.Draw()
            while (not 'OK' in status) and (not 'CONVERGED' in status) and (not 'LIMIT_REACHED' in status):

                print 'Fit failed for slice number {} with {} entries. Attempting refit {}/{}'.format(bini, int(h_p.GetEntries()), refit_counter+1, max_n_refits)
                tr =  TRandom()
                tr.SetSeed(0)
                dcb.SetParameter(0, tr.Uniform(  0              , 9999        ))              # Reset the parameters 
                dcb.SetParameter(1, tr.Uniform(  fit_range[0]   , fit_range[1]))
                dcb.SetParameter(2, tr.Uniform(  0              , 0.2         ))
                dcb.SetParameter(3, tr.Uniform(  0              , 5           ))

                fit = h_p.Fit("dcb", "QBRMWE")                           # Try the fit again
                status =  gMinuit.fCstatu                                # Get the fit status
                refit_counter += 1

                if ('OK' in status) or ('CONVERGED' in status):
                    print 'Refit successful!'
                if refit_counter == max_n_refits:
                    print 'Refit limit reached, ommiting slice {}'.format(bini)
                    status = 'LIMIT_REACHED'

            if refit_counter != max_n_refits:

                print "Slice {}/{} fit successfully".format(bini, n_bins)

                chi2 = dcb.GetChisquare()/dcb.GetNDF()
                mean = dcb.GetParameter(1)
                res  = dcb.GetParameter(2)
                res  = subtract_mcp_res(mcp_res_by_bin, res, bini)
                mean_err = chi2*dcb.GetParError(1)
                res_err  = chi2*dcb.GetParError(2)

                lowedge  = h.GetXaxis().GetBinLowEdge(bini)
                highedge = h.GetXaxis().GetBinLowEdge(bini+1)
                center   = (lowedge + highedge) / 2.

                bins.append( [lowedge, highedge, center] )
                hh_1_tmp.append([mean, mean_err])
                hh_2_tmp.append([res, res_err])
        else: 
            print "Slice {}/{} skipped, too few events ({}<{})".format(bini, n_bins, int(h_p.GetEntries()), min_n_events)

    bins, hh_1_tmp, hh_2_tmp = zip(*filter(lambda x: abs(x[2][0])>0.01, zip(bins, hh_1_tmp, hh_2_tmp)))    # Remove points where the resolution is <10 ps because this means the fit failed
    bins, hh_1_tmp, hh_2_tmp = zip(*filter(lambda x: x[2][1]<0.10, zip(bins, hh_1_tmp, hh_2_tmp)))         # Remove points where the res. err.  is >100ps because this means the fit failed

    xs              = array('d', [ x[2] for x in bins])
    xerr            = array('d', [(x[1]-x[0])/2. for x in bins])
    means           = array('d', [ x[0] for x in hh_1_tmp])
    means_err       = array('d', [ x[1] for x in hh_1_tmp])
    resolutions     = array('d', [ x[0] for x in hh_2_tmp])
    resolutions_err = array('d', [ x[1] for x in hh_2_tmp])
    hh_1 =  TGraphAsymmErrors(len(bins), xs, means       , xerr, xerr, means_err      , means_err      ) 
    hh_2 =  TGraphAsymmErrors(len(bins), xs, resolutions , xerr, xerr, resolutions_err, resolutions_err) 

    return hh_1, hh_2

def main():

    ## The function used to fit our distribution. N/Aeff (+) *c, (+) -> sum in quadrature
    def userfit(x,par):
        if x[0]>0:
            fit = pow(pow(par[0]/(x[0]),2) + pow(par[1],2), 0.5)                                
            return fit
    userfit = TF1('userfit', userfit, 1, 2500, 2) 
    userfit.SetParameters(100, 0.05)              # Set a guess for the parameters (N, c)

    gSystem.Load("/afs/cern.ch/user/m/mplesser/H4Analysis/CfgManager/lib/libCFGMan.so")
    gSystem.Load("/afs/cern.ch/user/m/mplesser/H4Analysis/lib/libH4Analysis.so")
    gSystem.Load("/afs/cern.ch/user/m/mplesser/H4Analysis/DynamicTTree/lib/libDTT.so")

    pos = 'C3'
    freq = 160
    temp = 18
    path = '/eos/user/m/mplesser/matrix_time_analysis_recos/ntuples_{}_{}_{}/compiled_roots/'.format(pos, freq, temp)
    file = path + 'ECAL_H4_Oct2018_{}MHz_{}deg_onefileperenergy_{}.root'.format(freq, temp, pos)
    tfile =  TFile(file)
    h4 = tfile.Get("h4")

    if   '160' in file: tunit = 6.238
    elif '120' in file: tunit = 8.317
    phase_corr = "int((fit_time[C3] - fit_time[MCP1] + fit_time[VFE_CLK])/{0})*{0}".format(tunit)
    dt_var     = "fit_time[C3] - fit_time[MCP1] + fit_time[VFE_CLK] - %s" % phase_corr
    amp        = "fit_ampl[C3]/b_rms[C3]"
    cuts       = "fit_ampl[MCP1]>200 && "
    cuts      += "fit_chi2[C3]<150 && fit_chi2[C3]>0.5  && n_tracks==1 && "
    cuts      += "fabs(fitResult[0].x()+5)<4 && fabs(fitResult[0].y()-5)<4 && "
    cuts      += "fit_terr[C3]<0.07 && fit_chi2[MCP1]<10 && fit_chi2[MCP1]>0.1 && "
    cuts      += "1"

    bins = 10,0,3000,1000,0,tunit
    h1 = TH2F("h1","", bins[0], bins[1], bins[2], bins[3], bins[4], bins[5])
    h4.Draw(dt_var+":"+amp+">>h1",TCut(cuts),"COLZ")

    #h1.FitSlicesY()                   # For debugging purposes, these lines are less accurate but run faster
    #res_fit = tfile.Get("h1_2")       # For debugging purposes, these lines are less accurate but run faster
    mean_fit, res_fit = fit_y_slices(h4, h1)
    res_fit.Fit("userfit","RM","",300,3000)
    res_fit.Draw("AP")

    ## For debugging purposes, these lines are less accurate but run faster
    #h1.FitSlicesY()
    #res_fit = tfile.Get("h1_2")

    root_savefile = TFile("/afs/cern.ch/user/m/mplesser/tmp/{}_{}_{}_res.root".format(pos, freq, temp), "recreate")
    root_savefile.cd()              
    res_fit.Write()
    raw_input("hodl")
    tfile.Close()



if __name__=="__main__":
    main()
