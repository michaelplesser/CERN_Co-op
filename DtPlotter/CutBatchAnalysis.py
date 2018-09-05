#!/usr/bin/env python3

#By Michael Plesser

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
        parser.add_argument('freq',		action='store', 	help='Sampling frequency of the data run (160 or 120 MHz)'			) 
        parser.add_argument('temp',		action='store', 	help='Temperature of the data run (18 or 9 deg C)'				) 
        parser.add_argument('energy',		action='store', 	help='Energy of the data, probably you want "compiled"'				) 
	parser.add_argument('-s', '--summary',	action='store_true',	help="Don't run the analysis, just read the resolutions from the log files."	)
        args = parser.parse_args () 
        
	if   (args.freq == '160') or (args.freq == '160MHz'): args.freq = '160MHz'	# Ensures consistent formatting 
        elif (args.freq == '120') or (args.freq == '120MHz'): args.freq = '120MHz'	# IE does the user enter '120', or '120MHz'? 
        if   (args.temp == '18' ) or (args.temp == '18deg' ): args.temp = '18deg'	# Resolve it either way 
        elif (args.temp == '9'  ) or (args.temp == '9deg'  ): args.temp = '9deg'	# blahblah licht mehr licht
        
	return args 

## Move all files put in .../www/php-plots/tmp/ to the destination folder
def move_files_to_folder(phpplots_path, dest, args):
	
	check_directory(phpplots_path, dest, True)

	for filei in os.listdir(phpplots_path+'tmp/'): 	
		try: shutil.move(phpplots_path+'tmp/'+filei, dest)
		except shutil.Error: pass

	print("\nFiles moved to {}".format(dest))					# Print where the files were moved to
	print "\n","#"*int(os.popen('stty size', 'r').read().split()[1]) 		# Print a line of ###'s, aesethetic	
	print      "#"*int(os.popen('stty size', 'r').read().split()[1]) 		# Print a line of ###'s, aesethetic	
	
	return

## Checks if a directory exists, if not makes it, and adds res/ and index.php (Needed for EOS page to be viewable/formatted)
def check_directory(phpplots_path, dest, rm_flag):
	
	if os.path.exists(dest) and rm_flag == True:					# If dest exists and the rm_flag has been raised, remove the folder first
		print('Removing folder {}...'.format(dest))				#	This avoids files from different analyses getting put together
		shutil.rmtree(dest)							#	...plots/ should NOT be used as permanent storage, may be overwritten!!!
	if not os.path.exists(dest):							# If the dest doesn't exist (or was just erased), make a folder
		print('Creating folder {}...'.format(dest))
		os.mkdir(dest)								

	shutil.copy2(phpplots_path+'index.php', dest)				# Add a copy of index.php to dest
	try: shutil.copytree(phpplots_path+'res/', dest+'res/')				# Add a copy of res/ to dest
	except OSError: pass								# shutil.copytree stupidly fails if .../res/ already exists 

	return
	
## Reads resolution values from log files and prints them out
def skim_resolutions(args, destinations):
	
	cutnames       = [x.split('/')[-2] for x in destinations]				# Name of batch, IE 'baseline', 'damp_cut', 'chi2_and_aeff', etc..
	C3down_res     = []
	C3up_res       = []
	C3down_res_err = []
	C3up_res_err   = []

	log_files  = []

	## Checks that the folders exist, exit if not
	for dest in destinations:
		if not os.path.exists(dest): sys.exit('Error!!! Folder {} not found. Have you not run that analysis, or moved those files?'.format(dest))

	## Get a list of all log files
	for dest in destinations:
		for filei in os.listdir(dest):
			if filei.endswith('log.txt'):	
				log_files.append(dest+filei)

	## Iterate over log files, skimming resolution values
	for filei in log_files:
		filename = filei.split('/')[-1]									# File name without the /path/
		with open(filei, 'r') as f:
			for line in f:
				if 'Constant term:' in line:							# If 'line' contains 'Constant term:'
					res = ''.join([d for d in line if d.isdigit() or d is '.'])		# Extract resolution from line (a bad method... )
					if   filename.startswith('C3up')  :	C3up_res.append(res)
					elif filename.startswith('C3down'):	C3down_res.append(res)
				if 'Constant term error:' in line:						# If 'line' contains 'Constant term error:'
					res_err = ''.join([d for d in line if d.isdigit() or d is '.'])		# Extract resolution uncertainty from line (a bad method... )
					if   filename.startswith('C3up')  :	C3up_res_err.append(res_err)
					elif filename.startswith('C3down'):	C3down_res_err.append(res_err)
	
	## For missing data fill with res and res_err with 'N/A', so 'zip' works properly below
	if C3down_res == []: 
		C3down_res     = ['N/A']*len(destinations)
		C3down_res_err = C3down_res
	if C3up_res == []  : 
		C3up_res       = ['N/A']*len(destinations)
		C3up_res_err   = C3up_res
	
	## Print out summary
	print('\n\t  Batch Resolution Analysis Summary for {}/{}:'.format(args.freq,args.temp))
	print(' '+'_'*68)
	print('|{0:^30}|{1:^18}|{2:^18}|'.format('Cut/Batch','C3down','C3up'))
	print('|'+'_'*30+'|'+'_'*18+'|'+'_'*18+'|')
	for cut, r1, err1, r2, err2 in zip(cutnames[:-1], C3down_res, C3down_res_err, C3up_res, C3up_res_err):	# cutnames[-1] is chi2_and_aeff, no resolution associated... 
		print('|'+'-'*30+'|'+'-'*18+'|'+'-'*18+'|')
		print('|{0:^30}| {1:^5} +- {2:^4} ps | {3:^5} +- {4:^4} ps |'.format(cut, r1, err1, r2, err2))	# Print out with formatting for fixed width display
	print('|'+'_'*30+'|'+'_'*18+'|'+'_'*18+'|')
	print('')
	
	return

def main():

	args = input_arguments()

	## File path setup. phpplots_path is the "base"
	phpplots_path 	= '/eos/user/m/mplesser/www/php-plots/'
	plots_path    	= phpplots_path	+ 'plots/'
	save_path 	= phpplots_path	+ 'plots/{}_{}/'.format(args.freq, args.temp)
	
	if not os.path.exists(phpplots_path): 	sys.exit("Error!!! no /<user>/www/php-plots folder found! \nAborting...\n")

	## Where to store the plots generated 
	destinations = [save_path + 'baseline/', 			\
			save_path + 'damp_cut/',			\
			save_path + 'pos_cut/', 			\
			save_path + 'lin_corr/', 			\
			save_path + 'damp_and_pos/', 			\
			save_path + 'damp_and_lin_corr/', 		\
			save_path + 'pos_and_lin_corr/',		\
			save_path + 'damp_and_pos_and_lin_corr/',	\
			save_path + 'chi2_and_aeff/' 			]

	
	## Building the commands we want to run	
	Dt_path = '/afs/cern.ch/user/m/mplesser/my_git/CERN_Co-op/DtPlotter/'
	cmd = ['python', Dt_path+'DtPlotter.py', '--freq', args.freq, '--temp', args.temp, '-e', args.energy]	# Basic command, specifies which files/runs to use
	chi2andaeff 	= cmd + ['-x'  , '-a'	]								# Command to make chi2 and Aeff plots
	baseline    	= cmd + ['-s'  , '--fit']								# Baseline dt resolution command, default cuts only
	da		= 	['--da', '1000'	]								# Misc extra cuts to be applied
	pc		= 	['--pc', '1'	]								# Misc extra cuts to be applied
	lc		= 	['--lc'		]								# Misc extra cuts to be applied
	
	## Commands you want run
	run_commands = [baseline,		\
			baseline + da,		\
			baseline + pc,		\
			baseline + lc,		\
			baseline + da+pc,	\
			baseline + da+lc,	\
			baseline + pc+lc,	\
			baseline + da+pc+lc,	\
			chi2andaeff		]
	
	## Skim resolutions from log files and exit instead of running analysis if '--summary' used
	if args.summary == True:
		skim_resolutions(args, destinations)
		return	
	
	## Check to make sure all relevant directories exist/are empty if need be
	check_directory(phpplots_path, plots_path, 		False)
	check_directory(phpplots_path, save_path,  		True )
	check_directory(phpplots_path, phpplots_path+'tmp/',	True )
	
	## Run the commands and move them to the proper destination	
	for runcmd, path in zip(run_commands, destinations):
		p = subprocess.Popen(runcmd)							# Run the command
		p.communicate()									# Wait for it to finish
		move_files_to_folder(phpplots_path, path, args)					# Move the plots to the proper folder under .../www/...
	
	## Print out resolutions from the analysis	
	skim_resolutions(args, destinations)
	
	return

if __name__=="__main__":
	main()

