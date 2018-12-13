#!/usr/bin/python

## By Michael Plesser

import os       
from ROOT import TFile

class FileTools:

    def __init__(self, args):
        self.args = args
        self.freq = self.args.freq
        self.temp = self.args.temp
        self.name = self.args.name
        ## Obviously substitute in your default path to ntuples
        self.defaultanalysispath = "/eos/user/m/mplesser/timing_resolution/batch_ntuples/"+self.name+"_"+self.freq+"_"+self.temp+"_EScan_edges/compiled_roots/"
        
    ## Save a .root of the given TObject
    def save_files(self, h, path, file_title, name_tag):
        root_savefile = TFile(path + file_title + name_tag + ".root", "recreate")
        root_savefile.cd()              
        h.Write()

    ## Output location for plots
    def output_location(self):
        ## Either use the commented out line, or change the savepath, again, obviously
        #savepath = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','plots'))+'/'           # In the same directory as DtPlotter.py, save to a /plots/ subdir
        savepath = '/eos/user/m/mplesser/www/php-plots/tmp/'                                            # Save to my web eos folder
        if os.path.exists(savepath) == False:                                                           # Creates an output directory if none exists
            os.mkdir(savepath)
        return savepath

    ## Define location of files to be analyzed
    def analysis_path(self):
        def e_and_p(filei):                                                                             # Returns the energy and position of a file from it's name
            return filei.split('_')[-2]+'_'+filei.split('_')[-1].split('.')[0]                          # Assumes the filename of form '<blablabla>_e_p.root'

        Files = []                                                                                      # Format: [ ["name", "<energy>_<position>"], ...]
        
        if self.args.f is not None:                                                                     # File specified
            file = self.args.f
            Files.append( [ file, e_and_p(file) ] )                       
            print "Found file: ", file
            return Files

        if self.args.d is None:  self.args.d = self.defaultanalysispath                                 # Use default directory if no -d flag raised
        for file in os.listdir(self.args.d):
            if file.endswith('.root'):

                if self.args.e is not None:                                                             # Energy specified, only adds files with that energy
                    if str(self.args.e) in file:
                        Files.append( [ self.args.d + file, e_and_p(file) ] )
                        print "Found file: ", self.args.d + file
                else:                                                                                   # Add all root files in analysispath
                    Files.append( [ self.args.d + file, e_and_p(file) ] )
                    print "Found file: ", self.args.d + file

        return Files
