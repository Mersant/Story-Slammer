import json
import os
import base64
import tempfile
import re
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

import tkinter as tk
from tkinter import filedialog
from colorama import init, Fore, Style
from moviepy.editor import VideoFileClip
from openai import OpenAI
from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth
import anthropic

# Initialize colorama for Windows compatibility
init()

# Load environment variables
load_dotenv()

# Initialize tkinter
root = tk.Tk()
root.withdraw()

# Constants and global variables
SETTINGS_FILE = "settings.json"

# Read prompt files
current_dir = os.getcwd()
summary_path = os.path.join(current_dir, "prompts", "initial_summary_prompt.txt")
chatbot_path = os.path.join(current_dir, "prompts", "chatbot_prompt.txt")
context_path = os.path.join(current_dir, "prompts", "context.txt")

with open(summary_path, 'r', encoding='utf-8') as file:
    initial_summary_prompt = file.read()

with open(chatbot_path, 'r', encoding='utf-8') as file:
    chatbot_prompt = file.read()

with open(context_path, 'r', encoding='utf-8') as file:
    context = file.read()

initial_summary_prompt = f"{initial_summary_prompt}\n<context>{context}</context>"

chatbot_system_prompt = "You are the world's greatest Engineer at a digital marketing company."
initial_summary_system_prompt = "You are the world's greatest software architect at a digital marketing company."

jira_tool = {
    "name": "Jira",
    "description": "Gets any Jira card and returns its details in XML format.",
    "input_schema": {
        "type": "object",
        "properties": {
            "card_name": {
                "type": "string",
                "description": "The name of the Jira card that will be returned."
            }
        },
        "required": ["card_name"]
    }
}

art = """
 _____ __  __       __                __ __  
(_  | /  \\|__)\\_/  (_ |   /\\ |\\/||\\/||_ |__) 
__) | \\__/|  \\ |   __)|__/--\\|  ||  ||__|  \\
"""

@dataclass
class Config:
    notes_path: str = ""
    images_path: str = ""
    recording_path: str = ""
    vault_path: str = ""

class ColorPrinter:
    @staticmethod
    def print(text: str, color: str = Fore.WHITE) -> None:
        print(f"{color}{text}{Style.RESET_ALL}")

    @staticmethod
    def input(prompt: str, color: str = Fore.YELLOW) -> str:
        return input(f"{color}{prompt}{Style.RESET_ALL}")

class FileHandler:
    @staticmethod
    def load_config(filename: str) -> Config:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                return Config(**json.load(f))
        return Config()

    @staticmethod
    def save_config(config: Config, filename: str) -> None:
        with open(filename, 'w') as f:
            json.dump(asdict(config), f, indent=4)

    @staticmethod
    def read_file(filepath: str) -> str:
        with open(filepath, 'r', encoding='utf-8') as file:
            return file.read()

class PathSelector:
    @staticmethod
    def get_file_path(title: str, file_type: str) -> str:
        if file_type == "folder":
            return filedialog.askdirectory(title=title)
        elif file_type == "markdown file":
            return filedialog.askopenfilename(title=title, filetypes=[("Markdown files, text files", "*.md;*.txt")])
        elif file_type == "video file":
            return filedialog.askopenfilename(title=title, filetypes=[("MP4 files", "*.mp4")])
        else:
            return filedialog.askopenfilename(title=title)

    @staticmethod
    def validate_file_path(path: str, file_type: str) -> bool:
        if not path:
            return True
        if not os.path.exists(path):
            ColorPrinter.print(f"Error: The specified {file_type} does not exist.", Fore.RED)
            return False
        if file_type == "folder" and not os.path.isdir(path):
            ColorPrinter.print("Error: The specified path is not a folder.", Fore.RED)
            return False
        if file_type == "markdown file" and not path.lower().endswith('.md'):
            ColorPrinter.print("Error: The specified file is not a markdown (.md) file.", Fore.RED)
            return False
        if file_type == "video file" and not path.lower().endswith('.mp4'):
            ColorPrinter.print("Error: The specified file is not an MP4 video file.", Fore.RED)
            return False
        return True

class DataProcessor:
    @staticmethod
    def get_image_data(image_folder_path: str) -> List[Dict[str, str]]:
        if not os.path.isdir(image_folder_path):
            raise ValueError(f"Error: '{image_folder_path}' is not a valid directory.")

        image_files = [f for f in os.listdir(image_folder_path) if os.path.isfile(os.path.join(image_folder_path, f))]

        if len(image_files) > 4:
            raise ValueError("Error: The image folder contains more than 4 files.")

        valid_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        processed_images = []

        for file in image_files:
            file_path = os.path.join(image_folder_path, file)
            file_extension = os.path.splitext(file)[1].lower()
            
            if file_extension not in valid_extensions:
                raise ValueError(f"Error: '{file}' is not a valid image format. Allowed formats are JPEG, PNG, GIF, and WebP.")
            
            with open(file_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            media_type = f"image/{file_extension[1:]}"
            if media_type == "image/jpg":
                media_type = "image/jpeg"
            
            processed_images.append({
                "type": "base64",
                "media_type": media_type,
                "data": encoded_string,
            })

        return processed_images

    @staticmethod
    def get_transcript_data(recording_file_path: str, whisper: OpenAI) -> str:
        if not os.path.isfile(recording_file_path):
            raise ValueError(f"Error: '{recording_file_path}' is not a valid file.")

        temp_audio = None
        audio_file = None

        try:
            temp_audio = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            temp_audio_path = temp_audio.name
            temp_audio.close()

            ColorPrinter.print("Extracting audio from the video...", Fore.CYAN)
            video = VideoFileClip(recording_file_path)
            video.audio.write_audiofile(temp_audio_path, codec='mp3')
            video.close()

            ColorPrinter.print("Transcribing the audio...", Fore.CYAN)
            audio_file = open(temp_audio_path, "rb")

            transcript = whisper.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

            return transcript.text

        except Exception as e:
            raise RuntimeError(f"Error during transcription: {str(e)}")

        finally:
            if audio_file:
                audio_file.close()
            if temp_audio:
                temp_audio.close()
            if os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                except PermissionError:
                    ColorPrinter.print(f"Warning: Unable to delete temporary file: {temp_audio_path}", Fore.YELLOW)

class JiraAPI:
    def __init__(self):
        self.base_url = os.getenv('JIRA_BASE_URL')
        self.username = os.getenv('ATLASSIAN_USERNAME')
        self.api_key = os.getenv('JIRA_API_KEY')
        self.auth = HTTPBasicAuth(self.username, self.api_key)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def get_issue_data(self, primary_issue_key: str) -> List[str]:
        issue_url = f"{self.base_url}/rest/api/2/issue/{primary_issue_key}?fields=parent,summary,status,assignee,priority,description"
        try:
            response = requests.get(issue_url, headers=self.headers, auth=self.auth)
            response.raise_for_status()
            primary_issue = response.json()
            parent_key = primary_issue['fields'].get('parent', {}).get('key', primary_issue_key)

            jql = f'issue = {parent_key} OR parent = {parent_key}'
            payload = {
                "jql": jql,
                "startAt": 0,
                "maxResults": 200,
                "fields": [
                    "summary",
                    "status",
                    "assignee",
                    "priority",
                    "description",
                    "parent"
                ]
            }

            response = requests.post(f"{self.base_url}/rest/api/2/search", json=payload, headers=self.headers, auth=self.auth)
            response.raise_for_status()

            response_text = response.text
            response_text = re.sub(r'-(.*?)-', r'<crossedout>\1</crossedout>', response_text)
            response_text = re.sub(r'\{(color|bgColor):#([0-9a-fA-F]{6})\}(.*?)\{/(color|bgColor)\}', r'<highlighted>\3</highlighted>', response_text)
            
            search_results = response.json()

            formatted_issues = []
            for issue in search_results['issues']:
                issue_key = issue['key']
                summary = issue['fields']['summary']
                status = issue['fields']['status']['name']
                assignee = issue['fields'].get('assignee')
                assignee = assignee['displayName'] if assignee else 'Unassigned'
                priority = issue['fields']['priority']['name']
                description = issue['fields'].get('description', 'No description provided')

                issue_type = 'primaryIssue' if issue_key == primary_issue_key else ('parentIssue' if issue_key == parent_key else 'relatedIssue')

                xml_string = f"""<{issue_type}>
    <key>{issue_key}</key>
    <summary>{summary}</summary>
    <status>{status}</status>
    <assignee>{assignee}</assignee>
    <priority>{priority}</priority>
    <description>{description}</description>
</{issue_type}>"""

                formatted_issues.append(xml_string)

            return formatted_issues
        
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"An error occurred while fetching Jira issues: {e}")

    def fetch_single_issue(self, issue_key: str) -> str:
        issue_url = f"{self.base_url}/rest/api/2/issue/{issue_key}"
        try:
            response = requests.get(issue_url, headers=self.headers, auth=self.auth)
            response.raise_for_status()
            
            issue_data = response.json()

            summary = issue_data['fields']['summary']
            status = issue_data['fields']['status']['name']
            assignee = issue_data['fields'].get('assignee')
            assignee = assignee['displayName'] if assignee else 'Unassigned'
            priority = issue_data['fields']['priority']['name']
            description = issue_data['fields'].get('description', 'No description provided')

            xml_string = f"""<fetchedIssue>
    <key>{issue_key}</key>
    <summary>{summary}</summary>
    <status>{status}</status>
    <assignee>{assignee}</assignee>
    <priority>{priority}</priority>
    <description>{description}</description>
</fetchedIssue>"""

            return xml_string

        except:
            return "<fetchedIssue>An unknown error occurred while fetching this issue.</fetchedIssue>"

class AIAssistant:
    def __init__(self, openai_client: OpenAI, claude_client: anthropic.Anthropic):
        self.whisper = openai_client
        self.claude = claude_client
        self.jira_api = JiraAPI()

    def get_claude_response(self, conversation_history: List[Dict[str, str]]) -> str:
        response = self.claude.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            temperature=0.6,
            system=chatbot_system_prompt,
            messages=conversation_history,
            tools=[jira_tool]
        )


        if response.stop_reason == "tool_use":
            tool_use = response.content[-1]
            tool_name = tool_use.name
            tool_input = tool_use.input
            conversation_history.append({"role": "assistant", "content": response.content})

            if tool_name == "Jira":
                ColorPrinter.print("Claude wants to use a tool", Fore.YELLOW)
                card_name = tool_input["card_name"]
                try:
                    formatted_jira_issue = self.jira_api.fetch_single_issue(card_name)
                    tool_response = {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": formatted_jira_issue
                            }
                        ]
                    }
                    ColorPrinter.print(f"Fetched Jira issue {card_name} with content length {len(formatted_jira_issue)}", Fore.YELLOW)
                    conversation_history.append(tool_response)
                    response = self.claude.messages.create(
                        model="claude-3-5-sonnet-20240620",
                        max_tokens=1000,
                        temperature=0.6,
                        system=chatbot_system_prompt,
                        messages=conversation_history,
                        tools=[jira_tool]
                    )
                except ValueError as e:
                    ColorPrinter.print(f"Error: {str(e)}", Fore.RED)

        return response.content[0].text

    def initial_conversation(self, conversation_history: List[Dict[str, str]], folder_path: str, file_name: str) -> List[Dict[str, str]]:
        summary = self.claude.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=4096,
            temperature=0.6,
            system=initial_summary_system_prompt,
            messages=conversation_history,
        ).content[0].text
        ColorPrinter.print("\nClaude's Initial Summary:", Fore.LIGHTRED_EX)
        ColorPrinter.print(summary, Fore.GREEN)

        file_path = os.path.join(folder_path, file_name)
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(summary)

        conversation_history.append({"role": "assistant", "content": summary})
        return conversation_history

    def interactive_conversation(self, conversation_history: List[Dict[str, str]]) -> None:
        ColorPrinter.print("\nYou can now ask questions about the Jira issues. Type 'exit' to end the conversation.", Fore.LIGHTRED_EX)
        while True:
            user_input = ColorPrinter.input("\nYour question: ", Fore.GREEN)
            if user_input.lower() == 'exit':
                break
            elif not user_input:
                ColorPrinter.print("Please enter a valid question.", Fore.RED)
                continue
            conversation_history.append({"role": "user", "content": user_input})

            response = self.get_claude_response(conversation_history)

            ColorPrinter.print("\nClaude's Response:", Fore.LIGHTRED_EX)
            ColorPrinter.print(response, Fore.LIGHTCYAN_EX)

            conversation_history.append({"role": "assistant", "content": response})

class StorySlammer:
    def __init__(self):
        self.config = FileHandler.load_config("settings.json")
        self.jira_api = JiraAPI()
        self.ai_assistant = AIAssistant(OpenAI(api_key=os.getenv("OPENAI_API_KEY")), anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY")))

    def run(self):
        ColorPrinter.print(art, Fore.CYAN)
        ColorPrinter.print(f"Using context with length: {len(context)}", Fore.BLUE)
        ColorPrinter.print(f"Using initial summary prompt with length: {len(initial_summary_prompt) - len(context)}", Fore.BLUE)
        ColorPrinter.print(f"Using chatbot prompt with length: {len(chatbot_prompt)}", Fore.BLUE)
        ColorPrinter.print("\nWelcome to Story Slammer!", Fore.CYAN)
        ColorPrinter.print("=========================", Fore.CYAN)

        jira_card = ColorPrinter.input("Enter the name of the Jira card you're working on: ", Fore.GREEN)
        self.update_config()

        jira_issue_data = self.jira_api.get_issue_data(jira_card) if jira_card else ""
        processed_images = DataProcessor.get_image_data(self.config.images_path) if self.config.images_path else ""
        notes_content = FileHandler.read_file(self.config.notes_path) if self.config.notes_path else ""
        transcript = DataProcessor.get_transcript_data(self.config.recording_path, self.ai_assistant.whisper) if self.config.recording_path else ""

        FileHandler.save_config(self.config, "settings.json")
        self.print_summary(jira_card)

        ColorPrinter.print("\nCommence Artificial Intelligence Procedures...", Fore.RED)

        conversation_content = []
        if processed_images:
            for image in processed_images:
                conversation_content.append({"type": "image", "source": image})
        
        conversation_content.append({
            "type": "text",
            "text": f"""
{initial_summary_prompt}
Here's the data for analysis:
<jira>{''.join(jira_issue_data)}</jira>
<notes>{notes_content}</notes>
<transcript>{transcript}</transcript>
"""
        })

        conversation_history = [{"role": "user", "content": conversation_content}]
        
        generated_conversation = self.ai_assistant.initial_conversation(conversation_history, self.config.vault_path, jira_card + ".md")

        conversation_history.append({"role": "user", "content": chatbot_prompt})
        conversation_history.append({"role": "assistant", "content": "I understand, and am prepared to answer any questions the user may have and use my tools when appropriate."})

        self.ai_assistant.interactive_conversation(generated_conversation)

    def update_config(self):
        self.config.notes_path = self.confirm_path("Your notes file is", self.config.notes_path, "markdown file")
        self.config.images_path = self.confirm_path("Your images folder is", self.config.images_path, "folder")
        self.config.recording_path = self.confirm_path("Your recording file is", self.config.recording_path, "video file")
        self.config.vault_path = self.confirm_path("Your vault folder is", self.config.vault_path, "folder")

    def confirm_path(self, prompt: str, current_value: str, file_type: str) -> str:
        response = ColorPrinter.input(f"{prompt} {f"set to {current_value}" if current_value else "not set"}. Is this correct? [y/n]: ")
        if response.lower() in ['', 'y', 'yes']:
            return current_value
        
        while True:
            response = ColorPrinter.input(f"Do you want to select a new {file_type}? [y/n]: ")
            if response.lower() in ['y', 'yes']:
                ColorPrinter.print(f"Please select a new {file_type}:", Fore.YELLOW)
                new_path = PathSelector.get_file_path(f"Select {file_type.capitalize()}", file_type)
                if new_path:
                    return new_path
                ColorPrinter.print("No file selected. Keeping the current value.", Fore.YELLOW)
                return current_value
            elif response.lower() in ['', 'n', 'no']:
                return ""
            ColorPrinter.print("Invalid input. Please enter 'y' for yes or 'n' for no.", Fore.RED)

    def print_summary(self, jira_card: str):
        ColorPrinter.print("\nThank you for providing the information!", Fore.CYAN)
        ColorPrinter.print("Here's a summary of what you entered:", Fore.CYAN)
        ColorPrinter.print(f"Jira Card: {jira_card}", Fore.GREEN)
        ColorPrinter.print(f"Notes File: {self.config.notes_path or 'Not provided'}", Fore.YELLOW)
        ColorPrinter.print(f"Images Folder: {self.config.images_path or 'Not provided'}", Fore.MAGENTA)
        ColorPrinter.print(f"Recording File: {self.config.recording_path or 'Not provided'}", Fore.BLUE)

if __name__ == "__main__":
    collector = StorySlammer()
    collector.run()