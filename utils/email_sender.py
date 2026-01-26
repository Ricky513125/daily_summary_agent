"""邮件发送模块"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Optional
from utils.logger import logger


class EmailSender:
    """邮件发送器"""
    
    def __init__(self, smtp_server: str, smtp_port: int, 
                 sender_email: str, sender_password: str):
        """
        初始化邮件发送器
        
        Args:
            smtp_server: SMTP服务器地址
            smtp_port: SMTP端口
            sender_email: 发件人邮箱
            sender_password: 发件人密码（或授权码）
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.logger = logger.bind(module="email_sender")
    
    def send_summary(
        self,
        receiver_emails: List[str],
        subject: str,
        content: str,
        attachments: Optional[List[str]] = None
    ) -> bool:
        """
        发送总结邮件
        
        Args:
            receiver_emails: 收件人邮箱列表
            subject: 邮件主题
            content: 邮件正文（支持HTML）
            attachments: 附件路径列表
        
        Returns:
            bool: 是否发送成功
        """
        try:
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(receiver_emails)
            msg['Subject'] = subject
            
            # 添加正文
            msg.attach(MIMEText(content, 'html', 'utf-8'))
            
            # 添加附件
            if attachments:
                for file_path in attachments:
                    self._attach_file(msg, file_path)
            
            # 连接SMTP服务器并发送
            self.logger.info(f"连接SMTP服务器: {self.smtp_server}:{self.smtp_port}")
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            self.logger.info(f"邮件发送成功: {receiver_emails}")
            return True
            
        except Exception as e:
            self.logger.error(f"邮件发送失败: {e}", exc_info=True)
            return False
    
    def _attach_file(self, msg: MIMEMultipart, file_path: str):
        """添加附件"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                self.logger.warning(f"附件不存在: {file_path}")
                return
            
            with open(file_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename={file_path.name}'
            )
            msg.attach(part)
            
            self.logger.debug(f"添加附件: {file_path.name}")
            
        except Exception as e:
            self.logger.error(f"添加附件失败 {file_path}: {e}")
    
    def send_text_email(
        self,
        receiver_emails: List[str],
        subject: str,
        text_content: str
    ) -> bool:
        """
        发送纯文本邮件
        
        Args:
            receiver_emails: 收件人邮箱列表
            subject: 邮件主题
            text_content: 邮件正文（纯文本）
        
        Returns:
            bool: 是否发送成功
        """
        try:
            msg = MIMEText(text_content, 'plain', 'utf-8')
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(receiver_emails)
            msg['Subject'] = subject
            
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            self.logger.info(f"纯文本邮件发送成功: {receiver_emails}")
            return True
            
        except Exception as e:
            self.logger.error(f"纯文本邮件发送失败: {e}", exc_info=True)
            return False


def markdown_to_html(markdown_content: str) -> str:
    """
    将Markdown转换为HTML（简单版本）
    
    如果需要更完整的转换，建议安装 markdown 库
    """
    try:
        import markdown
        return markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])
    except ImportError:
        # 如果没有 markdown 库，做简单的转换
        html = markdown_content
        html = html.replace('\n## ', '\n<h2>').replace('\n', '</h2>\n', 1)
        html = html.replace('\n### ', '\n<h3>').replace('\n', '</h3>\n', 1)
        html = html.replace('\n# ', '\n<h1>').replace('\n', '</h1>\n', 1)
        html = html.replace('\n\n', '<br><br>')
        html = f'<div style="font-family: Arial, sans-serif; line-height: 1.6;">{html}</div>'
        return html
