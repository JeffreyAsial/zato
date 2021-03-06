# -*- coding: utf-8 -*-

"""
Copyright (C) 2010 Dariusz Suchojad <dsuch at zato.io>

Licensed under LGPLv3, see LICENSE.txt for terms and conditions.
"""

# stdlib
import logging
from traceback import format_exc

# Django
from django.http import HttpResponse, HttpResponseServerError
from django.template.response import TemplateResponse

# anyjson
from anyjson import dumps

# Zato
from zato.admin.settings import engine_friendly_name
from zato.admin.web.views import change_password as _change_password
from zato.admin.web.forms import ChangePasswordForm
from zato.admin.web.forms.outgoing.sql import CreateForm, EditForm
from zato.admin.web.views import Delete as _Delete, method_allowed
from zato.common.odb.model import SQLConnectionPool

logger = logging.getLogger(__name__)

def _get_edit_create_message(params, prefix=''):
    """ Creates a base dictionary which can be used by both 'edit' and 'create' actions.
    """
    return {
        'id': params.get('id'),
        'cluster_id': params['cluster_id'],
        'name': params[prefix + 'name'],
        'is_active': bool(params.get(prefix + 'is_active')),
        'engine': params[prefix + 'engine'],
        'host': params[prefix + 'host'],
        'port': params[prefix + 'port'],
        'db_name': params[prefix + 'db_name'],
        'username': params[prefix + 'username'],
        'pool_size': params[prefix + 'pool_size'],
        'extra': params.get(prefix + 'extra'),
    }

def _edit_create_response(verb, id, name, engine, cluster_id):
    """ A common function for producing return data for create and edit actions.
    """
    return_data = {'id': id,
                   'message': 'Successfully {0} the outgoing SQL connection [{1}]'.format(verb, name.encode('utf-8')),
                   'engine_text': engine_friendly_name[engine],
                   'cluster_id': cluster_id,
                }

    return HttpResponse(dumps(return_data), mimetype='application/javascript')

@method_allowed('GET')
def index(req):
    """ Lists all the SQL connections.
    """
    items = []
    create_form = CreateForm()
    edit_form = EditForm(prefix='edit')
    change_password_form = ChangePasswordForm()

    if req.zato.cluster_id and req.method == 'GET':
        for item in req.zato.client.invoke('zato.outgoing.sql.get-list', {'cluster_id': req.zato.cluster_id}):

            _item = SQLConnectionPool()
            
            for name in('id', 'name', 'is_active', 'engine', 'host', 'port', 'db_name', 'username', 'pool_size'):
                value = getattr(item, name)
                setattr(_item, name, value)
            
            _item.extra = item.extra or ''
            _item.engine_text = engine_friendly_name[_item.engine]
            items.append(_item)

    return_data = {'zato_clusters':req.zato.clusters,
        'cluster_id':req.zato.cluster_id,
        'choose_cluster_form':req.zato.choose_cluster_form,
        'items':items,
        'create_form':create_form,
        'edit_form':edit_form,
        'change_password_form': change_password_form
        }

    return TemplateResponse(req, 'zato/outgoing/sql.html', return_data)

@method_allowed('POST')
def create(req):
    """ Creates a new SQL connection.
    """
    try:
        request = _get_edit_create_message(req.POST)
        engine = request['engine']
        response = req.zato.client.invoke('zato.outgoing.sql.create', request)

        return _edit_create_response('created', response.data.id, req.POST['name'], engine, req.zato.cluster.id)

    except Exception, e:
        msg = 'Could not create an outgoing SQL connection, e:[{e}]'.format(e=format_exc(e))
        logger.error(msg)
        return HttpResponseServerError(msg)


@method_allowed('POST')
def edit(req):
    """ Updates an SQL connection.
    """
    try:
        request = _get_edit_create_message(req.POST, 'edit-')
        engine = request['engine']
        req.zato.client.invoke('zato.outgoing.sql.edit', request)

        return _edit_create_response('updated', req.POST['id'], req.POST['edit-name'], engine, req.zato.cluster.id)

    except Exception, e:
        msg = 'Could not update the outgoing SQL connection, e:[{e}]'.format(e=format_exc(e))
        logger.error(msg)
        return HttpResponseServerError(msg)

class Delete(_Delete):
    url_name = 'out-sql-delete'
    error_message = 'Could not delete the SQL connection'
    service_name = 'zato.outgoing.sql.delete'

@method_allowed('POST')
def ping(req, cluster_id, id):
    """ Pings a database and returns the time it took, in milliseconds.
    """
    try:
        response = req.zato.client.invoke('zato.outgoing.sql.ping', {'id':id})
        
        if response.ok:
            return TemplateResponse(req, 'zato/outgoing/sql-ping-ok.html', 
                {'response_time':'%.3f' % float(response.data.response_time)})
        else:
            return HttpResponseServerError(response.details)
    except Exception, e:
        msg = 'Could not ping the outgoing SQL connection, e:[{}]'.format(format_exc(e))
        logger.error(msg)
        return HttpResponseServerError(msg)

@method_allowed('POST')
def change_password(req):
    return _change_password(req, 'zato.outgoing.sql.change-password')
