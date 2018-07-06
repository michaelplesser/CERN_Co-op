A simple tool for plotting histograms relevant to the H4TB analysis work

This repo should be placed in the folder CMSSW_8_0_26_patch1/src

To get this folder (if you don't already have it):

	cmsrel CMSSW_8_0_26_patch1
	cd CMSSW_8_0_26_patch1
	cmsenv
  

Usage:

	python 2DTreePlotter.py
  
(This will generate a PlotterTools2D.pyc compiled file, overwriting each time you run it)
	
PlotterTools2D.py is used to handle just about everything but graphics, go here first to edit file paths, what to plot, etc...

2DTreePlotter.py is more the graphical side, go here to adjust plot appearences et al.

