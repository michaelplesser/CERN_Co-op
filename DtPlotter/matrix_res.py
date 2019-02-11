#!/usr/bin/python

## By Michael Plesser
## Sloppy script, under development but pushed so others can see while I'm on holiday
## Don't judge meee

from ROOT import *
from array import array

def find_target_center(t_tree):
    
    print "\nFinding target centers...\n"

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

    x_center = hodo_x_center
    y_center = hodo_y_center
    print "{0:^9s}:".format(xtal[2]), "X center: {0:.2f}\t".format(x_center), "Y center: {0:.2f}".format(y_center)
    return x_center, y_center


def find_mcp_resolution(h):
     
    print "Finding MCP resolution contributions in each bin...\n"
    
    global xtal
    ## The MCP resolution vs A/n curve
    def mcp_res_fit(x,par):
        if x[0]>0:
            fit = pow(pow(par[0]/(x[0]),2) + pow( par[1]/pow(x[0],0.5), 2) + pow(par[2],2), 0.5)                                
            return fit
    mcp_res_fit = TF1('mcp_res_fit', mcp_res_fit, 50, 400, 3) 
    mcp_res_fit.SetParameters(1.139e-4, 0.1189, 4.458e-3)                           

    ## Find the mcp resolution contribution in each bin on the TH2F
    bin_edges = [] 
    bin_mcp_res = []
    for bin in range(1, h.GetNbinsX()+2):   bin_edges.append(h.GetXaxis().GetBinLowEdge(bin))   # Get bin edges
    for bin in range(h.GetNbinsX()):
        var     = 'fit_ampl[MCP1]/b_rms[MCP1]'
        cuts    = "fit_ampl[MCP1]>100 && "
        cuts   += "fit_chi2[MCP1]<10 && fit_chi2[MCP1]>0.1 && "
        cuts   += "n_tracks==1 && "
        cuts   += "fit_ampl[{0}]/b_rms[{0}]>={1} && ".format(xtal[0], bin_edges[bin])
        cuts   += "fit_ampl[{0}]/b_rms[{0}]< {1} && ".format(xtal[0], bin_edges[bin+1])
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

    print "Fitting Y slices...\n"
    bins     = []
    hh_1_tmp = []
    hh_2_tmp = []
    n_bins   = h.GetXaxis().GetNbins()
    for bini in range(1, n_bins+1):

        print "Fitting slice {0}/{1}".format(bini, n_bins)
        h_p   = h.ProjectionY("h_p", bini, bini)

        min_n_events = 200
        if h_p.GetEntries()<min_n_events:
            print "\tSlice skipped, too few events. ({0} < {1})".format(int(h_p.GetEntries()),min_n_events)
            continue

        ## Because the tails are a bit messy, fit the dist, then re-fit it only around the peak
        gaus = TF1("gaus","gaus",0,10)
        gaus.SetParameters(100, h_p.GetBinCenter(h_p.GetMaximumBin()), 0.05)
        gaus.SetParLimits(2,0.005,0.5)
        h_p.Fit("gaus","QRBM","",0,10)
        p_gaus  = gaus.GetParameters()
        l_edge  = h_p.GetBinCenter(h_p.FindFirstBinAbove(p_gaus[0]/5.)) # First bin above 1/4-max
        h_edge  = h_p.GetBinCenter(h_p.FindLastBinAbove( p_gaus[0]/5.)) # Last  bin above 1/4-max
        h_p.Fit("gaus","QRBM","",l_edge,h_edge)

        chi2 = gaus.GetChisquare()/gaus.GetNDF()
        mean = gaus.GetParameter(1)
        res  = gaus.GetParameter(2)
        res  = subtract_mcp_res(mcp_res_by_bin, res, bini)
        mean_err = chi2*gaus.GetParError(1)
        res_err  = chi2*gaus.GetParError(2)

        lowedge  = h.GetXaxis().GetBinLowEdge(bini)
        highedge = h.GetXaxis().GetBinLowEdge(bini+1)
        center   = (lowedge + highedge) / 2.

        bins.append( [lowedge, highedge, center] )
        hh_1_tmp.append([mean, mean_err])
        hh_2_tmp.append([res, res_err])

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

def pos_info(pos):
    if   pos == 'C3':       return ['C3',''  ,'C3']
    elif pos == 'C2':       return ['C2',''  ,'C2']
    elif pos == 'C4':       return ['C4',''  ,'C4']
    elif pos == 'C3down':   return ['C3','C2','C3down']
    elif pos == 'C3up':     return ['C3','C4','C3up']

def main():

    ## The function used to fit our distribution. N/Aeff (+) *c, (+) -> sum in quadrature
    def userfit(x,par):
        if x[0]>0:
            fit = pow(pow(par[0]/(x[0]),2) + pow(par[1],2), 0.5)                                
            return fit
    userfit = TF1('userfit', userfit, 1, 2500, 2) 
    userfit.SetParameters(100, 0.05)              # Set a guess for the parameters (N, c)

    ## Fns needed to make fitResult work
    gSystem.Load("/afs/cern.ch/user/m/mplesser/H4Analysis/CfgManager/lib/libCFGMan.so")
    gSystem.Load("/afs/cern.ch/user/m/mplesser/H4Analysis/lib/libH4Analysis.so")
    gSystem.Load("/afs/cern.ch/user/m/mplesser/H4Analysis/DynamicTTree/lib/libDTT.so")

    c1 = TCanvas("c1","c1") # Avoids the annoying "default TCanvas c1 created" message...

    ## File info
    global xtal
    pos  = 'C3'
    freq, temp  = 160, 18
    tunit       = 1000./(freq)  # t_unit is the period length for a given frequency. IE 160MHz is 6.25ns

    path = '/eos/user/m/mplesser/matrix_time_analysis_recos/ntuples_{}_{}_{}/compiled_roots/'.format(pos, freq, temp)
    file = 'ECAL_H4_Oct2018_{}MHz_{}deg_onefileperenergy_{}.root'.format(freq, temp, pos)
    tfile = TFile(path + file)
    h4 = tfile.Get("h4")

    xtal = pos_info(pos)
    xtal_center = find_target_center(h4)

    def single_xtal_analysis():
        ##################################
        print "#"*44
        print "Beginning single crystal resolution analysis"
        print "#"*44, '\n'
        ##################################

        ### Single crystal resolution ###
        xtal       = pos_info(pos)[0]
        t_var      = "( fit_time[{0}] - fit_time[MCP1] + fit_time[VFE_CLK] - int((fit_time[C3] - fit_time[MCP1] + fit_time[VFE_CLK])/{1})*{1} )".format(xtal, tunit)
        amp        = "fit_ampl[{0}]/b_rms[{0}]".format(xtal)
        cuts       = "n_tracks==1 && "
        cuts      += "fit_ampl[MCP1]>200 && fit_chi2[{0}]<100 && fit_chi2[{0}]>0.1 && fit_chi2[MCP1]<15 && fit_chi2[MCP1]>0.1 && ".format(xtal)
        cuts      += "fit_time[{0}]>0 && fit_time[VFE_CLK]>0 && fit_time[MCP1]>0 &&".format(xtal)
        cuts      += "fabs(fitResult[0].x()-{0})<3 && fabs(fitResult[0].y()-{1})<3 && ".format(xtal_center[0], xtal_center[1])  # TBD: import center finding functions
        cuts      += "1"

        bins = 20,100,2500,500,0,tunit
        h1 = TH2F("h1","", bins[0], bins[1], bins[2], bins[3], bins[4], bins[5])
        h4.Draw(t_var+":"+amp+">>h1",TCut(cuts),"COLZ")

        mean_fit, res_fit = fit_y_slices(h4, h1)    ## This is the "real" line
        
        # Some runtime checks. See the plot, check the cterm for reasonability, save plot.
        res_fit.Fit("userfit","RM","",300,2500)
        res_fit.Draw("AP")                          
        print "constant term: {0:.2f} ps, seem reasonable?".format(userfit.GetParameter(1)*1000.)
        root_savefile = TFile("/afs/cern.ch/user/m/mplesser/tmp/{}_{}_{}_res.root".format(pos, freq, temp), "recreate")
        root_savefile.cd()              
        res_fit.Write()
        tfile.cd()
        raw_input("hodl\n")

    
    def matrix_analysis():
        ##################################
        print "#"*36
        print "Beginning matrix resolution analysis"
        print "#"*36, '\n'
        ##################################

        ## general definitions first
        ampbias = 0.866                                                                                         # (for C3down)
        p0,p1   = 13.2714, 0.0242488
        w           = "( pow( pow( %s/(fit_ampl[{0}]/b_rms[{0}]), 2 ) + pow( %s,2 ), 0.5 ) )"   % (p0,p1)       # generic weight expression
        phase_corr  = "int((fit_time[{0}] - fit_time[MCP1] + fit_time[VFE_CLK])/%s)* %s "       % (tunit,tunit) # phase correction
        t           = "( fit_time[{0}] - fit_time[MCP1] + fit_time[VFE_CLK] - %s)"              % phase_corr    # generic time expression

        ## from the general pre-formatted forms above, insert crystal names to get proper ROOT-parsable string expressions to be Draw(n)
        w_C3, w_C2  = w.format('C3'), w.format('C2')
        t_C3, t_C2  = t.format('C3'), t.format('C2')

        ## Apply a correction to C2 due to shower propogation delays
        ## Impacts within a crystal are ~uniform in time, but in neighboring crystals there is a delay
        ## That delay is given by a t_vs_r slope, units time/distance, IE ns/mm below
        t_vs_r = 0.016 
        t_C2 += ' - {0}*(11 - ({1} - fitResult[0].y())) '.format(t_vs_r, xtal_center[1])
        
        ## Construct the weighted average of form ( (t1/w1) + (t2/w2) ) / ( (1/w1) + (1/w2) )
        t_m     = "( ({0}/{1}) + ( ({2}) /{3})  ) / ( (1./{1}) + (1./{3}) )".format(t_C3, w_C3, t_C2, w_C2) # weighted average, (t1/w1 + t2/w2)/(1/w1 + 1/w2)
        aeff    = "fit_ampl[C3]/b_rms[C3] + 0.866*fit_ampl[C2]/b_rms[C2]"
        cuts    = "n_tracks==1 && "
        cuts   += "fit_ampl[MCP1]>200 && fit_chi2[C3]<100 && fit_chi2[C3]>0.1 && fit_chi2[MCP1]<15 && fit_chi2[MCP1]>0.1 && "
        cuts   += "fit_time[C3]>0 && fit_time[VFE_CLK]>0 && fit_time[MCP1]>0 &&"
        cuts   += "fabs(fitResult[0].x()-{0})<8 && fabs(fitResult[0].y()-{1})<5 && ".format(xtal_center[0], xtal_center[1])  # TBD: import center finding functions
        cuts   += "fitResult[0].y()>({0}-11) &&".format(xtal_center[1])
        cuts   += "1"

        bins    = 20,100,2500,500,0,tunit
        hmatrix = TH2F("hmatrix","", bins[0], bins[1], bins[2], bins[3], bins[4], bins[5])
        h4.Draw(t_m+":"+aeff+">>hmatrix",TCut(cuts),"COLZ")

        matrix_mean, matrix_res = fit_y_slices(h4, hmatrix)  ## This is the "real" line

        # Some runtime checks. See the plot, check the cterm for reasonability, save plot.
        matrix_res.Fit("userfit","QRM","",300,2500)
        matrix_res.Draw("AP")                          
        print "constant term: {0:.2f} ps, seem reasonable?".format(userfit.GetParameter(1)*1000.)
        root_savefile = TFile("/afs/cern.ch/user/m/mplesser/tmp/{}_{}_{}_matrix_res.root".format(pos, freq, temp), "recreate")
        root_savefile.cd()              
        matrix_res.Write()
        tfile.cd()
        raw_input("hodl\n")

        ##################################
        ##################################
    print
    #single_xtal_analysis()
    matrix_analysis()

    tfile.Close()
if __name__=="__main__":
    main()


################################################################
### Functions from other analyses, holding bay for later use ###
    ### C3 res curve
    #f0 = TF1("f0", userfit,1,2500,2)
    #f0.SetParameters(13.2714, 0.0242488)
    ### C2 res curve
    #f0.SetParameters(14.0087, 0.0220734)

    ### tanh dt vs Y fit
    #f1 = TF1("f1","[0]*TMath::TanH([1]*x-[2])+[3]",-30,30)
    #f1.SetParameters(0.288857, 0.0808781, 0.786889, 0.375689)
    #hy = TH1F("hy","",80,-20,20)
    #h4.Draw("fitResult[0].y()>>hy")
    #C3_center = hy.GetMean()
    #t0 = f1.Eval(C3_center)
################################################################

