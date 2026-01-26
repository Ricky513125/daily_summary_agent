#!/usr/bin/env python
"""测试邮件配置"""
from config import *
from utils.email_sender import EmailSender
from datetime import datetime

def test_email():
    print("=" * 60)
    print("邮件配置测试")
    print("=" * 60)
    print(f"SMTP服务器: {SMTP_SERVER}")
    print(f"SMTP端口: {SMTP_PORT}")
    print(f"发件人: {SENDER_EMAIL}")
    print(f"收件人: {RECEIVER_EMAILS}")
    print("=" * 60)
    
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("❌ 错误：未配置发件人邮箱或密码")
        print("\n请在 .env 文件中配置:")
        print("SENDER_EMAIL=your_email@gmail.com")
        print("SENDER_PASSWORD=your_password")
        return False
    
    if not RECEIVER_EMAILS:
        print("❌ 错误：未配置收件人邮箱")
        print("\n请在 .env 文件中配置:")
        print("RECEIVER_EMAILS=receiver@example.com")
        return False
    
    try:
        sender = EmailSender(SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD)
        
        print("\n正在发送测试邮件...")
        result = sender.send_text_email(
            receiver_emails=RECEIVER_EMAILS,
            subject=f'测试邮件 - Daily Summary Agent - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            text_content=f'''这是一封测试邮件。

如果您收到这封邮件，说明邮件配置成功！

配置信息：
- SMTP服务器: {SMTP_SERVER}
- SMTP端口: {SMTP_PORT}
- 发件人: {SENDER_EMAIL}
- 测试时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

接下来您可以运行完整任务：
python main_v3.py

或启动定时任务：
python scheduler_v3.py

Daily Summary Agent V3
'''
        )
        
        if result:
            print("\n" + "=" * 60)
            print("✅ 邮件发送成功！")
            print("=" * 60)
            print(f"请检查收件箱: {', '.join(RECEIVER_EMAILS)}")
            print("注意：邮件可能在垃圾邮件文件夹中")
            print("\n接下来可以：")
            print("1. 运行完整任务: python main_v3.py")
            print("2. 启动定时任务: python scheduler_v3.py")
            return True
        else:
            print("\n" + "=" * 60)
            print("❌ 邮件发送失败")
            print("=" * 60)
            print("请检查日志文件: logs/agent.log")
            print("\n常见问题：")
            print("- Gmail: 需要使用应用专用密码（不是登录密码）")
            print("- QQ邮箱: 需要使用授权码（不是登录密码）")
            print("- 163邮箱: 需要使用授权密码")
            print("\n详细配置指南: EMAIL_SETUP_GUIDE.md")
            return False
            
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        print("\n请检查:")
        print("1. SMTP服务器地址和端口是否正确")
        print("2. 邮箱和密码是否正确")
        print("3. 网络连接是否正常")
        print("4. 防火墙是否阻止SMTP端口")
        return False

if __name__ == "__main__":
    success = test_email()
    exit(0 if success else 1)
