import asyncio
import random
from camoufox.async_api import AsyncCamoufox
from extension_manager import download_and_configure_nopecha


class BrowserManager:
    """Manages browser lifecycle and configuration"""

    def __init__(self, config):
        self.config = config
        self.browser = None
        self.page = None
        self.context_manager = None

    async def initialize(self):
        """Initialize browser with Camoufox and extensions"""
        import os
        import json

        # Check if we have a valid API key
        api_key = self.config.get('api_key', '')
        has_valid_key = api_key and api_key != "token_here" and api_key.strip()

        extension_dir = None
        addon_path = None

        # Only download and configure NopeCHA if we have a valid API key
        if has_valid_key:
            print("✓ Valid API key found, downloading NopeCHA extension...")
            extension_dir = await download_and_configure_nopecha(api_key)

            if not extension_dir:
                raise Exception("Failed to download/configure NopeCHA extension")

            # Verify extension directory exists
            addon_path = os.path.abspath(extension_dir)

            print(f"\n=== Extension Validation ===")
            print(f"Extension directory: {addon_path}")

            if not os.path.exists(addon_path):
                raise Exception(f"❌ NopeCHA extension directory not found: {addon_path}")
            if not os.path.isdir(addon_path):
                raise Exception(f"❌ Extension path is not a directory: {addon_path}")

            print(f"✓ Extension directory exists")

            # Validate directory contents
            files = os.listdir(addon_path)
            print(f"Files in directory ({len(files)} total): {files[:10]}...")

            manifest_path = os.path.join(addon_path, 'manifest.json')
            if not os.path.exists(manifest_path):
                raise Exception(f"❌ manifest.json not found in directory")

            print(f"✓ manifest.json found")

            # Read manifest info
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
                print(f"Extension: {manifest.get('name', 'Unknown')} v{manifest.get('version', '?')}")

            print(f"✓ Loading NopeCHA addon from: {addon_path}")
        else:
            print("\n" + "="*80)
            print("⚠️  NO API KEY CONFIGURED - SKIPPING NOPECHA")
            print("="*80)
            print("NopeCHA extension will NOT be loaded.")
            print("You will need to solve CAPTCHAs manually.")
            print("To enable auto-solve:")
            print("  1. Get API key from: https://nopecha.com/manage")
            print("  2. Add it to config.json: \"api_key\": \"your_key_here\"")
            print("="*80 + "\n")

        mode = self.config['mode']
        proxy_host = self.config.get('proxy_host')
        proxy_port = self.config.get('proxy_port')
        username = self.config.get('username')
        password = self.config.get('password')

        # Setup proxy configuration
        proxy_config = None
        if mode == 1:
            print("Using proxy without authentication")
            proxy_config = {
                "server": f"http://{proxy_host}:{proxy_port}"
            }
        elif mode == 2:
            print("Using proxy with authentication")
            proxy_config = {
                "server": f"http://{proxy_host}:{proxy_port}",
                "username": username,
                "password": password
            }
        else:
            print("Not using proxy")

        # Launch Camoufox browser with fingerprinting and extensions
        camoufox_config = {
            "headless": False,
            "locale": "en-US",
        }

        # Only add addons if we have NopeCHA extension
        if addon_path:
            camoufox_config["addons"] = [addon_path]

        if proxy_config:
            camoufox_config["proxy"] = proxy_config

        print("Launching Camoufox browser...")
        # Use AsyncCamoufox as a context manager
        self.context_manager = AsyncCamoufox(**camoufox_config)
        self.browser = await self.context_manager.__aenter__()

        print("✓ Camoufox browser launched successfully")

        # Create page
        self.page = await self.browser.new_page()

        # Show NopeCHA status
        if has_valid_key:
            print("✓ NopeCHA extension loaded with API key")
            print(f"  Key: ***{api_key[-4:] if len(api_key) > 4 else '***'}")
        else:
            print("⚠️  NopeCHA NOT loaded - manual CAPTCHA solving required")

        # Visit Google first (helps with bot detection)
        await self.page.goto('https://www.google.com', wait_until='domcontentloaded')
        await asyncio.sleep(1 + random.uniform(0.5, 1.5))

        return self.page

    async def close(self):
        """Close browser and cleanup resources"""
        try:
            if self.context_manager:
                await self.context_manager.__aexit__(None, None, None)
        except Exception:
            pass
        finally:
            self.browser = None
            self.page = None
            self.context_manager = None

