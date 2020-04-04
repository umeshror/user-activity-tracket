import logging

from cerberus import Validator
from flask import Blueprint
from flask import jsonify, request

from service import db

from service.models import User, ActivityLog
from service.utils import add_activity_log, user_schema, log_schema, to_datetime, error_response

logger = logging.getLogger(__name__)
views_bp = Blueprint("views", __name__)


# todo: set headers content-type


@views_bp.route("/health")
def health():
    # check if connection to SQL is fine
    users = User.query.first()
    return jsonify({
        "status": "OK"
    })


@views_bp.route("/users", methods=["GET"])
def get_users():
    """
    Gives list of all users
    return: {
          "users": [
            {
              "created_at": datetime,
              "email": str,
              "id": uuid_str,
              "name": str,
              "updated_at": datetime
            }
          ]
        }
    """
    users = User.query
    data = {
        'users': [user.to_dict() for user in users]
    }
    return jsonify(data)


@views_bp.route("/users", methods=["POST"])
def new_user():
    """
    Create new user
    POST_Data: {
          "email": str,
          "name": str
        }
    """
    data = request.get_json() or {}
    # validate is all required fields are present or not
    v = Validator(user_schema)
    if not v.validate(data):
        return error_response(400, v.errors)

    # create user instance
    user = User()
    user.name = data['name']
    user.email = data['email']

    # save it to db
    db.session.add(user)
    db.session.commit()

    data = user.to_dict()
    # Add activity_log for user creation
    add_activity_log('create', user.id, data)

    response = jsonify(data)
    response.status_code = 201
    return response


@views_bp.route("/users/<user_id>", methods=["GET"])
def get_user(user_id):
    """
    Gives information of single user
    :return: {
              "created_at": datetime,
              "email": str,
              "id": uuid_str,
              "name": str,
              "updated_at": datetime
            }
    """

    user = User.query.get(user_id)
    if not user:
        return error_response(404, 'Given id does not exist')

    return jsonify(user.to_dict())


@views_bp.route("/users/<user_id>", methods=["PATCH"])
def update_user(user_id):
    """
    Edit information of single user
    PATCH_data : {
          "email": new_str,
          "name": new_str
        }
    """
    schema = {
        "email": {'type': 'string',
                  'regex': "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$"},
        "name": {'type': 'string',
                 "minlength": 2}
    }
    data = request.get_json() or {}

    v = Validator(schema)
    if not v.validate(data):
        return error_response(400, v.errors)

    user = User.query.get(user_id)
    if not user:
        return error_response(404, 'Given id does not exist')


    if data.get('name'):
        user.name = data['name']
    if data.get('email'):
        user.email = data['email']
    db.session.commit()
    data = user.to_dict()

    # Add activity_log for user update
    add_activity_log('update', user.id, data)
    return jsonify(data)


@views_bp.route("/users/<user_id>", methods=["DELETE"])
def delete_user(user_id):
    """
    Delete user details of provided user_id
    """
    user = User.query.get(user_id)
    if not user:
        return error_response(404, 'Given id does not exist')
    db.session.delete(user)
    db.session.commit()

    # Add activity_log for user delete
    add_activity_log('delete', user_id, user.to_dict())
    response = jsonify()
    response.status_code = 204
    return response


@views_bp.route("/logs", methods=["GET"])
def get_logs():
    """
    Gives all activity logs
    """
    logs = ActivityLog.query
    data = {
        'logs': [log.to_dict() for log in logs]
    }
    return jsonify(data)


@views_bp.route("/logs/user/<user_id>", methods=["GET"])
def get_logs_by_user(user_id):
    """
    Gives all activity logs of particular user
    """
    logs = ActivityLog.query.filter_by(user_id=user_id)
    data = {
        'logs': [log.to_dict() for log in logs]
    }
    return jsonify(data)


@views_bp.route("/logs/replay", methods=["POST"])
def replay_logs():
    """
    Provides the ability to bring an instance database to a known state[POST data]
    POST_Data: {
      "logs":[
        {...ActivityLog data...},
        {...ActivityLog data...}
      ]
    }
    """

    data = request.get_json() or {}
    if 'logs' not in data:
        return error_response(400, 'Logs key not present')
    logs = data['logs']
    # if logs are empty then wipe all the data
    if logs == []:
        User.query.delete()
        ActivityLog.query.delete()

        db.session.commit()
    else:
        # validate if data sent is in right format
        v = Validator(log_schema)
        invalid_logs = [v.errors for log in logs if not v.validate(log)]
        if invalid_logs:
            # if any data is invalid then throw 400
            return error_response(400, invalid_logs)

        for log in logs:

            user_data = log['attributes']

            user = User.query.get(user_data['id'])

            # create user
            if log['action'] == 'create':
                if user:
                    return error_response(400, 'User with ID: {} already exist'.format(user_data['id']))
                user = User()
                user.id = user_data['id']
                user = get_user_instance(user, user_data)
                db.session.add(user)
            # update user
            elif log['action'] == 'update':
                if not user:
                    return error_response(404, 'User with ID: {} does not exist'.format(user_data['id']))
                user = get_user_instance(user, user_data)
            elif log['action'] == 'delete':
                if not user:
                    return error_response(404, 'User with ID: {} does not exist'.format(user_data['id']))
                db.session.delete(user)

            al = ActivityLog.query.get(log['id'])
            if al:
                return error_response(400, 'ActivityLog with ID: {} already exist'.format(user_data['id']))
            else:
                # create activity log
                al = ActivityLog()
                db.session.add(activity_log_instance(al, log))

        db.session.commit()

    response = jsonify()
    response.status_code = 204
    return response


def get_user_instance(user, user_data):
    """
    Gives User instance with mapped user_data
    """
    user.email = user_data['email']
    user.name = user_data['name']
    user.created_at = to_datetime(user_data['created_at'])
    user.updated_at = to_datetime(user_data['updated_at'])
    return user


def activity_log_instance(al, log_data):
    """
    Gives ActivityLog instance with mapped log_data
    """
    al.created_at = to_datetime(log_data['created_at'])
    al.updated_at = to_datetime(log_data['updated_at'])
    al.attributes = log_data['attributes']
    al.user_id = log_data['user_id']
    al.action = log_data['action']
    al.id = log_data['id']
    return al
