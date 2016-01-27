# from django.conf import settings # This urls.py file is looking for the TEST_CTS_PROXY_URL variable in the project settings.py file.
from django.shortcuts import render
from django.http import HttpResponse

import logging
import os
import requests
import json
from sparc_calculator import SparcCalc


def request_manager(request):

    try:
        calc = request.POST.get("calc")
        props = request.POST.getlist("props[]")
        structure = request.POST.get("chemical")
        single_prop = request.POST.get('single_prop') # is None if doesn't exist..

        logging.info("Incoming data to SPARC: {}, {}, {} (calc, props, chemical)".format(calc, props, structure))
        logging.info("Single prop: {}".format(single_prop))

        postData = {
            "calc": calc,
            "props": props
        }


        ############### filtered smiles stuff!!! ################################################
        # filtered_smiles = parseSmilesByCalculator(structure, "sparc") # call smilesfilter

        # logging.info("SPARC Filtered SMILES: {}".format(filtered_smiles)) 

        # if '[' in filtered_smiles or ']' in filtered_smiles:
        #   logging.warning("SPARC ignoring request due to brackets in SMILES..")
        #   postData.update({'error': "SPARC cannot process charged species or metals (e.g., [S+], [c+])"})
        #   return HttpResponse(json.dumps(postData), content_type='application/json')
        ###########################################################################################


        calcObj = SparcCalc(structure)


        # TODO: Handle request key for getting pka or ion_con props!!!
        if single_prop == 'ion_con':
            # make request to pka in sparc class:
            response = calcObj.makeCallForPka()
            post_data = {
                'data': calcObj.getPkaResults(response),
                'calc': calc,
                'prop': single_prop
            }
            logging.info("sparc post data: {}".format(post_data))
            return HttpResponse(json.dumps(post_data), content_type='application/json')
        elif single_prop == 'kow_wph':
            # make request to logD:
            ph = request.POST.get('ph') # get PH for logD calculation..
            response = calcObj.makeCallForLogD()
            post_data = { 
                'data': calcObj.getLogDForPH(response, ph),
                'calc': calc,
                'prop': single_prop
            }
            logging.info("sparc post data: {}".format(post_data))
            return HttpResponse(json.dumps(post_data), content_type='application/json')
        else:
            # business as usual:
            returnedData = calcObj.makeDataRequest() # make call for data!
            postData.update({"calc": "sparc", "props": props, "data": returnedData}) # add that data
            logging.info("SPARC POST Data: {}".format(postData))
            return HttpResponse(json.dumps(postData), content_type='application/json')

    except requests.HTTPError as e:
        logging.warning("HTTP Error occurred: {}".format(e))
        return HttpResponse(e.msg, status=e.code, content_type='text/plain')

    except ValueError as ve:
        logging.warning("POST data is incorrect: {}".format(ve))
        postData.update({"error": "value error"})
        return HttpResponse(json.dumps(postData), content_type='application/json')

    except requests.exceptions.ConnectionError as ce:
        logging.warning("Connection error occurred: {}".format(ce))
        postData.update({"error": "connection error"})
        return HttpResponse(json.dumps(postData), content_type='application/json')