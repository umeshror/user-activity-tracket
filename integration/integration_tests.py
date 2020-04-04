import unittest
import uuid
from os.path import join
from uuid import UUID

import arrow
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


class Base(object):
    API_HOST = "http://0.0.0.0:5000"
    LOGS_PATH = "logs"
    USERS_PATH = "users"
    BAD_REQUEST = "BAD_REQUEST"
    NOT_FOUND = "NOT_FOUND"

    def make_requests_retry_session(
            self,
            retries=3,
            backoff_factor=0.3,
            status_forcelist=(500, 502, 504),
            session=None,
    ):
        session = session or requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def attempt_db_wipe(self):
        self.session.post(
            join(self.API_HOST, self.LOGS_PATH, "replay"),
            json={"logs": []}
        )

    def attempt_user_create(self, email=None, name=None):
        user_res = self.session.post(
            join(self.API_HOST, self.USERS_PATH),
            json={
                "email": "foo@bar.com" if email is None else email,
                "name": "foo bar" if name is None else name
            }
        )

        if user_res.status_code == 201:
            return user_res.json()

    def setUp(self):
        self.session = self.make_requests_retry_session()
        self.attempt_db_wipe()


class UserIntegrationTests(Base, unittest.TestCase):

    def test_get_users_one(self):
        user_json = self.attempt_user_create()
        self.assertIsNot(user_json, None)

        users = self.session.get(
            join(self.API_HOST, self.USERS_PATH)
        ).json()

        self.assertEqual(
            users,
            {
                "users": [user_json]
            }
        )

    def test_create_new_user(self):
        user_res = self.session.post(
            join(self.API_HOST, self.USERS_PATH),
            json={
                "email": "foo@bar.com",
                "name": "Name",
            }
        )

        self.assertEqual(
            user_res.status_code,
            201
        )

        user_json = user_res.json()
        self.assertEqual(
            user_json["name"],
            "Name",
        )
        self.assertEqual(
            user_json["email"],
            "foo@bar.com",
        )

        # this should not fail
        UUID(user_json["id"])

    def test_create_user_with_invalid_data(self):
        user_res = self.session.post(
            join(self.API_HOST, self.USERS_PATH),
            json={
                "email": "foo@bar.com",
                "name": "N",
            }
        )

        expected_output = {
            "code": "BAD_REQUEST",
            "message": {
                "name": [
                    "min length is 2"
                ]
            }
        }

        self.assertEqual(
            user_res.status_code,
            400
        )
        self.assertEqual(
            user_res.json(),
            expected_output
        )

    def test_update_user(self):
        user = self.attempt_user_create()
        patch_res = self.session.patch(
            join(self.API_HOST, self.USERS_PATH, user["id"]),
            json={
                "name": "new name",
                "email": "new@email.com"
            }
        )

        self.assertEqual(
            patch_res.status_code,
            200
        )

        user_json = patch_res.json()
        self.assertEqual(
            user["id"],
            user_json["id"]
        )
        self.assertEqual(
            user_json["name"],
            "new name"
        )
        self.assertEqual(
            user_json["email"],
            "new@email.com"
        )

    def test_update_user_with_invalid_id(self):
        user = self.attempt_user_create()

        # with wrong ID
        patch_res = self.session.patch(
            join(self.API_HOST, self.USERS_PATH, str(uuid.uuid4())),
            json={
                "name": "new name",
                "email": "new@email.com"
            }
        )

        self.assertEqual(
            patch_res.status_code,
            404
        )
        expected_output = {
            "code": "NOT_FOUND",
            "message": "Given id does not exist"
        }

        self.assertEqual(
            patch_res.json(),
            expected_output
        )

    def test_update_user_with_invalid_email(self):
        user = self.attempt_user_create()

        # with wrong ID
        patch_res = self.session.patch(
            join(self.API_HOST, self.USERS_PATH, str(uuid.uuid4())),
            json={
                "name": "new name",
                "email": "newemail.com"
            }
        )

        self.assertEqual(
            patch_res.status_code,
            400
        )

    def test_delete_user(self):
        user = self.attempt_user_create()
        delete_res = self.session.delete(
            join(self.API_HOST, self.USERS_PATH, user["id"]),
        )

        self.assertEqual(
            delete_res.status_code,
            204
        )

    def test_delete_user_with_invalid_id(self):
        user = self.attempt_user_create()
        delete_res = self.session.delete(
            join(self.API_HOST, self.USERS_PATH, str(uuid.uuid4())),
        )

        self.assertEqual(
            delete_res.status_code,
            404
        )


class LogIntegrationTests(Base, unittest.TestCase):

    def test_get_logs_empty(self):
        logs = self.session.get(
            join(self.API_HOST, self.LOGS_PATH)
        ).json()

        self.assertEqual(
            logs,
            {
                "logs": []
            }
        )

    def test_get_logs_for_user(self):
        # log #1 for create user
        user = self.attempt_user_create(name="one")
        # log #2 for update user
        user_updated = self.session.patch(
            join(self.API_HOST, self.USERS_PATH, user["id"]),
            json={
                "name": "one_new",
            }
        ).json()

        logs = self.session.get(
            join(self.API_HOST, self.LOGS_PATH, "user", user["id"])
        ).json()["logs"]

        self.assertEqual(len(logs), 2)
        create, update = sorted(
            logs, key=lambda log: arrow.get(log["created_at"])
        )

        self.assertEqual(
            create["user_id"],
            user["id"]
        )
        self.assertEqual(
            create["action"],
            "create"
        )
        self.assertEqual(
            create["attributes"],
            user,
        )

        self.assertEqual(
            update["user_id"],
            user["id"]
        )
        self.assertEqual(
            update["action"],
            "update"
        )
        self.assertEqual(
            update["attributes"],
            user_updated,
        )

    def test_post_log_replay_wipe(self):
        # create 2 users
        user_one = self.attempt_user_create(name="one")
        user_two = self.attempt_user_create(name="two")

        # edit name of 'first' user
        self.session.patch(
            join(self.API_HOST, self.USERS_PATH, user_one["id"]),
            json={
                "name": "one_new",
            }
        ).json()

        # delete user 'two'
        self.session.delete(
            join(self.API_HOST, self.USERS_PATH, user_two["id"]),
        )

        # get logs as there were 4 operations 4 logs are expected
        logs = self.session.get(
            join(self.API_HOST, self.LOGS_PATH)
        ).json()["logs"]

        self.assertEqual(
            len(logs),
            4
        )

        # now send empty logs to replay which will wipe User data
        replay = self.session.post(
            join(self.API_HOST, self.LOGS_PATH, "replay"),
            json={"logs": []}
        )

        self.assertEqual(
            replay.status_code,
            204
        )

        logs = self.session.get(
            join(self.API_HOST, self.LOGS_PATH)
        ).json()

        self.assertEqual(
            logs,
            {
                "logs": []
            }
        )

    def test_post_log_replay_wipe_with_sequence(self):
        # create user 1 : log #1
        user_one = self.attempt_user_create(name="one")

        # edit this user : log #2
        self.session.patch(
            join(self.API_HOST, self.USERS_PATH, user_one["id"]),
            json={
                "name": "one_new",
            }
        ).json()

        # create user 2 : log #3
        user_two = self.attempt_user_create(name="two")

        # edit this user : log #4
        self.session.patch(
            join(self.API_HOST, self.USERS_PATH, user_two["id"]),
            json={
                "name": "two_new",
            }
        ).json()

        # delete user 'two' log #5
        self.session.delete(
            join(self.API_HOST, self.USERS_PATH, user_two["id"]),
        )

        # create user 3 : log #6
        user_two = self.attempt_user_create(name="three")
        """
        At this stage we have 
        6 Activity logs in db
        2 Users with name 'one' and 'three'
        """

        # get logs as there were 6 operations 6 logs are expected
        logs = self.session.get(
            join(self.API_HOST, self.LOGS_PATH)
        ).json()["logs"]

        self.assertEqual(
            len(logs),
            6
        )

        # now empty the DB to send all logs created above to replay the same sequence
        replay = self.session.post(
            join(self.API_HOST, self.LOGS_PATH, "replay"),
            json={"logs": []}
        )

        # now send all above logs to replay
        # we expect here 2 users to be created and 6 activity logs to be created
        replay = self.session.post(
            join(self.API_HOST, self.LOGS_PATH, "replay"),
            json={"logs": logs}
        )

        self.assertEqual(
            replay.status_code,
            204
        )

        # 6 activity logs should have been created
        logs = self.session.get(
            join(self.API_HOST, self.LOGS_PATH)
        ).json()["logs"]
        self.assertEqual(
            len(logs),
            6
        )

        # 2 users should have been created
        users = self.session.get(
            join(self.API_HOST, self.USERS_PATH)
        ).json()['users']
        self.assertEqual(
            len(users),
            2
        )


if __name__ == "__main__":
    unittest.main()
