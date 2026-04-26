#!/usr/bin/env python3
"""
LinkedIn Easy Apply Automation - Direct copy of the_last_application approach
Uses nodriver (undetected browser) with exact selectors and methods from reference implementation
"""
import asyncio
import time
import nodriver as uc
from pathlib import Path
import json
from dotenv import load_dotenv
import os
from openai import OpenAI

# Load environment
load_dotenv()
ROOT_DIR = Path(__file__).resolve().parent

# Exact CSS Selectors from the_last_application
CSS_SELECTORS = {
    "form_elements": {
        "form_element": ".fb-dash-form-element",
        "inline_feedback": ".artdeco-inline-feedback__message",
        "submit_button": "button[aria-label=\"Submit application\"]",
        "next_button": "button[aria-label=\"Continue to next step\"]",
        "review_button": "button[aria-label=\"Review your application\"]",
        "dismiss_button": "button[aria-label=\"Dismiss\"]",
        "discard_button": "Discard",
    },
    "easy_apply_button": "button.jobs-apply-button",
}

def get_attributes(elem):
    """Get element attributes - exact copy from the_last_application"""
    if not elem.attributes:
        return {}
    return {elem.attributes[i]: elem.attributes[i + 1] for i in range(0, len(elem.attributes), 2)}

async def check_inline_feedback(item):
    """Check for inline feedback - exact copy from the_last_application"""
    try:
        inline_feedback = await item.query_selector(CSS_SELECTORS["form_elements"]["inline_feedback"])
        if inline_feedback:
            feedback_text = inline_feedback.text
            print(f" - Inline Feedback: {feedback_text}")
            return feedback_text
    except:
        pass
    return None

class LinkedInAutoFiller:
    def __init__(self):
        self.browser = None
        self.page = None
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.default_answers = self._load_default_answers()
        self.user_info = self._load_user_info()
        self.use_ai = True
    
    def _load_default_answers(self):
        """Load default answers"""
        answers_file = ROOT_DIR / "answers.json"
        if answers_file.exists():
            try:
                with open(answers_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _load_user_info(self):
        """Load hardcoded user info"""
        user_info_file = ROOT_DIR / "user_info.json"
        if user_info_file.exists():
            try:
                with open(user_info_file, 'r') as f:
                    info = json.load(f)
                    print("✓ User info loaded from user_info.json")
                    return info
            except Exception as e:
                print(f"⚠️  Error loading user_info.json: {e}")
        return {}
    
    async def setup_browser(self):
        """Start nodriver browser - exact from the_last_application"""
        print("🌐 Starting undetected browser...")
        self.browser = await uc.start()
        print("✓ Browser started")
        return self.browser
    
    async def navigate_to_job(self, job_url: str):
        """Navigate to a job posting"""
        print(f"\n🔗 Navigating to: {job_url}")
        self.page = await self.browser.get(job_url)
        await asyncio.sleep(3)
        print("✓ Job page loaded")
    
    async def wait_for_manual_login(self, timeout: int = 300):
        """Wait for user to login - simplified version"""
        print("\n👤 Checking login status...")
        print(f"  Waiting for login (timeout: {timeout}s)...")
        print("  If LinkedIn asks you to login, please do so in the browser window.")
        
        start = time.time()
        check_count = 0
        
        # Multiple selectors to check for logged-in state
        login_indicators = [
            "[data-test-menu-open-btn]",  # Profile menu
            "a[href*='/mynetwork']",      # My Network link
            ".global-nav",                 # Global navigation
            "button[aria-label*='messaging']",  # Messaging
            "[data-test-global-nav]",     # Test attribute nav
        ]
        
        while time.time() - start < timeout:
            check_count += 1
            
            # Try each indicator
            for selector in login_indicators:
                try:
                    elem = await self.page.query_selector(selector)
                    if elem:
                        print(f"✓ Login detected! (found: {selector})")
                        return True
                except:
                    pass
            
            # Show progress
            if check_count % 10 == 0:
                elapsed = int(time.time() - start)
                remaining = timeout - elapsed
                print(f"  Still waiting... ({remaining}s remaining)")
            
            await asyncio.sleep(1)
        
        print("⚠️  Login timeout - proceeding anyway (may work if already logged in)")
        return True  # Return True to continue anyway
    
    async def find_easy_apply_button(self):
        """Find Easy Apply button - with multiple selectors and debugging"""
        print("\n🎯 Looking for Easy Apply button...")
        
        # Wait for page to fully load and scroll to ensure elements are visible
        await asyncio.sleep(2)
        
        try:
            # Scroll to make sure button is in viewport
            await self.page.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            await asyncio.sleep(1)
            await self.page.execute_script("window.scrollTo(0, 0);")
            await asyncio.sleep(1)
        except:
            pass
        
        # Try multiple selectors
        selectors = [
            "button.jobs-apply-button",
            "button[aria-label*='Apply']",
            "button:has-text('Easy Apply')",
            "a[aria-label*='Easy Apply']",
            "[data-apply-button]",
            "button[class*='apply']",
        ]
        
        for selector in selectors:
            try:
                print(f"  Trying: {selector}")
                btn = await self.page.query_selector(selector)
                if btn:
                    print(f"✓ Easy Apply button found with: {selector}")
                    return btn
            except Exception as e:
                print(f"    ✗ Selector failed: {e}")
        
        # Debug: show what buttons are on the page
        print("\n  📊 Debug - buttons on page:")
        try:
            buttons = await self.page.find_all("button")
            print(f"    Found {len(buttons)} buttons total")
            for i, btn in enumerate(buttons[:10]):  # Show first 10
                try:
                    text = await btn.text
                    attrs = btn.attributes if btn.attributes else {}
                    print(f"      {i+1}. Text: '{text}' | Class: '{attrs.get('class', 'N/A')}'")
                except:
                    pass
        except Exception as e:
            print(f"    Error listing buttons: {e}")
        
        print("✗ Easy Apply button not found")
        return None
    
    async def click_easy_apply_button(self, button):
        """Click Easy Apply button"""
        print("🖱️  Clicking Easy Apply button...")
        try:
            await button.scroll_into_view()
            await asyncio.sleep(0.5)
            await button.mouse_click()
            print("✓ Easy Apply button clicked")
            await asyncio.sleep(2)
            return True
        except Exception as e:
            print(f"✗ Error clicking button: {e}")
            return False
    
    async def answer_questions(self, label: str, output_options: list = None, inline_feedback: str = None):
        """Answer questions using user info, defaults, or AI"""
        if output_options is None:
            output_options = []
        
        label_lower = label.lower().strip("*")
        
        # Check for hardcoded user info first
        if "first name" in label_lower:
            answer = self.user_info.get("first_name", "")
            if answer:
                print(f"Using user info for '{label}': {answer}")
                return answer
        
        if "last name" in label_lower or "surname" in label_lower:
            answer = self.user_info.get("last_name", "")
            if answer:
                print(f"Using user info for '{label}': {answer}")
                return answer
        
        if "mobile" in label_lower and "phone" in label_lower and "number" in label_lower:
            answer = self.user_info.get("mobile_phone", "")
            if answer:
                print(f"Using user info for '{label}': {answer}")
                return answer
        
        if "email" in label_lower and not output_options:
            answer = self.user_info.get("email", "")
            if answer:
                print(f"Using user info for '{label}': {answer}")
                return answer
        
        # For dropdown fields, use first valid option
        if output_options:
            # Check if it's a country code field
            if "country" in label_lower or "country code" in label_lower:
                answer = self.user_info.get("phone_country_code", "")
                if answer and answer in output_options:
                    print(f"Using user info for '{label}': {answer}")
                    return answer
            
            # Otherwise, select the first non-"Select" option
            for opt in output_options:
                if "select" not in opt.lower():
                    print(f"Selecting first option for '{label}': {opt}")
                    return opt
        
        # Check if in default answers
        if label_lower in self.default_answers:
            answer = self.default_answers[label_lower]
            print(f"Answering from default answers for '{label}': {answer}")
            return answer
        
        if self.use_ai:
            # Build prompt
            query = label
            if inline_feedback:
                query = f"{label}\nNote: {inline_feedback}"
            
            try:
                if output_options:
                    # For options, be very specific about matching
                    prompt = f"Question: {label}\n\nAvailable options:\n"
                    for i, opt in enumerate(output_options, 1):
                        prompt += f"{i}. {opt}\n"
                    prompt += "\nChoose the SINGLE best option from the list above. Respond with ONLY the option text, nothing else."
                else:
                    # For text fields, provide context-aware answers
                    if "phone" in label_lower and "number" in label_lower:
                        prompt = f"Question: {label}\n\nProvide a realistic phone number for a job application (example format: 6135551234 or 416-555-1234)."
                    else:
                        prompt = f"Question: {query}\n\nProvide a concise, professional answer suitable for a job application (2-3 sentences max)."
                
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant answering job application questions. When options are provided, respond with ONLY the option text."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=150
                )
                
                answer = response.choices[0].message.content.strip()
                
                # Extract number if question asks "how many"
                if "how many" in label.lower():
                    import re
                    match = re.search(r'\d+', answer)
                    if match:
                        answer = match.group(0)
                
                # If options provided, try to match answer to one of them
                if output_options:
                    answer_lower = answer.lower()
                    # First try exact match
                    for opt in output_options:
                        if opt.lower() == answer_lower:
                            answer = opt
                            break
                    else:
                        # Try partial match
                        for opt in output_options:
                            if opt.lower() in answer_lower or answer_lower in opt.lower():
                                answer = opt
                                break
                        else:
                            # If no match, use first non-"Select" option
                            for opt in output_options:
                                if "select" not in opt.lower():
                                    answer = opt
                                    break
                
                print(f"AI generated answer for '{label}': {answer}")
                return answer
            except Exception as e:
                print(f"⚠️  AI error: {e}")
                if output_options:
                    # Return first valid option
                    for opt in output_options:
                        if "select" not in opt.lower():
                            return opt
                return "Yes"
        else:
            answer = self.default_answers.get("fallback_answer", "Prefer not to answer")
            print(f"AI disabled. Using fallback: {answer}")
            return answer
    
    async def loop_through_form_elements(self):
        """Loop through form elements - EXACT copy from the_last_application"""
        qa = {}
        
        form_items = await self.page.find_all(CSS_SELECTORS["form_elements"]["form_element"])
        
        if not form_items:
            print("No form items found.")
            return qa
        
        for item in form_items:
            await item.scroll_into_view()
            
            label_elem = await item.query_selector("label")
            label_text = (label_elem.text) if label_elem else "N/A"
            print(f"Form Item: {label_text}")
            
            input_elem = await item.query_selector("input, select, textarea, fieldset")
            
            if not input_elem:
                print(" - No input element found")
                continue
            
            input_tag_name = input_elem.tag_name
            
            if input_tag_name == "input":
                input_type = get_attributes(input_elem).get("type", "N/A")
                print(f" - Input Type: {input_type}")
                
                # Check for inline feedback
                inline_feedback = await check_inline_feedback(item)
                
                if input_type in ["text"]:
                    answer = await self.answer_questions(
                        label_text.strip("*"),
                        output_options=[],
                        inline_feedback=inline_feedback
                    )
                    print(f" - Answer: {answer}")
                    await input_elem.clear_input()
                    await input_elem.send_keys(answer)
                    await asyncio.sleep(1)
                    qa[label_text.strip("*")] = answer
            
            elif input_tag_name == "select":
                print(" - Select Element")
                await input_elem.scroll_into_view()
                await input_elem.mouse_click()
                
                options = await input_elem.query_selector_all("option")
                output_options = []
                for option in options:
                    opt_text = option.text
                    print(f" - Option: {opt_text}")
                    output_options.append(opt_text)
                
                inline_feedback = await check_inline_feedback(item)
                answer = await self.answer_questions(
                    label_text.strip("*"),
                    output_options=output_options,
                    inline_feedback=inline_feedback
                )
                print(f" - Answer: {answer}")
                await input_elem.send_keys(answer)
                await asyncio.sleep(1)
                qa[label_text.strip("*")] = answer
            
            elif input_tag_name == "textarea":
                print(" - Textarea Element")
                inline_feedback = await check_inline_feedback(item)
                answer = await self.answer_questions(
                    label_text.strip("*"),
                    inline_feedback=inline_feedback
                )
                print(f" - Answer: {answer}")
                await input_elem.send_keys(answer)
                await asyncio.sleep(1)
                qa[label_text.strip("*")] = answer
            
            elif input_tag_name == "fieldset":
                print(" - Fieldset Element")
                options = await input_elem.query_selector_all("label")
                legend = await input_elem.query_selector("legend")
                
                legend_text = (legend.text) if legend else label_text
                output_options = []
                
                for option in options:
                    opt_text = option.text
                    output_options.append(opt_text)
                
                inline_feedback = await check_inline_feedback(item)
                answer = await self.answer_questions(
                    legend_text.strip("*"),
                    output_options=output_options,
                    inline_feedback=inline_feedback
                )
                print(f" - Answer: {answer}")
                
                # Click the matching option
                for option in options:
                    opt_text = option.text
                    if opt_text.strip().lower() == answer.strip().lower():
                        await option.click()
                        print(f"   - Selected Option: {opt_text}")
                        break
                
                await asyncio.sleep(1)
                qa[legend_text.strip("*")] = answer
        
        return qa
    
    async def loop_through_form(self):
        """Main form loop - EXACT copy from the_last_application"""
        count = 0
        form_counter = 0
        question_answers = {}
        
        while True:
            qa = await self.loop_through_form_elements()
            
            # Check if we're looping infinitely
            if any(q in question_answers for q in qa):
                form_counter += 1
                if form_counter >= 3:
                    print("Detected repeated form elements. Exiting form loop.")
                    dismiss_btn = await self.page.query_selector(CSS_SELECTORS["form_elements"]["dismiss_button"])
                    if dismiss_btn:
                        await dismiss_btn.click()
                        print("Clicked Dismiss button.")
                        await asyncio.sleep(1)
                    return None
            
            question_answers = question_answers | qa
            print(f"Form iteration: {count}")
            count += 1
            
            # Use page.find() like the_last_application does - THIS WORKS!
            next_btn = await self.page.find(CSS_SELECTORS["form_elements"]["next_button"])
            if next_btn:
                await next_btn.scroll_into_view()
                await next_btn.click()
                print("✓ Clicked Next button.")
                await asyncio.sleep(1)
            else:
                # Try Review button
                review_btn = await self.page.find(CSS_SELECTORS["form_elements"]["review_button"])
                if review_btn:
                    await review_btn.scroll_into_view()
                    await review_btn.click()
                    print("✓ Clicked Review button.")
                    await asyncio.sleep(1)
                else:
                    # Try Submit button
                    submit_btn = await self.page.find(CSS_SELECTORS["form_elements"]["submit_button"])
                    if submit_btn:
                        await submit_btn.scroll_into_view()
                        await submit_btn.click()
                        print("✓ Clicked Submit button.")
                        await asyncio.sleep(4)
                    
                    dismiss_btn = await self.page.query_selector(CSS_SELECTORS["form_elements"]["dismiss_button"])
                    if dismiss_btn:
                        await dismiss_btn.click()
                        print("Clicked Dismiss button.")
                    
                    break
                
                print("No Next button found, assuming end of form.")
                
                # Debug: show all buttons on the page
                print("\n  📊 Debug - All buttons on page:")
                try:
                    buttons = await self.page.find_all("button")
                    print(f"    Total buttons: {len(buttons)}")
                    for i, btn in enumerate(buttons[:15]):  # Show first 15
                        try:
                            text = btn.text
                            attrs = btn.attributes if btn.attributes else {}
                            aria_label = attrs.get("aria-label", "")
                            print(f"      {i+1}. Text: '{text}' | aria-label: '{aria_label}'")
                        except:
                            print(f"cannot show button {i+1}")
                except Exception as e:
                    print(f"    Error listing buttons: {e}")
                
                break
        
        return question_answers
    
    async def apply_to_job(self):
        """Main application flow"""
        print("\n" + "="*60)
        print("Starting LinkedIn Easy Apply Automation")
        print("="*60)
        
        try:
            # Find and click Easy Apply
            easy_apply_btn = await self.find_easy_apply_button()
            if not easy_apply_btn:
                return False
            
            if not await self.click_easy_apply_button(easy_apply_btn):
                return False
            
            # Wait a bit for form to load
            await asyncio.sleep(2)
            
            # Process form
            print("\n📝 Processing form...")
            result = await self.loop_through_form()
            
            if result is None:
                print("Form processing cancelled")
                return False
            
            print("\n✅ Application submitted successfully!")
            return True
        
        except Exception as e:
            print(f"\n✗ Error during application: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def pause_before_close(self, seconds: int = 120):
        """Pause for inspection before closing browser"""
        print(f"\n⏸️  Pausing for {seconds} seconds so you can inspect the browser...")
        print("   You can check the form, see what was submitted, verify the data, etc.")
        print(f"   Browser will close automatically in {seconds} seconds.\n")
        
        for i in range(seconds, 0, -10):
            if i <= 10:
                print(f"   Closing in {i} seconds...")
            await asyncio.sleep(min(10, i))
    
    async def close(self):
        """Close browser"""
        if self.browser:
            try:
                self.browser.stop()
                print("\n🔒 Browser closed")
            except Exception as e:
                print(f"⚠️  Error closing browser: {e}")


async def main():
    """Main entry point"""
    filler = LinkedInAutoFiller()
    
    try:
        # Setup browser
        await filler.setup_browser()
        
        # Navigate to job (user will provide URL or via command line argument)
        if len(sys.argv) > 1:
            job_url = sys.argv[1]
            print(f"\n🔗 Using job URL from argument: {job_url}")
        else:
            job_url = input("\n🔗 Enter job URL: ").strip()
            if not job_url:
                job_url = "https://www.linkedin.com/jobs/view/4398495763/"
        
        await filler.navigate_to_job(job_url)
        
        # Wait for login if needed
        await filler.wait_for_manual_login()
        
        # Apply to job
        success = await filler.apply_to_job()
        
        # Pause before closing so user can inspect
        if success:
            await filler.pause_before_close(120)  # 2 minutes
        else:
            await filler.pause_before_close(60)   # 1 minute for errors
        
    except KeyboardInterrupt:
        print("\n⏸  Cancelled by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await filler.close()
        print("\n👋 Done!")


if __name__ == "__main__":
    import sys
    asyncio.run(main())
