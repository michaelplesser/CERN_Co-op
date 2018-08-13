#!/usr/local/bin/python

import os
import sys
import argparse
import subprocess
from ROOT import *

def input_arguments():
	parser = argparse.ArgumentParser(description='Easilly run hadd on root files by skimming their positions and energies from the info tree')
	
	parser.add_argument('directory', type=str, help='hadd files within the given directory by energy and position ')
	parser.add_argument('freq',	 type=str, help='Sampling frequency of files, IE 120 or 160')
	parser.add_argument('temp', 	 type=str, help='Sampling temperature, IE 9 or 18')

	return parser.parse_args()

## Makes sure that input args are given as integers (frequency and temperature)
def check_int_args(var):
	try: int(var)
	except ValueError: sys.exit( "\nFrequency and temperature should be input as integers!!! IE 120 9\nAborting...\n" )

def main():
	args = input_arguments()
	check_int_args(args.freq)
	check_int_args(args.temp)

	if not args.directory.endswith('/'): args.directory+='/' # For consistency, makes sure '/directory/path/ends/with/' <-- a '/'

	name_base      = "ECAL_H4_June2018_" + args.freq + "MHz_" + args.temp + "deg_"
	C3upenergies   = { '25GeV' : [], '50GeV' : [], '100GeV' : [], '150GeV' : [], '200GeV' : [], '250GeV' : [] }
	C3downenergies = { '25GeV' : [], '50GeV' : [], '100GeV' : [], '150GeV' : [], '200GeV' : [], '250GeV' : [] }
	mastertable    = { 'C3up'  : C3upenergies, 'C3down' : C3downenergies}

	# Get position and energy info on all files in the directory, and sort them into the mastertable (dict)
	for filei in os.listdir(args.directory):		# Iterate over all files in the given directory
		if filei.endswith(".root"):			# Only includes .root files
			print "Found file:", filei,"\t", 
			tfile = TFile(args.directory+filei)
			infotree  = tfile.Get("info")
			infotree.GetEntry(0)
			if   infotree.Positions == 2.5: position = 'C3down'
			elif infotree.Positions == 3.5: position = 'C3up'
			else: sys.exit("Unrecognized position, aborting...")
			energy   = str(int(infotree.Energy))+'GeV'
			print "Position:\t",position,"\tEnergy:\t",energy
			mastertable[position][energy].append(filei)	
	print
	
	# Create output directories if none exist
	if os.path.exists(args.directory+"reco_roots") == False:
		os.mkdir(args.directory+"/reco_roots")
	if os.path.exists(args.directory+"compiled_roots") == False:
		os.mkdir(args.directory+"/compiled_roots")

	# Build the 'hadd' command and run
	for i, p in  enumerate(mastertable):									# Iterate over positions: i=index, p=dict_key (position)
		compiledoutfile = args.directory + "compiled_roots/" + name_base + "compiled_" + p + ".root"	# Name of the compiled hadd output file
		compiledcommand = ["hadd",'-f', compiledoutfile]					# -f flag forces save file overwrite if necessary	
		for j, e in enumerate(mastertable[p]): 								# Iterate over energies : j=index, e=dict_key (energy)
			if len(mastertable[p][e]) != 0:								# Only create an hadd instance if there are actually files to hadd
				outfile = args.directory + "reco_roots/" + name_base + e + "_" + p + ".root"	# Name of the individual (energy) hadd output files
				command = ["hadd",'-f', outfile]					# -f flag forces save file overwrite if necessary				
				for filei in mastertable[p][e]:
					command.append(args.directory+filei) 		# Append the name of each file to be hadd-ed for each energy
					compiledcommand.append(args.directory+filei) 	# Append the name of each file to be hadd-ed all compiled
				p1 = subprocess.Popen(command)			# Run the individual (energy) hadd command
				p1.wait()					# Wait for it to finish before moving on
				print
		pcompiled = subprocess.Popen(compiledcommand)		# Run the compiled hadd command
		pcompiled.wait()					# Wait for it to finish before moving on
		print
				
if __name__=="__main__":
	main()

