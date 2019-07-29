import os
import requests
import datetime
import time
import re
import pytz
from simple_salesforce import Salesforce
from slackclient import SlackClient
from dotenv import load_dotenv

import pdb

# load settings from .env file
load_dotenv()

# constants
if os.environ.get("SALESFORCE_URL") is not None:
    SALESFORCE_URL = os.environ.get("SALESFORCE_URL")
    FLOAT_API_KEY = os.environ.get("FLOAT_API_KEY")
else:
    SALESFORCE_URL = "SALESFORCE DOMAIN"

RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
EXAMPLE_COMMAND = "sync"
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"


class FloatAPI:
    """
        api wrapper for FLOAT.COM
    """
    def __init__(self):
        self.url = "https://api.float.com/v3"
        self.access_key = FLOAT_API_KEY             # access key to float.com
        self.projects = []
        self.tasks = []
        self.people = []
        self.base_headers = {
            "Authorization":"Bearer {}".format(self.access_key),
            "User-Agent":"MedmetryPyFloat",
            "Content-Type":"application/json",
            "Accept":"application/json"
        }

    def get_people(self):
        resp = requests.get(self.url+"/people", headers=self.base_headers)

        if resp.status_code == 200:
            self.projects = resp.json()
        else:
            return None

    def get_person_by_id(self, people_id=17145442):
        resp = requests.get("{}/people/{}".format(self.url, people_id),
                            headers=self.base_headers)

        if resp.status_code < 400:
            return resp.json()
        else:
            return None

    def get_projects(self):
        resp = requests.get(self.url+"/projects", headers=self.base_headers)

        if resp.status_code == 200:
            self.projects = resp.json()
            return self.projects
        else:
            return None

    def get_project_by_id(self, project_id=17145442):
        resp = requests.get("{}/projects/{}".format(self.url, project_id),
                            headers=self.base_headers)

        if resp.status_code < 400:
            return resp.json()
        else:
            return None

    def get_tasks(self):
        resp = requests.get(self.url+"/tasks", headers=self.base_headers)

        if resp.status_code == 200:
            self.projects = resp.json()
            return self.tasks
        else:
            return None

    def get_task_by_id(self, task_id=17145442):
        resp = requests.get("{}/tasks/{}".format(self.url, task_id),
                            headers=self.base_headers)

        if resp.status_code < 400:
            return resp.json()
        else:
            return None
            


class ScheduleBot:
    """
        slackbot class
    """
    def __init__(self):
        # instantiate Salesforce instance
        self.sf = None
        self.project_table_name = 'pse__Proj__c'

        # instantiate Slack client
        self.slack_client = SlackClient(os.environ.get("SLACK_BOT_TOKEN"))
        # bot's user ID in Slack: value is assigned after the bot starts up
        self.slack_client_id = None

    def create_salesforce_instance(self, session_id):
        self.sf = Salesforce(instance=SALESFORCE_URL, session_id=session_id)

    def set_project_table_name(self):
        sobjects = self.sf.query_more("/services/data/v37.0/sobjects/", True)
        for sobject in sobjects["sobjects"]:
            if sobject["labelPlural"] == "Projects":
                self.project_table_name = sobject.name


    def parse_bot_commands(self, slack_events):
        """
            Parses a list of events coming from the Slack RTM API to find bot commands.
            If a bot command is found, this function returns a tuple of command and channel.
            If its not found, then this function returns None, None.
        """
        for event in slack_events:
            if event["type"] == "message" and not "subtype" in event:
                user_id, message = self.parse_direct_mention(event["text"])
                if user_id == self.slack_client_id:
                    return message, event["channel"]
        return None, None

    def parse_direct_mention(self, message_text):
        """
            Finds a direct mention (a mention that is at the beginning) in message text
            and returns the user ID which was mentioned. If there is no direct mention, returns None
        """
        matches = re.search(MENTION_REGEX, message_text)
        # the first group contains the username, the second group contains the remaining message
        return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

    def handle_command(self, command, channel):
        """
            Executes bot command if the command is known
        """
        # Default response is help text for the user
        default_response = "Not sure what you mean. Try *{}*.".format(EXAMPLE_COMMAND)

        # Finds and executes the given command, filling in response
        response = None

        # This is where you start to implement more commands!
        if command.startswith(EXAMPLE_COMMAND):
            float_api = FloatAPI()
            user = float_api.get_person_by_id()
            response = "User doesn't exists"
            if user:
                response = "User name is {}".format(user["name"])


        # Sends the response back to the channel
        self.slack_client.api_call(
            "chat.postMessage",
            channel=channel,
            text=response or default_response
        )

    def run(self):
        if self.slack_client.rtm_connect(with_team_state=False):
            print("Starter Bot connected and running!")
            # Read bot's user ID by calling Web API method `auth.test`
            self.slack_client_id = self.slack_client.api_call("auth.test")["user_id"]
            while True:
                command, channel = self.parse_bot_commands(self.slack_client.rtm_read())
                if command:
                    self.handle_command(command, channel)
                time.sleep(RTM_READ_DELAY)
        else:
            print("Connection failed. Exception traceback printed above.")

    def test(self):
        sobject = self.sf.query_more("/services/data/v37.0/sobjects/pse__Proj__c", True)
        projects = sobject["recentItems"]

        for project in projects:
            if "Southern Indiana Pediatrics" in project["Name"]:
                project_id = project["attributes"]["url"].split("/")[-1]
                milestone_id = self.get_milestone_id(project_id)
                if milestone_id is None:
                    print('milestone no')

                tasks = self.get_task_by_milestone_id(project_id, milestone_id)
                for task in tasks:
                    print(task)

    def get_milestone_id(self, project_id, milestone_name='Implementation and Training'):
        query = "select Id, Name from pse__Milestone__c \
                where (pse__Project__c='{}' and Name='{}')".format(project_id, milestone_name)
        sobject = self.sf.query(query)

        if sobject["totalSize"] == 0:
            return None

        return sobject["records"][0]['Id']

    def get_task_by_milestone_id(self, project_id, milestone_id):
        query = "select Id, pse__Project__c from pse__Project_Task__c \
                where (pse__Project__c='{}' and pse__Milestone__c='{}')".format(project_id, milestone_id)

        sobject = self.sf.query(query)
        print(query)

        if sobject["totalSize"] == 0:
            return []

        return sobject["records"]         

if __name__ == "__main__":
    session_id="00D30000001ICYF!AQ4AQI6BUgKPwydfcnrNrilIvdC7ZuZnZSFKiqorug0Odatmeqlnnv0.VtU1C09YdXxvSjJ1dQB01UoAVtF_VcpVdbJUX2Sl"
    bot = ScheduleBot()
    bot.create_salesforce_instance(session_id)
    bot.test()

    # bot = ScheduleBot()
    # bot.run()
    
