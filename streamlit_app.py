import streamlit as st
import trulens.dashboard.streamlit as trulens_st
from trulens.core import TruSession
from base import rag, filtered_rag, tru_rag, filtered_tru_rag, engine

MODELS = [
    "mistral-large2",
    "snowflake-arctic",
    "llama3-70b",
    "llama3-8b",
]

def init_messages():
    """
    Initialize chat history.
    """
    if st.session_state.clear_conversation or "messages" not in st.session_state:
        st.session_state.messages = []
    
    if not st.session_state.messages:
        st.session_state.messages.append({"role": "assistant", "content": "Ask me anything about Cloud Security Alerts!"})

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def init_service_metadata():
    """
    Initialize the session state for cortex search service metadata. Query the available
    cortex search services from the Snowflake session and store their names and search
    columns in the session state.
    """
    if "service_metadata" not in st.session_state:
        services = st.session.sql("SHOW CORTEX SEARCH SERVICES;").collect()
        service_metadata = []
        if services:
            for s in services:
                svc_name = s["name"]
                svc_search_col = st.session.sql(
                    f"DESC CORTEX SEARCH SERVICE {svc_name};"
                ).collect()[0]["search_column"]
                service_metadata.append(
                    {"name": svc_name, "search_column": svc_search_col}
                )

        st.session_state.service_metadata = service_metadata

def init_config_options():
    """
    Initialize the configuration options in the Streamlit sidebar. Allow the user to select
    a cortex search service, clear the conversation, toggle debug mode, and toggle the use of
    chat history. Also provide advanced options to select a model, the number of context chunks,
    and the number of chat messages to use in the chat history.
    """
    if "service_metadata" not in st.session_state:
        st.warning("Service metadata is not initialized. Initializing now...")
        init_service_metadata()
    
    st.sidebar.selectbox(
        "Select cortex search service:",
        [s["name"] for s in st.session_state.service_metadata],
        key="selected_cortex_search_service",
    )

    st.sidebar.button("Clear conversation", key="clear_conversation")
    st.sidebar.toggle("Debug", key="debug", value=False)
    st.sidebar.toggle("Use chat history", key="use_chat_history", value=True)

    with st.sidebar.expander("Advanced options"):
        st.selectbox("Select model:", MODELS, key="model_name")
        st.number_input(
            "Select number of context chunks",
            value=5,
            key="num_retrieved_chunks",
            min_value=1,
            max_value=10,
        )
        st.number_input(
            "Select number of messages to use in chat history",
            value=5,
            key="num_chat_messages",
            min_value=1,
            max_value=10,
        )

    st.sidebar.expander("Session State").write(st.session_state)

def generate_response(input_text, with_filters):
    if with_filters:
        app = filtered_tru_rag
        with filtered_tru_rag as recording:
            response = filtered_rag.query(input_text)
    else:
        app = tru_rag
        with tru_rag as recording:
            response = rag.query(input_text)

    record = recording.get()
    
    return record, response

def main():
    init_service_metadata()
    init_config_options()
    init_messages()

    tru = TruSession(database_engine=engine)

    with_filters = st.toggle("Use [Context Filter Guardrails](%s)" % "https://www.trulens.org/trulens_eval/guardrails/", value=False)

    if prompt := st.chat_input("Enter text:"):
        st.session_state.messages.append({"role": "user", "content": prompt})

        record, response = generate_response(prompt, with_filters)
        st.session_state.messages.append({"role": "assistant", "content": response})

        with st.chat_message("assistant"):
            st.markdown(response)

        with st.expander("See the trace of this record 👀"):
            trulens_st.trulens_trace(record=record)
        trulens_st.trulens_feedback(record=record)

    with st.expander("Open to see aggregate evaluation metrics"):
        st.title("Aggregate Evaluation Metrics")
        st.write("Powered by TruLens 🦑.")
        trulens_st.trulens_leaderboard()

if __name__ == "__main__":
    main()