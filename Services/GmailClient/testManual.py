from checkEmail import Nodes
#from emailDb import EmailDatabase

nodes = Nodes() 

#checkEmail.login()

emails = nodes.checkEmail({})

#print(emails)
print(emails['checkedEmailsIds'])
print()
#print(emails['newEmails'])

for threadId in emails['checkedEmailsIds']:
	emails = nodes.email_db.get_thread_emails(threadId)
	print(f"Found {len(emails)} emails for threadId {threadId}")
	for email in emails:
		email.printEmail(printBody = False)
		print()

#nodes.email_db.print_all_emails()

"""
for email in emails['newEmails']:
	email = Email(email)
	email.printEmail(printBody = False)
	print()
"""