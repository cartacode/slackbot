import os
import requests
from datetime import datetime
import time
import re
import pytz
from simple_salesforce import Salesforce, SFType
from slackclient import SlackClient
from dotenv import load_dotenv
import pytz
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
            self.people = resp.json()
            return resp.json()
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
        headers = self.base_headers
        headers["X-Pagination-Current-Page"] = '2'
        resp = requests.get(self.url+"/projects?per-page=200", headers=headers)

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
            self.tasks = resp.json()
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

    def get_tasks_by_params(self, params):
        """
            Get tasks by parameters
            /tasks/?project_id=xxxxxx
        """
        resp = requests.get("{}/tasks?{}".format(self.url, params),headers=self.base_headers)

        if resp.status_code < 400:
            return resp.json()
        else:
            return []

    def test(self):
        float_tasks = []

        projects = self.get_projects()
        for project in projects:
            if 'Southern Indiana' in project["name"]:
                float_tasks = self.get_tasks_by_params('project_id={}'.format(project["project_id"]))

        return float_tasks


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
        # variable to count updated tasks
        self.number_of_success = 0

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

        if not command.startswith(EXAMPLE_COMMAND):
            self.slack_client.api_call(
                "chat.postMessage",
                channel=channel,
                text=default_response
            )
        # This is where you start to implement more commands!
        if command.startswith(EXAMPLE_COMMAND):
            eastern = pytz.timezone('US/Eastern')
            print(' start command : ', channel)
            self.slack_client.api_call(
                "chat.postMessage",
                channel=channel,
                text='wait for a moment, please'
            )

            session_id = command.replace(EXAMPLE_COMMAND, '').strip()
            self.create_salesforce_instance(session_id)

            is_session_valid = True
            try:
                self.sf.query_more("/services/data/v37.0/sobjects/", True)
            except:
                is_session_valid = False

            if is_session_valid:
                try:
                    sf_tasks = []       
                    sf_project_task = SFType('pse__Project_Task__c', session_id, SALESFORCE_URL)
                    float_api = FloatAPI()

                    projects = float_api.get_projects()
                    for project in projects:
                        m = re.search(r'(?<=-)\d+', project["name"])
                        if m is not None:
                            print(project["name"])
                            sf_project_id = m.group(0)
                            # float_tasks = float_api.test()
                            float_tasks = float_api.get_tasks_by_params('project_id={}'.format(project["project_id"]))

                            if len(float_tasks) > 0:
                                tags = float_api.get_project_by_id(float_tasks[0]["project_id"])["tags"]
                                for tag in tags:
                                    if 'PR-' in tag:
                                        sf_tasks = bot.test(sf_project_id)

                                for float_task in float_tasks:
                                    fl_user = float_api.get_person_by_id(float_task["people_id"])
                                    for sf_task in sf_tasks:
                                        pdb.set_trace()
                                        # if float_task["name"] == 'Go Live' and  sf_task["Name"] == 'Onsite Go Live':
                                        if float_task["name"] == sf_task["Name"]:
                                            start_datetime = datetime.strptime(float_task['start_date'], '%Y-%m-%d')
                                            end_datetime = datetime.strptime(float_task['end_date'], '%Y-%m-%d')

                                            start_datetime_obj = eastern.localize(start_datetime).strftime("%Y-%m-%dT%H:%M:%S")
                                            end_datetime_obj = eastern.localize(end_datetime).strftime("%Y-%m-%dT%H:%M:%S")

                                            msg = ''
                                            if sf_task['pse__Assigned_Resources__c'] != fl_user["name"]:
                                                params["pse__Assigned_Resources__c"] = fl_user["name"]
                                                params["pse__Assigned_Resources_Long__c"] = fl_user["name"]
                                                msg = 'assigned resources '

                                            if sf_task['pse__Start_Date_Time__c'] != start_datetime_obj or sf_task['pse__End_Date_Time__c'] != end_datetime_obj:
                                                params['pse__Start_Date_Time__c'] = start_datetime_obj
                                                params['pse__End_Date_Time__c'] = end_datetime_obj
                                                msg = 'start & end time '

                                            if len(params.keys()) > 0:
                                                result = sf_project_task.update(sf_task["Id"], params, False)

                                                task_status_response = ''
                                                if result < 400:
                                                    self.number_of_success = self.number_of_success + 1
                                                    task_status_response = "Updated {}on TASK | project {}".format(msg, float_task["name"])
                                                    self.slack_client.api_call(
                                                        "chat.postMessage",
                                                        channel=channel,
                                                        text=task_status_response
                                                    )

                        else:
                            print("***********: ", project["name"])

                    if self.number_of_success == 0:
                        response = "Couldn't find tasks in salesforce"

                except Exception as e:
                    response = e.message
            else:
                response = 'Session is incorrect or expired!'

            # Sends the response back to the channel
            self.slack_client.api_call(
                "chat.postMessage",
                channel=channel,
                text=response or 'Finished!'
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

    def test(self, project_id):
        sobject = self.sf.query_more("/services/data/v38.0/sobjects/pse__Proj__c", True)
        projects = sobject["recentItems"]
        tasks = []

        milestone_obj = self.get_milestone_id(project_id)
        if milestone_obj['milestone_id'] is None:
            print('milestone no')

        sf_tasks = self.get_task_by_milestone_and_product(
            milestone_obj['project_id'],
            milestone_obj['milestone_id']
        )

        for task in sf_tasks:
            formatted_task = self.get_detail_task(task["attributes"]["url"])
            tasks.append(formatted_task)
        
        return tasks
    
    def get_detail_task(self, task_url):
        sobject = self.sf.query_more(task_url, True)
        return sobject


    def get_milestone_id(self, project_id, milestone_name='Implementation and Training'):
        query = "select Id, Name from pse__Proj__c where pse__Project_ID__c='{}'".format(project_id)

        sobject = self.sf.query(query)

        if sobject["totalSize"] == 0:
            return None

        global_project_id = sobject["records"][0]['Id']

        query = "select Id, Name from pse__Milestone__c \
                where pse__Project__c='{}' and Name='{}'".format(global_project_id, milestone_name)
        
        sobject = self.sf.query(query)
        if sobject["totalSize"] == 0:
            return None

        return {
            'milestone_id': sobject["records"][0]['Id'],
            'project_id': global_project_id
        }


    def get_task_by_milestone_and_product(self, project_id, milestone_id):
        query = "select Id, pse__Project__c from pse__Project_Task__c \
                where (pse__Project__c='{}' and pse__Milestone__c='{}')".format(project_id, milestone_id)

        sobject = self.sf.query(query)
        if sobject["totalSize"] == 0:
            return []

        return sobject["records"]

    def format_time(self, time_val):
        if time_val is None:
            return time_val
        return time_val.replace(' ', 'T')


if __name__ == "__main__":
    session_id="00D30000001ICYF!AQ4AQFD5sQAO_wr5B9jE.QwTQDufPwUjRdoagJLS64hgZZYi3waUnFhn1CP3L3D63EYtyB4ft0dWyYLIi6Grgn2kBG1F9QCo"
    bot = ScheduleBot()
    bot.run()

    
