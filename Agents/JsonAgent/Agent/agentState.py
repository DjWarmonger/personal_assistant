from typing import Any, Dict
from enum import Enum

from pydantic import Field

from tz_common.langchain_wrappers import AgentState


JsonDocument = Dict[str, Any]


class JsonDocumentType(Enum):
	INITIAL = "initial"  # Initial JSON document that can be restored by clear command. Should never be modified by agent.
	CURRENT = "current"  # Current working JSON document
	FINAL = "final"      # Final JSON document to be saved


class JsonAgentState(AgentState):

	# This is typed dict, must not have any methods

	# Can be restored via tool
	initial_json_doc: JsonDocument = Field(default_factory=dict)

	# Current working json document
	json_doc: JsonDocument = Field(default_factory=dict)

	# This will be saved when agent finishes the work
	final_json_doc: JsonDocument = Field(default_factory=dict)

	# This will be returned to chat user
	user_response: str = Field(default="")
	
