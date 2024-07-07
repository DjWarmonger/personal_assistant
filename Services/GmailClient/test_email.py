import pytest
from emailDb import EmailDatabase
from checkEmail import EmailStruct

@pytest.fixture
def email_db():
	db = EmailDatabase(':memory:')
	yield db
	db.close()

@pytest.fixture
def sample_email():
	return EmailStruct({
		'id': 'test_id',
		'threadId': 'test_thread_id',
		'subject': 'Test Subject',
		'sender': 'test@example.com',
		'snippet': 'This is a test email',
		'body': 'This is the body of the test email'
	})

def test_create_table(email_db):
	# Table should be created in the fixture
	email_db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='emails'")
	assert email_db.cursor.fetchone() is not None

def test_insert_email(email_db, sample_email):
	email_db.insert_email(sample_email)
	
	email_db.cursor.execute("SELECT * FROM emails WHERE id = ?", (sample_email.id,))
	row = email_db.cursor.fetchone()
	
	assert row is not None
	assert row[0] == sample_email.id
	assert row[1] == sample_email.thread_id
	assert row[2] == sample_email.subject
	assert row[3] == sample_email.sender
	assert row[4] == sample_email.snippet
	assert row[5] == sample_email.body

def test_get_email_by_id(email_db, sample_email):
	email_db.insert_email(sample_email)
	
	retrieved_email = email_db.get_email_by_id(sample_email.id)
	
	assert retrieved_email is not None
	assert retrieved_email.id == sample_email.id
	assert retrieved_email.thread_id == sample_email.thread_id
	assert retrieved_email.subject == sample_email.subject
	assert retrieved_email.sender == sample_email.sender
	assert retrieved_email.snippet == sample_email.snippet
	assert retrieved_email.body == sample_email.body

def test_get_nonexistent_email(email_db):
	nonexistent_email = email_db.get_email_by_id('nonexistent_id')
	assert nonexistent_email is None
