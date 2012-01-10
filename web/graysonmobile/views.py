import os
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.csrf import csrf_exempt  
from django.conf import settings
from grayson.view.common import ViewUtil
from grayson.view.common import ViewController

logger = logging.getLogger (__name__)

def get_template_name (name):
    return '/'.join ([ 'graysonmobile/html', name ])

@csrf_protect
def home (request):
    context = {}
    return ViewUtil.get_response (get_template_name ('index.html'), request, {})

def about (request):
    return ViewUtil.get_response (get_template_name ('about.html'), request, {})
    
def get_flows (request):
    controller = ViewController ()
    flows = controller.findFlows (request)
    for flow in flows:
        flowId = flow ['flow']
        flowId = flowId.replace ('-', '_').replace ('.grayson_upk', '')
        flow ['flow'] = flowId
        
        flow ['runCount'] = len (flow ['runs'])

    return flows

def flows (request):
    context = {
        'flows' : get_flows (request)
        }
    return ViewUtil.get_response (get_template_name ('flows.html'), request, context)

def runs (request):
    flow = request.REQUEST ['flow']
    response = ViewUtil.get_text_response ('fail')
    if flow:
        flows = get_flows (request)
        for f in flows:
            logger.error ('argh %s', f)
            print 'argh %s' % f
            name = f ['flow']
            if flow == name:
                context = {
                    'flow'  : f
                    }
                response = ViewUtil.get_response (get_template_name ('runs.html'), request, context)
                break
    return response

def icon (request):
    path = os.path.join (settings.SITE_ROOT, 'graysonmobile', 'static', 'img', 'letterg.png')
    image_data = open (path, "rb").read ()
    return HttpResponse (image_data, mimetype="image/png")
