#!/usr/bin/env python3

import os
import sys
import shutil
import argparse
import subprocess

'''
	Basic code that can be used as an example.
	For running a batch of DtPlotter analyses automatically.
	Assumes a basic EOS webfolder structure (can be adapted to others as needed):
		...www/php-plots	/tmp
					/plots	/<freq>_<temp>	/<specific configuration folder (dest)>
						... (others)	... (other configurations)
'''
 
def input_arguments(): 
        
	parser = argparse.ArgumentParser (description = 'Submit multiple templateMaker.py batches at once') 
        parser.add_argument('freq',	  action='store', help='Sampling frequency of the data run (160 or 120 MHz)') 
        parser.add_argument('temp',	  action='store', help='Temperature of the data run (18 or 9 deg C)') 
        parser.add_argument('energy',	  action='store', help='Energy of the data, probably you want "compiled"') 
        args = parser.parse_args () 
        
	return args 

## Move all files put in .../www/php-plots/tmp/ to the destination folder
def move_files_to_folder(phpplots_path, dest, args):
	
	check_directory(phpplots_path, dest)
	for filei in os.listdir(phpplots_path+'tmp/'): shutil.move(phpplots_path+'tmp/'+filei, dest)
	print("\nFiles moved to {}".format(dest))	
	
	return

## Checks if a directory exists, if not makes it, and adds res/ and index.php
def check_directory(phpplots_path, dest):
	
	if not os.path.exists(dest): os.mkdir(dest)					# If the dest doesn't exist, make a folder
	try: shutil.copytree(phpplots_path+'res/', dest+'res/')				# Add a copy of res/ to dest
	except OSError: pass								# shutil.copytree stupidly fails if .../res/ already exists 
	shutil.copy2(phpplots_path+'index.php', dest)					# Add a copy of index.php to dest

	return

def main():

	## Input arguments retrieval and formatting et al.
	args = input_arguments()
        if   (args.freq == '160') or (args.freq == '160MHz'): freq = '160MHz'           # Ensures consistent formatting 
        elif (args.freq == '120') or (args.freq == '120MHz'): freq = '120MHz'           # IE does the user enter '120', or '120MHz'? 
        if   (args.temp == '18' ) or (args.temp == '18deg' ): temp = '18deg'            # Resolve it either way 
        elif (args.temp == '9'  ) or (args.temp == '9deg'  ): temp = '9deg'             # blahblah licht mehr licht
		
	## File path setup. phpplots_path is the "base"
	phpplots_path 	= '/eos/user/m/mplesser/www/php-plots/'
	if not os.path.exists(phpplots_path): 	sys.exit("Error!!! no /<user>/www/php-plots folder found! \nAborting...\n")
	plots_path    	= phpplots_path	+ 'plots/'
	save_path 	= phpplots_path	+ 'plots/{}_{}/'.format(freq,temp)
	check_directory(phpplots_path, plots_path)
	check_directory(phpplots_path, save_path)

	## Building the commands we want to run	
	cmd = ['python', 'DtPlotter.py', '--freq', freq, '--temp', temp, '-e', args.energy]	# Basic command, specifies which files/runs to use
	chi2andaeff 	= cmd + ['-x'  , '-a'	]						# Command to make chi2 and Aeff plots
	baseline    	= cmd + ['-s'  , '--fit']						# Baseline dt resolution command, default cuts only
	da		= 	['--da', '500'	]						# Misc extra cuts to be applied
	pc		= 	['--pc', '1'	]						# Misc extra cuts to be applied
	lc		= 	['--lc'		]						# Misc extra cuts to be applied
	
	## Commands you want run
	run_commands = [chi2andaeff,		\
			baseline,		\
			baseline + da,		\
			baseline + pc,		\
			baseline + lc,		\
			baseline + da+pc,	\
			baseline + da+lc,	\
			baseline + pc+lc,	\
			baseline + da+pc+lc	]

	## Where to store the plots generated above
	destinations = [save_path + 'chi2_and_aeff/', 			\
			save_path + 'baseline/', 			\
			save_path + 'damp_cut/',			\
			save_path + 'pos_cut/', 			\
			save_path + 'lin_corr/', 			\
			save_path + 'damp_and_pos/', 			\
			save_path + 'damp_and_lin_corr/', 		\
			save_path + 'pos_and_lin_corr/',		\
			save_path + 'damp_and_pos_and_lin_corr/'	]

	## Run the commands and move them to the proper destination	
	shutil.rmtree(phpplots_path+'tmp/')							# Remove the tmp/ plot to prevent data mix-ups
	for runcmd, path in zip(run_commands, destinations):
		p = subprocess.Popen(runcmd)							# Run the command
		p.communicate()									# Wait for it to finish
		move_files_to_folder(phpplots_path, path, args)					# Move the plots to the proper folder under .../www/...
	
	### Experimental area ###
	for dest in destinations:
		for filei in dest:
			if filei.endswith('log.txt'):
				with open(dest+filei, 'r') as f:
					for line in f:
						if line.split(':')[0] == '\tConstant term':
							print(dest.split('/')[-2], '\t\t', line.split(':')[-1])


	
if __name__=="__main__":
	main()

