import os
import sys
import argparse
import subprocess

'''
	A basic script for creating templates using Simone's templateMaker.py
	Place this file in H4Analysis/scripts and run from the H4Analysis folder
	A few important formatting notes:
		cfg: 	Your cfg file must be in the format 'cfg/ECAL_H4_June2018_templates_<frequency>.cfg'
		input: 	Your should provide a csv file with two columns, run-number 1st, crystal position 2nd
			IE: 11307,C3
			    11308,C4
			    etc...
	Run as, for example: 'python templateSubmitter.py 160 18 /path/to/file_of_160MHz_18deg.list -c <channels>'
		(-c is optional, the default is use all channels listed in xtals_positions)
'''




def input_arguments():
	parser = argparse.ArgumentParser (description = 'Submit multiple templateMaker.py batches at once')
	parser.add_argument('freq',  action='store', help='Sampling frequency of the data run (160 or 120 MHz)')
	parser.add_argument('temp',  action='store', help='Temperature of the data run (18 or 9 deg C)')
	parser.add_argument('f'   ,  action='store', help='Input file containing run #s and positions, IE from Simones summary website')
	parser.add_argument('-c'  ,  action='store', help='Which channels to create templates for')
	args = parser.parse_args ()
	return args

## Read the list of runs and positions and compile them into a dictionary indexed by xtal name, with a list of runs at that position	
def get_runs_and_channels(f, r_a_cs):
	if not os.path.exists(f): sys.exit("Error!!! Input file not found!")
	with open(f, 'r') as fi:
		for line in fi:	
			if line == '\n': continue				# If the line is just '\n', skip it. "last line bug"
			position  = str(line.split(',')[1].split('\n')[0])	# line = '<pos>,<run#>\n'
			runnumber = str(line.split(',')[0])			# line = '<pos>,<run#>\n'
			r_a_cs[position].extend([runnumber])			# Add each run number under the right dictionary index	
	return r_a_cs

def main():
	## Crystal center positions in hodoscope coordinates
	xtal_positions = { 	'A1': [-5,6], 'A2': [-4,4], 'A3': [-3,4], \
				'B1': [-5,5], 'B2': [-5,4], 'B3': [-3,4], 'B4': [-3,5], 'B5': [-3,7], \
				'C1': [-3,4], 'C2': [-4,5], 'C3': [-4,4], 'C4': [-4,4], 'C5': [-4,5], \
				'D1': [-2,5], 'D2': [-3,4], 'D3': [-2,4], 'D4': [-3,4], 'D5': [-3,5], \
				'E1': [-2,4], 'E2': [-3,3], 'E3': [-1,3]	}
	
	args = input_arguments()
	if   (args.freq == '160') or (args.freq == '160MHz'): freq = '160MHz'		# Ensures consistent formatting
	elif (args.freq == '120') or (args.freq == '120MHz'): freq = '120MHz'		# IE does the user enter '120', or '120MHz'?
	if   (args.temp == '18' ) or (args.temp == '18deg' ): temp = '18deg'		# Resolve it either way
	elif (args.temp == '9'  ) or (args.temp == '9deg'  ): temp = '9deg'		# blahblah licht mehr licht
	
	if args.c is None: args.c = [ch for ch in xtal_positions]			# If no channels specified, use all of them
	else: 		   args.c = args.c.split(',')					# Otherwise use the input ones
	runs_and_channels = {ch:[] for ch in args.c}					# Initialize an empty dictionary with channel names as indices
	runs_and_channels = get_runs_and_channels(args.f, runs_and_channels)

	cmd 	= ['python', 	'scripts/templateMaker.py'			]	# Start with the "base", cmd, add options one by one using 'extend'	
	bins    = ['--bins',    '1000,-100,900'					]
	cfg 	= ['-t'    ,	'cfg/ECAL_H4_June2018_templates_'+freq+'.cfg'	]	
	if not os.path.exists(cfg[1]): sys.exit("Error!!! Cfg file not found!")
	cmd.extend(cfg)
	cmd.extend(bins)
	
	f = open('log_{}_{}_templateSubmitter.txt'.format(freq,temp), 'w')		# Keep a log file in case any template creations fail
	f.write(freq+" "+temp+" template log: \n\n")
	
	for ch in runs_and_channels:
		
		if len(runs_and_channels[ch][0]) == 0: continue				# If there are no runs, skip that crystal
		
		cutstring = 'amp_max[{}]>3000 && nFibresOnX[0]==2 && nFibresOnY[0]==2 && fabs(X[0]-{})<2 && fabs(Y[0]-{})<2'.format(ch, str(xtal_positions[ch][0]), str(xtal_positions[ch][1]))
		cut 	  = ['--cut' 	, cutstring						] 
		channels  = ['-c'	, ch							]
		runs      = ['-r'	, runs_and_channels[ch][0]				]
		output    = ['-o'	, 'tmp/'+ch+'_template_file_'+freq+'_'+temp+'.root'	]
		if not os.path.exists('tmp/'): mkdir ('tmp/')				# Make a tmp/ directory to hold the templates if none exists
	
		runcmd = []								# runcmd is the cmd command with channel-specific flags added
		runcmd.extend(cmd)
		runcmd.extend(output)
		runcmd.extend(channels)
		runcmd.extend(runs)
		runcmd.extend(cut)	
		
		print "\nRunning: ",' '.join(runcmd),'\n'
		subprocess.Popen(runcmd)						# Actually run the command
		
		if os.path.exists(output[1]): f.write("File {} creation successful!\n".format(output[1]))
		else: f.write("File {} creation FAILED!\n".format(output[1]))
	f.close()

	## Compile each individual template into one master .root file
	compilecmd = ['hadd', 'tmp/ECAL_H4_June2018_template_file_'+freq+'_'+temp+'.root', 'tmp/*'+freq+'_'+temp+'.root']	
	subprocess.Popen(compilecmd)

if __name__=="__main__":
	main()
