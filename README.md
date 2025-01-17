# StorySlammer
Story Slammer is WIP AI-powered tool designed to streamline the process of analyzing and summarizing Jira issues, notes, images, and recorded meetings. It leverages OpenAI's Whisper for transcription and Anthropic's Claude for conversation and analysis.

## Features
- Fetch and analyze Jira issues
- Process and analyze images related to your project
- Transcribe and analyze recorded meetings
- Incorporate notes and additional context
- Generate comprehensive summaries using AI
- Interactive Q&A session with AI about the analyzed data

## Setup

1. You can choose to create a `context.txt` file under the `prompts` directory if you so desire. This file is in the git ignore since its purpose is to hold relatively sensitive information to help story slammer give you better responses. For example, this file can be used to include the names of inviduals at the company so that Story Slammer will know who is working on a card and what team they belong to. Any information that Story Slammer could use to provide a better response can be put into this file.

## Usage

1. Set up your environment variables:
   Create a `.env` file in the project root and add the following:
   ```
   OPENAI_API_KEY=your_openai_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   JIRA_BASE_URL=your_jira_base_url
   ATLASSIAN_USERNAME=your_atlassian_username
   JIRA_API_KEY=your_jira_api_key
   ```
2. Run the main script:
   ```
   python story_slammer.py
   ```

2. Follow the prompts to:
   - Enter the Jira card you're working on
   - Confirm or update paths for notes, images, recordings, and output
   - Review the initial AI-generated summary
   - Engage in an interactive Q&A session with the AI about the analyzed data

## File Structure
- `story_slammer.py`: Main script containing the StorySlammer class
- `prompts/`: Directory containing prompt templates
  - `initial_summary_prompt.txt`: Prompt for generating the initial summary
  - `chatbot_prompt.txt`: Prompt for the interactive Q&A session
  - `context.txt`: Additional context for the AI
- `settings.json`: Configuration file storing user preferences
