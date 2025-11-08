import asyncio
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from mail_tm_client import MailTMWrapper
from fake_data import generate_creative_username
from faker import Faker
from check_email import check_email


class AssocManager:
    """Manages adding email aliases (assocs) to Microsoft accounts"""
    
    def __init__(self, page, config):
        self.page = page
        self.config = config
        self.mail_client = None
        
    async def add_assocs(self, num_aliases=2):
        """
        Add multiple email aliases to the Microsoft account.
        
        Args:
            num_aliases: Number of aliases to add (default: 2)
        """
        print(f"\n{'='*80}")
        print(f"ADDING EMAIL ALIASES (ASSOCS)")
        print(f"{'='*80}\n")
        
        # Navigate to Add Assoc page
        print("Navigating to Add Assoc page...")
        await self.page.goto('https://account.live.com/AddAssocId', wait_until='domcontentloaded')
        await asyncio.sleep(2)
        
        # Create temporary email for verification
        self.mail_client = MailTMWrapper()
        temp_email = await self.mail_client.create_account()
        
        # Step 1: Enter temporary email address
        print("\nStep 1: Entering temporary email for verification...")
        await self._enter_email(temp_email)
        
        # Step 2: Click Next button
        print("Step 2: Clicking Next button...")
        await self._click_next_button()
        await asyncio.sleep(3)
        
        # Step 3: Wait for and enter security code
        print("\nStep 3: Waiting for security code email...")
        security_code = await self.mail_client.wait_for_security_code(timeout=120)
        
        if not security_code:
            print("Failed to receive security code. Cannot continue.")
            return False
        
        print(f"Entering security code: {security_code}")
        await self._enter_security_code(security_code)
        
        # Step 4: Click Next button after code
        print("\nStep 4: Clicking Next after security code...")
        await self._click_next_button()
        await asyncio.sleep(3)
        
        # Step 4.5: Check for frame button #id__0 (sometimes appears)
        print("\nStep 4.5: Checking for frame button #id__0...")
        frame_clicked = await self._check_and_click_frame_button()
        if frame_clicked:
            print("Frame button #id__0 clicked")
            await asyncio.sleep(2)
        
        # Step 4.6: Check for "stay logged" button in frame (sometimes appears after 4.5)
        print("\nStep 4.6: Checking for 'stay logged' button in frame...")
        stay_logged_clicked = await self._check_and_click_stay_logged_button()
        if stay_logged_clicked:
            print("Stay logged button clicked")
            await asyncio.sleep(2)
        
        # Step 5: Check for Accept button and click if present
        print("\nStep 5: Checking for Accept button...")
        accepted = await self._check_and_accept()
        if accepted:
            print("Accept button clicked")
            await asyncio.sleep(2)
        
        # Now add the aliases
        aliases_added = []
        for i in range(num_aliases):
            print(f"\n{'='*80}")
            print(f"ADDING ALIAS {i+1}/{num_aliases}")
            print(f"{'='*80}\n")
            
            alias = await self._add_single_alias()
            if alias:
                aliases_added.append(alias)
                print(f"✓ Successfully added alias: {alias}")
                
                # If not the last one, click to add another (only if previous was successful)
                if i < num_aliases - 1:
                    print("\nPreparing to add next alias...")
                    await self._click_add_alias_link()
                    await asyncio.sleep(2)
            else:
                print(f"✗ Failed to add alias {i+1}")
                # Don't try to add next alias if current one failed
        
        print(f"\n{'='*80}")
        print(f"ALIAS ADDITION COMPLETE")
        print(f"{'='*80}")
        print(f"Aliases added: {len(aliases_added)}/{num_aliases}")
        for idx, alias in enumerate(aliases_added, 1):
            print(f"  {idx}. {alias}")
        print(f"{'='*80}\n")
        
        # Return aliases and MailTM credentials
        return {
            'aliases': aliases_added,
            'mailtm_email': self.mail_client.email,
            'mailtm_password': self.mail_client.password
        }
    
    async def _enter_email(self, email):
        """Step 1: Enter email address in the input field"""
        try:
            await self.page.wait_for_selector('#EmailAddress', timeout=10000)
            await self.page.fill('#EmailAddress', email)
            await asyncio.sleep(1)
        except PlaywrightTimeoutError:
            print("Could not find email input field #EmailAddress")
            raise
    
    async def _click_next_button(self):
        """Step 2 & 4: Click the Next button (#iNext)"""
        try:
            await self.page.wait_for_selector('#iNext', timeout=10000)
            await self.page.click('#iNext')
            await asyncio.sleep(1)
        except PlaywrightTimeoutError:
            print("Could not find Next button #iNext")
            raise
    
    async def _enter_security_code(self, code):
        """Step 3: Enter the security code received via email"""
        try:
            await self.page.wait_for_selector('#iOttText', timeout=10000)
            await self.page.fill('#iOttText', code)
            await asyncio.sleep(1)
        except PlaywrightTimeoutError:
            print("Could not find security code input #iOttText")
            raise
    
    async def _check_and_click_frame_button(self):
        """Step 4.5: Check if frame button #id__0 exists and click it"""
        try:
            frame_button = await self.page.wait_for_selector('#id__0', timeout=5000)
            if frame_button:
                await self.page.click('#id__0')
                return True
        except PlaywrightTimeoutError:
            # Frame button not present, that's okay
            return False
        return False
    
    async def _check_and_click_stay_logged_button(self):
        """Step 4.6: Check if 'stay logged' button button[data-testid="primaryButton"] exists and click it"""
        try:
            button = await self.page.wait_for_selector('button[data-testid="primaryButton"]', timeout=5000)
            if button:
                await self.page.click('button[data-testid="primaryButton"]')
                return True
        except PlaywrightTimeoutError:
            # Button not present, that's okay
            return False
        except Exception as e:
            print(f"Error checking for stay logged button: {e}")
            return False
    
    async def _check_and_accept(self):
        """Step 5: Check if Accept button exists and click it"""
        try:
            accept_button = await self.page.wait_for_selector('#acceptButton', timeout=5000)
            if accept_button:
                await self.page.click('#acceptButton')
                return True
        except PlaywrightTimeoutError:
            # Accept button not present, that's okay
            return False
        return False
    
    async def _add_single_alias(self):
        """
        Steps 6-7: Generate and add a single alias.
        
        Returns:
            str: The alias that was added (with @outlook.com) or None if failed
        """
        # Step 6: Generate new alias username and check availability
        fake = Faker()
        alias_available = False
        alias_username = None
        
        while not alias_available:
            first_name = fake.first_name()
            last_name = fake.last_name()
            alias_username = generate_creative_username(first_name, last_name)
            
            # Check availability (only @outlook.com for aliases)
            alias_email = f"{alias_username}@outlook.com"
            print(f"Step 6: Checking availability for alias: {alias_email}")
            
            email_check_result = check_email(alias_email)
            if email_check_result.get('isAvailable'):
                print(f"✓ {alias_email} is available")
                alias_available = True
            else:
                print(f"✗ {alias_email} is not available. Generating new alias...")
        
        try:
            # Wait for the alias input field
            await self.page.wait_for_selector('#AssociatedIdLive', timeout=10000)
            
            # Enter the alias (without @outlook.com)
            await self.page.fill('#AssociatedIdLive', alias_username)
            print(f"Entered alias: {alias_username}")
            await asyncio.sleep(1)
            
            # Step 7: Click Submit button
            print("Step 7: Clicking Submit button...")
            await self.page.wait_for_selector('#SubmitYes', timeout=10000)
            await self.page.click('#SubmitYes')
            await asyncio.sleep(2)
            
            # The presence of #idAddAliasLink confirms that the alias was successfully added
            print("Step 7.5: Waiting for confirmation that alias was added...")
            try:
                await self.page.wait_for_selector('#idAddAliasLink', timeout=10000)
                print("✓ Confirmation: #idAddAliasLink found - alias successfully added!")
                return f"{alias_username}@outlook.com"
            except PlaywrightTimeoutError:
                print("✗ Confirmation failed: #idAddAliasLink not found - alias may not have been added")
                return None
            
        except PlaywrightTimeoutError as e:
            print(f"Timeout while adding alias: {e}")
            return None
        except Exception as e:
            print(f"Error adding alias: {e}")
            return None
    
    async def _click_add_alias_link(self):
        """Step 8: Click the 'Add new alias' link to add another"""
        try:
            # Wait for the link without clicking yet (as per step 8 - half-step)
            await self.page.wait_for_selector('#idAddAliasLink', timeout=10000)
            print("Found 'Add new alias' link")
            
            # Now click it
            await self.page.click('#idAddAliasLink')
            await asyncio.sleep(1)
        except PlaywrightTimeoutError:
            print("Could not find 'Add new alias' link #idAddAliasLink")
            raise
