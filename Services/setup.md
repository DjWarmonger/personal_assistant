`conda create --name services python=3.10`

`conda activate services`

# Add project root to PYTHONPATH to enable common package import
`set PYTHONPATH=%PYTHONPATH%;F:\Programowanie\PersonalAssistant`

# Common libraries
`pip install ipykernel python-dotenv termcolor flask waitress requests pytest pydantic`

# Basic Google API
`pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib`

# Langchain for Gmail utils
`pip install -U openai langchain langgraph langchain_openai langchain-community`

# RSS
`pip install feedparser`


