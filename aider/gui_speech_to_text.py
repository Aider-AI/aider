import base64
import os

import streamlit as st
import streamlit.components.v1 as components


class SpeechToText:
    """Class to handle speech-to-text functionality in the GUI"""

    def render(self):
        """Render the speech-to-text component with LED indicator"""
        self._js_dir = os.path.dirname(__file__)

        # Create JS file path
        js_path = os.path.join(self._js_dir, "gui_speech_to_text.js")
        if not os.path.exists(js_path):
            st.error(f"JavaScript file not found: {js_path}")
            return

        # Read the JS file for data URL
        with open(js_path, "r") as f:
            js_content = f.read()

        # Create data URL for the JS file
        js_b64 = base64.b64encode(js_content.encode("utf-8")).decode("utf-8")
        js_data_url = f"data:text/javascript;base64,{js_b64}"

        # Create simple HTML component with a container for the JS to populate
        components.html(
            f"""
            <div id="speech-to-text-container"></div>
            <!-- Load JS file via data URL since direct src paths don't work in Streamlit iframe -->
            <script src="{js_data_url}"></script>
            """,
            height=50,
        )
