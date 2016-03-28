# from django.conf import settings # This urls.py file is looking for the TEST_CTS_PROXY_URL variable in the project settings.py file.
from django.shortcuts import render
from django.http import HttpResponse
from django.core.cache import cache

import logging
import requests
import json
import redis

from sparc_calculator import SparcCalc


def request_manager(request):

    try:
        calc = request.POST.get("calc")
        # props = request.POST.getlist("props[]")
        try:
            props = request.POST.get("props[]")  # expecting None if none
        except AttributeError:
            props = request.POST.get("props")
        structure = request.POST.get("chemical")
        sessionid = request.POST.get('sessionid')

        logging.info("Incoming data to SPARC: {}, {}, {} (calc, props, chemical)".format(calc, props, structure))

        post_data = {
            "calc": calc,
            "props": props
        }


        ############### Filtered SMILES stuff!!! ################################################
        # filtered_smiles = parseSmilesByCalculator(structure, "sparc") # call smilesfilter

        # logging.info("SPARC Filtered SMILES: {}".format(filtered_smiles)) 

        # if '[' in filtered_smiles or ']' in filtered_smiles:
        #   logging.warning("SPARC ignoring request due to brackets in SMILES..")
        #   post_data.update({'error': "SPARC cannot process charged species or metals (e.g., [S+], [c+])"})
        #   return HttpResponse(json.dumps(post_data), content_type='application/json')
        ###########################################################################################


        calcObj = SparcCalc(structure)


        ion_con_response, kow_wph_response, multi_response = None, None, None
        sparc_results = []

        # synchronous calls for ion_con, kow_wph, and the rest:

        for prop in props:

            if prop == 'ion_con':
                response = calcObj.makeCallForPka() # response as d ict returned..
                pka_data = calcObj.getPkaResults(response)
                ion_con_response = {
                    'calc': 'sparc',
                    'prop': 'ion_con',
                    'data': pka_data
                }
                sparc_results.append(ion_con_response)

            if prop == 'kow_wph':
                ph = request.POST.get('ph') # get PH for logD calculation..
                response = calcObj.makeCallForLogD() # response as dict returned..
                kow_wph_response = {
                    'calc': 'sparc',
                    'prop': 'kow_wph',
                    'data': calcObj.getLogDForPH(response, ph)
                }
                sparc_results.append(kow_wph_response)

        prop_map = calcObj.propMap.keys()
        if any(prop in prop_map for prop in props):
            logging.info("Making SPARC multi property request...")
            multi_response = calcObj.makeDataRequest()
            if 'calculationResults' in multi_response:
                multi_response = calcObj.parseMultiPropResponse(multi_response['calculationResults'])
                for prop_obj in multi_response:
                    logging.info("prop: {}".format(prop_obj['prop']))
                    if prop_obj['prop'] in props:
                        sparc_results.append(prop_obj)

        logging.info("SPARC RESULTS: {}".format(sparc_results))

        post_data.update({'data': sparc_results})

        # node/redis stuff:
        result_json = json.dumps(post_data)
        if sessionid:
            r = redis.StrictRedis(host='localhost', port=6379, db=0)  # instantiate redis (where should this go???)
            r.publish(sessionid, result_json)

        return HttpResponse(result_json, content_type='application/json')

    except requests.HTTPError as e:
        logging.warning("HTTP Error occurred: {}".format(e))
        return HttpResponse(e.msg, status=e.code, content_type='text/plain')

    except ValueError as ve:
        logging.warning("POST data is incorrect: {}".format(ve))
        post_data.update({"error": "{}".format(ve)})
        return HttpResponse(json.dumps(post_data), content_type='application/json')

    except requests.exceptions.ConnectionError as ce:
        logging.warning("Connection error occurred: {}".format(ce))
        post_data.update({"error": "connection error"})
        return HttpResponse(json.dumps(post_data), content_type='application/json')