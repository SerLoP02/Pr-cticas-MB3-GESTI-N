from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.adk.apps import App
from google.adk.plugins.context_filter_plugin import ContextFilterPlugin


from MB3_Agent.AgentTools import tools_prompts
from MB3_Agent.AgentTools.tools import ClientTools
from MB3_Agent.AgentTools.utils import my_filter


import logging
logging.basicConfig(level=logging.DEBUG)


client_id = "cliente_urbo"
client_tools = ClientTools(client_id)


tools=[
    client_tools.get_sql_metadata, 
    client_tools.ddbb_consultor, 
    client_tools.data_response, 
    client_tools.schema_explainer,
    client_tools.small_talker,
    client_tools.doc_retrieval
]

root_agent = LlmAgent(
    name = "MB3_GESTION",
    model = "gemini-3.1-flash-lite-preview",
    static_instruction = tools_prompts.SYSTEM_INSTRUCTIONS,
    tools = tools
)

app = App(
    name = "MB3_Agent",
    root_agent = root_agent,
    plugins = [ContextFilterPlugin(2, my_filter)]
)