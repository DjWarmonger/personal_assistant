import termcolor
import sqlite3

from emailStruct import EmailStruct

class EmailDatabase:
	def __init__(self, db_name='email_database.db'):
		self.conn = sqlite3.connect(db_name)
		self.cursor = self.conn.cursor()
		self.create_table()

	def create_table(self):
		self.cursor.execute('''
		CREATE TABLE IF NOT EXISTS emails
		(
			id TEXT PRIMARY KEY,
			thread_id TEXT,
			subject TEXT,
			sender TEXT,
			snippet TEXT,
			body TEXT
		)
		''')
		self.conn.commit()

	def insert_email(self, email: EmailStruct):
		self.cursor.execute('''
		INSERT OR REPLACE INTO emails (id, thread_id, subject, sender, snippet, body)
		VALUES (?, ?, ?, ?, ?, ?)
		''', (email.id, email.thread_id, email.subject, email.sender, email.snippet, email.body))
		self.conn.commit()
		print(termcolor.colored(f"Added new email", 'green'), email.id, email.subject)

	def _create_email_struct_from_row(self, row):
		return EmailStruct({
			'id': row[0],
			'threadId': row[1],
			'subject': row[2],
			'sender': row[3],
			'snippet': row[4],
			'body': row[5]
		})
	
	def get_all_email_ids(self):
		self.cursor.execute('SELECT id FROM emails')
		rows = self.cursor.fetchall()
		return [row[0] for row in rows]
	
	def get_all_thread_ids(self):
		self.cursor.execute('SELECT DISTINCT thread_id FROM emails')
		rows = self.cursor.fetchall()
		return [row[0] for row in rows]

	def get_email_by_id(self, email_id):
		self.cursor.execute('SELECT * FROM emails WHERE id = ?', (email_id,))
		row = self.cursor.fetchone()
		if row:
			return self._create_email_struct_from_row(row)
		return None
	
	def get_thread_emails(self, thread_id):
		self.cursor.execute('SELECT * FROM emails WHERE thread_id = ? ORDER BY id', (thread_id,))
		rows = self.cursor.fetchall()
		return [self._create_email_struct_from_row(row) for row in rows]

	def close(self):
		self.conn.close()
		
	def print_all_emails(self):
		self.cursor.execute('SELECT * FROM emails')
		rows = self.cursor.fetchall()
		for row in rows:
			email = self._create_email_struct_from_row(row)
			email.printEmail()
			print()  # Add a blank line between emails for better readability