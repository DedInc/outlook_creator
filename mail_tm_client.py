import asyncio
import re
from mailtm import MailTMClient
from selectolax.parser import HTMLParser


class MailTMWrapper:
    """Wrapper for MailTM to handle temporary email for Microsoft verification"""
    
    def __init__(self):
        self.client = None
        self.email = None
        self.password = "TempPass123!"
        
    async def create_account(self):
        """Create a temporary email account"""
        try:
            # Fetch available domains
            domains = MailTMClient.get_domains()
            
            if not domains:
                raise Exception("No MailTM domains available")
            
            # Generate a random email using first domain
            import random
            import string
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
            self.email = f"{username}@{domains[0].domain}"
            
            # Create account and initialize client
            account = MailTMClient.create_account(
                address=self.email,
                password=self.password
            )
            
            # Initialize the MailTMClient with credentials
            self.client = MailTMClient(account=self.email, password=self.password)
            
            print(f"Created temporary email: {self.email}")
            return self.email
            
        except Exception as e:
            print(f"Error creating MailTM account: {e}")
            raise
    
    async def wait_for_security_code(self, timeout=120):
        """
        Wait for Microsoft security code email and extract the code.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            str: The security code (6 digits) or None if not found
        """
        print(f"Waiting for security code email (timeout: {timeout}s)...")
        
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                # Get messages
                messages = self.client.get_messages()
                
                for message in messages:
                    # Check if it's from Microsoft
                    if "microsoft" in message.from_.address.lower():
                        print(f"Found email from: {message.from_.address}")
                        print(f"Subject: {message.subject}")
                        
                        # Get the full message content
                        message_source = self.client.get_message_source(message.id)
                        html_content = message_source.data
                        
                        # Parse HTML to extract security code
                        code = self._extract_security_code(html_content)
                        
                        if code:
                            print(f"✓ Security code extracted: {code}")
                            return code
                        else:
                            print("Could not extract code from email, trying to parse differently...")
                            # Try alternative parsing
                            code = self._extract_code_alternative(html_content)
                            if code:
                                print(f"✓ Security code extracted (alternative): {code}")
                                return code
                
                # Wait before checking again
                await asyncio.sleep(3)
                
            except Exception as e:
                print(f"Error checking messages: {e}")
                await asyncio.sleep(3)
        
        print("Timeout: No security code received")
        return None
    
    def _extract_security_code(self, html_content):
        """
        Extract security code from Microsoft email HTML.
        
        Based on the example in impl_assocs.md:
        Security code: <span style="...">902829</span>
        """
        try:
            parser = HTMLParser(html_content)
            
            # Get text content
            text_content = parser.text()
            
            # Pattern: "Security code: XXXXXX" where X is digit
            match = re.search(r'Security code:\s*(\d{6})', text_content)
            if match:
                return match.group(1)
            
            # Alternative: Look for 6-digit code in bold/strong tags
            for tag_name in ['span', 'strong', 'b']:
                nodes = parser.css(tag_name)
                for node in nodes:
                    text = node.text().strip()
                    if re.match(r'^\d{6}$', text):
                        return text
            
            return None
            
        except Exception as e:
            print(f"Error parsing HTML: {e}")
            return None
    
    def _extract_code_alternative(self, html_content):
        """Alternative method to extract code using regex on raw HTML"""
        try:
            # Look for 6-digit codes in the HTML
            matches = re.findall(r'\b(\d{6})\b', html_content)
            
            # Filter out common false positives (like years, etc.)
            for match in matches:
                # Security codes are typically not starting with 19, 20 (years)
                if not match.startswith('19') and not match.startswith('20'):
                    return match
            
            return None
            
        except Exception as e:
            print(f"Error in alternative parsing: {e}")
            return None
