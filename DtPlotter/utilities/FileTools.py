#!/usr/bin/python

## By Michael Plesser

import os       
from ROOT import TFile

class FileTools:
    def __init__(self, args):
        self.args = args
        self.freq = self.args.freq
        self.temp = self.args.temp

        self.defaultanalysispath = "/eos/user/m/mplesser/timing_resolution/batch_ntuples/ECAL_H4_June2018_"+self.freq+"_"+self.temp+"_EScan_edges/compiled_roots/"
        
    ## Save a .root of the given TObject
    def save_files(self, h, path, file_title, name_tag):
        root_savefile = TFile(path + file_title + name_tag + ".root", "recreate")
        root_savefile.cd()              
        h.Write()
        print  "Saved file:", path + file_title + name_tag + '.root'

    ## Output location for plots
    def output_location(self):
        #savepath = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','plots'))+'/'           # In the same directory as DtPlotter.py, save to a /plots/ subdir
        savepath = '/eos/user/m/mplesser/www/php-plots/tmp/'                                            # Save to my web eos folder
        if os.path.exists(savepath) == False:                                                           # Creates an output directory if none exists
            os.mkdir(savepath)
        return savepath

    ## Define location of files to be analyzed
    def analysis_path(self):
        
        print
        Files = []                                                                                          # Format: [ ["name", "<energy>_<position>"], ...]
        if self.args.d is None:  self.args.d = self.defaultanalysispath                                     # Use default directory if no -d flag raised
        for file in os.listdir(self.args.d):
            if file.endswith('.root'):
                energy_position = file.split('_')[-2]+'_'+file.split('_')[-1].split('.')[0]                 # Assumes the filename of form <blablabla>_energy_position.root
                if self.args.f is not None:                                                                 # File specified
                    file = self.args.f
                    Files.append( [ file, energy_position ] )                       
                    print "Found file: ", file
                    return Files

                if self.args.e is not None:                                                                 # Energy specified, only adds files with that energy
                    if file.split('_')[-2]==self.args.e:
                        Files.append( [ self.args.d + file, energy_position ] )
                        print "Found file: ", self.args.d + file
                else:                                                                                       # Add all root files in analysispath
                    Files.append( [ self.args.d + file, energy_position ] )
                    print "Found file: ", self.args.d + file

        return Files
