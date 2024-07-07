# TODO: Unify across projects

from pydantic import BaseModel
from datetime import datetime

class FeedItem(BaseModel):
	item_key: str
	title: str
	link: str
	summary: str | None = None
	timestamp: datetime | None = None

	class Config:
		from_attributes = True
