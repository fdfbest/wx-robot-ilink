import requests
import time
import json
import os

CREDENTIALS_FILE = "credentials.json"

# 尝试加载已保存的凭证
token = None
bot_id = None
user_id = None
base_url = "https://ilinkai.weixin.qq.com"

if os.path.exists(CREDENTIALS_FILE):
    print("发现已保存的凭证，正在验证...")
    with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
        saved = json.load(f)
    
    token = saved.get("token")
    bot_id = saved.get("bot_id")
    user_id = saved.get("user_id")
    base_url = saved.get("base_url", "https://ilinkai.weixin.qq.com")
    
    # 测试token是否有效（HTTP 200即有效）
    test_resp = requests.post(
        f"{base_url}/ilink/bot/getupdates",
        headers={
            "Content-Type": "application/json",
            "AuthorizationType": "ilink_bot_token",
            "Authorization": f"Bearer {token}"
        },
        json={"get_updates_buf": ""}
    )
    
    if test_resp.status_code == 200:
        print("[OK] Token 有效，跳过扫码登录")
        print(f"\n===== 已加载凭证 =====")
        print(f"Token: {token}")
        print(f"Bot ID: {bot_id}")
        print(f"User ID: {user_id}")
        print(f"Base URL: {base_url}")
    else:
        print(f"[FAIL] Token 无效 (HTTP {test_resp.status_code})，需要重新登录")
        token = None
else:
    print("未找到已保存的凭证")

# 如果token无效，重新扫码登录
if not token:
    # 第一步：获取二维码
    print("\n正在获取二维码...")
    qr_resp = requests.get("https://ilinkai.weixin.qq.com/ilink/bot/get_bot_qrcode?bot_type=3")
    qr_data = qr_resp.json()
    
    qrcode = qr_data["qrcode"]
    qrcode_url = qr_data["qrcode_img_content"]
    
    print(f"二维码字符串: {qrcode}")
    print(f"二维码链接: {qrcode_url}")
    print("请用微信扫码...")
    
    # 第二步：轮询二维码状态
    print("等待扫码确认...")
    while True:
        time.sleep(1)
        
        status_resp = requests.get(
            f"https://ilinkai.weixin.qq.com/ilink/bot/get_qrcode_status?qrcode={qrcode}",
            headers={"iLink-App-ClientVersion": "1"}
        )
        status_data = status_resp.json()
        
        current_status = status_data["status"]
        print(f"当前状态: {current_status}")
        
        if current_status == "scaned":
            print("已扫码，请在手机上确认...")
        elif current_status == "confirmed":
            print("登录成功！")
            break
        elif current_status == "expired":
            print("二维码已过期，请重新运行脚本")
            exit()
    
    # 第三步：获取 token 和用户ID
    token = status_data["bot_token"]
    bot_id = status_data["ilink_bot_id"]
    user_id = status_data["ilink_user_id"]
    base_url = status_data.get("baseurl", "https://ilinkai.weixin.qq.com")
    
    print(f"\n===== 登录凭证 =====")
    print(f"Token: {token}")
    print(f"Bot ID: {bot_id}")
    print(f"User ID: {user_id}")
    print(f"Base URL: {base_url}")

# 第四步：等待用户发送消息（仅在没有user_id时）
if not user_id:
    print("\n请在微信中给机器人发送一条任意消息...")
    get_updates_buf = ""
    while True:
        time.sleep(1)
        
        updates_resp = requests.post(
            f"{base_url}/ilink/bot/getupdates",
            headers={
                "Content-Type": "application/json",
                "AuthorizationType": "ilink_bot_token",
                "Authorization": f"Bearer {token}"
            },
            json={"get_updates_buf": get_updates_buf}
        )
        updates_data = updates_resp.json()
        
        if updates_data.get("get_updates_buf"):
            get_updates_buf = updates_data["get_updates_buf"]
        
        messages = updates_data.get("msgs", [])
        for msg in messages:
            if msg.get("message_type") == 1:  # 1 = 用户消息
                from_user = msg.get("from_user_id", "")
                if from_user:
                    print(f"收到消息，来自: {from_user}")
                    user_id = from_user
                    break
        
        if user_id:
            break
        
        print("等待用户发送消息...")
else:
    print(f"\n已加载用户ID: {user_id}")

# 保存凭证
credentials = {
    "token": token,
    "bot_id": bot_id,
    "user_id": user_id,
    "base_url": base_url
}
with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
    json.dump(credentials, f, ensure_ascii=False, indent=2)
print(f"\n凭证已保存到 {CREDENTIALS_FILE}")

# 第五步：发送测试消息
print("\n正在推送测试消息...")
test_body = {
    "msg": {
        "from_user_id": "",
        "to_user_id": user_id,
        "client_id": f"bot-{int(time.time())}-pytest",
        "message_type": 2,
        "message_state": 2,
        "item_list": [
            {
                "type": 1,
                "text_item": {
                    "text": "测试消息：Python脚本获取token成功！"
                }
            }
        ]
    }
}

test_headers = {
    "Content-Type": "application/json",
    "AuthorizationType": "ilink_bot_token",
    "Authorization": f"Bearer {token}",
    "X-WECHAT-UIN": "MTIzNDU2Nzg="
}

test_resp = requests.post(
    f"{base_url}/ilink/bot/sendmessage",
    headers=test_headers,
    json=test_body
)

print(f"推送响应: {test_resp.status_code}")
print("测试完成！")
