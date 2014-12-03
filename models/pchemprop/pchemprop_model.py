"""
2014-08-13 (np)
"""

import urllib2
import json
import requests
import pchemprop_parameters # Chemical Calculator and Transformation Pathway parameters
from REST import jchem_rest
from django.http import HttpRequest
import logging
from models.chemspec import chemspec_model # for getStructInfo(), TODO: move func to more generic place
import decimal

n = 3 # number of decimal places to round value

class pchemprop(object):
	def __init__(self, run_type, chem_struct, smiles, name, formula, mass, chemaxon, epi, 
					test, sparc, measured, melting_point, boiling_point, water_sol, 
					vapor_press, mol_diss, ion_con, henrys_law_con, kowNoPh, kowWph, kowPh, koc):

		self.run_type = run_type # defaults to "single", "batch" coming soon...
		self.jid = jchem_rest.gen_jid() # get time of run

		self.chem_struct = chem_struct
		self.smiles = smiles
		self.name = name
		self.formula = formula
		self.mass = mass

		# chemical properties (values 'on' or None) -- django params
		self.melting_point = melting_point
		self.boiling_point = boiling_point
		self.water_sol = water_sol
		self.vapor_press = vapor_press
		self.mol_diss = mol_diss
		self.ion_con = ion_con
		self.henrys_law_con = henrys_law_con
		self.kowNoPh = kowNoPh
		self.kowWph = kowWph
		self.kowPh = kowPh
		self.koc = koc

		# Create dictionary of chemprops with keys --> field names
		checkedPropsDict = {
			"melting_point": self.melting_point,
			"boiling_point": self.boiling_point,
			"water_sol": self.water_sol,
			"vapor_press": self.vapor_press,
			"mol_diss": self.mol_diss,
			"ion_con": self.ion_con,
			"henrys_law_con": self.henrys_law_con,
			"kow_no_ph": self.kowNoPh,
			"kow_wph": self.kowWph,
			"kow_ph": self.kowPh,
			"koc": self.koc
		}

		# calcluators' checkboxes (values 'true' or None) -- static html from cts_pchem.html
		self.chemaxon = chemaxon
		self.epi = epi
		self.test = test
		self.sparc = sparc
		self.measured = measured

		calcluatorsDict = {
			"chemaxon": self.chemaxon,
			"epi": self.epi,
			"test": self.test,
			"sparc": self.sparc,
			"measured": self.measured
		}

		# dict with keys of checked calculators and values of 
		# checked properties that are also available for said calculators
		checkedCalcsAndPropsDict = {}
		for calcKey, calcValue in calcluatorsDict.items():
			if calcValue == 'true' or calcValue == 'on':
				# get checked parameters that are available for calculator
				propList = []
				for propKey, propValue in checkedPropsDict.items():
					# find checked properties
					if propValue == 'on' or propValue == 'true':
						# check if property is available for calculator:
						if pchemprop_parameters.pchempropAvailable(calcKey, propKey):
							propList.append(propKey)
				checkedCalcsAndPropsDict.update({calcKey:propList})

		self.checkedCalcsAndPropsDict = checkedCalcsAndPropsDict
		# logging.warning("Checked Calculators and Properties:")
		# logging.warning(checkedCalcsAndPropsDict)

		self.chemaxonResultsDict = getChemaxonResults(self.chem_struct, checkedCalcsAndPropsDict)

		# get results from json:
		# self.chemaxonResultsDict = parseChemaxonResults(chemaxonResultsDict)

		self.resultsDict = {
			"chemaxon": self.chemaxonResultsDict,
			"epi": None,
			"sparc": None,
			"test": None
		}

		# fileout = open('C:\\Documents and Settings\\npope\\Desktop\\out.txt', 'w')
		# fileout.write(json.dumps(self.chemaxonResultsDict))
		# fileout.close()

def getChemaxonResults(structure, checkedCalcsAndPropsDict):
	"""
	Input: dict of checked/available properties for calculators
	Returns: dict of chemaxon props in web-service-friendly format
	"""

	chemaxonPropsList = checkedCalcsAndPropsDict.get('chemaxon', None)

	if chemaxonPropsList:

		propMethodsList = ['KLOP', 'PHYS', 'VG', 'WEIGHTED']
		chemaxonDict = {} # dict of results (values) per method (keys)

		for method in propMethodsList:
			postDict = {}
			# loop through chemaxon properties
			for prop in chemaxonPropsList:
				if prop == "solubility":
					postDict.update({
						"chemical": structure,
						"solubility": {
							"pHLower": 0,
							"pHUpper": 14,
							"pHStep": 0.1,
							"unit": "LOGS"
						}
					})
				if prop == "ion_con":
					# make call to getChemSpecData() for pKa values
					postDict.update({
						"chemical": structure,
						"pKa": { 
							"pHLower": 0, # note: default values
							"pHUpper": 14,
							"pHStep": 0.1
						}
					})
				if prop == "kow_no_ph":
					postDict.update({
						"logP": {
							"method": method
						}
					})
				if prop == "kow_wph":
					postDict.update({
						"logD": {
							"method": method
						}
					})

			if postDict != None:
				response = makeRequest(postDict) # get data per method
				chemaxonDict.update({method: json.loads(response)}) # results per method dictionary

		return buildChemaxonResultsDict(chemaxonDict)



def buildChemaxonResultsDict(chemaxonDict):
	"""
	Parses results from chemaxon data call

	Inputs: chemaxon dict
	"""

	propsList = [] # list of propDicts
	propDict = {}

	# loop through results per method
	for method, result in chemaxonDict.items():

		root = result['data'][0]

		if 'pKa' in root:
			# get mostAcidic and mostBasic values (both are list)
			pkaList = []
			for val in root['pKa']['mostAcidic']:
				pkaList.append(round(val, n))
			pkbList = []
			for val in root['pKa']['mostBasic']:
				pkbList.append(round(val, n))

			if 'Ionization Constant' in propDict:
				propDict['Ionization Constant'].update({
					method: {
						"pKa": pkaList,
						"pKb": pkbList
					}
				})
			else:
				propDict.update({
					"Ionization Constant": {
						method: {
							"pKa": pkaList,
							"pKb": pkbList
						} 
					}
				})

		dataDict = {}
		structInfo = {}
		if 'logP' in root:
			logPkeys = ['logpnonionic', 'logdpi', 'structInfo']
			logPname = "Octanol/Water Partition Coefficient"
			# get logpnonionic, logdpi, and imageUrl
			if 'logpnonionic' in root['logP'] and not isinstance(root['logP']['logpnonionic'], dict):
				dataDict.update({
					"logpnonionic": round(root['logP']['logpnonionic'], n)
				})
			else:
				dataDict.update({
					"logpnonionic": "none"
				})
			if 'logdpi' in root['logP'] and not isinstance(root['logP']['logdpi'], dict):
				dataDict.update({
					"logdpi": round(root['logP']['logdpi'], n)
				})
			else:
				dataDict.update({
					"logdpi": "none"
				})
			# if 'result' in root['logP']:
			# 	if 'structureData' in root['logP']['result']:
			# 		# Get smiles, iupac, mass, etc. as dict for logP structure
			# 		# TODO: move getStructInfo() to more generic place. it's used in all workflows
			# 		structInfo = chemspec_model.getStructInfo(root['logP']['result']['structureData']['structure'])
			# 		dataDict[logPname].update({'structInfo': structInfo})
			# 	if 'image' in root['logP']['result']:
			# 		dataDict.update({
			# 			"image": root['logP']['result']['image']['imageUrl']
			# 		})

			if logPname in propDict:
				propDict[logPname].update({
					method: dataDict 
				})
			else:
				propDict.update({
					logPname: {
						method: dataDict
					}
				})

		if 'logD' in root:
			logDname = "Octanol/Water Partition Coefficient at pH"
			if 'logD' in root['logD']:
				if logDname in propDict:
					propDict[logDname].update({
						method: {
							"logD": round(root['logD']['logD'], n)
						}
					})
				else:
					propDict.update({
						logDname: {
							method: {
								"logD": round(root['logD']['logD'], n)
							}
						}
					})

	return propDict
	

def makeRequest(postData):
	"""
	Makes request to jchem-cts ws
	Input: post data as dict
	Returns: response content (json string)
	"""
	request = HttpRequest()
	request.POST = postData
	response = jchem_rest.getChemSpecData(request)
	return response.content