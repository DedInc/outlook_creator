import asyncio
import json
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from browser_manager import BrowserManager
from form_filler import SignupFormFiller

# Load the configuration from config.json
with open('config.json', 'r') as f:
    config = json.load(f)

class AccGen:
    """Main account generator class"""

    def __init__(self):
        self.browser_manager = BrowserManager(config)
        self.form_filler = None

    async def open_signup_page(self):
        """Initialize browser and navigate to signup page"""
        page = await self.browser_manager.initialize()
        self.form_filler = SignupFormFiller(page, config)
        await self.form_filler.navigate_to_signup()


    async def fill_signup_form(self):
        """Fill the signup form using the form filler"""
        # Fill email and get user data
        email, password, first_name, last_name, birth_date = await self.form_filler.fill_email()

        # Click Next button after email
        await self.form_filler.click_next_button("after email")

        # Fill password
        await self.form_filler.fill_password(password)

        # Click Next button after password
        await self.form_filler.click_next_button("after password")

        # Check if the password error message is present
        page = self.browser_manager.page
        try:
            await page.wait_for_selector("#PasswordError", timeout=3000)
            print("Password error appeared. Restarting the registration process ...")
            await self.form_filler.navigate_to_signup()
            await self.fill_signup_form()  # Restart the registration process
            return
        except PlaywrightTimeoutError:
            print("No password error, continuing to birth date...")
            pass  # No error, continue

        # Fill birth date
        await self.form_filler.fill_birth_date(birth_date)

        # Click Next button after birth date
        await self.form_filler.click_next_button("after birth date")

        # Fill name fields
        name_filled = await self.form_filler.fill_name(first_name, last_name)

        if name_filled:
            # Click Next button after name
            await self.form_filler.click_next_button("after name")

        # Check if SMS verification is required
        try:
            await page.wait_for_selector('//label[contains(text(), "Phone number")]', timeout=10000)
            # If so, quit the script
            print("SMS verification required. Please change your proxy.")
            await self.browser_manager.close()
            return
        except PlaywrightTimeoutError:
            pass

        # Wait for captcha solution (also checks for Microsoft block)
        captcha_result = await self.form_filler.wait_for_captcha_solution()

        # Check if Microsoft blocked the registration
        if captcha_result == "BLOCKED":
            print("\n" + "="*80)
            print("RESTARTING DUE TO MICROSOFT BLOCK")
            print("="*80)
            print("Closing browser and restarting registration...")
            await self.browser_manager.close()
            await asyncio.sleep(3)
            # Raise exception to trigger retry in create_account loop
            raise Exception("Microsoft blocked registration - restarting")

        if not captcha_result:
            return

        print("Captcha solved! Account successfully generated.")

        # Save account
        await self.form_filler.save_account(email, password, first_name, last_name, birth_date)

    async def create_account(self):
        """Main account creation loop with retry logic"""
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
                    await self.browser_manager.close()
                    await asyncio.sleep(2)
                except Exception as e:
                    # Handle Microsoft block and other errors
                    if "Microsoft blocked" in str(e):
                        print(f"Microsoft block detected, retrying with new session...")
                    else:
                        print(f"Error occurred: {e}")
                        print("Restarting the account creation process ...")
                    # Close current browser instance before retry
                    await self.browser_manager.close()
                    await asyncio.sleep(3)
        finally:
            # Clean up resources at the end
            await self.browser_manager.close()


async def main():
    """Main entry point"""
    acc_gen = AccGen()
    await acc_gen.create_account()


if __name__ == '__main__':
    asyncio.run(main())
