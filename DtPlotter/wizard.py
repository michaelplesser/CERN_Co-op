#!/usr/local/bin/python

import os
import time 
import subprocess

## Select method of specifying analysis files, by directory, file, or energy
def file_method(cmd):	
	print "Select your file method:"
	print "\tTo use a directory enter: \t\t\t 1 or -d"
	print "\tTo use a specific file enter:\t\t\t 2 or -f"
	print "\tTo use an energy/frequency/temperature enter:\t 3 or -e"
	print "\tTo use the default path enter: \t\t\t nothing\n"
	fmode = raw_input("Choose now: ")
	while fmode in ['1', '2', '3', '-d', '-f', '-e', None] == False: fmode = raw_input("Error!!! Input not reognized, try again")	
	print
	if fmode   == '1' or fmode == '-d': 
		directory = raw_input("Enter the directory: ")
		while os.path.exists(directory) == False:
			directory = raw_input("Directory not found!!! Try again: ")
		cmd.append('-d')
		cmd.append(directory)
		freq   = raw_input("Enter the sampling frequency (--freq)  (Default: 160MHz): ")	
		temp   = raw_input("Enter the temperature 	 (--temp)  (Default: 18deg) : ")
		if freq != '':
			cmd.append('--freq')
			cmd.append(freq)
		if temp != '':
			cmd.append('--temp')
			cmd.append(temp)
	elif fmode == '2' or fmode == '-f': 
		filei = raw_input("Enter the file: ")
		while os.path.exists(filei) == False:
			filei = raw_input("File not found!!! Try again: ")
		cmd.append('-f')
		cmd.append(filei)
	elif fmode == '3' or fmode == '-e': 
		energy = raw_input("Enter the energy: ")
		freq   = raw_input("Enter the sampling frequency (--freq)  (Default: 160MHz): ")	
		temp   = raw_input("Enter the temperature 	 (--temp)  (Default: 18deg) : ")
		cmd.append('-e')
		cmd.append(energy)
		if freq != '':
			cmd.append('--freq')
			cmd.append(freq)
		if temp != '':
			cmd.append('--temp')
			cmd.append(temp)
	elif fmode == '': pass	
	
	return cmd

## Select which plots to create, chi2, Aeff, and/or resolution vs aeff
def plot_method(cmd):	
	print
	print "Now select which plots to create"
	print "\tTo create chi-squared plots enter:		\t 1 or -x "
	print "\tTo create an Aeff plot enter:			\t 2 or -a "
	print "\tTo create a resolution vs Aeff plot enter:	\t 3 or -s "
	print "\tTo select multiple, enter the numbers/letters separated by commas, IE '1,2,3'\n"
	plots = raw_input("Choose now: ").split(',')
	while plots[0] == '': plots = raw_input("Not enough choices given!!! Try again: ").split(',')	
	print	
	for p in plots:
		if p == '1' or p == '-x':
			cmd.append('-x')
			print "Enter the bounds for your chi2 plots formatted as nbins,lowerbound,upperbound"
			print "Leave blank to use the defaults"
			bins = raw_input("Enter now: ")
			while len(bins.split(',')) != 3 and bins != '': bins = raw_input("Bins not recognized!!! Enter again: ")
			if bins != '': cmd.append(bins)
			print
		elif p == '2' or p == '-a':
			cmd.append('-a')
			print "Enter the bounds for your Aeff plot formatted as X_nbins,X_lowerbound,X_upperbound,Y_nbins,Y_lowerbound,Y_upperbound"
			print "Leave blank to use the defaults"
			bins = raw_input("Enter now: ")
			while len(bins.split(',')) != 6 and bins != '': bins = raw_input("Bins not recognized!!! Enter again: ")
			if bins != '': cmd.append(bins)
			print
		elif p == '3' or p == '-s':
			cmd.append('-s')
			print "Enter the bounds for your resolution vs Aeff plot formatted as X_nbins,X_lowerbound,X_upperbound,Y_nbins,Y_lowerbound,Y_upperbound"
			print "Leave blank to use the defaults"
			bins = raw_input("Enter now: ")
			while len(bins.split(',')) != 6 and bins != '': bins = raw_input("Bins not recognized!!! Enter again: ")
			if bins != '': cmd.append(bins)
			print 
			print "Use quantile binning?"
			print "Enter anything for yes, leave blank for no"
			q   = raw_input("Choose now: ")
			if q != '': cmd.append('-q')
			print 
			print "Fit the resolution plot?"
			print "Enter anything for yes, leave blank for no"
			fit = raw_input("Choose now: ")
			if fit is not None: cmd.append('--fit')
	return cmd

## Select which cuts to apply
def cuts_method(cmd):
	print
	print "Now select which cuts to use"
	print "\tTo use a cut on chi2 values  enter:				\t 1 or --xc"
	print "\tTo use a cut on the minimum amp_max of an event enter:		\t 2 or --am"
	print "\tTo use a square position cut enter:				\t 3 or --pc"
	print "\tTo use a linear correction to adjust for walking mean enter:	\t 4 or --lc"
	print "\tTo select multiple, enter the numbers/letters separated by commas, IE '1,2,3'"
	cuts = raw_input("Choose now: ").split(',')
	print
	for c in cuts:
		if c == '1' or c == '--xc': 
			cmd.append( '--xc')
			print "Enter the chi2 cuts formatted as min_chi2_xtal1,max_chi2_xtal1,min_chi2_xtal2,max_chi2_xtal2"
			print "Leave blank for default"
			chicut = raw_input("Enter now: ")
			while chicut.split(',') != 4 and chicut != '': chicut = raw_input("Error!!! Try again: ")
			if chicut.split(',') == 4: cmd.append(chicut)
		elif c == '2' or c == '--am': 
			cmd.append('--am')
			print "Enter the minimum value for max_ampl of an event to be allowed: "
			print "Leave blank for default"
			ampmax = raw_input("Enter now: ")
			if ampmax != '': cmd.append(ampmax)
		elif c == '3' or c == '--pc': 
			cmd.append('--pc')
			print "Enter the size of the box around target center to cut on (in mm): "
			print "Leave blank for default"
			poscut = raw_input("Enter now: ")
			if poscut != '': cmd.append(poscut)
		elif c == '4' or c == '--lc': 
			cmd.append('--lc')
	return cmd

def main():
	
	cmd = ['python', 'DtPlotter.py']
	
	print
	print ' 			 ____	 _________			     '	 
	print ' 			|  _ \	|___   ___|			     '	
	print ' 			| | \ \	    | |				     '	 
	print ' 			| | | |	    | |				     '			
	print ' 			| |_/ /	    | |				     '	 
	print ' 			|____/	    |_|				     '	
	print '									     '	 
	print '__       __       __   _    _____        __        _____    ____      '
	print '\ \     /  \     / /  | |  |___  |      /  \      |  _  \  |  _ \     '
	print ' \ \   / /\ \   / /   | |     / /      / /\ \     | |_| |  | | \ \    '
	print '  \ \ / /  \ \ / /    | |    / /      /  __  \    |    _/  | | | |    ' 	
	print '   \ v /    \ v /     | |   / /__    /  /  \  \   | |\ \   | |_/ /    '	
	print '    \_/      \_/      |_|  |_____|  /__/    \__\  |_| \_\  |____/     '	
	print	 

	print "Welcome to the DtPlotter wizard tool"
	print "This is a basic tool to help aquaint new users with DtPlotter"
	print "wizard.py walks the user through building a DtPlotter.py command with arguments"
	print "This should be used primarily for learning purposes"
	print

	cmd = file_method(cmd)
	cmd = plot_method(cmd)
	cmd = cuts_method(cmd)			


	print
	print "Command generated: ", ' '.join(cmd)
	print
	subprocess.Popen(cmd)
	
if __name__=="__main__":
	main()
