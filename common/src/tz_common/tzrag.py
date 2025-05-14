import os
import json
from typing import Optional

from langfuse.decorators import observe, langfuse_context

from lightrag import LightRAG, QueryParam
from lightrag.llm import gpt_4o_mini_complete, gpt_4o_complete
from lightrag.utils import xml_to_json
from neo4j import GraphDatabase # TODO: Install neo4j

from tz_common.aitoolbox import AIToolbox
from tz_common import log

class TZRAG:
	
	session_id: str = None
	user_id: str = None

	def set_langfuse_context(self, toolbox: AIToolbox, session_id: str, user_id: str):
		self.toolbox = toolbox

		# TODO:one-liner to set session and user ids
		self.session_id = toolbox.session_id
		self.user_id = toolbox.user_id

	def __init__(self, working_dir: str, overwrite: bool = False):
		self.working_dir = working_dir
		if overwrite:
			self.clear()
		self.rag = self.create_lightrag()

		self.entities = set()
		self.entity_types = ["people", "organizations", "locations", "technologies", "events", "activities", "items", "skills"]

		self.facts = []

		# This name is fixed, and used by LightRAG library
		self.xml_path= os.path.join(self.working_dir, 'graph_chunk_entity_relation.graphml')


    # TODO: Use neo4j directly as backend?
	def create_lightrag(self, path: Optional[str] = None) -> LightRAG:
		# https://github.com/HKUDS/LightRAG

		WORKING_DIR = path if path is not None else self.working_dir

		if not os.path.exists(WORKING_DIR):
			os.makedirs(WORKING_DIR, exist_ok=True)

		rag = LightRAG(
			working_dir=WORKING_DIR,
			llm_model_func=gpt_4o_mini_complete,
			#llm_model_func=gpt_4o_complete,
			#graph_storage="Neo4JStorage",
			log_level="ERROR" # Disable internal debug logs
		)
		
		# TODO: Use local CUDA acceleration on PC

		return rag
	
	def set_entity_types(self, entity_types: list[str]):

		self.entity_types = entity_types
	
	@observe
	def create_custom_entries(self, input: str,
						   entity_types: list[str] = [],
						   exclusive_types: bool = True,
						   additional_context: str = "") -> str:
		
		if len(input) == 0:
			return {}
		if len(input) > 10000:
			log.error(f"Input is too long: {len(input)} characters", input)
			return {}

		# TODO; Custom details (time and date, address, strings)
		# TODO: Extra formatting (Polish or not?)
		# TODO: Generate relevant examples by other model?

		langfuse_context.update_current_trace(
			session_id=self.session_id,
			user_id=self.user_id
		)

		system_prompt = f"""
		`You are an expert in information extraction and knowledge graph construction. Your task is to read the following text and extract entities and relationships, then format them according to the lightrag framework specifications.

		**Instructions:**

		1. **Entity Extraction:**
		- Identify all significant entities mentioned in the text. Entities can be of the following types{" ONLY" if exclusive_types else ""}: {", ".join(entity_types)}.
		- For each entity, provide the following information:
			- `entity_name`: The name of the entity. Use full name if possible.
			- `entity_type`: The type of the entity (e.g. "Person", "Organization", "Location", "Event").
			- `description`: A concise but specific description or any relevant information about the entity extracted from the text. Avoid general categories, include specific names or identifiers. Include details such as time and date, if any.

		2. **Relationship Extraction:**
		- Identify meaningful relationships between the entities you've extracted.
		- For each relationship, provide the following information:
			- `src_id`: The `entity_name` of the source entity.
			- `tgt_id`: The `entity_name` of the target entity.
			- `description`: A brief description of the relationship extracted from the text.
			- `keywords`: Keywords that represent the relationship (e.g., "workplace", "current location", "detection", "transfer", "completed training").
			- `weight`: A numerical value representing the confidence or strength of the relationship (from 0.1 to 1.0).

		3. **Formatting:**
		- Present the extracted entities and relationships in a JSON-like format as shown in the example below.
		- Ensure the output matches the structure required by the lightrag framework.
		- Do not translate Polish text. Use the nominative form of entity names and keywords.

		**Example Output Format:**

		{{
			"entities": [
				{{
					"entity_name": "CompanyA",
					"entity_type": "Organization",
					"description": "A major technology company",
				}},
				{{
					"entity_name": "ProductX",
					"entity_type": "Item",
					"description": "A popular product developed by CompanyA",
				}}
			],
			"relationships": [
				{{
					"src_id": "CompanyA",
					"tgt_id": "ProductX",
					"description": "CompanyA develops ProductX",
					"keywords": "development, production",
					"weight": 1.0,
				}}
			]
		}}
		"""

		prompt = f"""Extract the following text into entities and relationships:
		<input>
		{input}
		</input>
		"""

		if additional_context:
			prompt += f"""\nHere is the list of already known entities:
			<additional context>
			{additional_context}
			</additional context>
			Use these known names to identify entities in the input text. Avoid altering or misspelling entity names in your output.
			"""

		response = self.toolbox.send_openai_request(prompt, system_prompt=system_prompt, json_format=True, max_tokens=2048)

		try:
			response = json.loads(response)
		except json.JSONDecodeError:
			log.error(f"Failed to parse response:", response)
			# Return empty response if parsing fails to avoid interrupting indexing
			response = {
				"entities": [],
				"relationships": []
			}

		return response
	

	@observe
	def correct_entity_names(self, input: str, entities: set[str]) -> str:

		system_prompt = """
		You are careful analyst. Your taks is to correct entity names in the input text to avoid misspellings, adding new names for entities or translating names that are already known. Use full names if possible. Use nominative form of entity names.

		<examples>
		* If "Tomasz Zieliński" is in the list of known entities, then "Tomasza" should be corrected to "Tomasz Zieliński". Also "Tom Zielinski" should be corrected to "Tomasz Zieliński".
		* If "Kraków" is in the list of known entities, then "Krakow" should be corrected to "Kraków".
		* If "Szkoła Podstawowa nr. 17" is in the list of known entities, then "Primary School" should be translated to "Szkoła Podstawowa nr. 17".
		</examples>

		<known entities>
		{entities}
		</known entities>
		"""

		prompt = f"""
		Correct the following text. Replace any entity name with the correct one from the list of known entities. If there is no entity with a similar name, leave it as is.

		<input>
		{input}
		</input>

		Avoid any extra changes or comments. The output should be formatted as json possible to parse.
		"""

		response = self.toolbox.send_openai_request(prompt, system_prompt=system_prompt, json_format=True, max_tokens=2048)

		try:
			response = json.loads(response)
		except json.JSONDecodeError:
			log.error(f"Failed to parse response:", response)
			# Return empty response if parsing fails to avoid interrupting indexing
			response = {
				"entities": [],
				"relationships": []
			}

		log.ai(f"Corrected entity names:", response)

		return response
	

	@observe(capture_input=False, capture_output=False)
	def populate_entities_from_file(self,
								 filename: str,
								 txt: str,
								 context: dict = {},
								 insert_facts: bool = True):
		
		# TODO: Context is now unused

		paragraphs = self.toolbox.split_paragraphs(txt)
		#log.debug(f"Splitted {filename} into {len(paragraphs)} paragraphs")

		for paragraph in paragraphs:
			# TODO: Process in parallel?
			entries = self.create_custom_entries(paragraph, additional_context=str(self.entities))

			if entries:
				entries = self.correct_entity_names(entries, self.entities)
			else:
				continue

			if "entities" in entries:
				for e in entries["entities"]:
					e["source_id"] = filename
					self.entities.add(e["entity_name"])

			if "relationships" in entries:	
				for r in entries["relationships"]:
					r["source_id"] = filename

			if ("entities" in entries and entries["entities"]) or ("relationships" in entries and entries["relationships"]):
				log.knowledge(f"Inserting entries for {filename}", str(entries))

				entries["chunk"] = [{"content": paragraph, "source_id": filename}]
				# Always store facts, even if they are not inserted into RAG
				self.facts.append(entries)
				if insert_facts:
					self.rag.insert_custom_kg(entries)

			if len(self.entities) > 0:
				log.knowledge(f"List of already known entities:", str(self.entities))

	@observe
	def query_rag(self, question) -> str:
		# TODO: Set Langfuse context
		
		if self.session_id is not None and self.user_id is not None:
			langfuse_context.update_current_trace(
				session_id=self.session_id,
			user_id=self.user_id
		)
		
		log.user(question)

		ret = self.rag.query(question, param=QueryParam(mode="local"))
		log.knowledge(f"Query result:", str(ret))

		return str(ret)
	
	@observe(capture_input=False, capture_output=False)
	def populate_from_entries(self, entries: list[dict] = []):

		if not entries:
			log.debug("No entries provided, using stored facts")
			entries = self.facts

		# TODO: Insert of overwrite facts? Or just ignore
		#self.facts.extend(entries)

		for e in entries:
			self.rag.insert_custom_kg(e)


	def save_facts(self, path: str = ""):

		if not path:
			path = os.path.join(self.working_dir, "facts.json")

		with open(path, 'w', encoding='utf-8') as f:
			json.dump(self.facts, f, ensure_ascii=False, indent=4)
		log.flow(f"Facts saved to: {path}")


	def load_facts(self, path: str = ""):

		if not path:
			path = os.path.join(self.working_dir, "facts.json")

		try:
			with open(path, 'r', encoding='utf-8') as f:
				self.facts = json.load(f)
			log.flow(f"Facts loaded from: {path}")
		except FileNotFoundError:
			log.error(f"File not found - {path}")


	def save_to_json(self, path: str = ""):

		if not path:
			path = os.path.join(self.working_dir, "graph_data.json")

		if not os.path.exists(self.xml_path):
			log.error(f"File not found - {self.xml_path}")
			return None

		json_data = xml_to_json(self.xml_path)
		if json_data:
			with open(path, 'w', encoding='utf-8') as f:
				json.dump(json_data, f, ensure_ascii=False, indent=2)
			log.flow(f"JSON file created: {path}")
			return json_data
		else:
			log.error("Failed to create JSON data")
			return None
	

	def dump_knowledge(self, path = "") -> dict:
		
		json_data = xml_to_json(self.xml_path)

		knowledge = {"nodes": [], "relationships": []}

		for node in json_data.get("nodes", []):
			knowledge["nodes"].append({"id": node.get("id"), "description": node.get("description")})

		for edge in json_data.get("edges", []):
			knowledge["relationships"].append({"source": edge.get("source"), "target": edge.get("target"), "description": edge.get("description")})

		# TODO: if path already exists, just load from it? Which has better performance?
		if path:
			with open(path, 'w', encoding='utf-8') as f:
				json.dump(knowledge, f, ensure_ascii=False, indent=2)
			log.flow(f"JSON file created: {path}")

		return knowledge
	
	def dump_knowledge_yaml(self, path: str = ""):

		knowledge = self.dump_knowledge()
		if not path:
			path = os.path.join(self.working_dir, "knowledge.yaml")

		import yaml
		yaml_str = yaml.dump(knowledge, allow_unicode=True, sort_keys=False, indent=2)
		with open(path, 'w', encoding='utf-8') as f:
			f.write(yaml_str)
		log.flow(f"YAML file created: {path}")

		return yaml_str


	def clear(self):

		# FIXME: Permission denied while LightRAG is loading files
		import shutil
		try:
			if os.path.exists(self.working_dir):
				shutil.rmtree(self.working_dir)
			os.makedirs(self.working_dir, exist_ok=True)
		except PermissionError as e:
			log.error(f"Permission denied when clearing directory {self.working_dir}: {e}")
		except OSError as e:
			log.error(f"Error clearing/creating directory {self.working_dir}: {e}")


	def process_in_batches(self, tx, query, data, batch_size):
		"""Process data in batches and execute the given query."""
		for i in range(0, len(data), batch_size):
			batch = data[i:i + batch_size]
			tx.run(query, {"nodes": batch} if "nodes" in query else {"edges": batch})

	
	def define_relation_types(self):
		# TODO: Define relation types with LLM
		pass


	def export_facts_to_neo4j(self,
								neo4j_uri: str,
								neo4j_username: str,
								neo4j_password: str):
		self.define_relation_types()

		# TODO: Export facts directly to Neo4j
		pass


	def export_to_neo4j(self,
						neo4j_uri: str,
						neo4j_username: str,
						neo4j_password: str):

		json_data = self.save_to_json()
		if json_data is None:
			return
		
		BATCH_SIZE_NODES = 500
		BATCH_SIZE_EDGES = 100

		# Load nodes and edges
		nodes = json_data.get('nodes', [])
		edges = json_data.get('edges', [])

		# Modified Neo4j queries
		delete_all_query = """
		MATCH (n)
		DETACH DELETE n
		"""

		create_nodes_query = """
		UNWIND $nodes AS node
		MERGE (e:Entity {id: node.id})
		SET e.entity_type = node.entity_type,
			e.description = node.description,
			e.source_id = node.source_id,
			e.displayName = node.id
		WITH e, node
		CALL apoc.create.addLabels(e, [node.entity_type]) YIELD node as result
		RETURN count(*)
		"""

		# TODO: Create some type for relations

		create_edges_query = """
		UNWIND $edges AS edge
		MATCH (source {id: edge.source})
		MATCH (target {id: edge.target})
		MERGE (source)-[r:RELATES_TO {
			weight: edge.weight,
			description: edge.description,
			keywords: edge.keywords,
			source_id: edge.source_id
		}]->(target)
		RETURN count(*)
		"""

		# Connect to Neo4j and execute queries
		try:
			driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
			with driver.session() as session:
				# Delete all existing nodes and relationships
				log.flow("Deleting existing data...")
				session.run(delete_all_query)

				# Create nodes
				log.flow("Creating nodes...")
				session.execute_write(lambda tx: self.process_in_batches(tx, create_nodes_query, nodes, BATCH_SIZE_NODES))
				
				# Create edges
				log.flow("Creating edges...")
				session.execute_write(lambda tx: self.process_in_batches(tx, create_edges_query, edges, BATCH_SIZE_EDGES))
				
				log.flow("Graph creation completed successfully!")
			
		except Exception as e:
			log.error(f"Exception: {e}")
		finally:
			driver.close()


	def save_entities(self, path: str = ""):
		if not path:
			path = os.path.join(self.working_dir, "entities.json")

		with open(path, 'w', encoding='utf-8') as f:
			json.dump(list(self.entities), f, ensure_ascii=False, indent=2)
			log.flow(f"JSON file created: {path}")


	def load_entities(self, path: str = ""):
		if not path:
			path = os.path.join(self.working_dir, "entities.json")

		with open(path, 'r', encoding='utf-8') as f:
			self.entities = set(json.load(f))
			log.flow(f"Entities loaded from: {path}")


	def clear_entities(self):

		self.entities = set()
