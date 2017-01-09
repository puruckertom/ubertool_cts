from django.template.loader import render_to_string
from django.http import HttpResponse
import importlib
import linksLeft
import os

def descriptionPage(request, model='none', header='none'):
    viewmodule = importlib.import_module('.views', 'cts_app.models.'+model)
    header = viewmodule.header

    text_file2 = open(os.path.join(os.environ['PROJECT_PATH'], 'cts_app/models/'+model+'/'+model+'_text.txt'),'r')
    xx = text_file2.read()
    html = render_to_string('01cts_uberheader.html', {'title': header+' Description'})
    html = html + render_to_string('02cts_uberintroblock_wmodellinks.html', {'model':model,'page':'description'})
    html = html + linksLeft.linksLeft()
    html = html + render_to_string('04cts_ubertext_start.html', {
            'model_attributes': header+' Overview',
            'text_paragraph':xx})

    html = html + render_to_string('04cts_ubertext_nav.html', {'model':model})

    html = html + render_to_string('04cts_ubertext_end.html', {})
    html = html + render_to_string('05cts_ubertext_links_right.html', {})
    html = html + render_to_string('06cts_uberfooter.html', {'links': ''})
    
    response = HttpResponse()
    response.write(html)
    return response