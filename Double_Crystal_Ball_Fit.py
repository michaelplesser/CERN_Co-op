#!/usr/bin/python

from ROOT import TF1

'''
    It was surprisingly difficult to find a simple and short double-sided
    crystal ball function to use for fitting data in ROOT considering the
    one-sided crystal ball is now built in to new ROOT releases
    Use this as an example, the cleanest version I've seen yet
'''

def main():

    ## Double sided crystal ball function
    def double_xtal_ball(x,par):
        f1 = TF1('f1','crystalball')
        f2 = TF1('f2','crystalball')
        f1.SetParameters(par[0]/2, par[1], par[2],    par[3], par[4])           # The trick is to share all variables but change the
        f2.SetParameters(par[0]/2, par[1], par[2], -1*par[3], par[4])           # sign of 'A', which determines the side of the tail
        return f1(x) + f2(x)

    double_xtal_ball = TF1("double_xtal_ball", double_xtal_ball, -2, 2, 5)      # -2 to 2 is my sample fit range, adjust as needed
    double_xtal_ball.SetParNames("c","mu","sig","A","n")                        # Not necessary, but helpful for clarity!
    
    ## Set par. limits to help the minimizer converge
    ## Example values, tune based on your specific usage case. Not all limits may be necessary for you
    ## Depending on statistics and usage cases you may not need these at all... Play around
    double_xtal_ball.SetParLimits(0 , 0 ,999)                                   # c >= 0
    double_xtal_ball.SetParLimits(1 ,-2 ,2  )                                   # mu between -2 and 2
    double_xtal_ball.SetParLimits(2 , 0 ,0.5)                                   # sigma between 0 and 0.5
    double_xtal_ball.SetParLimits(3 , 0 ,99 )                                   # A >= 0
    double_xtal_ball.SetParLimits(4 , 0 ,999)                                   # n >= 0
    double_xtal_ball.SetParameters(1, 0.5, 0.05, 1, 1)                          # Some guesses to help things along 

    ## You can now use double_xtal_ball like any other TF1, IE histogram.Fit("double_xtal_ball")

if __name__=="__main__":
    main()
