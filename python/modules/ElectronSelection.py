import os
import sys
import math
import json
import ROOT
import random

from PhysicsTools.NanoAODTools.postprocessing.framework.datamodel import Collection
from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module

from utils import getGraph, getHist, combineHist2D, getSFXY, deltaR

class ElectronSelection(Module):
    VETO = 0
    LOOSE = 1
    MEDIUM = 2
    TIGHT = 3

    def __init__(
        self,
        inputCollection = lambda event: Collection(event, "Electron"),
        outputName = "tightElectrons",
        triggerMatch = False,
        electronID = TIGHT,
        electronMinPt = 5.,
        electronMaxEta = 2.4,
        storeKinematics=['pt','eta'],
        storeWeights=False,
        selectLeadingOnly=False,
        globalOptions={"isData":False, "year":2016}
    ):
        
        self.globalOptions = globalOptions
        self.inputCollection = inputCollection
        self.outputName = outputName
        self.electronMinPt = electronMinPt
        self.electronMaxEta = electronMaxEta
        self.storeKinematics = storeKinematics
        self.storeWeights = storeWeights
        self.selectLeadingOnly = selectLeadingOnly
        self.triggerMatch = triggerMatch
        self.electronID = electronID

        if triggerMatch:
            self.trigger_object = lambda event: Collection(event, "TrigObj")


        id_alias_dict = {1: "Loose", 2: "Medium", 3: "Tight"}

        id_hist_dict = {
                2016: "2016LegacyReReco_ElectronREPLACE_Fall17V2.root",
                2017: "2017_ElectronREPLACE.root",
                2018: "2018_ElectronREPLACE.root"
        }

        #tight id efficiency
        self.idHist = getHist(
            "PhysicsTools/NanoAODTools/data/electron/{}/{}".format(globalOptions["year"], id_hist_dict[globalOptions["year"]].replace("REPLACE", id_alias_dict[self.electronID])),
            "EGamma_SF2D"
        )

 
    def beginJob(self):
        pass
        
    def endJob(self):
        pass
        
    def beginFile(self, inputFile, outputFile, inputTree, wrappedOutputTree):
        self.out = wrappedOutputTree
        self.out.branch("n"+self.outputName, "I")
 
        if not self.globalOptions["isData"] and self.storeWeights:
            self.out.branch(self.outputName+"_weight_id_nominal","F")
            self.out.branch(self.outputName+"_weight_id_up","F")
            self.out.branch(self.outputName+"_weight_id_down","F")
            
        for variable in self.storeKinematics:
            self.out.branch(self.outputName+"_"+variable,"F",lenVar="n"+self.outputName)
            
        
    def endFile(self, inputFile, outputFile, inputTree, wrappedOutputTree):
        pass
        
    def analyze(self, event):
        """process event, return True (go to next module) or False (fail, go to next event)"""
        electrons = self.inputCollection(event)
        muons = Collection(event, "Muon")
        
        selectedElectrons = []
        unselectedElectrons = []
 
        weight_id_nominal = []
        weight_id_up = []
        weight_id_down = []
        
        for electron in electrons:
            if electron.pt>self.electronMinPt and math.fabs(electron.eta)<self.electronMaxEta and (electron.cutBased>self.electronID):

                if muons is not None and len(muons) > 0:

                    mindr = min(map(lambda muon: deltaR(muon, electron), muons))
                    if mindr < 0.05:
                        unselectedElectrons.append(electron)
                        continue

                selectedElectrons.append(electron)
                weight_id,weight_id_err = getSFXY(self.idHist,electron.eta,electron.pt)
                weight_id_nominal.append(weight_id)
                weight_id_up.append((weight_id+weight_id_err))
                weight_id_down.append((weight_id-weight_id_err))
            else:
                unselectedElectrons.append(electron)

        if len(selectedElectrons) > 0:
            if self.selectLeadingOnly:
                unselectedElectrons.extend(selectedElectrons[1:])
                selectedElectrons = [selectedElectrons[0]]

            if not self.globalOptions["isData"] and self.storeWeights:
                weight_id_nominal = reduce(lambda x, y: x*y, weight_id_nominal)
                weight_id_up = reduce(lambda x, y: x*y, weight_id_up)
                weight_id_down = reduce(lambda x, y: x*y, weight_id_down)

        elif not self.globalOptions["isData"] and self.storeWeights:
            weight_id_nominal = 1.
            weight_id_up = 1.
            weight_id_down = 1.


        if not self.globalOptions["isData"] and self.storeWeights:
            self.out.fillBranch(self.outputName+"_weight_id_nominal", weight_id_nominal)
            self.out.fillBranch(self.outputName+"_weight_id_up", weight_id_up)
            self.out.fillBranch(self.outputName+"_weight_id_down", weight_id_down)
        


        self.out.fillBranch("n"+self.outputName,len(selectedElectrons))
        for variable in self.storeKinematics:
            self.out.fillBranch(self.outputName+"_"+variable,map(lambda electron: getattr(electron,variable),selectedElectrons))
 

        setattr(event,self.outputName,selectedElectrons)
        setattr(event,self.outputName+"_unselected",unselectedElectrons)

        return True
        