## Abe Tishelman-Charny Edited by Michael Plesser
## Last revised: July 5 2018
## The purpose of this file and 2DTreePlotter.py are to plot H4Analysis outputs
## If you get an error about libpython2.7, move the 2DTreePlotter folder inside ~/CMSSW_8_0_26_patch1/src and run cmsenv

from ROOT import *
import sys
import os

## Cuts to selection

Cuts = []
Cuts.append('wf_t.WF_ch == digi_t.C3_T && abs(wf_t.WF_val)<10000 && abs(wf_t.WF_time)<1000 && digi_t.amp_max[C3_T]<10000')

## Output location for plots

outputLoc = os.path.expanduser('~') + '/CMSSW_8_0_26_patch1/src/2DTreePlotter/template_plots/'
if os.path.exists(outputLoc) == False:	# Creates a ~/CMSSW_8_0_26_patch1/src/template_plots/ directory if none exists
	os.mkdir(outputLoc)

##Plots to be created (append used for future uses, creating multiple plots)
#[ Y-values to be plotted : X-values to be plotted, Plot Name, xbins, xmin, xmax, ybins, ymin, ymax, xtitle, ytitle, draw option]

Vars = []
Vars.append(['(wf_t.WF_val / digi_t.amp_max[C3_T]) : wf_t.WF_time - digi_t.time_max[C3_T]', 'C3_Template', 1000, -50, 50, 100, -0.1, 1.1, 't - tmax (ns)', 'normalized ADC Counts', 'COLZ']) # Normalized Template

## Scan desired directory for root files 

analysispath = os.path.expanduser('~') + '/H4Analysis/ntuples/'
root_files = []
runs = []
for file in os.listdir(analysispath):
	if file.endswith('.root'):
		root_files.append(os.path.join(file))
		runs.append(file.split('_')[-1].split('.')[0])	# Skim run numbers from file names, assuming form <blablabla>_runnum.root		

Files = []
for name, run in zip(root_files, runs):
	Files.append([os.path.expanduser('~') + '/H4Analysis/ntuples/' + name,run,1,1,4]) 
