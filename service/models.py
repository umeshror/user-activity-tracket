import uuid
from datetime import datetime
from pprint import pprint

from sqlalchemy_utils import ChoiceType, JSONType

from service import db


class ActivityLog(db.Model):
    TYPES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    ]
    id = db.Column(db.Text(length=36), default=lambda: str(uuid.uuid4()), primary_key=True)

    action = db.Column(ChoiceType(TYPES))

    user_id = db.Column(db.String(255), db.ForeignKey('user.id'))

    attributes = db.Column(JSONType)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    __tablename__ = 'ActivityLog'

    def __repr__(self):
        return 'User id {}'.format(self.user_id)

    def to_dict(self):
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action.code,
            "attributes": self.attributes,
            'created_at': self.created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'updated_at': self.updated_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        }
        return data


class User(db.Model):
    """
    User model used for storing name and email of the user
    """

    id = db.Column(db.Text(length=36), default=lambda: str(uuid.uuid4()), primary_key=True)

    email = db.Column(db.String(120), index=True)
    name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    __tablename__ = 'user'

    def __repr__(self):
        return 'User {}'.format(self.name)

    def to_dict(self):
        """

        """
        data = {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'created_at': self.created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'updated_at': self.updated_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        }
        return data
