import os
import requests
import datetime
import time
import re
import pytz
from simple_salesforce import Salesforce
from dotenv import load_dotenv

# load settings from .env file
load_dotenv()

if os.environ.get('SALESFORCE_URL') is not None:
    SALESFORCE_URL = os.environ.get('SALESFORCE_URL')
    FLOAT_API_KEY = os.environ.get('FLOAT_API_KEY')
else:
    SALESFORCE_URL = 'SALESFORCE DOMAIN'


class FloatAPI:
    """
    api wrapper for FLOAT.COM
    """
    def __init__(self):
        self.url = 'https://api.float.com/v3'
        self.access_key = FLOAT_API_KEY             # access key to float.com
        self.projects = []
        self.tasks = []
        self.people = []
        self.base_headers = {
            'Authorization':'Bearer {}'.format(self.access_key),
            'User-Agent':'MedmetryPyFloat',
            'Content-Type':'application/json',
            'Accept':'application/json'
        }

    def get_people(self):
        resp = requests.get(self.url+'/people', headers=self.base_headers)

        if resp.status_code == 200:
            self.projects = resp.json()
        else:
            print('error')

    def get_person_by_id(self, people_id=17145442):
        resp = requests.get('{}/people/{}'.format(self.url, people_id),
                            headers=self.base_headers)

        if resp.status_code < 400:
            return resp.json()
        else:
            print('The person doesn\'t exists')

    def get_projects(self):
        resp = requests.get(self.url+'/projects', headers=self.base_headers)

        if resp.status_code == 200:
            self.projects = resp.json()
        else:
            print('error')

    def get_project_by_id(self, project_id=17145442):
        resp = requests.get('{}/projects/{}'.format(self.url, project_id),
                            headers=self.base_headers)

        if resp.status_code < 400:
            return resp.json()
        else:
            print('The project doesn\'t exists')

    def get_tasks(self):
        resp = requests.get(self.url+'/tasks', headers=self.base_headers)

        if resp.status_code == 200:
            self.projects = resp.json()
        else:
            print('error')

    def get_task_by_id(self, task_id=17145442):
        resp = requests.get('{}/tasks/{}'.format(self.url, task_id),
                            headers=self.base_headers)

        if resp.status_code < 400:
            return resp.json()
        else:
            print('The tasl doesn\'t exists')
            


class ScheduleBot:
    """
    slackbot class
    """
    def __init__(self, session_id):
        self.sf = Salesforce(instance=SALESFORCE_URL, session_id=session_id)

    def test_salesforce(self):
        end = datetime.datetime.now(pytz.UTC)
        records = self.sf.Contact.updated(end - datetime.timedelta(days=10), end)
        print(records)


if __name__ == "__main__":
    bot = ScheduleBot('session_id')
    float_api = FloatAPI()
    float_api.get_people_by_id()