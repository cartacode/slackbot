import os
import pytz
from simple_salesforce import Salesforce
import datetime

from dotenv import load_dotenv
load_dotenv()

if os.environ.get('SALESFORCE_URL') is not None:
    SALESFORCE_URL = os.environ.get('SALESFORCE_URL')
else:
    SALESFORCE_URL = 'SALESFORCE DOMAIN'

if __name__ == "__main__":
    sf = Salesforce(instance='SALESFORCE_URL', session_id='00D30000001ICYF!AQ4AQAR_2a_pRTrbUPlMdrvogVcxK7_Tc0gMu3uz8Sz0T5wB_OCRpvpgunOa7OAt2oh0wVT2FbEvw9EJG7OGto8V5ETGcqQ2')

    end = datetime.datetime.now(pytz.UTC)
    records = sf.Contact.updated(end - datetime.timedelta(days=10), end)
    print records