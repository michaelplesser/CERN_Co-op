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
        ...www/php-plots    /tmp
                    /plots  /<freq>_<temp>  /<specific configuration folder (dest)>
                        ... (others)    ... (other configurations)
'''
 
def input_arguments(): 
        
    parser = argparse.ArgumentParser(description = 'Submit multiple templateMaker.py batches at once') 
    parser.add_argument('freq',             action='store',         help="Sampling frequency of the data run (160 or 120 MHz)") 
    parser.add_argument('temp',             action='store',         help="Temperature of the data run (18 or 9 deg C)") 
    parser.add_argument('energy',           action='store',         help="Energy of the data, probably you want 'compiled'") 
    parser.add_argument('-s', '--summary',  action='store_true',    help="Don't run the analysis, just read the resolutions from the log files.")
    parser.add_argument('-r', '--rerun'  ,  action='store_true',    help="Run/re-run only specific runs, selected from a list")
    args = parser.parse_args() 
        
    if   (args.freq == '160') or (args.freq == '160MHz'): args.freq = '160MHz'      # Ensures consistent formatting 
    elif (args.freq == '120') or (args.freq == '120MHz'): args.freq = '120MHz'      # IE does the user enter '120', or '120MHz'? 
    if   (args.temp == '18' ) or (args.temp == '18deg' ): args.temp = '18deg'       # Resolve it either way 
    elif (args.temp == '9'  ) or (args.temp == '9deg'  ): args.temp = '9deg'        # blahblah licht mehr licht
        
    return args 

## Move all files put in .../www/php-plots/tmp/ to the destination folder
def move_files_to_folder(phpplots_path, dest, args):
    
    check_directory(phpplots_path, dest, True)

    for filei in os.listdir(phpplots_path+'tmp/'):  
        try: shutil.move(phpplots_path+'tmp/'+filei, dest)
        except shutil.Error: pass

    print("\nFiles moved to {}".format(dest))                                       # Print where the files were moved to
    print "\n","#"*int(os.popen('stty size', 'r').read().split()[1])                # Print a line of ###'s, aesethetic 
    print      "#"*int(os.popen('stty size', 'r').read().split()[1])                # Print a line of ###'s, aesethetic 
    
    return

## Checks if a directory exists, if not makes it, and adds res/ and index.php (Needed for EOS page to be viewable/formatted)
def check_directory(phpplots_path, dest, rm_flag):
    
    if os.path.exists(dest) and rm_flag == True:                                    # If dest exists and the rm_flag has been raised, remove the folder first
        print('Removing folder {}...'.format(dest))                                 #   This avoids files from different analyses getting put together
        shutil.rmtree(dest)                                                         #   ...plots/ should NOT be used as permanent storage, may be overwritten!!!
    if not os.path.exists(dest):                                                    # If the dest doesn't exist (or was just erased), make a folder
        print('Creating folder {}...'.format(dest))
        os.mkdir(dest)                              

    shutil.copy2(phpplots_path+'index.php', dest)                                   # Add a copy of index.php to dest
    try: shutil.copytree(phpplots_path+'res/', dest+'res/')                         # Add a copy of res/ to dest
    except OSError: pass                                                            # shutil.copytree stupidly fails if .../res/ already exists 

    return
    
## Reads resolution values from log files and prints them out
def skim_resolutions(args, destinations):
    
    cutnames       = [x.split('/')[-2] for x in destinations]                       # Name of batch, IE 'baseline', 'damp_cut', 'chi2_and_aeff', etc..
    C3down_status  = []
    C3up_status    = []
    C3down_res     = []
    C3up_res       = []
    C3down_res_err = []
    C3up_res_err   = []

    log_files = []

    ## Checks that the folders exist, exit if not
    for dest in destinations:
        if not os.path.exists(dest): sys.exit('Error!!! Folder {} not found. Have you not run that analysis, or moved those files?'.format(dest))

    ## Get a list of all log files
    ## We keep each destinations log files separate so we can more easilly tell if any are missing, without annoying searches by name
    for dest in destinations:
        logs = []                           # Keep each destinations logs in an array. IE for baseline [<down>,<up>], damp [<down>,<up>], etc...
        for filei in os.listdir(dest):
            if filei.endswith('log.txt'):   
                logs.append(dest+filei)
        log_files.append(logs)

    ## Iterate over log files, skimming resolution values
    for logi in log_files:
        ## Check to see if any log files are missing and if so fill that data with 'N/A'
        if len(logi) != 2:                      # If we don't have a C3down and a C3up file...
            if not 'C3down' in logi[0]:         # If we're missing C3down_log.txt
                C3down_res.append('N/A')        # Fill with 'N/A'
                C3down_res_err.append('N/A')
                C3down_status.append('  ')
            if not 'C3up' in logi[0]:           # If we're missing C3up_log.txt
                C3up_res.append('N/A')          # Fill with 'N/A'
                C3up_res_err.append('N/A')
                C3up_status.append('  ')
        ## For the files we DO have, skim res and res_err from the log
        for filei in logi:
            filename = filei.split('/')[-1]                                                     # File name without the /path/
            with open(filei, 'r') as f:
                for line in f:
                    if 'Constant term:' in line:                                                # If 'line' contains 'Constant term:'
                        res = ''.join([d for d in line if d.isdigit() or d is '.'])             # Extract resolution from line (a bad method... )
                        if   filename.startswith('C3up')  : C3up_res.append(res)
                        elif filename.startswith('C3down'): C3down_res.append(res)
                    if 'Constant term error:' in line:                                          # If 'line' contains 'Constant term error:'
                        res_err = ''.join([d for d in line if d.isdigit() or d is '.'])         # Extract resolution uncertainty from line (a bad method... )
                        if   filename.startswith('C3up')  : C3up_res_err.append(res_err)
                        elif filename.startswith('C3down'): C3down_res_err.append(res_err)
                    if 'Reduced  fit chi2:' in line:
                        red_chi2 = ''.join([d for d in line if d.isdigit() or d is '.'])[1:]    # Extract reduced chi2 from line (a bad method... )
                        if   red_chi2 == '':
                            status = '**'
                        elif (float(red_chi2) > 1) and (float(red_chi2) < 2): 
                            status = ' *'
                        elif float(red_chi2) > 2: 
                            status = '**'
                        else:            
                            status = '  '
                        if   filename.startswith('C3up')  : C3up_status.append(status)
                        elif filename.startswith('C3down'): C3down_status.append(status)
                        
    ## Print out summary
    print('\n\t  Batch Resolution Analysis Summary for {}/{}:'.format(args.freq,args.temp))
    print(' '+'_'*76)
    print('|{0:^30}|{1:^22}|{2:^22}|'.format('Cut/Batch','C3down','C3up'))
    print('|'+'_'*30+'|'+'_'*22+'|'+'_'*22+'|')
    for cut, status1, r1, err1, status2, r2, err2 in zip(cutnames[:-1],C3down_status,C3down_res,C3down_res_err,C3up_status,C3up_res,C3up_res_err):  # cutnames[-1] is chi2_and_aeff, ignore
        print('|'+'-'*30+'|--|'+'-'*19+'|--|'+'-'*19+'|')
        print('|{0:^30}|{1}| {2:^5} +- {3:^5} ps |{4}| {5:^5} +- {6:^5} ps |'.format(cut,status1,r1,err1,status2,r2,err2))      # Print out with formatting for fixed width display
    print('|'+'_'*30+'|__|'+'_'*19+'|__|'+'_'*19+'|')
    print("('*'  means the fit's reduced chi2 is > 1. These fits may not be trustworthy  )")
    print("('**' means the fit's reduced chi2 is > 2. These fits are likely untrustworthy)")
    print('')
    
    return

def rerun_specific_run(args, destinations, run_cmds):

    print "Select which run(s) to redo from the list below:"
    print "(For multiple re-runs, enter numbers separated by commas, IE 1,4,6)"
    for i in range(len(destinations)):
        print "\t {} \t {}".format(i, destinations[i].split('/')[-2])
    reruns = raw_input("Select which runs to redo: ")
    reruns = list(map(int, reruns.split(',')))            # Convert the string to a list of int's
    print

    rerun_cmds  = []
    rerun_dests = []
    for i in range(len(destinations)):
        if i in reruns:
            rerun_cmds.append(run_cmds[i])
            rerun_dests.append(destinations[i])

    ## File path setup. phpplots_path is the "base"
    phpplots_path, plots_path, save_path = path_init(args)
    
    ## Check to make sure all relevant directories exist/are empty if need be
    check_directory(phpplots_path, plots_path,              False)
    check_directory(phpplots_path, save_path,               False)
    check_directory(phpplots_path, phpplots_path+'tmp/',    True )
    
    ## Run the commands and move them to the proper destination 
    for rerun_cmd, path in zip(rerun_cmds, rerun_dests):
        p = subprocess.Popen(rerun_cmd)                             # Run the command
        p.communicate()                                             # Wait for it to finish
        move_files_to_folder(phpplots_path, path, args)             # Move the plots to the proper folder under .../www/...
    
    ## Print out resolutions from the analysis  
    skim_resolutions(args, destinations)

def path_init(args):
    ## File path setup. phpplots_path is the "base"
    phpplots_path   = '/eos/user/m/mplesser/www/php-plots/'
    plots_path      = phpplots_path + 'plots/'
    save_path       = phpplots_path + 'plots/{}_{}/'.format(args.freq, args.temp)
    
    if not os.path.exists(phpplots_path):                           # This is the one path that has to exist before. The other folders will be created on the fly`
        sys.exit("Error!!! no /<user>/www/php-plots folder found! \nAborting...\n")

    return phpplots_path, plots_path, save_path

def main():

    args = input_arguments()

    ## File path setup. phpplots_path is the "base"
    phpplots_path, plots_path, save_path = path_init(args)

    ## Make a copy of the DtPlotter files so you can continue editing while a batch is running without changing the code while it runs
    Dt_path = '/afs/cern.ch/user/m/mplesser/my_git/CERN_Co-op/DtPlotter/'
    if os.path.exists(Dt_path+'tmp/'): shutil.rmtree(Dt_path+'tmp/')
    shutil.copytree(Dt_path, Dt_path+'tmp/')                                                                    
    
    ## Building the commands we want to run 
    cmd = ['python', Dt_path+'tmp/DtPlotter.py', '--freq', args.freq, '--temp', args.temp, '-e', args.energy]   # Base command, specifies which files/runs to use
    chi2andaeff     = cmd + ['-x'  , '-a'    ]                                                                  # Command to make chi2 and Aeff plots
    baseline        = cmd + ['-r'  , '--fit' ]                                                                  # Baseline dt resolution command, default cuts only
    da      =   ['--da', '500']                                                                                 # Misc extra cuts to be applied
    pc      =   ['--pc', '1'  ]                                                                                 # Misc extra cuts to be applied
    lc      =   ['--lc'       ]                                                                                 # Misc extra cuts to be applied
    
    ## Commands you want run
    run_commands = [baseline,               \
                    baseline + da,          \
                    baseline + pc,          \
                    baseline + lc,          \
                    baseline + da+pc,       \
                    baseline + da+lc,       \
                    baseline + pc+lc,       \
                    baseline + da+pc+lc,    \
                    chi2andaeff             ]
    
    ## Where to store the plots generated 
    destinations = [save_path + 'baseline/',                    \
                    save_path + 'damp_cut/',                    \
                    save_path + 'pos_cut/',                     \
                    save_path + 'lin_corr/',                    \
                    save_path + 'damp_and_pos/',                \
                    save_path + 'damp_and_lin_corr/',           \
                    save_path + 'pos_and_lin_corr/',            \
                    save_path + 'damp_and_pos_and_lin_corr/',   \
                    save_path + 'chi2_and_aeff/'                ]

    ## Skim resolutions from log files and exit instead of running analysis if '--summary' used
    if args.summary == True:
        skim_resolutions(args, destinations)
        shutil.rmtree(Dt_path+'tmp/')
        return  

    ## Run/re-run only select commands
    if args.rerun == True:
        rerun_specific_run(args, destinations, run_commands)
        shutil.rmtree(Dt_path+'tmp/')
        return

    ## Check to make sure all relevant directories exist/are empty if need be
    check_directory(phpplots_path, plots_path,              False)
    check_directory(phpplots_path, save_path,               True )
    check_directory(phpplots_path, phpplots_path+'tmp/',    True )
    
    ## Run the commands and move them to the proper destination 
    for runcmd, path in zip(run_commands, destinations):
        p = subprocess.Popen(runcmd)                                # Run the command
        p.communicate()                                             # Wait for it to finish
        move_files_to_folder(phpplots_path, path, args)             # Move the plots to the proper folder under .../www/...
    
    ## Print out resolutions from the analysis  
    skim_resolutions(args, destinations)
    
    shutil.rmtree(Dt_path+'tmp/')
    return

if __name__=="__main__":
    main()

