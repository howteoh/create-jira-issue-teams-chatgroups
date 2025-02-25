import requests
from msal import PublicClientApplication
import webbrowser
from urllib.parse import quote  # Add this import
import json
import time
from datetime import datetime
import xml.etree.ElementTree as ET
import os
import logging

class TokenManager:
    def __init__(self):
        self.token_cache_file = os.path.join(os.path.expanduser('~'), '.teams_chat_token.json')
        self.client_id = "a5386bbf-f6f4-4462-9a91-03a57adbadfd"
        self.authority = "https://login.microsoftonline.com/realtek.com"
        self.scope = ["Chat.Create", "Chat.ReadWrite", "User.Read"]
        
        # 創建 MSAL 應用
        self.app = PublicClientApplication(
            self.client_id,
            authority=self.authority
        )
        
        # 載入快取的 token
        self.load_token_cache()
    
    def load_token_cache(self):
        """載入快取的 token"""
        try:
            if os.path.exists(self.token_cache_file):
                with open(self.token_cache_file, 'r') as f:
                    cache_data = json.load(f)
                    self.app.token_cache._cache = cache_data
        except Exception as e:
            print(f"Error loading token cache: {e}")
    
    def save_token_cache(self):
        """保存 token 到快取"""
        try:
            cache_data = self.app.token_cache._cache
            with open(self.token_cache_file, 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            print(f"Error saving token cache: {e}")
    
    def get_token(self):
        """獲取 access token，優先使用快取"""
        accounts = self.app.get_accounts()
        
        if accounts:
            # 嘗試使用快取的 token
            result = self.app.acquire_token_silent(self.scope, account=accounts[0])
            if result:
                return result['access_token']
        
        # 如果沒有快取或快取已過期，重新獲取
        # 使用 prompt=none 避免顯示賬號選擇器
        result = self.app.acquire_token_interactive(
            self.scope,
            prompt="none"  # 不顯示賬號選擇器
        )
        if result:
            self.save_token_cache()
            return result['access_token']
        
        raise Exception("Failed to get access token")

# 創建全局 TokenManager 實例
token_manager = TokenManager()

# Function to create a Teams chat
def create_teams_chat(access_token, chat_name, owner_email):
    url = "https://graph.microsoft.com/beta/chats"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    body = {
        "chatType": "group",
        "topic": chat_name,
        "members": [
            {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users/{owner_email}"
            }
        ]
    }
    
    print("Creating chat with owner...")
    try:
        response = requests.post(url, headers=headers, json=body)
        if response.status_code == 201:
            chat = response.json()
            print("Chat created successfully!")
            return chat
        else:
            print(f"Error creating chat: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return None

def add_member_to_chat(access_token, chat_id, member_email):
    url = f"https://graph.microsoft.com/beta/chats/{chat_id}/members"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    body = {
        "@odata.type": "#microsoft.graph.aadUserConversationMember",
        "roles": ["guest"],
        "visibleHistoryStartDateTime": "0001-01-01T00:00:00Z",
        "user@odata.bind": f"https://graph.microsoft.com/beta/users/{member_email}"
    }
    
    try:
        response = requests.post(url, headers=headers, json=body)
        if response.status_code in [201, 200]:
            print(f"Member {member_email} added successfully!")
            return response.json()
        else:
            print(f"Error adding member: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception occurred while adding member: {str(e)}")
        return None

def get_teams_chats(access_token):
    url = "https://graph.microsoft.com/beta/chats"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting chats: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return None

def get_chat_members(access_token, chat_id):
    url = f"https://graph.microsoft.com/beta/chats/{chat_id}/members"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        print("Members Response status code:", response.status_code)
        print("Members Response content:", response.text)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting chat members: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return None

def handle_message(message):
    """處理來自擴充功能的消息"""
    try:
        if message.get('action') == 'createSelectedChats':
            # 創建選定的聊天
            selected_issues = message.get('selectedIssues', [])
            owner_email = message.get('ownerEmail')
            member_emails = message.get('memberEmails', [])
            
            results = []
            for issue in selected_issues:
                result = create_teams_chat_single(issue['title'], owner_email, member_emails)
                if result:
                    results.append(result)
                time.sleep(2)  # 避免請求過快
            
            return {
                'success': True,
                'result': results
            }
        else:
            raise Exception(f"Unknown action: {message.get('action')}")
            
    except Exception as e:
        return {
            'success': False,
            'message': str(e)
        }

def main(chat_name, owner_email, member_emails, issue_link=None, issue_key=None, issue_title=None, assignee=None, assignee_email=None):
    """創建 Teams 聊天"""
    try:
        # 如果沒有指定 chat_name，使用預設值
        if chat_name is None:
            chat_name = "Test Chat"
            
        return create_teams_chat_single(
            chat_name, 
            owner_email, 
            member_emails, 
            issue_link=issue_link,
            issue_key=issue_key,
            issue_title=issue_title,
            assignee=assignee,
            assignee_email=assignee_email
        )
    except Exception as e:
        print(f"Error in main: {str(e)}")
        return None

def send_pinned_link(access_token, chat_id, issue_link, issue_key):
    """發送並釘選 issue 連結"""
    url = f"https://graph.microsoft.com/beta/chats/{chat_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # 發送消息
    message = f"<p><a href='{issue_link}'>{issue_key}</a></p>"
    body = {
        "body": {
            "contentType": "html",
            "content": message
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=body)
        if response.status_code == 201:
            # 獲取消息 ID
            message_id = response.json().get('id')
            
            # 釘選消息
            pin_url = f"https://graph.microsoft.com/beta/chats/{chat_id}/messages/{message_id}/pin"
            pin_response = requests.post(pin_url, headers=headers)
            
            return pin_response.status_code in [201, 204]
        return False
    except Exception as e:
        print(f"Error sending/pinning issue link: {str(e)}")
        return False

def send_chat_message(access_token, chat_id, issue_key, issue_title, assignee=None, assignee_email=None):
    """發送格式化的聊天消息"""
    url = f"https://graph.microsoft.com/beta/chats/{chat_id}/messages"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # 使用已有的 assignee 名字
    assignee_name = assignee or assignee_email.split('@')[0]
    
    # 構建消息內容
    message = f"""<p>hello {assignee_name}</p>
<p>請協助查看 {issue_title}</p>
<p>的問題,謝謝</p>"""

    body = {
        "body": {
            "contentType": "html",
            "content": message
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=body)
        if response.status_code == 201:
            print("Message sent successfully!")
            return True
        else:
            print(f"Error sending message: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Exception occurred while sending message: {str(e)}")
        return False

def create_teams_chat_single(chat_name, owner_email, member_emails, issue_link=None, issue_key=None, issue_title=None, assignee=None, assignee_email=None):
    """創建單個 Teams 聊天"""
    try:
        access_token = token_manager.get_token()
        print("Access Token acquired successfully")
        
        # 創建聊天
        chat = create_teams_chat(access_token, chat_name, owner_email)
        
        if chat:
            chat_id = chat["id"]
            print(f"Chat created with ID: {chat_id}")
            
            # 添加其他成員
            for email in member_emails:
                print(f"\nAdding member: {email}")
                add_member_to_chat(access_token, chat_id, email)
            
            # 如果有 issue 資訊，發送消息
            if issue_link and issue_key and issue_title:
                time.sleep(2)  # 等待群組創建完成
                
                # 發送並釘選 issue 連結
                send_pinned_link(access_token, chat_id, issue_link, issue_key)
                
                time.sleep(1)  # 稍等一下，確保消息順序
                
                # 發送初始消息
                send_chat_message(
                    access_token,
                    chat_id,
                    issue_key,
                    issue_title,
                    assignee,
                    assignee_email
                )
            
            return {
                "id": chat_id,
                "name": chat_name,
                "owner": owner_email,
                "members": member_emails,
                "webUrl": f"https://teams.microsoft.com/l/chat/{chat_id}/0"
            }
    except Exception as e:
        print(f"Error creating chat: {str(e)}")
        return None

def create_chat(app, chat_name, owner_email, member_emails):
    """
    建立 Teams 聊天
    """
    try:
        # 建立聊天的請求內容
        chat_request = {
            "chatType": "group",
            "topic": chat_name,
            "members": [
                {
                    "@odata.type": "#microsoft.graph.aadUserConversationMember",
                    "roles": ["owner"],
                    "user": {
                        "email": owner_email
                    }
                }
            ]
        }
        
        # 添加所有成員到初始請求中
        for email in member_emails:
            chat_request["members"].append({
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": [],
                "user": {
                    "email": email
                }
            })
            
        # 建立聊天
        try:
            response = app.client.post("/beta/chats", json=chat_request)
            chat_id = response.json()['id']
            
            # 發送初始訊息
            initial_message = {
                "body": {
                    "content": f"Chat created for: {chat_name}",
                    "contentType": "text"
                }
            }
            message = app.client.post(f"/beta/chats/{chat_id}/messages", json=initial_message)
            
            # 嘗試釘選訊息 (如果失敗也不中斷流程)
            try:
                message_id = message.json()['id']
                app.client.post(f"/beta/chats/{chat_id}/messages/{message_id}/pin")
            except Exception as e:
                logging.warning(f"Failed to pin message: {str(e)}")
                
            # 返回聊天資訊
            return {
                'id': chat_id,
                'name': chat_name,
                'owner': owner_email,
                'members': member_emails,
                'webUrl': f"https://teams.microsoft.com/l/chat/{chat_id}/0"
            }
            
        except Exception as e:
            logging.error(f"Error creating chat: {str(e)}")
            raise
            
    except Exception as e:
        logging.error(f"Error in create_chat: {str(e)}")
        raise

if __name__ == "__main__":
    # 測試代碼
    result = main(
        "Test Chat",
        "howteoh@realtek.com",
        ["teamsmm001@realtek.com"]
    )
    print(result)
