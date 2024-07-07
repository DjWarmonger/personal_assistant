class EmailStruct:
	def __init__(self, email_data):
		self.id = email_data['id']
		self.thread_id = email_data['threadId']
		self.subject = email_data['subject']
		self.sender = email_data['sender']
		self.snippet = email_data['snippet']
		self.body = email_data['body']

	def to_dict(self):
		return {
			"id": self.id,
			"threadId": self.thread_id,
			"subject": self.subject,
			"sender": self.sender,
			"snippet": self.snippet,
			"body": self.body
		}
	
	def printEmail(self, printBody = True):
		print("\n".join(f"{key}: {value}" for key, value in self.to_dict().items() if key != "body"))
		if printBody:
			print(self.body)
