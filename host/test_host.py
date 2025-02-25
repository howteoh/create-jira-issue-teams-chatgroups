#!/usr/bin/env python
import sys
import json
import struct
import logging
import os
import traceback
import ctypes
from datetime import datetime

# 添加父目錄到 Python 路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# 導入 create_teams_chat
import create_teams_chat

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# 設置日誌
log_file = os.path.join(os.path.expanduser('~'), 'teams_chat_host.log')
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 同時輸出到檔案
with open(os.path.join(os.path.expanduser('~'), 'host_stderr.log'), 'a', encoding='utf-8') as f:
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    f.write(f"\n=== New Session Started at {current_time} ===\n")
    f.write(f"Running as admin: {is_admin()}\n")
    f.write(f"Current user: {os.getenv('USERNAME')}\n")
    f.write(f"Current directory: {os.getcwd()}\n")
    f.write(f"Python path: {sys.executable}\n")
    f.write(f"Script path: {__file__}\n")

logging.info('=== Script started ===')
logging.info(f'Running as admin: {is_admin()}')
logging.info(f'Current working directory: {os.getcwd()}')
logging.info(f'Python executable: {sys.executable}')
logging.info(f'Command line arguments: {sys.argv}')

def get_message():
    try:
        # 讀取消息長度（4 bytes）
        raw_length = sys.stdin.buffer.read(4)
        if not raw_length:
            logging.warning('No message length received')
            return None
            
        # 解析消息長度
        message_length = struct.unpack('=I', raw_length)[0]
        logging.info(f'Expected message length: {message_length}')
        
        # 讀取實際消息
        message = sys.stdin.buffer.read(message_length).decode('utf-8')
        logging.info(f'Received message: {message}')
        
        return json.loads(message)
    except Exception as e:
        logging.error(f'Error in get_message: {str(e)}')
        logging.error(traceback.format_exc())
        return None

def send_message(message):
    try:
        # 將消息轉換為 JSON 並編碼
        encoded_content = json.dumps(message).encode('utf-8')
        
        # 準備長度資訊
        encoded_length = struct.pack('=I', len(encoded_content))
        
        # 寫入長度
        sys.stdout.buffer.write(encoded_length)
        sys.stdout.buffer.flush()
        
        # 寫入消息內容
        sys.stdout.buffer.write(encoded_content)
        sys.stdout.buffer.flush()
        
        logging.info(f'Sent message: {message}')
    except Exception as e:
        logging.error(f'Error in send_message: {str(e)}')
        logging.error(traceback.format_exc())

def main():
    logging.info('=== Script started ===')
    logging.info(f'Running as admin: {is_admin()}')
    logging.info(f'Current working directory: {os.getcwd()}')
    logging.info(f'Python executable: {sys.executable}')
    
    try:
        while True:  # 持續運行直到收到退出信號
            message = get_message()
            if message is None:
                logging.info('No more messages, exiting')
                break
                
            logging.info(f'Processing message: {message}')
            
            try:
                # 從消息中獲取參數
                chat_name = message.get('chatName', 'Group Chat Name')
                owner_email = message.get('ownerEmail', 'howteoh@realtek.com')
                member_emails = message.get('memberEmails', ['teamsmm001@realtek.com'])
                
                logging.info(f'Creating chat with name: {chat_name}, owner: {owner_email}, members: {member_emails}')
                
                # 調用 create_teams_chat
                result = create_teams_chat.main(chat_name, owner_email, member_emails)
                
                if result:
                    response = {
                        "success": True,
                        "message": "Chat created successfully",
                        "result": result
                    }
                else:
                    response = {
                        "success": False,
                        "message": "Failed to create chat"
                    }
                
            except Exception as e:
                logging.error(f'Error creating chat: {str(e)}')
                logging.error(traceback.format_exc())
                response = {
                    "success": False,
                    "message": f"Error: {str(e)}"
                }
            
            send_message(response)
            logging.info('Response sent successfully')
            
    except Exception as e:
        error_msg = f'Critical error in main: {str(e)}'
        logging.error(error_msg)
        logging.error(traceback.format_exc())
        try:
            send_message({"success": False, "message": str(e)})
        except:
            logging.error('Failed to send error message')

if __name__ == '__main__':
    try:
        main()
        logging.info('=== Script completed normally ===')
    except Exception as e:
        logging.error(f'=== Script failed: {str(e)} ===')
        logging.error(traceback.format_exc()) 