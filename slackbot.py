import os
import requests
import pytz
from simple_salesforce import Salesforce
import datetime

from dotenv import load_dotenv
load_dotenv()

if os.environ.get('SALESFORCE_URL') is not None:
    SALESFORCE_URL = os.environ.get('SALESFORCE_URL')
    FLOAT_API_KEY = os.environ.get('FLOAT_API_KEY')
    FLOAT_API_URL = os.environ.get('FLOAT_API_URL')
else:
    SALESFORCE_URL = 'SALESFORCE DOMAIN'


class FloatAPI:
    """
    api wraper for FLOAT.COM
    """
    def __init__(self):
        self.url = FLOAT_API_URL
        self.access_key = FLOAT_API_KEY

    def get_people(self):
        headers={
            'Authorization':'Bearer {}'.format(self.FLOAT_API_KEY),
            'User-Agent':'MedmetryPyFloat',
            'Content-Type':'application/json',
            'Accept':'application/json'
        }

        pplresp = requests.get(self.url+'/people',headers=headers)
        print(pplresp.body)



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
    .get_people()