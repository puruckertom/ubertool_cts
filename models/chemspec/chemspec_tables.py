"""
.. module:: chemspec_tables
   :synopsis: A useful module indeed.
"""

# import numpy
from django.template import Context, Template
# from django.utils.safestring import mark_safe
# import logging
import time
import datetime
from django.template.loader import render_to_string
import logging
import json
from PIL import Image
import urllib2
from StringIO import StringIO
from django.utils.safestring import mark_safe

# logger = logging.getLogger("chemspecTables")

def getheaderpv():
    headings = ["Parameter", "Value"]
    return headings

def getpkaheader():
    headings = ['Basic pKa Value(s)', 'Acidic pKa Value(s)']
    return headings

def getheaderspecies():
    headings = ["Parent Species", "Microspecies"]
    return headings

def gethtmlrowsfromcols(data, headings):
    columns = [data[heading] for heading in headings]

    # get the length of the longest column
    max_len = len(max(columns, key=len))

    for col in columns:
        # padding the short columns with None
        col += [None,] * (max_len - len(col))

    # Then rotate the structure...
    rows = [[col[i] for col in columns] for i in range(max_len)]
    return rows


# def getdjtemplate():
#     dj_template ="""
#     <table class="out_">
#     {# headings #}
#         <tr>
#         {% for heading in headings %}
#             <th>{{ heading }}</th>
#         {% endfor %}
#         </tr>
#     {# data #}
#     {% for row in data %}
#     <tr>
#         {% for val in row %}
#             <td>{{ val|default:'None' }}</td>
#         {% endfor %}
#     </tr>
#     {% endfor %}
#     </table>
#     """
#     return dj_template


def getdjtemplate():
    dj_template ="""
    <dl class="shiftRight">
    {% for label, value in data %}
        <dd>
        <b>{{label}}</b> {{value|default:"none"}}
        </dd>
    {% endfor %}
    </dl>
    """
    return dj_template


def getImagesTemplate():
    images_template = """
    <br>
    <dl class="shiftRight">
    {% if data.Parent or data.Microspecies %}
        <dt class="imgHeader"><b>Parent</b></dt>
        {% for item in data.Parent %}
            <dd><img src="{{item}}"><dd>
        {% endfor %}
        <dt class="imgHeader"><b>Microspecies</b></dt>
        <dd>
        {% if data.Microspecies %}
            
            {% for item in data.Microspecies %}
                <img src="{{item}}">
            {% endfor %}
        {% else %}
            <p class="shiftRight">No microspecies</p>
        {% endif %}
        </dd>
    {% else %}
        <dd>
        {% for item in data.stereoImageUrl %}
            <img src="{{item}}">
        {% endfor %}
        </dd>
        <dd>
        {% for item in data.tautImageUrl %}
            <img src="{{item}}">
        {% endfor %}
        </dd>
    {% endif %}
    </dl>
    """
    return images_template


def getMolTblData(chemspec_obj):
    data = {
        "Parameter": ['Structure:', 'SMILES:', 'IUPAC:', 'Formula:', 'Mass:'],
        "Value": [chemspec_obj.chem_struct, chemspec_obj.smiles, chemspec_obj.name, chemspec_obj.formula, chemspec_obj.mass],
        # "Image": [chemspec_obj.parentImage]
    }
    return data


def getIsoPtData(chemspec_obj):
    data = {
        "Parameter": ['isoelectric point:'],
        "Value": [chemspec_obj.isoPtDict['isoPt']]
        # "Value": ['test']
    }
    return data


# Ionization Constants (pKa) Parameters Data
def getPkaData(chemspec_obj):
    data = {
        "Parameter": ['Number of Decimals:', 'pH Lower Limit:', 'pH Upper Limit:', 'pH Step Size:','Generate Major Microspecies at pH:', 'Isoelectric Point (pl) pH Step Size of Charge Distribution:' ],
        "Value": [chemspec_obj.pKa_decimals, chemspec_obj.pKa_pH_lower, chemspec_obj.pKa_pH_upper, chemspec_obj.pKa_pH_increment, chemspec_obj.pH_microspecies, chemspec_obj.isoelectricPoint_pH_increment ],
    }
    return data


# Dominate Tautomer Distribution Data
def getTautData(chemspec_obj):
    data = {
        "Parameter": ['Maximum Number of Structures:', 'at pH:' ],
        "Value": [chemspec_obj.tautomer_maxNoOfStructures, chemspec_obj.tautomer_pH ]
    }
    return data


# Stereoisomers Data
def getStereoData(chemspec_obj):
    data = {
        "Parameter": ['Maximum Number of Structures:'],
        "Value": [chemspec_obj.stereoisomers_maxNoOfStructures]
    }
    return data


# Parent/Micro species data dictionary for templating
def getPkaValues(chemspec_obj):
    # jsonData = json.dumps(chemspec_obj.result)
    
    data = { 
        "Parameter": ['Basic pKa Value(s):', 'Acidic pKa Value(s):'],
        "Value": [chemspec_obj.pkaDict['mostBasicPka'], chemspec_obj.pkaDict['mostAcidicPka']],
    }
    return data


# Parent and Microspecies Images
def getSpeciesImages(chemspec_obj):
    data = {
        "Parent": [chemspec_obj.pkaDict['parentImage']],
        "Microspecies": chemspec_obj.pkaDict['msImageUrlList']
    }
    return data


pvheadings = getheaderpv()
pkaheadings = getpkaheader()

djtemplate = getdjtemplate()
tmpl = Template(djtemplate)

imagesTemplate = getImagesTemplate()
tmplImg = Template(imagesTemplate)


def table_all(chemspec_obj):
    html_all = '<script type="text/javascript" src="/static/stylesheets/structure_wrapper.js"></script>'
    html_all = html_all + table_struct(chemspec_obj)
    html_all = html_all + table_pka_input(chemspec_obj)     
    html_all = html_all + table_taut_input(chemspec_obj)
    html_all = html_all + table_stereo_input(chemspec_obj) 
    html_all = html_all + table_isoPt_results(chemspec_obj)
    html_all = html_all + table_isoPt_plot(chemspec_obj)
    html_all = html_all + table_majorMs_Images(chemspec_obj)
    html_all = html_all + table_pka_results(chemspec_obj)
    html_all = html_all + table_images(chemspec_obj)
    html_all = html_all + table_microplot(chemspec_obj)
    html_all = html_all + table_stereo_results(chemspec_obj)
    html_all = html_all + table_taut_results(chemspec_obj)
    html_all = html_all + render_to_string('cts_plot_microspecies_dist.html')
    return html_all

def timestamp(chemspec_obj="", batch_jid=""):
    if chemspec_obj:
        st = datetime.datetime.strptime(chemspec_obj.jid, '%Y%m%d%H%M%S%f').strftime('%A, %Y-%B-%d %H:%M:%S')
    else:
        st = datetime.datetime.strptime(batch_jid, '%Y%m%d%H%M%S%f').strftime('%A, %Y-%B-%d %H:%M:%S')
    html="""
    <div class="out_">
        <b>Chemical Speciation - Version 1.0 (Alpha)<br>
    """
    html = html + st
    html = html + " (EST)</b>"
    html = html + """
    </div>"""
    return html

    
"""
Structure Information Table
"""
def table_struct(chemspec_obj):
    html = """
    <br>
    <H3 class="out_1 collapsible" id="section1"><span></span>User Inputs</H3>
    <div class="out_">
        <H4 class="out_1 collapsible" id="section2"><span></span><b>Molecular Information</b></H4>
            <div class="out_ container_output">
    """

    molTblData = getMolTblData(chemspec_obj)
    molTblRows = gethtmlrowsfromcols(molTblData, pvheadings)
    html = html + tmpl.render(Context(dict(data=molTblRows, headings=pvheadings)))

    #try to add structure image:
    # html = html + mark_safe('<img src="' + chemspec_obj.image + '" alt="Structure Image"></img>')

    html = html + """
    </div>
    """
    return html


"""
pKa User Input Table
"""
def table_pka_input(chemspec_obj):
    if chemspec_obj.pkaDict:
        html = """
        <H4 class="out_1 collapsible" id="section3"><span></span><b>Ionization Constants (pKa) Parameters</b></H4>
            <div class="out_ container_output">
        """
        t1data = getPkaData(chemspec_obj)
        t1rows = gethtmlrowsfromcols(t1data,pvheadings)
        # t2data = gett2data(chemspec_obj)
        # t2rows = gethtmlrowsfromcols(t2data, pvheadings)
        html = html + tmpl.render(Context(dict(data=t1rows, headings=pvheadings)))
        # html = html + tmpl.render(Context(dict(data=t2rows, headings=pvheadings)))
        html = html + """
        </div>
        """
        return html
    else:
        return ""


"""
Tautomer User Input Table
"""
def table_taut_input(chemspec_obj):
    if chemspec_obj.tautDict:
        html = """
        <H4 class="out_1 collapsible" id="section4"><span></span><b>Dominate Tautomer Distribution Parameters</b></H4>
                    <div class="out_ container_output">
        """
        tblData = getTautData(chemspec_obj)
        tblRows = gethtmlrowsfromcols(tblData, pvheadings)
        html = html + tmpl.render(Context(dict(data=tblRows, headings=pvheadings)))
        html = html + """
        </div>
        """
        return html
    else:
        return ""


"""
Stereoisomers User Input Table
"""
def table_stereo_input(chemspec_obj):
    if chemspec_obj.stereoDict:
        html = """
        <H4 class="out_1 collapsible" id="section5"><span></span><b>Stereoisomers Parameters</b></H4>
                    <div class="out_ container_output">
        """
        tblData = getStereoData(chemspec_obj)
        tblRows = gethtmlrowsfromcols(tblData, pvheadings)
        html = html + tmpl.render(Context(dict(data=tblRows, headings=pvheadings)))
        html = html + """
        </div></div>
        """
        return html
    else:
        return "</div>" #close out Molecular Info div (last input checked)


"""
isoelectricPoint Calculations Table
"""
def table_isoPt_results(chemspec_obj):
    if chemspec_obj.isoPtDict:
        html = """
        <H3 class="out_1 collapsible" id="section6"><span></span>Isoelectric Point</H3>
        <div class="out_">
        """
        tblData = getIsoPtData(chemspec_obj)
        tblRows = gethtmlrowsfromcols(tblData, pvheadings)
        html = html + tmpl.render(Context(dict(data=tblRows, headings=pvheadings)))
        html = html + """

        """
        return html
    else:
        return ""


def table_isoPt_plot(chemspec_obj):
    if chemspec_obj.isoPtDict:
        html = """
        <H4 class="out_1 collapsible" id="section9"><span></span><b>Isoelectric Point Plot</b></H4>
        <div class="out_" id="section6">
        """
        # if chemspec_obj.isoPtDict['isoPtChartData']:
        if 'isoPtChartData' in chemspec_obj.isoPtDict:
            html = html + """
            <div id="isoelectric-point" class="plot"></div>
            <div id="isoPtData" class="hideData">
            """
            html = html + mark_safe(json.dumps(chemspec_obj.isoPtDict['isoPtChartData']))
            html = html + """
            </div>
            """
        else:
            html = html + """
            <p class="shiftRight">No isoelectric point</p>
            """
        html = html + """
        </div></div>
        """
        return html
    else:
        return ""


"""
majorMicrospecies Image Table
"""
def table_majorMs_Images(chemspec_obj):
    if chemspec_obj.majorMsDict:
        html = """
        <H3 class="out_1 collapsible" id="section6"><span></span>Major Microspecies</H3>
        <div class="out_">
        """
        html = html + wrap_molecule(chemspec_obj.majorMsDict)
        html = html + """
        </div>
        """
        return html
    else:
        return ""


"""
pKa Calculations Table
"""
def table_pka_results(chemspec_obj):
    if chemspec_obj.pkaDict:
        html = """
        <H3 class="out_1 collapsible" id="section6"><span></span>pKa</H3>
        <div class="out_">
            <H4 class="out_1 collapsible" id="section7"><span></span><b>Most Acidic/Basic</b></H4>
                    <div class="out_ container_output">
        """
        t3data = getPkaValues(chemspec_obj)
        t3rows = gethtmlrowsfromcols(t3data, pvheadings)
        html = html + tmpl.render(Context(dict(data=t3rows, headings=pvheadings)))
        html = html + """
        </div>
        """
        return html
    else:
        return ""


"""
parent and microspecies images table
"""
def table_images(chemspec_obj):

    if chemspec_obj.pkaDict:
        html = """
        <H4 class="out_1 collapsible" id="section8"><span></span><b>Parent/Microspecies Images</b></H4>
        <div class="out_">
        """
        html = html + "Parent: "
        html = html + wrap_molecule(chemspec_obj.pkaDict['parent'])

        # tblData = getSpeciesImages(chemspec_obj)
        # html = html + tmplImg.render(Context(dict(data=tblData)))
        html = html + "Microspecies: "
        logging.warning(chemspec_obj.pkaDict['msImageUrlList'])
        if chemspec_obj.pkaDict['msImageUrlList']:
            for item in chemspec_obj.pkaDict['msImageUrlList']:
                html = html + wrap_molecule(item)
        else:
            html += "none"
        html = html + """
        </div>
        """
        return html
    else:
        return ""


"""
Microspecies Distribution Plot "Table"
"""
def table_microplot(chemspec_obj):

    if chemspec_obj.pkaDict:
        html = """
        <H4 class="out_1 collapsible" id="section9"><span></span><b>Microspecies Distribution Plot</b></H4>
        <div class="out_" id="section6">
        """
        if chemspec_obj.pkaDict['microDistData']:
            html = html + """
            <div id="microspecies-distribution" class="plot"></div>
            <div id="microDistData1" class="hideData">
            """
            html = html + mark_safe(json.dumps(chemspec_obj.pkaDict['microDistData']))
            html = html + """
            </div>
            """
        else:
            html = html + """
            <p class="shiftRight">No microspecies for plotting</p>
            """
        html = html + """
        </div></div>
        """
        return html
    else:
        return ""


"""
Stereoisomers Image Table
"""
def table_stereo_results(chemspec_obj):

    logging.warning(str(chemspec_obj.stereoDict))

    if chemspec_obj.stereoDict:
        html = """
        <H3 class="out_1 collapsible" id="section10"><span></span>Stereoisomers</H3>
        <div class="out_">
        """
        html = html + tmplImg.render(Context(dict(data=chemspec_obj.stereoDict)))
        html = html + """
        </div>
        """
        return html
    else:
        return ""


"""
Tautomer Image Table
"""
def table_taut_results(chemspec_obj):

    if chemspec_obj.tautDict:
        html = """
        <H3 class="out_1 collapsible" id="section11"><span></span>Tautomerization</H3>
        <div class="out_">
        """
        html = html + tmplImg.render(Context(dict(data=chemspec_obj.tautDict)))
        html = html + """
        </div><br><br>
        """
        return html
    else:
        return ""


"""
Wraps molecule image result with a table
and populates said table with molecular details.

Inputs: property dict (e.g., pka, taut)
Outputs: data wrapped in table with image and name
"""
def wrap_molecule(propDict):

    image = propDict['image']
    formula = propDict['formula']
    iupac = propDict['iupac']
    mass = propDict['mass']
    smiles = propDict['smiles']

    infoDict = {
        "image": image,
        "formula": formula,
        "iupac": iupac,
        "mass": mass,
        "smiles": smiles
    }

    html = render_to_string('structure_wrapper.html', infoDict)

    return html 
