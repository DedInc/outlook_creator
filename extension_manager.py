import os
import json
import zipfile
import aiohttp


async def download_and_configure_nopecha(api_key):
    """Download and configure NopeCHA extension for Firefox (extracted directory)"""
    extension_dir = './nopecha_firefox'
    manifest_path = os.path.join(extension_dir, 'manifest.json')

    # Check if extension directory already exists
    if os.path.exists(extension_dir) and os.path.isdir(extension_dir):
        if os.path.exists(manifest_path):
            print(f"✓ NopeCHA extension directory already exists: {extension_dir}")
            # Always update API key (even if empty, to ensure manifest is correct)
            if api_key and api_key != "token_here" and api_key.strip():
                print("Updating API key in existing extension...")
                await _update_manifest_api_key(manifest_path, api_key)
            else:
                print("⚠️  No valid API key provided - NopeCHA will NOT work with automation!")
                print("   Get API key from: https://nopecha.com/manage")
            return extension_dir

    print("Downloading NopeCHA extension (Firefox automation version)...")

    try:
        # Download firefox_automation.zip (for Playwright/Camoufox automation)
        url = "https://github.com/NopeCHALLC/nopecha-extension/releases/latest/download/firefox_automation.zip"
        print(f"Downloading from: {url}")

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()

                zip_data = await response.read()

        print(f"✓ Downloaded {len(zip_data)} bytes")

        # Extract to directory
        print(f"Extracting to {extension_dir}...")
        os.makedirs(extension_dir, exist_ok=True)

        import io
        with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_ref:
            zip_ref.extractall(extension_dir)

        print(f"✓ Extracted to: {os.path.abspath(extension_dir)}")

        # Verify manifest.json exists
        if not os.path.exists(manifest_path):
            raise Exception(f"manifest.json not found after extraction!")

        # Configure the API key
        if api_key and api_key != "token_here" and api_key.strip():
            await _update_manifest_api_key(manifest_path, api_key)
        else:
            print("⚠️  No valid API key provided - NopeCHA will NOT work with automation!")
            print("   Get API key from: https://nopecha.com/manage")
            print("   Add it to config.json in the 'api_key' field")

        return extension_dir

    except Exception as e:
        print(f"❌ Error downloading NopeCHA extension: {e}")
        print("Please download manually from: https://github.com/NopeCHALLC/nopecha-extension/releases/latest")
        import traceback
        traceback.print_exc()
        return None


async def _update_manifest_api_key(manifest_path, api_key):
    """Update the NopeCHA API key in manifest.json"""
    try:
        # Read manifest
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        print(f"Updating manifest.json with API key...")

        # Update nopecha section - preserve existing settings
        if 'nopecha' not in manifest:
            manifest['nopecha'] = {}

        # Set the API key
        manifest['nopecha']['key'] = api_key

        # Also add to keys array if it exists
        if 'keys' not in manifest['nopecha']:
            manifest['nopecha']['keys'] = []
        if api_key and api_key not in manifest['nopecha']['keys']:
            manifest['nopecha']['keys'].append(api_key)

        # Ensure autosolve is enabled
        manifest['nopecha']['enabled'] = True
        manifest['nopecha']['autosolve'] = True

        # Enable auto-solve for ALL captcha types (including the ones Outlook might use)
        manifest['nopecha']['recaptcha_auto_solve'] = True
        manifest['nopecha']['recaptcha_auto_open'] = True
        manifest['nopecha']['hcaptcha_auto_solve'] = True
        manifest['nopecha']['hcaptcha_auto_open'] = True
        manifest['nopecha']['funcaptcha_auto_solve'] = True
        manifest['nopecha']['funcaptcha_auto_open'] = True
        manifest['nopecha']['turnstile_auto_solve'] = True

        # Enable additional CAPTCHA types that might appear
        manifest['nopecha']['awscaptcha_auto_solve'] = True
        manifest['nopecha']['awscaptcha_auto_open'] = True
        manifest['nopecha']['geetest_auto_solve'] = True
        manifest['nopecha']['geetest_auto_open'] = True
        manifest['nopecha']['lemincaptcha_auto_solve'] = True
        manifest['nopecha']['lemincaptcha_auto_open'] = True
        manifest['nopecha']['textcaptcha_auto_solve'] = True
        manifest['nopecha']['perimeterx_auto_solve'] = True

        print(f"✓ API key configured in manifest.json")
        print(f"  - Key: {'***' + api_key[-4:] if len(api_key) > 4 else '***'}")
        print(f"  - Autosolve: enabled for ALL CAPTCHA types")

        # Write back manifest
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)

        print(f"✓ manifest.json updated successfully")

    except Exception as e:
        print(f"❌ Error updating manifest API key: {e}")
        import traceback
        traceback.print_exc()

