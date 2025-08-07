import streamlit as st
import requests
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import google.generativeai as genai
from datetime import datetime
import re
from urllib.parse import urlparse
import os
import subprocess
import sys
import platform
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Function to install system dependencies for headless servers
def install_system_dependencies():
    """Install Chromium and dependencies for headless servers"""
    try:
        system = platform.system().lower()
        
        if system == "linux":
            st.info("🔧 Installing Chromium dependencies for headless server...")
            
            # Update package list and install chromium
            commands = [
                "apt-get update -y",
                "apt-get install -y chromium-browser chromium-chromedriver",
                "apt-get install -y fonts-liberation libasound2 libatk-bridge2.0-0 libdrm2 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libxss1 libnss3"
            ]
            
            for cmd in commands:
                try:
                    result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=300)
                    if result.returncode != 0:
                        st.warning(f"Command failed: {cmd}")
                        st.warning(f"Error: {result.stderr}")
                except subprocess.TimeoutExpired:
                    st.warning(f"Command timed out: {cmd}")
                except Exception as e:
                    st.warning(f"Error running command {cmd}: {str(e)}")
            
            st.success("✅ System dependencies installed successfully!")
            return True
            
        else:
            st.info("🖥️ Non-Linux system detected. Assuming Chrome/Chromium is available.")
            return True
            
    except Exception as e:
        st.error(f"Failed to install system dependencies: {str(e)}")
        return False

# Install dependencies on first run
if 'dependencies_installed' not in st.session_state:
    st.session_state.dependencies_installed = install_system_dependencies()

# Page configuration
st.set_page_config(
    page_title="HR Policy Generator",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .step-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2e8b57;
        margin: 1rem 0;
        padding: 0.5rem;
        border-left: 4px solid #2e8b57;
        background-color: #f0f8f5;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #e7f3ff;
        border: 1px solid #b3d9ff;
        margin: 1rem 0;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        margin: 1rem 0;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class HRPolicyGenerator:
    def __init__(self):
        # Load API keys from environment variables
        self.tavily_api_key = os.getenv('TAVILY_API_KEY')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.driver = None
        
        # Check if API keys are available
        if not self.tavily_api_key:
            st.error("❌ TAVILY_API_KEY not found in .env file")
        if not self.gemini_api_key:
            st.error("❌ GEMINI_API_KEY not found in .env file")
        
    def setup_selenium(self):
        """Setup Selenium WebDriver with Chrome/Chromium options for headless servers"""
        try:
            chrome_options = Options()
            
            # Essential headless options
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--disable-features=TranslateUI")
            chrome_options.add_argument("--disable-ipc-flooding-protection")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--remote-debugging-port=9222")
            
            # User agent to avoid detection
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Additional options for headless servers
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")  # Faster loading
            chrome_options.add_argument("--disable-javascript")  # We only need text content
            
            # Try different approaches to find Chrome/Chromium
            chrome_paths = [
                "/usr/bin/chromium-browser",  # Ubuntu/Debian
                "/usr/bin/chromium",          # Some Linux distros
                "/usr/bin/google-chrome",     # Google Chrome on Linux
                "/usr/bin/chrome",            # Alternative
                "chromium-browser",           # System PATH
                "chromium",                   # System PATH
                "google-chrome",              # System PATH
            ]
            
            driver_paths = [
                "/usr/bin/chromedriver",      # System chromedriver
                "/usr/lib/chromium-browser/chromedriver",  # Ubuntu location
                "chromedriver",               # System PATH
            ]
            
            # Find available Chrome binary
            chrome_binary = None
            for path in chrome_paths:
                if os.path.isfile(path) or subprocess.run(['which', path], capture_output=True).returncode == 0:
                    chrome_binary = path
                    break
            
            if chrome_binary:
                chrome_options.binary_location = chrome_binary
                st.info(f"🌐 Using Chrome/Chromium at: {chrome_binary}")
            
            # Try to create WebDriver with different approaches
            driver_created = False
            
            # Approach 1: Try webdriver-manager (if available)
            if not driver_created:
                try:
                    from webdriver_manager.chrome import ChromeDriverManager
                    from webdriver_manager.core.utils import ChromeType
                    
                    # Try regular Chrome first, then Chromium
                    for chrome_type in [ChromeType.GOOGLE, ChromeType.CHROMIUM]:
                        try:
                            driver_path = ChromeDriverManager(chrome_type=chrome_type).install()
                            service = Service(driver_path)
                            self.driver = webdriver.Chrome(service=service, options=chrome_options)
                            driver_created = True
                            st.success(f"✅ WebDriver created using webdriver-manager with {chrome_type}")
                            break
                        except Exception as e:
                            continue
                            
                except ImportError:
                    pass
            
            # Approach 2: Try system chromedriver paths
            if not driver_created:
                for driver_path in driver_paths:
                    try:
                        if os.path.isfile(driver_path) or subprocess.run(['which', driver_path], capture_output=True).returncode == 0:
                            service = Service(driver_path)
                            self.driver = webdriver.Chrome(service=service, options=chrome_options)
                            driver_created = True
                            st.success(f"✅ WebDriver created using system chromedriver at: {driver_path}")
                            break
                    except Exception as e:
                        continue
            
            # Approach 3: Try default Chrome (let Selenium find it)
            if not driver_created:
                try:
                    self.driver = webdriver.Chrome(options=chrome_options)
                    driver_created = True
                    st.success("✅ WebDriver created using default Chrome")
                except Exception as e:
                    pass
            
            if not driver_created:
                raise Exception("Could not create WebDriver with any approach")
                
            # Test the driver
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            
            return True
            
        except Exception as e:
            error_msg = f"Failed to setup Selenium WebDriver: {str(e)}"
            st.error(error_msg)
            st.error("💡 **Troubleshooting:**")
            st.error("1. Make sure the system dependencies are installed")
            st.error("2. Try installing webdriver-manager: `pip install webdriver-manager`")
            st.error("3. For manual setup, install chromium-browser and chromium-chromedriver")
            return False
    
    def search_tavily(self, query, location):
        """Search using Tavily API for official policy sources"""
        if not self.tavily_api_key:
            st.error("Tavily API key not provided")
            return []
        
        # Enhanced query for official sources
        enhanced_query = f"{query} {location} official government policy law regulation site:gov OR site:legislation OR site:official"
        
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_api_key,
            "query": enhanced_query,
            "search_depth": "advanced",
            "include_answer": True,
            "include_raw_content": True,
            "max_results": 10,
            "include_domains": ["gov", "legislation", "official", "law"]
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json().get('results', [])
        except requests.exceptions.RequestException as e:
            st.error(f"Tavily search failed: {str(e)}")
            return []
    
    def extract_content_selenium(self, url, max_chars=5000):
        """Extract content from URL using Selenium"""
        if not self.driver:
            if not self.setup_selenium():
                return ""
        
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Remove unwanted elements
            unwanted_tags = ['script', 'style', 'nav', 'header', 'footer', 'aside']
            for tag in unwanted_tags:
                elements = self.driver.find_elements(By.TAG_NAME, tag)
                for element in elements:
                    self.driver.execute_script("arguments[0].remove();", element)
            
            # Extract main content
            content_selectors = [
                'main', 'article', '.content', '.main-content', 
                '#content', '#main', '.policy-content', '.legal-content'
            ]
            
            content = ""
            for selector in content_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        content = elements[0].get_attribute('textContent')
                        break
                except:
                    continue
            
            if not content:
                content = self.driver.find_element(By.TAG_NAME, "body").get_attribute('textContent')
            
            # Clean and limit content
            content = re.sub(r'\s+', ' ', content).strip()
            return content[:max_chars] if len(content) > max_chars else content
            
        except Exception as e:
            st.warning(f"Could not extract content from {url}: {str(e)}")
            return ""
    
    def generate_policy_with_gemini(self, policy_type, location, extracted_data):
        """Generate policy using Gemini AI"""
        if not self.gemini_api_key:
            st.error("Gemini API key not provided")
            return ""
        
        try:
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            prompt = f"""
            As an expert HR policy consultant, create a comprehensive {policy_type} policy for {location}.
            
            Use the following official legal and regulatory information as your primary source:
            
            {extracted_data}
            
            Requirements:
            1. Create a professional, legally compliant {policy_type} policy
            2. Include all mandatory requirements specific to {location}
            3. Structure the policy with clear sections and subsections
            4. Include purpose, scope, definitions, procedures, and compliance requirements
            5. Add relevant legal references and citations where applicable
            6. Ensure the language is clear, professional, and actionable
            7. Include effective date and review requirements
            8. Add any location-specific cultural or legal considerations
            
            Format the policy as a complete, ready-to-implement document with:
            - Policy title and version
            - Effective date
            - Table of contents
            - All required sections
            - Appendices if needed
            
            Make sure the policy is current as of {datetime.now().strftime('%B %Y')} and complies with the latest regulations.
            """
            
            response = model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            st.error(f"Failed to generate policy with Gemini: {str(e)}")
            return ""
    
    def cleanup(self):
        """Cleanup resources"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

# Initialize session state
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'policy_type' not in st.session_state:
    st.session_state.policy_type = ""
if 'location' not in st.session_state:
    st.session_state.location = ""
if 'generated_policy' not in st.session_state:
    st.session_state.generated_policy = ""

# Main app
def main():
    st.markdown('<h1 class="main-header">🏢 HR Policy Generator</h1>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Generate country-specific HR policies using AI and official government sources</div>', unsafe_allow_html=True)
    
    # Sidebar for API status and info
    with st.sidebar:
        st.header("🔑 API Status")
        
        # Check API key status
        tavily_status = "✅ Connected" if os.getenv('TAVILY_API_KEY') else "❌ Missing"
        gemini_status = "✅ Connected" if os.getenv('GEMINI_API_KEY') else "❌ Missing"
        
        st.write(f"**Tavily API:** {tavily_status}")
        st.write(f"**Gemini API:** {gemini_status}")
        
        if not os.getenv('TAVILY_API_KEY') or not os.getenv('GEMINI_API_KEY'):
            st.error("⚠️ Create a .env file with:\n```\nTAVILY_API_KEY=your_key_here\nGEMINI_API_KEY=your_key_here\n```")
        
        st.header("📋 Progress")
        step_status = ["❌", "❌", "❌", "❌"]
        if st.session_state.step > 1:
            step_status[0] = "✅"
        if st.session_state.step > 2:
            step_status[1] = "✅"
        if st.session_state.step > 3:
            step_status[2] = "✅"
        if st.session_state.step > 4:
            step_status[3] = "✅"
            
        st.write(f"{step_status[0]} Step 1: Select Policy Type")
        st.write(f"{step_status[1]} Step 2: Choose Location")
        st.write(f"{step_status[2]} Step 3: Research & Extract")
        st.write(f"{step_status[3]} Step 4: Generate Policy")
    
    # Step 1: Policy Type Selection
    if st.session_state.step == 1:
        st.markdown('<div class="step-header">Step 1: Select Policy Type</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            policy_categories = {
                "Employment Policies": [
                    "Employment Contract Policy",
                    "Recruitment and Selection Policy",
                    "Probationary Period Policy",
                    "Termination and Dismissal Policy"
                ],
                "Workplace Policies": [
                    "Anti-Harassment and Discrimination Policy",
                    "Health and Safety Policy",
                    "Remote Work Policy",
                    "Workplace Conduct Policy"
                ],
                "Leave and Benefits": [
                    "Annual Leave Policy",
                    "Sick Leave Policy",
                    "Maternity/Paternity Leave Policy",
                    "Bereavement Leave Policy"
                ],
                "Compensation": [
                    "Salary and Wage Policy",
                    "Overtime Policy",
                    "Performance Bonus Policy",
                    "Expense Reimbursement Policy"
                ],
                "Data and Privacy": [
                    "Employee Privacy Policy",
                    "Data Protection Policy",
                    "Confidentiality Policy",
                    "Social Media Policy"
                ]
            }
            
            selected_category = st.selectbox("Select Policy Category", list(policy_categories.keys()))
            selected_policy = st.selectbox("Select Specific Policy", policy_categories[selected_category])
            
            # Custom policy option
            st.write("Or enter a custom policy type:")
            custom_policy = st.text_input("Custom Policy Type")
            
            final_policy = custom_policy if custom_policy else selected_policy
            
        with col2:
            st.info("💡 **Tips:**\n- Choose policies that are most critical for your organization\n- Consider local legal requirements\n- Start with employment basics if unsure")
        
        if st.button("Continue to Location Selection", type="primary"):
            if final_policy:
                st.session_state.policy_type = final_policy
                st.session_state.step = 2
                st.rerun()
            else:
                st.error("Please select or enter a policy type")
    
    # Step 2: Location Selection
    elif st.session_state.step == 2:
        st.markdown('<div class="step-header">Step 2: Choose Location</div>', unsafe_allow_html=True)
        st.info(f"**Selected Policy:** {st.session_state.policy_type}")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            # Country selection with popular options
            popular_countries = [
                "United States", "United Kingdom", "Canada", "Australia", 
                "Germany", "France", "Netherlands", "Singapore", "India", "South Africa"
            ]
            
            location_type = st.radio("Choose location type:", ["Popular Countries", "Custom Location"])
            
            if location_type == "Popular Countries":
                location = st.selectbox("Select Country", popular_countries)
            else:
                location = st.text_input("Enter Country/Region", placeholder="e.g., New Zealand, European Union, etc.")
            
            # Optional: State/Province for countries with federal systems
            if location in ["United States", "Canada", "Australia", "India"]:
                state_province = st.text_input(f"State/Province (optional)", placeholder="e.g., California, Ontario, etc.")
                if state_province:
                    location = f"{state_province}, {location}"
        
        with col2:
            st.warning("⚠️ **Important:**\n- Ensure you have the right to generate policies for this location\n- Local legal review is recommended\n- Consider consulting local employment lawyers")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back to Policy Selection"):
                st.session_state.step = 1
                st.rerun()
        
        with col2:
            if st.button("Start Research & Generation", type="primary"):
                if location:
                    st.session_state.location = location
                    st.session_state.step = 3
                    st.rerun()
                else:
                    st.error("Please select or enter a location")
    
    # Step 3: Research and Extraction
    elif st.session_state.step == 3:
        st.markdown('<div class="step-header">Step 3: Research & Extract Legal Information</div>', unsafe_allow_html=True)
        st.info(f"**Policy:** {st.session_state.policy_type} | **Location:** {st.session_state.location}")
        
        # Check API keys from environment
        if not os.getenv('TAVILY_API_KEY') or not os.getenv('GEMINI_API_KEY'):
            st.error("⚠️ Missing API keys. Please check your .env file contains both TAVILY_API_KEY and GEMINI_API_KEY")
            return
        
        # Initialize the generator
        generator = HRPolicyGenerator()
        
        if st.button("🔍 Start Research Process", type="primary"):
            try:
                with st.spinner("🔍 Searching for official policy sources..."):
                    search_results = generator.search_tavily(st.session_state.policy_type, st.session_state.location)
                
                if not search_results:
                    st.error("No official sources found. Please try different search terms or location.")
                    return
                
                st.success(f"Found {len(search_results)} official sources")
                
                # Display found sources
                with st.expander("📋 Found Sources", expanded=True):
                    for i, result in enumerate(search_results[:5]):  # Show top 5
                        st.write(f"**{i+1}. {result.get('title', 'N/A')}**")
                        st.write(f"URL: {result.get('url', 'N/A')}")
                        st.write(f"Score: {result.get('score', 'N/A')}")
                        st.write("---")
                
                # Extract content from sources
                all_extracted_data = ""
                successful_extractions = 0
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, result in enumerate(search_results[:5]):  # Process top 5 sources
                    url = result.get('url', '')
                    if url:
                        status_text.text(f"Extracting from source {i+1}/5: {urlparse(url).netloc}")
                        
                        content = generator.extract_content_selenium(url)
                        if content:
                            all_extracted_data += f"\n\n--- SOURCE: {result.get('title', 'Unknown')} ({url}) ---\n{content}"
                            successful_extractions += 1
                        
                        progress_bar.progress((i + 1) / 5)
                        time.sleep(1)  # Rate limiting
                
                status_text.empty()
                progress_bar.empty()
                
                if successful_extractions == 0:
                    st.error("Could not extract content from any sources. Please try again or check your internet connection.")
                    return
                
                st.success(f"Successfully extracted data from {successful_extractions} sources")
                
                # Generate policy
                with st.spinner("🤖 Generating policy with AI..."):
                    generated_policy = generator.generate_policy_with_gemini(
                        st.session_state.policy_type,
                        st.session_state.location,
                        all_extracted_data
                    )
                
                if generated_policy:
                    st.session_state.generated_policy = generated_policy
                    st.session_state.step = 4
                    st.success("Policy generated successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to generate policy. Please try again.")
                
            except Exception as e:
                st.error(f"An error occurred during the research process: {str(e)}")
            finally:
                generator.cleanup()
        
        if st.button("← Back to Location Selection"):
            st.session_state.step = 2
            st.rerun()
    
    # Step 4: Display Generated Policy
    elif st.session_state.step == 4:
        st.markdown('<div class="step-header">Step 4: Generated Policy</div>', unsafe_allow_html=True)
        st.success("✅ Policy successfully generated!")
        
        # Policy metadata
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Policy Type", st.session_state.policy_type)
        with col2:
            st.metric("Location", st.session_state.location)
        with col3:
            st.metric("Generated", datetime.now().strftime("%Y-%m-%d"))
        
        # Display the policy
        st.markdown("### 📋 Generated Policy Document")
        
        # Policy content in expandable section
        with st.expander("📄 Full Policy Document", expanded=True):
            st.markdown(st.session_state.generated_policy)
        
        # Download options
        st.markdown("### 💾 Download Options")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.download_button(
                label="📄 Download as Text",
                data=st.session_state.generated_policy,
                file_name=f"{st.session_state.policy_type}_{st.session_state.location.replace(', ', '_')}_policy.txt",
                mime="text/plain"
            )
        
        with col2:
            # Convert to markdown format
            markdown_content = f"# {st.session_state.policy_type}\n\n**Location:** {st.session_state.location}\n\n**Generated:** {datetime.now().strftime('%Y-%m-%d')}\n\n---\n\n{st.session_state.generated_policy}"
            st.download_button(
                label="📝 Download as Markdown",
                data=markdown_content,
                file_name=f"{st.session_state.policy_type}_{st.session_state.location.replace(', ', '_')}_policy.md",
                mime="text/markdown"
            )
        
        # Action buttons
        st.markdown("### 🔄 Next Steps")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🆕 Generate New Policy", type="primary"):
                # Reset session state
                for key in ['step', 'policy_type', 'location', 'generated_policy']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        
        with col2:
            if st.button("📝 Modify Current Policy"):
                st.session_state.step = 3  # Go back to research step
                st.rerun()
        
        with col3:
            if st.button("📧 Get Implementation Help"):
                st.info("💡 **Implementation Tips:**\n- Review with legal counsel\n- Customize for your organization\n- Train managers on new policies\n- Set up review schedules\n- Communicate changes to employees")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8rem;'>
        ⚠️ <strong>Disclaimer:</strong> This tool generates draft policies for reference only. 
        Always consult with qualified legal professionals before implementing any HR policies.
        Policies should be reviewed and customized for your specific organizational needs and local regulations.
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()