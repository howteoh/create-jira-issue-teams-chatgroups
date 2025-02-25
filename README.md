# Teams Chat Creator Extension

A Chrome extension that creates Teams chat groups from JIRA issues.

## Features

- Create Teams chat groups directly from JIRA issues
- Filter issues based on comment time and target users
- Customizable settings for JIRA XML URL and target users
- Automatically add issue assignees to chat groups
- Save and restore email settings

## Installation

1. Install Python requirements:
```bash
pip install requests msal
```

2. Install the host application:
- Run `host/install_host.bat` as administrator

3. Install the Chrome extension:
- Open Chrome and go to `chrome://extensions/`
- Enable "Developer mode"
- Click "Load unpacked" and select the `extension` folder

## Configuration

1. Click the settings icon in the extension
2. Configure:
   - JIRA API Token
   - JIRA Username
   - JIRA Filter XML URL
   - Comment Hours Filter
   - Target JIRA Users

## Usage

1. Open the extension
2. Select the issues you want to create chat groups for
3. Enter owner and member emails
4. Click "Create Selected Chats Group"

## Author

Created by HowTeoh