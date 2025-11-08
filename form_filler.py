import asyncio
import random
import os
import time
import aiofiles
import numpy as np
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from fake_data import generate_fake_data
from check_email import check_email
from excel_logger import append_account


class SignupFormFiller:
    """Handles the Outlook signup form filling process"""

    def __init__(self, page, config):
        self.page = page
        self.config = config
        self.api_key = config.get('api_key', '')

        # Create a unique "personality" for this session to vary behavior
        # This makes each bot instance behave slightly differently
        self.typing_speed_factor = random.uniform(0.7, 1.4)  # Some people type faster/slower
        self.mistake_probability = random.uniform(0.02, 0.08)  # 2-8% chance of mistakes
        self.distraction_probability = random.uniform(0.05, 0.15)  # 5-15% chance of distraction
        self.patience_level = random.uniform(0.8, 1.3)  # Affects how long they wait
        self.mouse_precision = random.uniform(0.2, 0.8)  # How precisely they click

        # Track session state for more realistic behavior
        self.actions_count = 0
        self.last_mistake_action = -10  # Don't make mistakes too frequently

    def _gaussian_delay(self, min_val, max_val, skew=0):
        """
        Generate more human-like delay using normal distribution instead of uniform.
        Humans tend to cluster around average times, not uniformly distributed.

        Args:
            min_val: Minimum value
            max_val: Maximum value
            skew: Skew the distribution (-1 to 1, negative = faster, positive = slower)
        """
        mean = (min_val + max_val) / 2
        # Standard deviation is about 1/6 of range (99.7% within range by 3-sigma rule)
        std = (max_val - min_val) / 6

        # Apply skew
        if skew != 0:
            mean += (max_val - min_val) * skew * 0.2

        # Generate value from normal distribution
        value = np.random.normal(mean, std)

        # Clamp to range
        return max(min_val, min(max_val, value))

    async def human_delay(self, min_seconds=0.5, max_seconds=2.0, delay_type="normal"):
        """
        Generate human-like delays with various patterns using realistic distributions.

        Args:
            min_seconds: Minimum delay time
            max_seconds: Maximum delay time
            delay_type: Type of delay pattern ("normal", "thinking", "reading", "typing")
        """
        # Apply personality patience factor
        min_seconds *= self.patience_level
        max_seconds *= self.patience_level

        if delay_type == "thinking":
            # Longer pauses that simulate thinking - use gaussian distribution
            delay = self._gaussian_delay(1.0, 4.0, skew=0.3)
        elif delay_type == "reading":
            # Medium pauses for reading content
            delay = self._gaussian_delay(0.8, 2.5, skew=0.1)
        elif delay_type == "typing":
            # Short pauses between keystrokes
            delay = self._gaussian_delay(0.05, 0.2)
        else:
            # Normal interaction delay
            delay = self._gaussian_delay(min_seconds, max_seconds)

        # Add occasional longer pauses to simulate distraction (varies by personality)
        if random.random() < self.distraction_probability:
            # Distraction length varies - sometimes brief, sometimes long
            distraction_types = [
                (0.3, 0.8, 0.5),   # Brief distraction (50% chance)
                (0.8, 2.0, 0.3),   # Medium distraction (30% chance)
                (2.0, 5.0, 0.15),  # Long distraction (15% chance)
                (5.0, 10.0, 0.05), # Very long distraction (5% chance)
            ]

            for min_d, max_d, prob in distraction_types:
                if random.random() < prob:
                    delay += self._gaussian_delay(min_d, max_d)
                    break

        await asyncio.sleep(delay)

    async def human_type(self, selector, text, use_fill=False):
        """
        Type text in a human-like manner with variable speed and occasional mistakes.

        Args:
            selector: The element selector to type into
            text: The text to type
            use_fill: If True, use fill() instead of type() for speed (less human-like)
        """
        self.actions_count += 1

        if use_fill or len(text) > 30:
            # For long text or when speed is preferred, use fill but add delays
            await self.page.fill(selector, text)
            await self.human_delay(0.3, 0.8, "typing")
        else:
            # Type character by character with variable speed
            await self.page.click(selector)
            await self.human_delay(0.1, 0.3)

            for i, char in enumerate(text):
                # Variable typing speed based on personality and character
                base_delay = self._gaussian_delay(50, 150) * self.typing_speed_factor

                # Some characters are harder to type (shift keys, numbers, special chars)
                if char.isupper() or char.isdigit() or not char.isalnum():
                    base_delay *= random.uniform(1.1, 1.4)

                await self.page.type(selector, char, delay=base_delay)

                # Occasional longer pauses (simulate thinking or looking at keyboard)
                # Less likely if we just made a mistake
                if random.random() < 0.08 and (self.actions_count - self.last_mistake_action) > 3:
                    await self.human_delay(0.2, 0.6, "thinking")

                # Make mistakes based on personality, but not too frequently
                should_make_mistake = (
                    random.random() < self.mistake_probability and
                    i < len(text) - 1 and
                    (self.actions_count - self.last_mistake_action) > 5  # At least 5 actions since last mistake
                )

                if should_make_mistake:
                    self.last_mistake_action = self.actions_count

                    # Different types of mistakes
                    mistake_type = random.random()

                    if mistake_type < 0.6:
                        # Type wrong character (most common) - use nearby keys
                        keyboard_neighbors = {
                            'a': 'sqwz', 'b': 'vghn', 'c': 'xdfv', 'd': 'sfcxe', 'e': 'wrds',
                            'f': 'dgcvrt', 'g': 'fhbvty', 'h': 'gjnbyu', 'i': 'ujko', 'j': 'hknmu',
                            'k': 'jlmio', 'l': 'kop', 'm': 'njk', 'n': 'bhjm', 'o': 'iklp',
                            'p': 'ol', 'q': 'wa', 'r': 'etfd', 's': 'awedxz', 't': 'ryfg',
                            'u': 'yihj', 'v': 'cfgb', 'w': 'qase', 'x': 'zsdc', 'y': 'tugh',
                            'z': 'asx'
                        }

                        next_char = text[i+1] if i+1 < len(text) else char
                        # Sometimes type the next character early, sometimes a neighbor key
                        if random.random() < 0.4 and next_char.isalpha():
                            wrong_char = next_char.lower()
                        else:
                            neighbors = keyboard_neighbors.get(char.lower(), 'abcdefghijklmnopqrstuvwxyz')
                            wrong_char = random.choice(neighbors)

                        await self.page.type(selector, wrong_char, delay=self._gaussian_delay(50, 100))

                        # Reaction time - notice the mistake
                        await self.human_delay(0.1, 0.4)

                        # Delete it (sometimes delete multiple times if "panicked")
                        backspaces = 1 if random.random() < 0.9 else 2
                        for _ in range(backspaces):
                            await self.page.press(selector, 'Backspace')
                            await self.human_delay(0.05, 0.15)

                    elif mistake_type < 0.85:
                        # Double-type a character (25% of mistakes)
                        await self.page.type(selector, char, delay=self._gaussian_delay(30, 80))
                        await self.human_delay(0.1, 0.3)
                        await self.page.press(selector, 'Backspace')
                        await self.human_delay(0.05, 0.15)

                    else:
                        # Skip a character then go back (15% of mistakes)
                        # Skip current, type next, then backspace and fix
                        if i + 1 < len(text):
                            next_char = text[i + 1]
                            await self.page.type(selector, next_char, delay=self._gaussian_delay(50, 100))
                            await self.human_delay(0.15, 0.35)
                            await self.page.press(selector, 'Backspace')
                            await self.human_delay(0.05, 0.15)
                            # Now type the correct character (will be typed in next iteration)

            await self.human_delay(0.2, 0.5)

    async def human_click(self, selector, force=False):
        """
        Click an element with human-like behavior.
        Camoufox's humanize=True handles mouse movement automatically.

        Args:
            selector: The element selector to click
            force: Whether to force the click
        """
        self.actions_count += 1

        # Small delay before clicking (simulating decision time)
        await self.human_delay(0.2, 0.6)

        # Camoufox with humanize=True will automatically add realistic mouse movement
        # We just need to click - it handles the rest
        await self.page.click(selector, force=force)

        # Vary post-click delay
        await self.human_delay(0.3, 0.7)

    async def random_mouse_movement(self):
        """
        Occasionally move mouse randomly to simulate natural behavior.
        Humans don't keep mouse perfectly still.
        Camoufox's humanize=True will make the movement realistic.
        """
        if random.random() < 0.3:  # 30% chance
            try:
                # Get viewport size
                viewport = self.page.viewport_size
                if viewport:
                    # Move to a random position (Camoufox will humanize the movement)
                    x = random.randint(100, viewport['width'] - 100)
                    y = random.randint(100, viewport['height'] - 100)
                    await self.page.mouse.move(x, y)
                    await asyncio.sleep(self._gaussian_delay(0.1, 0.3))
            except:
                pass

    async def occasional_idle(self):
        """
        Simulate occasional moments where user is idle (reading, thinking, distracted).
        This should be called between major actions.
        """
        # Vary idle behavior based on action count
        idle_chance = 0.15 if self.actions_count < 5 else 0.25  # More likely to pause as form progresses

        if random.random() < idle_chance:
            idle_type = random.random()

            if idle_type < 0.5:
                # Short pause - reading or thinking
                await self.human_delay(1.0, 3.0, "reading")
            elif idle_type < 0.8:
                # Medium pause - maybe checking something
                await self.human_delay(2.0, 5.0, "thinking")
                # Maybe move mouse during this time
                await self.random_mouse_movement()
            else:
                # Long pause - distracted or multitasking
                await self.human_delay(3.0, 8.0, "thinking")
                if random.random() < 0.5:
                    await self.random_mouse_movement()

    async def navigate_to_signup(self):
        """Navigate to Outlook signup page"""
        print("Navigating to Outlook signup page...")
        await self.page.goto('https://signup.live.com/signup', wait_until='domcontentloaded')

        # Wait for the actual form elements to appear instead of networkidle
        print("Waiting for signup form elements to load...")
        try:
            # Wait for either email input or the switch link
            await self.page.wait_for_selector('input[type="email"], #liveSwitch, #usernameInput', timeout=30000)
            print("Signup page loaded successfully")
        except PlaywrightTimeoutError:
            print("Warning: Signup form not detected quickly, but continuing...")

        # Human-like delay to simulate reading the page
        await self.human_delay(1.5, 3.5, "reading")

        # Sometimes move mouse while reading
        await self.random_mouse_movement()
        
    async def fill_email(self):
        """Fill email field and generate available email"""
        print("Waiting for email input field...")
        email_input_selector = None
        try:
            await self.page.wait_for_selector('input[type="email"]', timeout=30000)
            email_input_selector = 'input[type="email"]'
            print("Found input[type='email']")
        except PlaywrightTimeoutError:
            try:
                await self.page.wait_for_selector("#usernameInput", timeout=10000)
                email_input_selector = "#usernameInput"
                print("Found #usernameInput")
            except PlaywrightTimeoutError:
                await self.page.wait_for_selector('input[name="MemberName"]', timeout=10000)
                email_input_selector = 'input[name="MemberName"]'
                print("Found input[name='MemberName']")

        # Small delay before starting to type (simulate reading the field label)
        await self.human_delay(0.5, 1.2, "reading")

        # Generate fake data and check email availability
        email_available = False
        while not email_available:
            login, password, first_name, last_name, birth_date = generate_fake_data()
            # Randomly choose between @outlook.com and @hotmail.com for registration
            domain = random.choice(["@outlook.com", "@hotmail.com"])
            email = login + domain
            email_check_result = check_email(email)
            if email_check_result.get('isAvailable'):
                print(f"{email} is available, continuing with the registration process ...")
                email_available = True
            else:
                print(f"{email} is not available. Generating new email ...")

        # If the email is available, continue with the registration process
        print(f"Filling email input with: {email}")
        # Use human-like typing for email
        await self.human_type(email_input_selector, email, use_fill=True)

        return email, password, first_name, last_name, birth_date
        
    async def click_next_button(self, context=""):
        """Click the Next button with multiple selector fallbacks"""
        next_button_selector = None
        try:
            await self.page.wait_for_selector('button[data-testid="primaryButton"]', timeout=10000)
            next_button_selector = 'button[data-testid="primaryButton"]'
            print(f"Found Next button: button[data-testid='primaryButton'] {context}")
        except PlaywrightTimeoutError:
            try:
                await self.page.wait_for_selector("#nextButton", timeout=10000)
                next_button_selector = "#nextButton"
                print(f"Found Next button: #nextButton {context}")
            except PlaywrightTimeoutError:
                await self.page.wait_for_selector('button[type="submit"]', timeout=10000)
                next_button_selector = 'button[type="submit"]'
                print(f"Found Next button: button[type='submit'] {context}")

        # Use human-like click
        await self.human_click(next_button_selector)
        
    async def fill_password(self, password):
        """Fill password field"""
        print("Waiting for password field...")
        password_input_selector = None
        try:
            await self.page.wait_for_selector('input[type="password"]', timeout=10000)
            password_input_selector = 'input[type="password"]'
            print("Found password input: input[type='password']")
        except PlaywrightTimeoutError:
            await self.page.wait_for_selector("#Password", timeout=10000)
            password_input_selector = "#Password"
            print("Found password input: #Password")

        # Small delay before typing (simulate thinking about password)
        await self.human_delay(0.8, 1.8, "thinking")

        # Type the password into the input field with human-like behavior
        await self.human_type(password_input_selector, password, use_fill=True)
        
    async def fill_birth_date(self, birth_date):
        """Fill birth date fields"""
        # Month names mapping
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        # Small delay before interacting (simulate reading the form)
        await self.human_delay(0.4, 0.9, "reading")

        # Wait until the birth month dropdown is available
        try:
            # Try standard select element first
            await self.page.wait_for_selector('select[aria-label*="Month"]', timeout=5000)
            await self.human_delay(0.2, 0.5)
            await self.page.select_option('select[aria-label*="Month"]', str(birth_date.month))
            print("Selected birth month")
        except PlaywrightTimeoutError:
            # Try Fluent UI dropdown button
            await self.page.wait_for_selector('button[name="BirthMonth"]', timeout=5000)

            # Check if dropdown is already expanded
            is_expanded = await self.page.get_attribute('button[name="BirthMonth"]', 'aria-expanded')
            if is_expanded != 'true':
                # Click to open dropdown with human-like behavior
                await self.human_click('button[name="BirthMonth"]', force=True)
                # Wait for dropdown options to appear
                await self.page.wait_for_selector('[role="option"]', timeout=5000)

            # Get month name and click the option by text
            month_name = month_names[birth_date.month - 1]
            await self.human_delay(0.3, 0.7, "reading")
            await self.human_click(f'[role="option"]:has-text("{month_name}")')
            print(f"Selected birth month: {month_name}")

        # Human-like delay between fields
        await self.human_delay(0.4, 0.9)

        # Wait until the birth day dropdown is available
        try:
            # Try standard select element first
            await self.page.wait_for_selector('select[aria-label*="Day"]', timeout=5000)
            await self.human_delay(0.2, 0.5)
            await self.page.select_option('select[aria-label*="Day"]', str(birth_date.day))
            print("Selected birth day")
        except PlaywrightTimeoutError:
            # Try Fluent UI dropdown button
            await self.page.wait_for_selector('button[name="BirthDay"]', timeout=5000)

            # Check if dropdown is already expanded
            is_expanded = await self.page.get_attribute('button[name="BirthDay"]', 'aria-expanded')
            if is_expanded != 'true':
                # Click to open dropdown with human-like behavior
                await self.human_click('button[name="BirthDay"]', force=True)
                # Wait for dropdown options to appear
                await self.page.wait_for_selector('[role="option"]', timeout=5000)

            # Click the option by text (day number)
            await self.human_delay(0.2, 0.5, "reading")
            await self.human_click(f'[role="option"]:has-text("{birth_date.day}")')
            print(f"Selected birth day: {birth_date.day}")

        # Human-like delay between fields
        await self.human_delay(0.4, 0.9)

        # Wait until the birth year input field is available
        try:
            # Try aria-label first
            await self.page.wait_for_selector('input[aria-label*="Year"]', timeout=5000)
            await self.human_type('input[aria-label*="Year"]', str(birth_date.year))
            print("Filled birth year")
        except PlaywrightTimeoutError:
            # Try name attribute
            await self.page.wait_for_selector('input[name="BirthYear"]', timeout=5000)
            await self.human_type('input[name="BirthYear"]', str(birth_date.year))
            print("Filled birth year using name attribute")
        
    async def fill_name(self, first_name, last_name):
        """Fill first and last name fields"""
        try:
            # Wait for first name input
            await self.page.wait_for_selector('input[name="firstNameInput"]', timeout=10000)

            # Small delay before typing (simulate reading the field)
            await self.human_delay(0.5, 1.0, "reading")

            # Type first name with human-like behavior
            await self.human_type('input[name="firstNameInput"]', first_name)
            print(f"Filled first name: {first_name}")

            # Human-like delay between fields (moving to next field)
            await self.human_delay(0.5, 1.2)

            # Type last name with human-like behavior
            await self.human_type('input[name="lastNameInput"]', last_name)
            print(f"Filled last name: {last_name}")

            return True
        except PlaywrightTimeoutError:
            print("Name input fields not found, continuing...")
            return False
            
    async def check_for_block(self):
        """
        Check if Microsoft blocked the registration (shows block image).
        Returns True if blocked, False if OK to continue.
        """
        print('\nChecking for Microsoft block/ban...')

        try:
            # Check for the block verification image
            # Multiple selectors to catch different variations
            block_selectors = [
                'img[src*="block_verify"]',
                'img[data-testid="accessibleImg"][src*="block"]',
                'img[alt=""][src*="logincdn.msftauth.net"]',
            ]

            for selector in block_selectors:
                block_img = await self.page.query_selector(selector)
                if block_img:
                    src = await block_img.get_attribute('src')
                    print(f'\n{"="*80}')
                    print('❌ MICROSOFT BLOCKED THIS REGISTRATION!')
                    print(f'{"="*80}')
                    print(f'Block image detected: {src}')
                    print('This means:')
                    print('  • Your IP/proxy is flagged by Microsoft')
                    print('  • You need to change proxy or wait')
                    print('  • Registration will be restarted automatically')
                    print(f'{"="*80}\n')
                    return True

            print('✓ No block detected, continuing...')
            return False

        except Exception as e:
            print(f'Could not check for block: {e}')
            return False

    async def wait_for_captcha_solution(self):
        """Wait for NopeCHA to solve the captcha (or manual solve if no API key)"""
        print('\n' + '='*80)
        print('CAPTCHA DETECTION')
        print('='*80)

        has_nopecha = self.api_key and self.api_key != "token_here" and self.api_key.strip()

        if has_nopecha:
            print(f'✓ Using NopeCHA with API key: ***{self.api_key[-4:]}')
        else:
            print('⚠️  No NopeCHA - Manual CAPTCHA solving required')
            print('   To enable auto-solve, add API key to config.json')
            print('   Get one at: https://nopecha.com/manage')

        # IMPORTANT: Check for Microsoft block BEFORE waiting for CAPTCHA
        # Wait 2-3 seconds for the page to fully load and show block if present
        await self.human_delay(2.0, 3.0, "reading")

        is_blocked = await self.check_for_block()
        if is_blocked:
            # Return special value to indicate restart needed
            return "BLOCKED"

        # Check current URL
        current_url = self.page.url
        print(f'Current URL: {current_url}')

        # Try to detect CAPTCHA iframes
        print('\nDetecting CAPTCHA type...')
        try:
            # Check for FunCAPTCHA (Arkose Labs) - most common for Outlook
            funcaptcha_frames = await self.page.query_selector_all('iframe[src*="arkoselabs.com"], iframe[src*="funcaptcha.com"]')
            if funcaptcha_frames:
                print(f'✓ Detected FunCAPTCHA (Arkose Labs) - {len(funcaptcha_frames)} iframe(s)')

            # Check for reCAPTCHA
            recaptcha_frames = await self.page.query_selector_all('iframe[src*="recaptcha"]')
            if recaptcha_frames:
                print(f'✓ Detected reCAPTCHA - {len(recaptcha_frames)} iframe(s)')

            # Check for hCAPTCHA
            hcaptcha_frames = await self.page.query_selector_all('iframe[src*="hcaptcha"]')
            if hcaptcha_frames:
                print(f'✓ Detected hCAPTCHA - {len(hcaptcha_frames)} iframe(s)')

        except Exception as e:
            print(f'Could not detect CAPTCHA type: {e}')

        # Different behavior based on whether we have NopeCHA
        if has_nopecha:
            print('\nWaiting for NopeCHA to solve the CAPTCHA...')
            print('This may take 30-120 seconds depending on CAPTCHA complexity.')
            print('='*80 + '\n')

            # Wait up to 300 seconds for NopeCHA to solve the captcha
            try:
                await self.page.wait_for_selector('//span[@class="ms-Button-label label-117" and @id="id__0"]', timeout=300000)
                print("\n" + "="*80)
                print("✓ CAPTCHA SOLVED SUCCESSFULLY!")
                print("="*80 + "\n")
                return True
            except PlaywrightTimeoutError:
                print("\n" + "="*80)
                print("✗ NOPECHA TIMED OUT")
                print("="*80)
                print("\nPossible reasons:")
                print("  1. Out of credits (check https://nopecha.com/manage)")
                print("  2. CAPTCHA type not supported")
                print("  3. Extension not loaded properly")
                print("\nFalling back to manual solve...")
        else:
            print('\n' + '='*80)
            print('MANUAL CAPTCHA SOLVING REQUIRED')
            print('='*80)
            print('NopeCHA is not loaded (no API key configured).')
            print('Please solve the CAPTCHA manually in the browser window.')
            print('='*80 + '\n')

        # Manual solve (either no NopeCHA or NopeCHA failed)
        input("Press Enter after solving captcha manually...")
        try:
            await self.page.wait_for_selector('//span[@class="ms-Button-label label-117" and @id="id__0"]', timeout=60000)
            print("✓ Captcha solved manually!")
            return True
        except PlaywrightTimeoutError:
            print("✗ Captcha still not solved. Exiting...")
            return False
                
    async def save_account(self, email, password, first_name, last_name, birth_date, assoc_data=None):
        """Save generated account to file and Excel"""
        # Save the generated email and password to a file
        async with aiofiles.open('generated.txt', 'a') as f:
            # Check if the file is empty
            if os.path.exists('generated.txt') and os.path.getsize('generated.txt') > 0:
                await f.write("\n")
            await f.write(f"Email: {email}\n")
            
            # Add aliases if available
            if assoc_data and assoc_data.get('aliases'):
                await f.write(f"Aliases:\n")
                for alias in assoc_data['aliases']:
                    await f.write(f" - {alias}\n")
            
            await f.write(f"Password: {password}\n")
            
            # Add MailTM credentials if available
            if assoc_data:
                await f.write(f"Linked MailTM Account:\n")
                await f.write(f" - Email: {assoc_data.get('mailtm_email', 'N/A')}\n")
                await f.write(f" - Password: {assoc_data.get('mailtm_password', 'N/A')}\n")
            
            print("Account information saved to generated.txt")

        # Format aliases for Excel (separate columns)
        alias_1 = ""
        alias_2 = ""
        mailtm_email = ""
        mailtm_password = ""
        
        if assoc_data:
            if assoc_data.get('aliases'):
                aliases = assoc_data['aliases']
                alias_1 = aliases[0] if len(aliases) > 0 else ""
                alias_2 = aliases[1] if len(aliases) > 1 else ""
            mailtm_email = assoc_data.get('mailtm_email', '')
            mailtm_password = assoc_data.get('mailtm_password', '')

        row_data = [
            email,
            password,
            first_name,
            last_name,
            birth_date.isoformat(),
            self.config.get("proxy_host", ""),
            self.config.get("proxy_port", ""),
            self.config.get("username", ""),
            self.config.get("password", ""),
            time.strftime("%Y-%m-%d %H:%M:%S"),
            alias_1,
            alias_2,
            mailtm_email,
            mailtm_password,
        ]
        append_account(row_data)

