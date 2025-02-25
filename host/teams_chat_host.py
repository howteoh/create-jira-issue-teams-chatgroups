#!/usr/bin/env python
import sys
import json
import struct
import os
import logging
import traceback
import time

# 添加父目錄到 Python 路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# 現在可以導入 create_teams_chat
import create_teams_chat

# 設置日誌
try:
    log_path = os.path.join(os.path.expanduser('~'), 'teams_chat_native_host.log')
    print(f"Attempting to create log file at: {log_path}", file=sys.stderr)
    
    logging.basicConfig(
        filename=log_path,
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 同時輸出到 stderr
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.DEBUG)
    logging.getLogger('').addHandler(console)
    
    logging.info('Logging initialized successfully')
except Exception as e:
    print(f"Error setting up logging: {str(e)}", file=sys.stderr)
    print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)

# Native messaging protocol helper functions
def get_message():
    try:
        logging.debug("Waiting for message...")
        raw_length = sys.stdin.buffer.read(4)
        if not raw_length:
            logging.warning("No message length received")
            return None
        message_length = struct.unpack('=I', raw_length)[0]
        logging.debug(f"Message length: {message_length}")
        message = sys.stdin.buffer.read(message_length).decode('utf-8')
        logging.debug(f"Received message: {message}")
        return json.loads(message)
    except Exception as e:
        logging.error(f"Error in get_message: {str(e)}")
        logging.error(traceback.format_exc())
        return None

def send_message(message):
    try:
        logging.debug(f"Sending message: {message}")
        encoded_message = json.dumps(message).encode('utf-8')
        encoded_length = struct.pack('=I', len(encoded_message))
        sys.stdout.buffer.write(encoded_length)
        sys.stdout.buffer.write(encoded_message)
        sys.stdout.buffer.flush()
        logging.debug("Message sent successfully")
    except Exception as e:
        logging.error(f"Error in send_message: {str(e)}")
        logging.error(traceback.format_exc())

def sanitize_chat_name(title):
    """清理聊天名稱以符合 Teams 的要求"""
    # 1. 移除開頭和結尾的空白
    title = title.strip()
    
    # 2. 移除不允許的特殊字元
    # Teams 不允許: <>*%&:{}?+/\|"#
    invalid_chars = '<>*%&:{}?+/\\|"#'
    for char in invalid_chars:
        title = title.replace(char, '-')
        
    # 3. 將多個空白替換為單個空白
    title = ' '.join(title.split())
    
    # 4. 限制長度為 250 字元
    if len(title) > 250:
        title = title[:247] + '...'
        
    # 5. 確保不是空字串
    if not title:
        title = 'New Chat'
        
    return title

def handle_message(message):
    """處理來自擴充功能的消息"""
    try:
        action = message.get('action')
        logging.info(f'Processing message: {message}')
        
        if action == 'createSelectedChats':
            selected_issues = message.get('selectedIssues', [])
            owner_email = message.get('ownerEmail')
            member_emails = message.get('memberEmails', [])
            
            logging.info(f'Creating chats for {len(selected_issues)} issues')
            logging.info(f'Selected issues: {selected_issues}')
            logging.info(f'Owner email: {owner_email}')
            logging.info(f'Member emails: {member_emails}')
            
            if not selected_issues:
                raise Exception("No issues selected")
            
            if not owner_email:
                raise Exception("Owner email is required")
                
            if not member_emails:
                raise Exception("Member emails are required")
            
            results = []
            for issue in selected_issues:
                try:
                    chat_name = sanitize_chat_name(issue['title'])
                    issue_link = issue.get('link')
                    issue_key = issue.get('key')
                    issue_title = issue.get('title')
                    assignee = issue.get('assignee')
                    assignee_email = issue.get('assigneeEmail')
                    
                    logging.info('=== Processing issue ===')
                    logging.info(f'Chat name: {chat_name}')
                    logging.info(f'Issue link: {issue_link}')
                    logging.info(f'Issue key: {issue_key}')
                    logging.info(f'Issue title: {issue_title}')
                    logging.info(f'Assignee: {assignee}')
                    logging.info(f'Assignee email: {assignee_email}')
                    
                    # 如果有 assignee email，添加到成員列表
                    chat_members = member_emails.copy()
                    if assignee_email and assignee_email not in chat_members:
                        chat_members.append(assignee_email)
                        logging.info(f'Added assignee to members: {assignee_email}')
                    
                    logging.info(f'Final member list: {chat_members}')
                    
                    try:
                        result = create_teams_chat.main(
                            chat_name=chat_name,
                            owner_email=owner_email,
                            member_emails=chat_members,
                            issue_link=issue_link,
                            issue_key=issue_key,
                            issue_title=issue_title,
                            assignee=assignee,
                            assignee_email=assignee_email
                        )
                        logging.info(f'Chat creation result: {result}')
                    except Exception as e:
                        logging.error(f'Error in create_teams_chat.main: {str(e)}')
                        logging.error(traceback.format_exc())
                        raise
                    
                    if result:
                        logging.info(f'Chat created successfully: {result}')
                        results.append(result)
                    else:
                        logging.error('Failed to create chat')
                        
                    time.sleep(2)
                except Exception as e:
                    logging.error(f"Error creating chat for {issue['title']}: {str(e)}")
                    logging.error(traceback.format_exc())
                    continue
            
            if not results:
                raise Exception("Failed to create any chats")
            
            response = {
                'success': True,
                'message': 'Chats created successfully',
                'result': results
            }
            logging.info(f'Sending response: {response}')
            return response
            
        else:
            raise Exception(f"Unknown action: {action}")
            
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error handling message: {error_msg}")
        logging.error(traceback.format_exc())
        return {
            'success': False,
            'message': error_msg
        }

def main():
    try:
        logging.info('Native messaging host started')
        while True:
            message = get_message()
            if message is None:
                logging.info('No message received, exiting')
                break
                
            logging.info(f'Processing message: {message}')
            
            # 使用新的消息處理函數
            response = handle_message(message)
            
            logging.info(f'Sending response: {response}')
            send_message(response)
            
    except Exception as e:
        error_msg = f"Critical error in main: {str(e)}\n{traceback.format_exc()}"
        logging.error(error_msg)
        send_message({'success': False, 'message': str(e)})

def test_mode():
    """測試模式，檢查所有必要的設置"""
    try:
        logging.info("=== Testing native messaging host ===")
        
        # 檢查必要的模組
        import json
        import struct
        import sys
        import create_teams_chat
        logging.info("All required modules are available")
        
        # 測試 stdin/stdout
        logging.info("Testing stdin/stdout...")
        sys.stdout.buffer.write(struct.pack('=I', 4))
        sys.stdout.buffer.write(b'test')
        sys.stdout.buffer.flush()
        logging.info("stdin/stdout test passed")
        
        return True
    except Exception as e:
        logging.error(f"Test failed: {str(e)}")
        return False

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        success = test_mode()
        sys.exit(0 if success else 1)
    else:
        main() 