import os
import termcolor
from dotenv import load_dotenv

from langchain_community.agent_toolkits import GmailToolkit
from langchain_community.tools.gmail.search import GmailSearch
from langchain_community.tools.gmail.utils import get_gmail_credentials, build_resource_service

from emailStruct import EmailStruct
from emailDb import EmailDatabase

load_dotenv()

class Nodes:

	def __init__(self):
		self.login()
		self.gmail = GmailToolkit(api_resource=self.api_resource)
		self.email_db = EmailDatabase()
		self.checkedEmailsIds = self.email_db.get_all_email_ids()
		print(termcolor.colored(f"Known emails:", 'blue'), self.checkedEmailsIds)
		self.thread = self.email_db.get_all_thread_ids()
		print(termcolor.colored(f"Known threads:", 'blue'), self.thread)

	def login(self):
		# token.json will be created automatically after the first successful authentication
		credentials = get_gmail_credentials(token_file="token.json", client_secrets_file="credentials.json", scopes=["https://mail.google.com/"])
		self.api_resource = build_resource_service(credentials=credentials)

	def checkEmail(self, state):
		search = GmailSearch(api_resource=self.gmail.api_resource)

		emails = search('newer_than:1d')
		checked_emails = state['checkedEmailsIds'] if 'checkedEmailsIds' in state else []
		new_emails = []

		for email_data in emails:
			if (email_data['id'] not in checked_emails and
				email_data['threadId'] not in self.thread and
				os.environ['MY_EMAIL'] not in email_data['sender']
			):
				self.thread.append(email_data['threadId'])
				email = EmailStruct(email_data)
				new_emails.append(email.to_dict())
				self.email_db.insert_email(email)
		checked_emails.extend([email_data['id'] for email_data in emails])

		return {
			**state,
			"checkedEmailsIds": checked_emails,
			"newEmails": new_emails
		}

