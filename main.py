import streamlit as st
from google import genai
from google.genai import types
import json

gemini_api_key = st.secrets["GEMINI_API_KEY"]

# --- Configuration ---
# Configure the Gemini API with your key.
# IMPORTANT: Replace "YOUR_GEMINI_API_KEY" with your actual API key.
# For better security, use Streamlit's secrets management for deployment.
try:
    # It's recommended to load API keys from a secure location rather than hardcoding

    client = genai.Client(api_key=gemini_api_key)
    chat = client.chats.create(model='gemini-2.5-flash')
except Exception as e:
    st.error(f"Error configuring Gemini API: {e}")
    st.stop()


# --- Helper Functions ---
def get_ai_response(prompt):
    """
    Sends a prompt to the Gemini API and returns the response.
    """
    try:
        response = chat.send_message(prompt, config=types.GenerateContentConfig(
            temperature=0.8  # Slightly lower temp for more predictable JSON
        ))
        return response.text
    except Exception as e:
        st.error(f"An error occurred with the AI model: {e}")
        return None


def initialize_session_state():
    if 'todo_list' not in st.session_state:
        st.session_state.todo_list = []
    if 'chat_response' not in st.session_state:
        st.session_state.chat_response = None


# --- Task Renderer with Subtask CRUD ---
def render_tasks(tasks, level=0, parent_key="root"):
    total_tasks = 0
    completed_tasks = 0

    for i, raw_item in enumerate(tasks):
        # Normalize: ensure dict
        if isinstance(raw_item, str):
            item = {"task": raw_item, "priority": "Medium", "completed": False}
        else:
            item = raw_item

        total_tasks += 1
        task_label = f"{item.get('task', 'No task description')} (Priority: {item.get('priority', 'Medium')})"

        # 🔑 Unique key prefix for this task (path style)
        task_key = f"{parent_key}_{level}_{i}"

        with st.expander(task_label, expanded=True):
            # Completed checkbox
            new_status = st.checkbox(
                "Completed",
                value=item.get('completed', False),
                key=f"chk_{task_key}"
            )
            item['completed'] = new_status
            if new_status:
                completed_tasks += 1

            # Add subtask
            new_subtask_text = st.text_input(
                f"Add subtask under '{item['task']}'",
                key=f"input_sub_{task_key}"
            )
            if st.button("Add Subtask", key=f"btn_add_sub_{task_key}"):
                if new_subtask_text.strip():
                    if "sub_tasks" not in item or not isinstance(item["sub_tasks"], list):
                        item["sub_tasks"] = []
                    item["sub_tasks"].append({
                        "task": new_subtask_text.strip(),
                        "priority": "Medium",
                        "completed": False
                    })
                    st.rerun()

            # Delete task
            if st.button(f"Delete '{item['task']}'", key=f"btn_del_{task_key}"):
                tasks.pop(i)
                st.rerun()

            # Render subtasks recursively (pass task_key forward)
            if 'sub_tasks' in item and isinstance(item['sub_tasks'], list):
                sub_total, sub_completed = render_tasks(
                    item['sub_tasks'],
                    level + 1,
                    parent_key=task_key
                )
                total_tasks += sub_total
                completed_tasks += sub_completed

    return total_tasks, completed_tasks




# --- Main Application ---
def main():
    st.title("📝 AI-Powered Conversational To-Do List")
    initialize_session_state()

    # --- Natural Language Input ---
    st.header("What would you like to do?")
    natural_language_input = st.text_area(
        "Describe your tasks, ask to add/remove/update items, or ask questions about your list.",
        height=150,
        placeholder="e.g., I need to prepare for the project launch. This includes creating a presentation and finishing the report. The presentation is the highest priority."
    )

    if st.button("✨ Submit"):
        if natural_language_input:
            with st.spinner("AI is thinking..."):
                current_list_json = json.dumps(st.session_state.todo_list, indent=2)

                if not st.session_state.todo_list:
                    prompt = f"""
                    You are a meticulous personal assistant. Transform the following plans into a structured to-do list in JSON format.
                    - Break down broad goals into actionable tasks.
                    - Use 'sub_tasks' for related subtasks.
                    - Include 'priority' as 'High', 'Medium', or 'Low'.
                    - Include 'completed': false for all.
                    - Output JSON only.

                    User Input: "{natural_language_input}"
                    """
                else:
                    prompt = f"""
                    The current to-do list is:
                    ```json
                    {current_list_json}
                    ```

                    User request: "{natural_language_input}"

                    CRITICAL RULES:
                    1. If modifying: output only updated JSON (entire list).
                    2. If question: output plain text answer only.
                    """

                ai_response = get_ai_response(prompt)

                if ai_response:
                    try:
                        json_response = ai_response.strip().replace("```json", "").replace("```", "")
                        new_list = json.loads(json_response)
                        st.session_state.todo_list = new_list
                        st.session_state.chat_response = None
                        st.success("Your to-do list has been updated!")
                    except (json.JSONDecodeError, TypeError):
                        st.session_state.chat_response = ai_response
        else:
            st.warning("Please enter something.")

    st.markdown("---")

    # --- To-Do List Display ---
    st.header("Your Interactive To-Do List")
    if st.session_state.todo_list:
        total_tasks, completed_tasks = render_tasks(st.session_state.todo_list)

        # Progress Bar
        st.header("Your Progress")
        if total_tasks > 0:
            progress_percentage = completed_tasks / total_tasks
            st.progress(progress_percentage)
            st.write(f"{completed_tasks} out of {total_tasks} tasks completed ({progress_percentage:.0%})")
        else:
            st.write("Your list is ready for tasks.")
    else:
        st.info("Your generated to-do list will appear here once you describe your tasks above.")

    # --- Conversational Responses ---
    if st.session_state.chat_response:
        st.markdown("---")
        st.subheader("AI Assistant:")
        st.info(st.session_state.chat_response)


if __name__ == "__main__":
    main()