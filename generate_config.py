"""
首次設定工具 — 執行一次即可產生 config.yaml
使用方式：python generate_config.py
"""
import yaml
import bcrypt
import secrets
import getpass

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()

def main():
    print("=== 超市銷售儀表板 — 帳號設定工具 ===\n")
    print("請輸入要建立的使用者帳號（輸入空白 username 結束）\n")

    users = {}
    while True:
        username = input("帳號（英文，例如 admin）: ").strip()
        if not username:
            break
        name = input(f"  {username} 的顯示名稱: ").strip()
        email = input(f"  {username} 的電子郵件: ").strip()
        password = getpass.getpass(f"  {username} 的密碼: ")
        hashed = hash_password(password)
        users[username] = {"email": email, "name": name, "password": hashed}
        print(f"  ✓ 帳號 '{username}' 已新增\n")

    if not users:
        print("未新增任何帳號，程式結束。")
        return

    cookie_key = secrets.token_hex(16)
    config = {
        "credentials": {"usernames": users},
        "cookie": {
            "expiry_days": 30,
            "key": cookie_key,
            "name": "supermarket_dashboard_auth",
        },
    }

    with open("config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    print("✓ config.yaml 已成功產生！")
    print("  記得將 config.yaml 加入 .gitignore（已預設加入）。")
    print("\n現在可以執行：streamlit run app.py")

if __name__ == "__main__":
    main()
