import os
import zipfile
import aiohttp
import aiofiles
import random
from patchright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import asyncio
import json
from fake_data import generate_fake_data
from check_email import check_email
from excel_logger import append_account

# Load the configuration from config.json
with open('config.json', 'r') as f:
    config = json.load(f)

# Extract the proxy details from the configuration
proxy_host = config['proxy_host']
proxy_port = config['proxy_port']
username = config['username']
password = config['password']


async def download_nopecha_extension():
    """Download and extract NopeCHA extension if it doesn't exist"""
    extension_dir = './nopecha'
    version_file = './nopecha/.version'

    # Check if extension already exists and is the correct version
    if os.path.exists(extension_dir) and os.path.isdir(extension_dir):
        # Check if it's the correct version (chromium.zip for channel="chrome")
        if os.path.exists(version_file):
            async with aiofiles.open(version_file, 'r') as f:
                version = (await f.read()).strip()
                if version == 'chromium':
                    print("NopeCHA extension (chromium version) already exists")
                    return True
                else:
                    print(f"Wrong NopeCHA version detected ({version}). Re-downloading correct version...")
                    import shutil
                    shutil.rmtree(extension_dir)
        else:
            print("NopeCHA extension version unknown. Re-downloading...")
            import shutil
            shutil.rmtree(extension_dir)

    print("NopeCHA extension not found. Downloading...")

    try:
        # Download chromium.zip (for real Chrome browser with channel="chrome")
        # chromium.zip = for installed Chrome/Edge browsers
        # chromium_automation.zip = for Playwright's bundled Chromium (when not using channel)
        url = "https://github.com/NopeCHALLC/nopecha-extension/releases/latest/download/chromium.zip"
        print(f"Downloading chromium.zip from: {url}")

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()

                # Save the zip file
                zip_path = './nopecha_extension.zip'
                async with aiofiles.open(zip_path, 'wb') as f:
                    await f.write(await response.read())

        print("Download complete. Extracting...")

        # Extract the zip file (synchronous, but fast operation)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extension_dir)

        # Create version marker file
        async with aiofiles.open(version_file, 'w') as f:
            await f.write('chromium')

        # Remove the zip file
        os.remove(zip_path)

        print("NopeCHA extension (chromium version) installed successfully!")
        return True

    except Exception as e:
        print(f"Error downloading NopeCHA extension: {e}")
        print("Please download manually from: https://github.com/NopeCHALLC/nopecha-extension/releases/latest")
        print("Download chromium.zip for use with channel='chrome'")
        return False

class AccGen:
    def __init__(self, proxy_host=None, proxy_port=None, username=None, password=None):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.username = username
        self.password = password
        self.api_key = config.get('api_key', '')

    async def open_signup_page(self):
        if not self.playwright:
            # Download NopeCHA extension if it doesn't exist
            await download_nopecha_extension()

            mode = config['mode']

            # Setup proxy configuration
            proxy_config = None
            if mode == 1:
                print("Using proxy without authentication")
                proxy_config = {
                    "server": f"http://{self.proxy_host}:{self.proxy_port}"
                }
            elif mode == 2:
                print("Using proxy with authentication")
                proxy_config = {
                    "server": f"http://{self.proxy_host}:{self.proxy_port}",
                    "username": self.username,
                    "password": self.password
                }
            else:
                print("Not using proxy")

            # Start Playwright
            self.playwright = await async_playwright().start()

            # Launch browser with Chrome channel
            launch_options = {
                "channel": "chrome",
                "headless": False,
                "args": [
                    "--lang=en",
                    "--disable-blink-features=AutomationControlled",
                    f"--disable-extensions-except=./nopecha",
                    f"--load-extension=./nopecha"
                ]
            }

            if proxy_config:
                launch_options["proxy"] = proxy_config

            self.browser = await self.playwright.chromium.launch(**launch_options)

            # Create context with NopeCHA settings
            self.context = await self.browser.new_context(
                locale="en-US"
            )

            # Create page
            self.page = await self.context.new_page()

            # Configure NopeCHA extension
            try:
                # Visit NopeCHA setup page to configure the extension
                await self.page.goto('https://nopecha.com/setup')

                if self.api_key and self.api_key != "token_here":
                    # Set NopeCHA API key via localStorage
                    await self.page.evaluate(f"""
                        localStorage.setItem('nopecha-key', '{self.api_key}');
                        localStorage.setItem('nopecha-enabled', 'true');
                    """)
                    print("NopeCHA API key configured successfully")
                else:
                    # Enable NopeCHA without API key (uses free trial credits)
                    await self.page.evaluate("""
                        localStorage.setItem('nopecha-enabled', 'true');
                    """)
                    print("NopeCHA enabled with free trial (no API key)")
            except Exception as e:
                print(f"Warning: Could not configure NopeCHA: {e}")

            # Visit Google first (helps with bot detection)
            await self.page.goto('https://www.google.com', wait_until='domcontentloaded')
            await asyncio.sleep(1 + random.uniform(0.5, 1.5))

            # Navigate to signup page - don't wait for networkidle, just load
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

            # Random delay to appear more human-like
            await asyncio.sleep(1.5 + random.uniform(0.5, 2.5))


    async def fill_signup_form(self):
        # Wait until the page is fully loaded
        print("Waiting for signup form to load...")

        # Wait until the email input field is available with multiple selectors
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

        # Generate fake data and check email availability
        email_available = False
        while not email_available:
            login, password, first_name, last_name, birth_date = generate_fake_data()
            email = login + "@outlook.com"
            email_check_result = check_email(email)
            if email_check_result.get('isAvailable'):
                print(f"{email} is available, continuing with the registration process ...")
                email_available = True
            else:
                print(f"{email} is not available. Generating new email ...")

        # If the email is available, continue with the registration process
        print(f"Filling email input with: {email}")
        await self.page.fill(email_input_selector, email)

        # Small human-like delay after typing
        await asyncio.sleep(random.uniform(0.3, 0.7))

        # Wait until the "Next" button is available and click it
        # New selector: button[data-testid="primaryButton"]
        next_button_selector = None
        try:
            await self.page.wait_for_selector('button[data-testid="primaryButton"]', timeout=10000)
            next_button_selector = 'button[data-testid="primaryButton"]'
            print("Found Next button: button[data-testid='primaryButton']")
        except PlaywrightTimeoutError:
            try:
                await self.page.wait_for_selector("#nextButton", timeout=10000)
                next_button_selector = "#nextButton"
                print("Found Next button: #nextButton")
            except PlaywrightTimeoutError:
                await self.page.wait_for_selector('button[type="submit"]', timeout=10000)
                next_button_selector = 'button[type="submit"]'
                print("Found Next button: button[type='submit']")

        await self.page.click(next_button_selector)
        print("Clicked Next button, waiting for password field...")

        # Wait until the password input field is available
        password_input_selector = None
        try:
            await self.page.wait_for_selector('input[type="password"]', timeout=10000)
            password_input_selector = 'input[type="password"]'
            print("Found password input: input[type='password']")
        except PlaywrightTimeoutError:
            await self.page.wait_for_selector("#Password", timeout=10000)
            password_input_selector = "#Password"
            print("Found password input: #Password")

        # Type the password into the input field
        await self.page.fill(password_input_selector, password)

        # Small human-like delay after typing
        await asyncio.sleep(random.uniform(0.3, 0.7))

        # Click Next button after password
        try:
            await self.page.wait_for_selector('button[data-testid="primaryButton"]', timeout=10000)
            await self.page.click('button[data-testid="primaryButton"]')
            print("Clicked Next button after password")
        except PlaywrightTimeoutError:
            await self.page.wait_for_selector("#nextButton", timeout=10000)
            await self.page.click("#nextButton")
            print("Clicked #nextButton after password")

        # Check if the password error message is present
        try:
            await self.page.wait_for_selector("#PasswordError", timeout=3000)
            print("Password error appeared. Restarting the registration process ...")
            await self.page.goto('https://signup.live.com/signup')
            await self.fill_signup_form()  # Restart the registration process
            return
        except PlaywrightTimeoutError:
            print("No password error, continuing to birth date...")
            pass  # No error, continue

        # NEW ORDER: Birth date comes BEFORE name!
        # Month names mapping
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        # Wait until the birth month dropdown is available
        try:
            # Try standard select element first
            await self.page.wait_for_selector('select[aria-label*="Month"]', timeout=5000)
            await self.page.select_option('select[aria-label*="Month"]', str(birth_date.month))
            print("Selected birth month")
        except PlaywrightTimeoutError:
            # Try Fluent UI dropdown button
            await self.page.wait_for_selector('button[name="BirthMonth"]', timeout=5000)

            # Check if dropdown is already expanded
            is_expanded = await self.page.get_attribute('button[name="BirthMonth"]', 'aria-expanded')
            if is_expanded != 'true':
                # Click to open dropdown, force click to bypass label interception
                await self.page.click('button[name="BirthMonth"]', force=True)
                # Wait for dropdown options to appear
                await self.page.wait_for_selector('[role="option"]', timeout=5000)

            # Get month name and click the option by text
            month_name = month_names[birth_date.month - 1]
            await self.page.click(f'[role="option"]:has-text("{month_name}")')
            print(f"Selected birth month: {month_name}")

        # Small human-like delay
        await asyncio.sleep(random.uniform(0.2, 0.5))

        # Wait until the birth day dropdown is available
        try:
            # Try standard select element first
            await self.page.wait_for_selector('select[aria-label*="Day"]', timeout=5000)
            await self.page.select_option('select[aria-label*="Day"]', str(birth_date.day))
            print("Selected birth day")
        except PlaywrightTimeoutError:
            # Try Fluent UI dropdown button
            await self.page.wait_for_selector('button[name="BirthDay"]', timeout=5000)

            # Check if dropdown is already expanded
            is_expanded = await self.page.get_attribute('button[name="BirthDay"]', 'aria-expanded')
            if is_expanded != 'true':
                # Click to open dropdown, force click to bypass label interception
                await self.page.click('button[name="BirthDay"]', force=True)
                # Wait for dropdown options to appear
                await self.page.wait_for_selector('[role="option"]', timeout=5000)

            # Click the option by text (day number)
            await self.page.click(f'[role="option"]:has-text("{birth_date.day}")')
            print(f"Selected birth day: {birth_date.day}")

        # Small human-like delay
        await asyncio.sleep(random.uniform(0.2, 0.5))

        # Wait until the birth year input field is available
        try:
            # Try aria-label first
            await self.page.wait_for_selector('input[aria-label*="Year"]', timeout=5000)
            await self.page.fill('input[aria-label*="Year"]', str(birth_date.year))
            print("Filled birth year")
        except PlaywrightTimeoutError:
            # Try name attribute
            await self.page.wait_for_selector('input[name="BirthYear"]', timeout=5000)
            await self.page.fill('input[name="BirthYear"]', str(birth_date.year))
            print("Filled birth year using name attribute")

        # Small human-like delay after typing
        await asyncio.sleep(random.uniform(0.3, 0.7))

        # Click Next button after birth date
        try:
            await self.page.wait_for_selector('button[data-testid="primaryButton"]', timeout=10000)
            await self.page.click('button[data-testid="primaryButton"]')
            print("Clicked Next button after birth date, waiting for name fields...")
        except PlaywrightTimeoutError:
            await self.page.wait_for_selector("#nextButton", timeout=10000)
            await self.page.click("#nextButton")
            print("Clicked #nextButton after birth date, waiting for name fields...")

        # Fill in first name and last name
        try:
            # Wait for first name input
            await self.page.wait_for_selector('input[name="firstNameInput"]', timeout=10000)
            await self.page.fill('input[name="firstNameInput"]', first_name)
            print(f"Filled first name: {first_name}")

            # Small human-like delay between fields
            await asyncio.sleep(random.uniform(0.2, 0.5))

            # Fill last name
            await self.page.fill('input[name="lastNameInput"]', last_name)
            print(f"Filled last name: {last_name}")

            # Small human-like delay after typing
            await asyncio.sleep(random.uniform(0.3, 0.7))

            # Click Next button after name
            await self.page.click('button[data-testid="primaryButton"]')
            print("Clicked Next button after name, waiting for CAPTCHA...")
        except PlaywrightTimeoutError:
            print("Name input fields not found, continuing...")
            pass

        # Check if SMS verification is required
        try:
            await self.page.wait_for_selector('//label[contains(text(), "Phone number")]', timeout=10000)
            # If so, quit the script
            print("SMS verification required. Please change your proxy.")
            await self.browser.close()
            await self.playwright.stop()
            return
        except PlaywrightTimeoutError:
            pass

        # NopeCHA will automatically solve the captcha
        print('NopeCHA is solving the captcha automatically...')
        if self.api_key and self.api_key != "token_here":
            print('Using NopeCHA with API key')
        else:
            print('Using NopeCHA free trial (100 credits)')

        # Wait up to 300 seconds for NopeCHA to solve the captcha
        try:
            await self.page.wait_for_selector('//span[@class="ms-Button-label label-117" and @id="id__0"]', timeout=300000)
            print("Captcha solved automatically by NopeCHA!")
        except PlaywrightTimeoutError:
            print("Captcha solving timed out.")
            print("If you're using free trial, you may have run out of credits.")
            print("You can get an API key at: https://nopecha.com/")
            print("Or solve the captcha manually and press Enter...")
            input("Press Enter after solving captcha manually...")
            try:
                await self.page.wait_for_selector('//span[@class="ms-Button-label label-117" and @id="id__0"]', timeout=60000)
            except PlaywrightTimeoutError:
                print("Captcha still not solved. Exiting...")
                return

        print("Captcha solved! Account successfully generated.")

        # Save the generated email and password to a file
        async with aiofiles.open('generated.txt', 'a') as f:
            # Check if the file is empty
            if os.path.exists('generated.txt') and os.path.getsize('generated.txt') > 0:
                await f.write("\n")
            await f.write(f"Email: {email}\n")
            await f.write(f"Password: {password}\n")
            print("Email and password saved to generated.txt")

        import time
        row_data = [
            email,
            password,
            first_name,
            last_name,
            birth_date.isoformat(),
            config.get("proxy_host", ""),
            config.get("proxy_port", ""),
            config.get("username", ""),
            config.get("password", ""),
            time.strftime("%Y-%m-%d %H:%M:%S"),
            "",
            "",
            "",
            "",
        ]
        append_account(row_data)

    async def create_account(self):
        try:
            while True:
                try:
                    await self.open_signup_page()
                    await self.fill_signup_form()
                    break  # If the account creation process is successful, break out of the loop
                except PlaywrightTimeoutError as e:
                    print(f"Timeout occurred: {e}")
                    print("Restarting the account creation process ...")
                    # Close current browser instance before retry
                    try:
                        if self.page:
                            await self.page.close()
                        if self.context:
                            await self.context.close()
                        if self.browser:
                            await self.browser.close()
                        if self.playwright:
                            await self.playwright.stop()
                    except Exception:
                        pass
                    # Reset instances for retry
                    self.playwright = None
                    self.browser = None
                    self.context = None
                    self.page = None
                    await asyncio.sleep(2)
        finally:
            # Clean up resources at the end
            try:
                if self.page:
                    await self.page.close()
            except Exception:
                pass
            try:
                if self.context:
                    await self.context.close()
            except Exception:
                pass
            try:
                if self.browser:
                    await self.browser.close()
            except Exception:
                pass
            try:
                if self.playwright:
                    await self.playwright.stop()
            except Exception:
                pass

async def main():
    acc_gen = AccGen(proxy_host=proxy_host, proxy_port=proxy_port, username=username, password=password)
    await acc_gen.create_account()

if __name__ == '__main__':
    asyncio.run(main())
