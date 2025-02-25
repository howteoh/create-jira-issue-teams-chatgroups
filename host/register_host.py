import os
import sys
import winreg
import json

def register_host():
    # 獲取當前腳本的絕對路徑
    host_path = os.path.abspath(os.path.dirname(__file__))
    manifest_path = os.path.join(host_path, "com.realtek.teams_chat.json")
    
    # 讀取 manifest 檔案
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    # 註冊表路徑
    registry_locations = {
        'chrome': r'SOFTWARE\Google\Chrome\NativeMessagingHosts',
        'chrome-beta': r'SOFTWARE\Google\Chrome Beta\NativeMessagingHosts',
        'chrome-dev': r'SOFTWARE\Google\Chrome Dev\NativeMessagingHosts',
        'chrome-canary': r'SOFTWARE\Google\Chrome SxS\NativeMessagingHosts'
    }
    
    for browser, registry_location in registry_locations.items():
        try:
            # 創建或打開註冊表鍵
            with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, registry_location) as root_key:
                # 創建子鍵
                with winreg.CreateKey(root_key, manifest['name']) as key:
                    # 設置 manifest 路徑
                    winreg.SetValue(key, '', winreg.REG_SZ, manifest_path)
            print(f"Successfully registered host for {browser}")
        except Exception as e:
            print(f"Failed to register host for {browser}: {str(e)}")

if __name__ == '__main__':
    try:
        register_host()
        print("Host registration completed successfully!")
    except Exception as e:
        print(f"Error registering host: {str(e)}")
        sys.exit(1) 