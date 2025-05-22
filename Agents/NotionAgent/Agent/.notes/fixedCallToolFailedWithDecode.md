### Call tool failed

> Call tool failed: (AgentAction(id='KVvMY4Rq8SQisd45L9b5wDki', created_at=datetime.datetime(2025, 5, 17, 14, 42, 27, 172223, tzinfo=datetime.timezone.utc), task_id='', agent_id='', description="ChangeFavourties (KVvMY4Rq8SQisd45L9b5wDki) with args: {'urlOrUuid': '47', 'add': True, 'title': 'TODO'}", related_messages=[], related_documents=[], status=<ActionStatus.IN_PROGRESS: 1>, resolution=None), "'CustomUUID' object has no attribute 'decode'")

* Solution:

The issue is most likely that the CustomUUID passed to sqlite3 is the object itself, not its string representation. The strict validator in CustomUUID should have caught the invalid '47' input first. Since it didn't (or a different error was reported), it implies that either the CustomUUID validation logic in the running environment is different from what I've seen, or there's a subtle path where the CustomUUID object itself is passed to the database layer. The decode call is a strong hint that the receiving code thought it had a bytes object.