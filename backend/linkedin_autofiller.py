"""
LinkedIn Easy Apply Autofiller - Production-ready module
Extracted and refactored from test_auto_fill.py
Uses nodriver for undetected browser automation
"""
import asyncio
import time
import nodriver as uc
from openai import OpenAI
import os
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# CSS Selectors for LinkedIn Easy Apply form
CSS_SELECTORS = {
    "form_elements": {
        "form_element": ".fb-dash-form-element",
        "inline_feedback": ".artdeco-inline-feedback__message",
        "submit_button": "button[aria-label=\"Submit application\"]",
        "next_button": "button[aria-label=\"Continue to next step\"]",
        "review_button": "button[aria-label=\"Review your application\"]",
        "dismiss_button": "button[aria-label=\"Dismiss\"]",
        "discard_button": "Discard",
        "upload_resume_button": "span[role=\"button\"][aria-label*=\"Upload resume button\"]",
    },
    "easy_apply_button": "button.jobs-apply-button",
}


def get_attributes(elem):
    """Get element attributes from DOM element"""
    if not elem.attributes:
        return {}
    return {elem.attributes[i]: elem.attributes[i + 1] for i in range(0, len(elem.attributes), 2)}


async def check_inline_feedback(item):
    """Check for inline feedback message on form element"""
    try:
        inline_feedback = await item.query_selector(CSS_SELECTORS["form_elements"]["inline_feedback"])
        if inline_feedback:
            feedback_text = inline_feedback.text
            logger.info(f"Inline Feedback: {feedback_text}")
            return feedback_text
    except:
        pass
    return None


class LinkedInAutoFiller:
    """
    Automation class for LinkedIn Easy Apply form filling
    Handles browser control, form parsing, and AI-powered question answering
    """
    
    def __init__(self, user_info: Dict, default_answers: Optional[Dict] = None, use_ai: bool = True, resume_file_path: str = None):
        """
        Initialize the autofiller
        
        Args:
            user_info: Dictionary with user information (first_name, last_name, email, mobile_phone, etc.)
            default_answers: Dictionary of pre-defined answers for common questions
            use_ai: Whether to use OpenAI for intelligent answers
            resume_file_path: Path to the resume PDF file to upload
        """
        self.browser = None
        self.page = None
        self.user_info = user_info
        self.default_answers = default_answers or {}
        self.use_ai = use_ai
        self.resume_file_path = resume_file_path
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if use_ai else None
        self.status_callback = None  # Optional callback for progress updates
        self.resume_uploaded = False  # Track if resume has been uploaded
        logger.info(f"LinkedInAutoFiller initialized with user: {user_info.get('first_name', 'Unknown')}")
        if resume_file_path:
            logger.info(f"Resume file path: {resume_file_path}")
    
    def set_status_callback(self, callback):
        """Set a callback function to report progress"""
        self.status_callback = callback
    
    def _update_status(self, step: str, message: str):
        """Update status via callback if set"""
        if self.status_callback:
            self.status_callback(step, message)
        logger.info(f"Status: {step} - {message}")
    
    async def setup_browser(self):
        """Start undetected Chrome browser"""
        self._update_status("setup", "Starting undetected browser...")
        try:
            # Create browser config with all necessary flags for macOS
            config = uc.Config()
            config.no_sandbox = True
            config.headed = True  # Show browser window
            
            # Explicit Chrome path for macOS
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            if os.path.exists(chrome_path):
                config.browser_executable_path = chrome_path
                logger.info(f"Using Chrome at: {chrome_path}")
            
            # Additional flags to help with browser startup
            config.add_argument("--disable-dev-shm-usage")  # Reduce memory usage
            config.add_argument("--disable-gpu")  # Disable GPU
            config.add_argument("--no-first-run")
            config.add_argument("--no-default-browser-check")
            
            self.browser = await uc.start(config=config)
            logger.info("Browser started successfully")
            return self.browser
        except Exception as e:
            logger.error(f"Failed to start browser with config: {e}")
            # Fallback: try minimal config
            try:
                logger.info("Attempting minimal browser startup...")
                config = uc.Config()
                config.no_sandbox = True
                self.browser = await uc.start(config=config)
                logger.info("Browser started successfully (minimal config)")
                return self.browser
            except Exception as e2:
                logger.error(f"Minimal browser start also failed: {e2}")
                raise
    
    async def navigate_to_job(self, job_url: str):
        """Navigate to a LinkedIn job posting"""
        self._update_status("navigate", f"Navigating to job: {job_url}")
        self.page = await self.browser.get(job_url)
        await asyncio.sleep(3)
        logger.info("Job page loaded")
    
    async def wait_for_manual_login(self, timeout: int = 300):
        """Wait for user to manually login to LinkedIn"""
        self._update_status("login", "Waiting for manual LinkedIn login...")
        logger.info("Checking login status...")
        
        start = time.time()
        check_count = 0
        
        login_indicators = [
            "[data-test-menu-open-btn]",
            "a[href*='/mynetwork']",
            ".global-nav",
            "button[aria-label*='messaging']",
            "[data-test-global-nav]",
        ]
        
        while time.time() - start < timeout:
            check_count += 1
            
            for selector in login_indicators:
                try:
                    elem = await self.page.query_selector(selector)
                    if elem:
                        logger.info(f"Login detected!")
                        self._update_status("login", "Login successful!")
                        return True
                except:
                    pass
            
            if check_count % 10 == 0:
                elapsed = int(time.time() - start)
                remaining = timeout - elapsed
                logger.debug(f"Still waiting for login... ({remaining}s remaining)")
            
            await asyncio.sleep(1)
        
        logger.warning("Login timeout - proceeding anyway")
        return True
    
    async def find_easy_apply_button(self):
        """Find and return the Easy Apply button"""
        self._update_status("detect_button", "Looking for Easy Apply button...")
        logger.info("Searching for Easy Apply button...")
        
        await asyncio.sleep(2)
        
        try:
            await self.page.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            await asyncio.sleep(1)
            await self.page.execute_script("window.scrollTo(0, 0);")
            await asyncio.sleep(1)
        except:
            pass
        
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
                logger.debug(f"Trying selector: {selector}")
                btn = await self.page.query_selector(selector)
                if btn:
                    logger.info(f"Easy Apply button found!")
                    self._update_status("detect_button", "Easy Apply button found!")
                    return btn
            except Exception as e:
                logger.debug(f"Selector failed: {e}")
        
        logger.error("Easy Apply button not found")
        self._update_status("detect_button", "Easy Apply button not found")
        return None
    
    async def click_easy_apply_button(self, button):
        """Click the Easy Apply button"""
        self._update_status("click_button", "Clicking Easy Apply button...")
        logger.info("Clicking Easy Apply button...")
        try:
            await button.scroll_into_view()
            await asyncio.sleep(0.5)
            await button.mouse_click()
            logger.info("Easy Apply button clicked successfully")
            self._update_status("click_button", "Easy Apply button clicked")
            await asyncio.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Error clicking button: {e}")
            self._update_status("click_button", f"Error clicking button: {e}")
            return False
    
    async def answer_questions(self, label: str, output_options: List[str] = None, inline_feedback: str = None):
        """
        Answer a form question using multiple strategies:
        1. User info (hardcoded values)
        2. Default answers cache
        3. AI-generated answers
        """
        if output_options is None:
            output_options = []
        
        label_lower = label.lower().strip("*")
        
        # Strategy 1: Check hardcoded user info
        if "first name" in label_lower:
            answer = self.user_info.get("first_name", "")
            if answer:
                logger.info(f"Using user info for '{label}': {answer}")
                return answer
        
        if "last name" in label_lower or "surname" in label_lower:
            answer = self.user_info.get("last_name", "")
            if answer:
                logger.info(f"Using user info for '{label}': {answer}")
                return answer
        
        if "mobile" in label_lower and "phone" in label_lower and "number" in label_lower:
            answer = self.user_info.get("mobile_phone", "")
            if answer:
                logger.info(f"Using user info for '{label}': {answer}")
                return answer
        
        if "email" in label_lower and not output_options:
            answer = self.user_info.get("email", "")
            if answer:
                logger.info(f"Using user info for '{label}': {answer}")
                return answer
        
        # Strategy 2: For dropdowns, select appropriate option
        if output_options:
            if "country" in label_lower or "country code" in label_lower:
                answer = self.user_info.get("phone_country_code", "")
                if answer and answer in output_options:
                    logger.info(f"Using user info for '{label}': {answer}")
                    return answer
            
            for opt in output_options:
                if "select" not in opt.lower():
                    logger.info(f"Selecting option for '{label}': {opt}")
                    return opt
        
        # Strategy 3: Check default answers cache
        if label_lower in self.default_answers:
            answer = self.default_answers[label_lower]
            logger.info(f"Using cached answer for '{label}': {answer}")
            return answer
        
        # Strategy 4: Use AI for intelligent answers
        if self.use_ai and self.openai_client:
            logger.info(f"Using AI to generate answer for '{label}'")
            try:
                if output_options:
                    prompt = f"Question: {label}\n\nAvailable options:\n"
                    for i, opt in enumerate(output_options, 1):
                        prompt += f"{i}. {opt}\n"
                    prompt += "\nChoose the SINGLE best option from the list above. Respond with ONLY the option text, nothing else."
                else:
                    if "phone" in label_lower and "number" in label_lower:
                        prompt = f"Question: {label}\n\nProvide a realistic phone number for a job application (example format: 6135551234 or 416-555-1234)."
                    else:
                        prompt = f"Question: {label}\n\nProvide a concise, professional answer suitable for a job application (2-3 sentences max)."
                
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
                logger.info(f"AI generated answer for '{label}': {answer}")
                
                # Extract number if question asks "how many"
                if "how many" in label.lower():
                    import re
                    match = re.search(r'\d+', answer)
                    if match:
                        answer = match.group(0)
                
                # Try to match to available options
                if output_options:
                    answer_lower = answer.lower()
                    for opt in output_options:
                        if opt.lower() == answer_lower:
                            answer = opt
                            break
                    else:
                        for opt in output_options:
                            if opt.lower() in answer_lower or answer_lower in opt.lower():
                                answer = opt
                                break
                        else:
                            for opt in output_options:
                                if "select" not in opt.lower():
                                    answer = opt
                                    break
                
                return answer
            except Exception as e:
                logger.error(f"AI error: {e}")
                if output_options:
                    for opt in output_options:
                        if "select" not in opt.lower():
                            return opt
                return "Yes"
        
        # Fallback
        logger.warning(f"No answer strategy worked for '{label}'")
        return "Prefer not to answer"
    
    async def _handle_upload_resume_buttons(self):
        """
        Handle the 'Upload resume' button that appears on the form
        The button is a span with role="button" and aria-label containing "Upload resume button"
        """
        logger.debug("Checking for upload resume button...")
        
        # Try to find the upload button span
        selectors = [
            "span[role=\"button\"][aria-label*=\"Upload resume button\"]",
            "span[aria-label*=\"Upload resume\"]",
            "label.jobs-document-upload__upload-button",
        ]
        
        for selector in selectors:
            try:
                logger.debug(f"Trying selector: {selector}")
                upload_btn = await self.page.find(selector)
                if upload_btn:
                    logger.info(f"Found upload button with selector: {selector}")
                    await upload_btn.scroll_into_view()
                    await asyncio.sleep(0.5)
                    await upload_btn.mouse_click()
                    logger.info("Clicked upload resume button")
                    self._update_status("fill_form", "Clicking upload resume button...")
                    await asyncio.sleep(2)  # Wait for dialog/file input to appear
                    
                    # Now try to upload the resume file if we have it
                    if self.resume_file_path and os.path.exists(self.resume_file_path):
                        await self._upload_resume_file()
                    return
            except Exception as e:
                logger.debug(f"Selector failed: {e}")
    
    async def _upload_resume_file(self):
        """Upload resume file using file input that appears after clicking upload button"""
        logger.info(f"Attempting to upload resume file: {self.resume_file_path}")
        
        try:
            # Give the file dialog a moment to open
            await asyncio.sleep(1)
            
            # Find file input by name attribute (consistent across LinkedIn)
            file_input = await self.page.find("input[name='file']")
            
            if file_input:
                logger.info(f"Found file input")
                
                # Copy file path to clipboard for pasting in macOS dialog
                import subprocess
                try:
                    # Use macOS pbcopy to copy to clipboard
                    process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
                    process.communicate(self.resume_file_path.encode('utf-8'))
                    logger.info(f"Copied file path to clipboard")
                except Exception as e:
                    logger.warning(f"Could not copy to clipboard: {e}")
                
                # Focus the file input
                await file_input.focus()
                await asyncio.sleep(0.5)
                
                # Send Cmd+V to paste the path from clipboard
                await file_input.send_keys("\u0003v")  # Cmd+V
                await asyncio.sleep(1)
                
                # Send Return key to confirm
                logger.info("Sending Return key to confirm file selection")
                await file_input.send_keys("\n")
                
                logger.info("Waiting for upload to process...")
                await asyncio.sleep(7)  # Wait 7 seconds for upload to complete
                
                logger.info("Resume file uploaded successfully")
                self._update_status("fill_form", "Resume uploaded successfully")
                self.resume_uploaded = True  # Mark as uploaded
                return True
            else:
                logger.warning("No file input found after clicking upload button")
                return False
        except Exception as e:
            logger.error(f"Error uploading resume: {e}")
            self._update_status("fill_form", f"Error uploading resume: {e}")
            return False
    
    async def loop_through_form_elements(self):
        """Process all form elements on current step"""
        qa = {}
        
        # Note: Don't check for upload resume button here - it's on step 2
        # It will be handled after we click Next from step 1
        
        form_items = await self.page.find_all(CSS_SELECTORS["form_elements"]["form_element"])
        
        if not form_items:
            logger.warning("No form items found")
            return qa
        
        for i, item in enumerate(form_items):
            logger.debug(f"Processing form item {i+1}/{len(form_items)}")
            
            await item.scroll_into_view()
            
            label_elem = await item.query_selector("label")
            label_text = (label_elem.text) if label_elem else "N/A"
            logger.info(f"Form Item: {label_text}")
            
            input_elem = await item.query_selector("input, select, textarea, fieldset")
            
            if not input_elem:
                logger.debug("No input element found")
                continue
            
            input_tag_name = input_elem.tag_name
            
            if input_tag_name == "input":
                input_type = get_attributes(input_elem).get("type", "N/A")
                logger.debug(f"Input Type: {input_type}")
                
                inline_feedback = await check_inline_feedback(item)
                
                if input_type == "file":
                    # Handle file upload (resume)
                    logger.info(f"File input found: {label_text}")
                    if "resume" in label_text.lower() or "attachment" in label_text.lower():
                        if self.resume_file_path and os.path.exists(self.resume_file_path):
                            logger.info(f"Uploading resume: {self.resume_file_path}")
                            try:
                                # Use nodriver's send_keys to upload file
                                await input_elem.send_keys(self.resume_file_path)
                                logger.info("Resume uploaded successfully")
                                self._update_status("fill_form", f"Resume uploaded: {label_text}")
                                await asyncio.sleep(2)
                                qa[label_text.strip("*")] = self.resume_file_path
                            except Exception as e:
                                logger.error(f"Error uploading resume: {e}")
                                self._update_status("fill_form", f"Error uploading resume: {e}")
                        else:
                            logger.warning(f"Resume file not found or not provided: {self.resume_file_path}")
                    else:
                        logger.debug(f"Skipping non-resume file upload: {label_text}")
                
                elif input_type in ["text", "email", "tel", "url", "number"]:
                    answer = await self.answer_questions(
                        label_text.strip("*"),
                        output_options=[],
                        inline_feedback=inline_feedback
                    )
                    logger.info(f"Answer: {answer}")
                    await input_elem.clear_input()
                    await input_elem.send_keys(answer)
                    await asyncio.sleep(1)
                    qa[label_text.strip("*")] = answer
            
            elif input_tag_name == "select":
                logger.debug("Select Element")
                await input_elem.scroll_into_view()
                await input_elem.mouse_click()
                
                options = await input_elem.query_selector_all("option")
                output_options = []
                for option in options:
                    opt_text = option.text
                    logger.debug(f"Option: {opt_text}")
                    output_options.append(opt_text)
                
                inline_feedback = await check_inline_feedback(item)
                answer = await self.answer_questions(
                    label_text.strip("*"),
                    output_options=output_options,
                    inline_feedback=inline_feedback
                )
                logger.info(f"Answer: {answer}")
                await input_elem.send_keys(answer)
                await asyncio.sleep(1)
                qa[label_text.strip("*")] = answer
            
            elif input_tag_name == "textarea":
                logger.debug("Textarea Element")
                inline_feedback = await check_inline_feedback(item)
                answer = await self.answer_questions(
                    label_text.strip("*"),
                    inline_feedback=inline_feedback
                )
                logger.info(f"Answer: {answer}")
                await input_elem.send_keys(answer)
                await asyncio.sleep(1)
                qa[label_text.strip("*")] = answer
            
            elif input_tag_name == "fieldset":
                logger.debug("Fieldset Element")
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
                logger.info(f"Answer: {answer}")
                
                for option in options:
                    opt_text = option.text
                    if opt_text.strip().lower() == answer.strip().lower():
                        await option.click()
                        logger.info(f"Selected Option: {opt_text}")
                        break
                
                await asyncio.sleep(1)
                qa[legend_text.strip("*")] = answer
        
        return qa
    
    async def loop_through_form(self):
        """Main form loop - process all form steps"""
        self._update_status("fill_form", "Starting form filling...")
        count = 0
        form_counter = 0
        question_answers = {}
        
        while True:
            self._update_status("fill_form", f"Processing form step {count + 1}...")
            logger.info(f"Form iteration: {count}")
            
            qa = await self.loop_through_form_elements()
            
            # Check if we're looping infinitely
            if any(q in question_answers for q in qa):
                form_counter += 1
                if form_counter >= 3:
                    logger.warning("Detected repeated form elements. Exiting form loop.")
                    self._update_status("fill_form", "No more form steps")
                    dismiss_btn = await self.page.query_selector(CSS_SELECTORS["form_elements"]["dismiss_button"])
                    if dismiss_btn:
                        await dismiss_btn.click()
                        logger.info("Clicked Dismiss button")
                        await asyncio.sleep(1)
                    return None
            
            question_answers = question_answers | qa
            count += 1
            
            # Try to find Next button
            next_btn = await self.page.find(CSS_SELECTORS["form_elements"]["next_button"])
            if next_btn:
                await next_btn.scroll_into_view()
                await next_btn.click()
                logger.info("Clicked Next button")
                self._update_status("fill_form", "Moving to next step...")
                await asyncio.sleep(1)
                
                # After clicking Next, check for upload resume button ONLY if not already uploaded
                if not self.resume_uploaded:
                    logger.debug("Checking for upload resume button...")
                    await self._handle_upload_resume_buttons()
                    await asyncio.sleep(1)
            else:
                # Try Review button
                review_btn = await self.page.find(CSS_SELECTORS["form_elements"]["review_button"])
                if review_btn:
                    await review_btn.scroll_into_view()
                    await review_btn.click()
                    logger.info("Clicked Review button")
                    self._update_status("fill_form", "Reviewing application...")
                    await asyncio.sleep(1)
                else:
                    # Try Submit button
                    submit_btn = await self.page.find(CSS_SELECTORS["form_elements"]["submit_button"])
                    if submit_btn:
                        await submit_btn.scroll_into_view()
                        await submit_btn.click()
                        logger.info("Clicked Submit button")
                        self._update_status("fill_form", "Application submitted!")
                        await asyncio.sleep(4)
                    
                    dismiss_btn = await self.page.query_selector(CSS_SELECTORS["form_elements"]["dismiss_button"])
                    if dismiss_btn:
                        await dismiss_btn.click()
                        logger.info("Clicked Dismiss button")
                    
                    break
                
                logger.info("No Next button found, assuming end of form")
                break
        
        return question_answers
    
    async def apply_to_job(self):
        """Main application flow"""
        logger.info("=" * 60)
        logger.info("Starting LinkedIn Easy Apply Automation")
        logger.info("=" * 60)
        
        try:
            easy_apply_btn = await self.find_easy_apply_button()
            if not easy_apply_btn:
                self._update_status("error", "Easy Apply button not found")
                return False
            
            if not await self.click_easy_apply_button(easy_apply_btn):
                self._update_status("error", "Failed to click Easy Apply button")
                return False
            
            await asyncio.sleep(2)
            
            logger.info("Processing form...")
            result = await self.loop_through_form()
            
            if result is None:
                logger.warning("Form processing cancelled")
                self._update_status("error", "Form processing cancelled")
                return False
            
            logger.info("Application submitted successfully!")
            self._update_status("success", "Application submitted successfully!")
            return True
        
        except Exception as e:
            logger.error(f"Error during application: {e}", exc_info=True)
            self._update_status("error", f"Error: {str(e)}")
            return False
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            try:
                self.browser.stop()
                logger.info("Browser closed")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
    
    async def run(self, job_url: str, pause_seconds: int = 60):
        """
        Main entry point - run the complete autofill process
        
        Args:
            job_url: LinkedIn job posting URL
            pause_seconds: Seconds to keep browser open after completion
        """
        try:
            await self.setup_browser()
            await self.navigate_to_job(job_url)
            await self.wait_for_manual_login()
            success = await self.apply_to_job()
            
            if success:
                self._update_status("pausing", f"Keeping browser open for {pause_seconds} seconds for inspection...")
                logger.info(f"Pausing for {pause_seconds} seconds for inspection...")
                for i in range(pause_seconds, 0, -10):
                    if i <= 10:
                        logger.debug(f"Closing in {i} seconds...")
                    await asyncio.sleep(min(10, i))
            else:
                logger.info("Application failed, pausing for 30 seconds...")
                await asyncio.sleep(30)
            
            return success
        
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            self._update_status("error", f"Fatal error: {str(e)}")
            return False
        
        finally:
            await self.close()
