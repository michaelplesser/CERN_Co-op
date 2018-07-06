## Abe Tishelman-Charny Edited by Michael Plesser
## Last revised: July 5 2018
## The purpose of this file and PlotterTools2D.py are to plot H4Analysis outputs
## If you get an error about libpython2.7, move the 2DTreePlotter folder inside ~/CMSSW_8_0_26_patch1/src and run cmsenv

from PlotterTools2D import * # Almost ALL user-level parameters are set from PlotterTools2D, go there first
from ROOT import *	

## Checks if a file name has already been used, and if so instead of overwriting, simply add a number flag
def overwrite_check(filename):
	while ( (filename+'.pdf') in os.listdir(outputLoc)) == True:		# If the file name has already been used
		if len(filename.split(' '))==1:					# If it has been only used once, IE 'dummyfile'
			filename += " 1"					# Make it into "dummyfile 1"
		else:								# If there are multiple already, IE "dummyfile 2" exists
			filename = filename.split(' ')[0] + ' ' + str( int(filename.split(' ')[-1]) + 1 ) # Increment the end number by 1
	return filename

def main():
	## Stats box parameters
	#gStyle.SetOptStat(0)	# No stats box 
	gStyle.SetStatY(0.9)	# Y-position (fraction of pad size)                
	gStyle.SetStatX(0.9)	# X-position         
	gStyle.SetStatW(0.2)	# Width           
	gStyle.SetStatH(0.1)	# Height

	gROOT.SetBatch(kTRUE)	# Don't show graphics 

	for i in xrange(len(Vars)):	# For each plot of interest, set in PlotterTools2D.py			
		cut = Cuts[i]		# Cuts for the current plot of interest
		v    = Vars[i]		# For all things to plot. Each element in Vars has ~10 elements

		hists = []
		#leg = TLegend(0.6, 0.7, 0.89, 0.89)
		#leg.SetBorderSize(0)
		#Max = -0.
		for fi,f in enumerate(Files):			# For each file (fi is file number)
			c0 = TCanvas('c0', 'c0', 800, 600)
			plot_title = 'Run ' + f[1] + ' ' + v[1]
			file_title = 'Run_' + f[1] + '_' + v[1]
			ch = TChain('h4')			# Main tree (friends with other trees)
			ch.Add(f[0])				# Add file path
			hname = f[1] +'_'+str(fi)		# Statsbox title 
			h = TH2F(hname, plot_title, v[2], v[3], v[4], v[5], v[6], v[7])
			ch.Draw(v[0]+'>>'+hname, TCut(cut), v[10])
			h.GetXaxis().SetTitle(v[8])
			h.GetYaxis().SetTitle(v[9])
	 		#h.SetLineColor(  f[2])
			#h.SetMarkerColor(f[2])
			#h.SetMarkerStyle(f[3])
			#h.SetMarkerSize( f[4])
			#h.SetFillColor(  f[3])
			hists.append([h,ch,f[1]])	# f[1] = run number
		
		c0.SaveAs(outputLoc + overwrite_check(file_title) + '.pdf')

## Legacy Section, maybe for future use?

	   ## Make canvas for each file 
	   #c0 = TCanvas('c0', 'c0', 800, 600)
	   #c1 = TCanvas('c1', 'c1', 800, 600)
	   #c2 = TCanvas('c2', 'c2', 800, 600)
	   
	   ## Should plot in loop of files
	   
	   #for fi,hh in enumerate(hists):
	      #leg.AddEntry(hh[0], hh[2], 'lf')
	      #if fi == 0:
		 #print f
		 # Can make draw option list entry 
		 #hh[0].Draw(v[10]) # Draw
	      #if fi > 0:
		 #hh[0].Draw('CONT2 same')
		 #hh[0].Draw() # Don't know what I want to do with this yet 
	   #leg.Draw('same')
	   #c0.SaveAs(outputLoc+'2D_'+v[1]+ '_' + overwrite_check(file_title) + '.pdf')
	   #c1.SaveAs(outputLoc+'2D_'+v[1]+ '_' + overwrite_check(file_title) + '.pdf')
	   #c2.SaveAs(outputLoc+'2D_'+v[1]+ '_' + overwrite_check(file_title) + '.pdf')
	   #c0.SaveAs(outputLoc+'2D_'+v[1]+'.png')


if __name__ == "__main__":
	main()
