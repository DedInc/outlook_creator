import asyncio
from playwright.async_api import TimeoutError as PlaywrightTimeoutError


async def enable_email_forwarding(page, mail_tm_email):
    """
    Enable email forwarding to mail.tm for an Outlook account.
    
    Steps:
    1. Navigate to https://outlook.live.com/mail/0/options/mail/forwarding
    2. Click switch #switch-r4r to enable forwarding
    3. Type the mail.tm email into #field-r6l__control
    4. Click the Save button
    5. Wait for 1.5 seconds
    
    Args:
        page: Playwright page object
        mail_tm_email: The mail.tm email address to forward to
        
    Returns:
        True if forwarding enabled successfully, False otherwise
    """
    print('\n' + '='*80)
    print('EMAIL FORWARDING ENABLER')
    print('='*80)
    
    try:
        # Step 1: Navigate to the forwarding settings page
        print('Navigating to email forwarding settings page...')
        await page.goto('https://outlook.live.com/mail/0/options/mail/forwarding', wait_until='domcontentloaded')
        
        print('✓ Navigated to settings page')
        print('Waiting for interface to fully load...')
        
        # Wait for the page to load
        await asyncio.sleep(5)
        
        # Step 2: Enable forwarding by clicking switch
        print('Enabling email forwarding...')
        try:
            forwarding_switch = await page.wait_for_selector('input[role="switch"]', timeout=60000)
            if forwarding_switch:
                await forwarding_switch.click()
                await asyncio.sleep(0.5)
                print('✓ Forwarding switch enabled')
        except PlaywrightTimeoutError:
            print('✗ Could not find forwarding switch (input[role="switch"])')
            return False
        
        # Step 3: Type the mail.tm email into the forwarding field
        print(f'Entering forwarding email: {mail_tm_email}')
        try:
            email_field = await page.wait_for_selector('input[type="text"]', timeout=60000)
            if email_field:
                await email_field.click()
                await email_field.fill(mail_tm_email)
                await asyncio.sleep(0.5)
                print('✓ Forwarding email entered')
        except PlaywrightTimeoutError:
            print('✗ Could not find email field (input[type="text"])')
            return False
        
        # Step 4: Find and click the Save button
        print('Looking for Save button...')
        try:
            # Find all buttons with type="button"
            buttons = await page.query_selector_all('button[type="button"]')
            
            save_button = None
            for button in buttons:
                text_content = await button.text_content()
                if text_content and text_content.strip() == 'Save':
                    save_button = button
                    break
            
            if save_button:
                print('✓ Found Save button, clicking...')
                await save_button.click()
                # Step 5: Wait for 1.5 seconds
                await asyncio.sleep(1.5)
                print('✓ Forwarding settings saved successfully!')
                print('='*80 + '\n')
                return True
            else:
                print('✗ Could not find Save button')
                print('='*80 + '\n')
                return False
                
        except Exception as e:
            print(f'✗ Error clicking Save button: {e}')
            print('='*80 + '\n')
            return False
        
    except PlaywrightTimeoutError:
        print('✗ Timeout navigating to settings page')
        print('='*80 + '\n')
        return False
        
    except Exception as e:
        print(f'✗ Error enabling email forwarding: {e}')
        print('='*80 + '\n')
        return False
