# CERN_Co-op
Collection of code from my 2018 Co-op at CERN/CMS through Dr. Orimoto and Northeastern University

## DtPlotter:
Code for studying timing resolution in ECAL crystals from the June2018 test beam data.
First time users should try running wizard.py to help understand the available command line options.
DtPlotter.py is the main code, utilities/PlotterTools.py are the helper functions put in a class and another file, wizard.py is a very basic tool to help new users get aquainted with building commands, and CutBatchAnalysis.py is a template that can be adapted to automate running several analyses using different cuts.

## H4Analysis_bonus_tools
Misc scripts and macros to make using Simone Pigazzini's https://github.com/simonepigazzini/H4Analysis/tree/vfe_dev easier

### AutoHadd.py:
A script to automatically run hadd commands on reconstructed root files from Simone Pigazzini's H4Analysis repo, especially from the SubmitBatch.py script. Very conveniently handles consistent file naming, and sorting runs by position and energy from the info TTree.

Run as:
>python AutoHadd.py /path/to/files (frequency) (temperature)

### templateSubmitter.py:
Made to make template creation more convenient. Uses a list of run numbers and crystal positions to make many templates. Get Simone Pigazzini's H4Analysis repo, and put this file under 'H4Analysis/scripts'.

Run as: 
>python scripts/templateSubmitter.py (frequency) (temperature) (runs_and_positions.list) {-c (channels) <--optional}

See the in-code comments for more info on formatting

###

# ViceTools:
Tools for controlling vice boards for testing VFE and FE components and ECAL data streams.
