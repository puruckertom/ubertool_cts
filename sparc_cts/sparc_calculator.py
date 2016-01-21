__author__ = 'KWOLFE'

import sys
import json
import logging
import requests
import os
from enum import Enum
import math

from REST.calculator import Calculator
from REST.calculator import CTSChemicalProperties


########################## SPARC physical properties calculator interface ###################
headers = {'Content-Type': 'application/json'}
class SparcCalc(Calculator):
    def __init__(self, smiles=None, pressure=760.0, meltingpoint=0.0, temperature=25.0):

        self.base_url = os.environ['CTS_SPARC_SERVER']
        self.multiproperty_url = '/sparc-integration/rest/calc/multiProperty'
        self.name = "sparc"
        self.smiles = smiles
        self.solvents = dict()
        self.pressure = pressure
        self.meltingpoint = meltingpoint
        self.temperature = temperature
        self.propMap = {
            "water_sol" : "SOLUBILITY",
            "vapor_press" : "VAPOR_PRESSURE",
            "henrys_law_con" : "HENRYS_CONSTANT",
            "mol_diss" : "DIFFUSION",
            "boiling_point": "BOILING_POINT"
        }
        self.sparc_props = [
            { 'name': "VAPOR_PRESSURE", 'units': "Torr" },
            { 'name': "BOILING_POINT", 'units': "degreesC" },
            { 'name': "DIFFUSION", 'units': "NO_UNITS" },
            { 'name': "VOLUME", 'units': "cmCubedPerMole" },
            { 'name': "DENSITY", 'units': "gPercmCubed" },
            { 'name': "POLARIZABLITY", 'units': "angCubedPerMolecule" },
            { 'name': "INDEX_OF_REFRACTION", 'units': "dummy" },
            { 'name': "HENRYS_CONSTANT", 'units': "AtmPerMolPerM3" },
            { 'name': "SOLUBILITY", 'units': "mgPerL" },
            { 'name': "ACTIVITY", 'units': "dummy" },
            { 'name': "ELECTRON_AFFINITY", 'units': "dummy" },
            { 'name': "DISTRIBUTION", 'units': "NO_UNITS" }
        ]

    def get_sparc_query(self):
        query = {
            'pressure': self.pressure,
            'meltingpoint': self.meltingpoint,
            'temperature': self.temperature,
            'calculations': self.getCalculations(),
            'smiles': self.smiles,
            'userId': None,
            'apiKey': None,
            'type': 'MULTIPLE_PROPERTY',
            'doSolventInit': False
        }
        return query

    def get_calculation(self, sparc_prop=None, units=None):
        calc = {
            'solvents': [],
            'units': units,
            'pressure': self.pressure,
            'meltingpoint': self.meltingpoint,
            'temperature': self.temperature,
            'type': sparc_prop
        }
        return calc

    def get_solvent(self, smiles=None, name=None):
        solvent = {
            'solvents': None,
            'smiles': smiles,
            'mixedSolvent': None,
            'name': name
        }
        return solvent


    def getCalculations(self):

        calculations = []
        calculations.append(self.get_calculation("VAPOR_PRESSURE", "Torr"))
        calculations.append(self.get_calculation("BOILING_POINT", "degreesC"))
        calculations.append(self.get_calculation("DIFFUSION", "NO_UNITS"))
        calculations.append(self.get_calculation("VOLUME", "cmCubedPerMole"))
        calculations.append(self.get_calculation("DENSITY", "gPercmCubed"))
        calculations.append(self.get_calculation("POLARIZABLITY", "angCubedPerMolecule"))
        calculations.append(self.get_calculation("INDEX_OF_REFRACTION", "dummy"))

        calcHC = self.get_calculation("HENRYS_CONSTANT", "AtmPerMolPerM3")
        calcHC["solvents"].append(self.get_solvent("O", "water"))
        calculations.append(calcHC)

        calcSol = self.get_calculation("SOLUBILITY", "mgPerL")
        calcSol["solvents"].append(self.get_solvent("O", "water"))
        calculations.append(calcSol)

        calcAct = self.get_calculation("ACTIVITY", "dummy")
        calcAct["solvents"].append(self.get_solvent("O", "water"))
        calculations.append(calcAct)

        calculations.append(self.get_calculation("ELECTRON_AFFINITY", "dummy"))

        calcDist = self.get_calculation("DISTRIBUTION", "NO_UNITS")
        calcDist["solvents"].append(self.get_solvent("O", "water"))

        calculations.append(calcDist)

        return calculations


    def makeDataRequest(self):

        # Testing on local machine using static sparc response file:
        post = self.get_sparc_query()
        headers = {'Content-Type': 'application/json'}
        url = self.base_url
        logging.info("SPARC URL: {}".format(url))
        logging.info("SPARC POST: {}".format(post))
        fileout = open('C:\\Users\\nickpope\\Desktop\\sparc_response.txt', 'r')
        response_json_string = fileout.read()
        fileout.close()
        logging.info("SPARC Response: {}".format(response_json_string))
        logging.info("Type: {}".format(type(response_json_string)))
        self.results = json.loads(response_json_string)
        # self.performUnitConversions(self.results)
        return self.results

        # Actual calls to SPARC calculator:
        # post = self.get_sparc_query()
        # url = self.base_url

        # logging.info("SPARC URL: {}".format(url))
        # logging.info("SPARC POST: {}".format(post))

        # try:
        #     response = requests.post(url, data=json.dumps(post), headers=headers, timeout=30)
        #     self.results = json.loads(response.content)
        # except requests.exceptions.ConnectionError as ce:
        #     logging.info("connection exception: {}".format(ce))
        #     raise
        # except requests.exceptions.Timeout as te:
        #     logging.info("timeout exception: {}".format(te))
        #     raise
        # else:
        #     return self.results


    def makeCallForPKA(self):
        """
        Separate call for pKa. Not sure why but
        what what I'm told it needs to be done 
        separately for now
        """
        pka_url = "/rest/calc/fullSpeciation"
        url = self.base_url + pka_url
        post = {
            "type":"FULL_SPECIATION",
            "temperature":25.0,
            "minPh":0,
            "phIncrement":0.5,
            "smiles": self.smiles,
            "username":"browser1",
            "elimAcid":[],
            "elimBase":[],
            "considerMethylAsAcid": True
        }
        try:
            response = requests.post(url, data=json.dumps(post), headers=headers, timeout=20)
            results = json.loads(response.content)
        except Exception as e:
            logging.warning("SPARC PKA CALL ERROR: {}".format(e))
            raise
        else:
            return results


    def makeCallForLogD(self):
        """
        Seprate call for octanol/water partition
        coefficient with pH (logD?)
        """
        logd_url = "/rest/calc/logd"
        url = self.base_url + logd_url
        post = {
           "type":"LOGD",
           "solvent": {
              "solvents": None,
              "smiles": "O",
              "mixedSolvent": False,
              "name": "water"
           },
           "temperature": 25.0,
           "pH_minimum": 0,
           "pH_increment": 0.5,
           "ionic_strength": 0.0,
           "smiles": self.smiles
        }
        try:
            response = requests.post(url, data=json.dumps(post), headers=headers, timeout=20)
            results = json.loads(response.content)
        except Exception as e:
            logging.warning("SPARC LOGD CALL ERROR: {}".format(e))
            raise
        else:
            return results

    def getLogDForPH(self, results, ph=7.0):
        """
        Gets logD value at ph from
        logD response data
        TODO: add ph functionality
        """
        plot_data = results['plotCoordinates'] # list of [x,y]..
        for xypair in plot_data:
            if xypair[0] == ph:
                return xypair[1]