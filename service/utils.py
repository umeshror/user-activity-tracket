from datetime import datetime

from flask import jsonify
from werkzeug.http import HTTP_STATUS_CODES

from service import db
from service.models import ActivityLog


def add_activity_log(action, user_id, attributes):
    """
    Logs the Activity,
    Get called when User's create/update/delete operation happens
    """
    log = ActivityLog()
    log.action = action
    log.user_id = user_id
    log.attributes = attributes
    db.session.add(log)
    db.session.commit()
    return log


def to_datetime(strng):
    """
    retrun datetime instance from string
    """
    return datetime.strptime(strng, "%Y-%m-%dT%H:%M:%S.%fZ")


def error_response(status_code, message=None):
    """
    generic error message handler
    """
    error_message = None
    if status_code == 400:
        error_message = "BAD_REQUEST"
    elif status_code == 404:
        error_message = "NOT_FOUND"
    payload = {
        'code': error_message or HTTP_STATUS_CODES.get(status_code, 'Unknown error')
    }
    if message:
        payload['message'] = message
    response = jsonify(payload)
    response.status_code = status_code
    return response


user_schema = {
    "email": {'type': 'string',
              'regex': "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$",
              'required': True},
    "name": {'type': 'string',
             "minlength": 2,
             'required': True}
}

log_schema = {
    "id": {'type': 'string',
           'regex': "^[a-f0-9]{8}-[a-f0-9]{4}-[1345][a-f0-9]{3}-[a-f0-9]{4}-[a-f0-9]{12}$",
           'required': True},
    "user_id": {'type': 'string',
                'regex': "^[a-f0-9]{8}-[a-f0-9]{4}-[1345][a-f0-9]{3}-[a-f0-9]{4}-[a-f0-9]{12}$",
                'required': True},
    "action": {'type': 'string',
               'allowed': ['create', 'update', 'delete'],
               'required': True},
    "attributes": {
        'type': 'dict',
        'required': True,
        'schema': {
            "id": {'type': 'string',
                   'regex': "^[a-f0-9]{8}-[a-f0-9]{4}-[1345][a-f0-9]{3}-[a-f0-9]{4}-[a-f0-9]{12}$",
                   'required': True},
            "email": {'type': 'string',
                      "regex": "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$",
                      'required': True},
            "name": {'type': 'string',
                     "minlength": 2,
                     'required': True},
            "created_at": {'type': 'datetime',
                           'coerce': to_datetime,
                           'required': True},
            "updated_at": {'type': 'datetime',
                           'coerce': to_datetime,
                           'required': True}
        }
    },
    "created_at": {'type': 'datetime',
                   'coerce': to_datetime,
                   'required': True},
    "updated_at": {'type': 'datetime',
                   'coerce': to_datetime,
                   'required': True}
}
